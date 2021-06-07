''' Main command line processing '''

import logging
import os
import shutil
import subprocess
import tempfile

from pathlib import Path

from apt_lan import client, server, pkgs, utils


def run_server_sync(app):
    # share_config = Path(f"/var/lib/samba/usershares/{app.pkg_name}")

    # Ensure that file share is properly configured.
    app.share_path.mkdir(parents=True, exist_ok=True)
    # server.ensure_ftp_setup(app.ports[0], app.share_path, app.loglevel)
    server.ensure_rsyncd_setup(app.ports[0], app.share_path, app.loglevel)

    # Create a list of approved debs to copy from archives to local-cache:
    system_debs = pkgs.list_archive_debs(app.deb_archives.get('system'))
    logging.debug(f"System debs count: {len(system_debs)}")
    logging.debug(f"System debs: {', '.join(system_debs)}")
    good_debs = pkgs.list_good_debs()
    logging.debug(f"Good debs count: {len(good_debs)}")
    approved_debs = pkgs.list_approved_debs(system_debs, good_debs)
    logging.debug(f"Approved debs count: {len(approved_debs)}")
    logging.debug(f"Approved debs: {', '.join(approved_debs)}")

    # Copy debs in the approved list to lan_archive if adequate space.
    dest_dir = app.deb_archives.get('lan')
    dest_stats = pkgs.ensure_destination(dest_dir)
    logging.debug(f"LAN archive path: {dest_dir}")

    # List debs already in lan_archive and determine free space there.
    dest_debs = dest_stats.get('Packages')
    dest_bytes_free = dest_stats.get('Free Space')
    dest_free_human = utils.convert_bytes_to_human(dest_bytes_free)
    logging.debug(f"LAN archive space: {dest_free_human.get('Number'):5.1f} {dest_free_human.get('Unit')}")
    logging.debug(f"LAN archive package count: {len(dest_debs)}")
    logging.debug(f"LAN archive packages: {', '.join(dest_debs)}")

    # Remove debs already in destination from copy list.
    debs_to_copy = pkgs.list_debs_to_copy(approved_debs, dest_debs)
    # Get list of debs from superseded_debs_file.
    superseded_debs_file = dest_dir / 'superseded.txt'
    superseded_debs = []
    if superseded_debs_file.is_file():
        superseded_debs = pkgs.get_superseded_debs(superseded_debs_file)
    else:
        # Create empty file to be populated later.
        superseded_debs_file.touch()
    # Remove debs in "superseded_debs" list from copy list.
    for deb in debs_to_copy[:]:
        if deb in superseded_debs:
            debs_to_copy.remove(deb)

    logging.debug(f"Packages to copy count: {len(debs_to_copy)}")
    if len(debs_to_copy) == 0:
        # Already up-to-date. Nothing more to do.
        logging.info('Server packages already synced.\n')
        return 0

    logging.debug(f"Packages to copy: {', '.join(debs_to_copy)}")

    copy_bytes = 0
    for deb in debs_to_copy:
        file = Path(app.deb_archives.get('system') / deb)
        deb_bytes = file.stat().st_size
        copy_bytes += deb_bytes
    copy_size_human = utils.convert_bytes_to_human(copy_bytes)

    # Ensure free space at destination.
    ch = copy_size_human
    dh = dest_free_human
    # Ensure at least 100 MB of space left after copy.
    if dest_bytes_free - 100000000 < copy_bytes:
        logging.error(f"{ch.get('Number'):5.1f} {ch.get('Unit')} to copy, but only {dh.get('Number'):5.1f} {dh.get('Unit')} available in {dest_dir}")
        return 1

    # Log the copy details.
    ct = len(debs_to_copy)
    s = 's'
    if ct == 1:
        s = ''
    logging.info(f"Copying {ct} package{s}, {ch.get('Number'):5.1f} {ch.get('Unit')}, to {dest_dir}")

    # Copy debs.
    debs_copied = []
    for deb in debs_to_copy:
        if deb not in dest_debs:
            src_file = app.deb_archives.get('system') / deb
            copied = shutil.copy(src_file, dest_dir)
            debs_copied.append(copied)
    os.sync()

    # Delay the script if another sync is in progress.
    old_pkgs_gz = dest_dir / 'Packages.gz.old'
    utils.delay_if_other_sync_in_progress(old_pkgs_gz)
    # Rename Packages.gz file (if it exists) during file changes.
    pkgs_gz = dest_dir / 'Packages.gz'
    if pkgs_gz.is_file():
        pkgs_gz.rename(old_pkgs_gz)

    # Prepare to gather package lists.
    kept_debs = []                                                  # newest
    dest_debs = pkgs.ensure_destination(dest_dir).get('Packages')   # existing in destination

    # List amd64 packages to keep.
    logging.info("Listing amd64 packages to be kept...")
    cmd = ['dpkg-scanpackages', '--arch', 'amd64', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout.splitlines()
    logging.info(f"{len(output)} amd64 packages found.")
    for line in output:
        if 'Filename: ' in line:
            deb = line.split(':')[1].strip().split('/')[-1]
            kept_debs.append(deb)
            logging.debug(f"{deb} added to list of kept packages.")

    # List i386 packages to keep.
    logging.info("Listing i386 packages to be kept...")
    cmd = ['dpkg-scanpackages', '--arch', 'i386', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout.splitlines()
    logging.info(f"{len(output)} i386 packages found.")
    # Add scanned packages to kept_debs list.
    for line in output:
        if 'Filename: ' in line:
            deb = line.split(':')[1].strip().split('/')[-1]
            kept_debs.append(deb)
            logging.debug(f"{deb} added to list of kept packages.")

    # Remove non-kept packages.
    removed_debs = []
    kept_debs = list(set(kept_debs))
    kept_debs.sort()
    logging.debug(f"All kept packages: {', '.join(kept_debs)}")
    for deb in dest_debs:
        if deb not in kept_debs:
            superseded_debs.append(deb)
            removed_debs.append(deb)
            file = dest_dir / deb
            file.unlink()
            logging.debug(f"{file} removed from LAN cache.")
    superseded_debs.sort()

    # Update superseded_debs_file.
    with open(superseded_debs_file, 'w') as f:
        for deb in superseded_debs:
            f.write(f"{deb}\n")
    logging.debug(f"Superseded packages file: {superseded_debs_file}.")
    logging.info(f"{len(kept_debs)} packages in apt-lan cache. {len(superseded_debs)} others are listed as obsolete. {len(removed_debs)} were removed.")

    # Rebuild Packages.gz file.
    pkgs.rebuild_pkgs_gz(dest_dir, pkgs_gz, old_pkgs_gz)

    logging.info("System packages sync complete.\n")
    return 0

def run_client_sync(app):
    # Outline:
    #   - Find LAN sources. (assumes IPv4 for now)
    #   - Sync their packages locally.
    #       - only same release and arch
    #   - Rebuild local Packages.gz

    # Ensure that share folder exists.
    dest_dir = app.deb_archives.get('lan')
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Get current packages list.
    local_debs = pkgs.list_archive_debs(dest_dir)

    # Define Packages.gz file names.
    pkgs_gz = dest_dir / 'Packages.gz'
    old_pkgs_gz = dest_dir / 'Packages.gz.old'

    # Get LAN IP and subnet.
    own_ip, netmask = client.get_info()
    if not own_ip or not netmask:
        logging.error(f"LAN details not found; device: {device}, family: {conn_fam}, gateway: {conn_gw}")
        return 1

    # Loop through LAN IPs and copy debs from each one.
    #   - List LAN IPs with correct port open.
    share_ips = client.get_share_ips(own_ip, netmask, app.ports)
    logging.info(f"{len(share_ips)} LAN share IPs found.")
    logging.debug(f"LAN share IPs: {share_ips}")
    superseded_debs_file = dest_dir / 'superseded.txt'
    superseded_debs_file.touch(exist_ok=True)
    superseded_debs_own = pkgs.get_superseded_debs(superseded_debs_file)
    logging.debug(f"{len(superseded_debs_own)} superseded packages already identified.")
    for ip in share_ips:
        share_uri = f"ftp://{ip}/{app.os_rel}/{app.arch_d}"
        share_uri = f"rsync://{ip}/apt-lan/{app.os_rel}/{app.arch_d}"
        # Get file list from IP address.
        ip_files = client.get_files_from_share(share_uri, app.ports[0])
        logging.info(f"{len(ip_files)} files found at {ip} for {app.os_rel}/{app.arch_d}.")

        # Skip this server if another sync is in progress there.
        if 'Packages.gz.old' in ip_files:
            logging.info(f"Another sync is in progress at {ip}. Skipping.")
            return 1
        # Update superseded_debs list from LAN share.
        superseded_debs_ip = []
        if 'superseded.txt' in ip_files[:]:
            # Use tempdir because file will be downloaded to CWD.
            with Path(tempfile.mkdtemp()) as tempdir:
                client.get_files_from_share(share_uri, app.ports[0], ["superseded.txt"], tempdir)
                new_superseded = tempdir / 'superseded.txt'
                superseded_debs_ip = pkgs.get_superseded_debs(new_superseded)
            ip_files.remove('superseded.txt')
        for s in superseded_debs_ip:
            if s not in superseded_debs_own:
                superseded_debs_own.append(s)
        superseded_debs_own.sort()

        # Update superseded_debs_file.
        with open(superseded_debs_file, 'w') as f:
            for deb in superseded_debs_own:
                f.write(f"{deb}\n")
        logging.debug(f"Superseded packages file: {superseded_debs_file}.")

        # Rename Packages.gz file (if it exists) during file changes.
        if pkgs_gz.is_file():
            pkgs_gz.rename(old_pkgs_gz)

        # Get new packages from LAN share.
        debs_to_get = [d for d in ip_files if d[-4:] == '.deb' and d not in local_debs and d not in superseded_debs_own]
        logging.info(f"{len(debs_to_get)} packages to get from {ip}.")
        if len(debs_to_get) == 0:
            # Already up-to-date. Nothing more to do.
            logging.info(f'LAN packages already synced from {ip}.\n')
            return 0
        logging.debug(f"Packages to get from {ip}: {debs_to_get}")
        client.get_files_from_share(share_uri, app.ports[0], debs_to_get, dest_dir)

        # Rebuild Packages.gz file.
        pkgs.rebuild_pkgs_gz(dest_dir, pkgs_gz, old_pkgs_gz)

    # Ensure correct Packages.gz file.
    final_debs = pkgs.list_archive_debs(dest_dir)
    if final_debs != local_debs or not pkgs_gz.is_file():
        # Rebuild Packages.gz file.
        #   TODO: This rebuilds it unnecessarily if any packages were added above.
        #       But the point is to make sure the folder ends in an accurate
        #       state, regardless of how successful the sync was. Ideally, I
        #       would just confirm that Packages.gz matches the file list.
        pkgs.rebuild_pkgs_gz(dest_dir, pkgs_gz, old_pkgs_gz)

    logging.info("LAN packages sync complete.\n")
    return 0
