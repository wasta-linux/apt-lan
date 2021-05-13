''' Main command line processing '''

import logging
import os
import shutil
import subprocess
import tempfile


from pathlib import Path

from apt_lan import client, server, pkgs, utils


def run_server_sync(app):
    ret = 8 # rough completion level

    share_config = Path(f"/var/lib/samba/usershares/{app.pkg_name}")
    # Ensure that samba share is properly configured.
    # server.ensure_smb_setup(share_config, app.share_path)
    server.ensure_ftp_setup(app.share_path)
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
    # TODO: change this to initially copy to a "partial" sub-folder.
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
    ret = 7

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
    logging.debug(f"Packages to copy: {', '.join(debs_to_copy)}")
    ret = 6

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
        return ret

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
    ret = 5

    # Delay the script if another sync is in progress.
    old_pkgs_gz = dest_dir / 'Packages.gz.old'
    utils.delay_if_other_sync_in_progress(old_pkgs_gz)
    # Rename Packages.gz file (if it exists) during file changes.
    pkgs_gz = dest_dir / 'Packages.gz'
    if pkgs_gz.is_file():
        pkgs_gz.rename(old_pkgs_gz)

    # TODO: What do I do about blocking APT at this point? I don't want to resort
    #   to anything that requires elevated privileges. This would be the only time
    #   they're needed.

    # TODO: Move files from "partial" sub-folder into true destination.

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
        # if any(i in line for i in ['Filename: ']):
        if 'Filename: ' in line:
            deb = line.split(':')[1].strip().split('/')[-1]
            kept_debs.append(deb)
            logging.debug(f"{deb} added to list of kept packages.")
    ret = 4

    # List i386 packages to keep.
    logging.info("Listing i386 packages to be kept...")
    cmd = ['dpkg-scanpackages', '--arch', 'i386', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout.splitlines()
    logging.info(f"{len(output)} i386 packages found.")
    # Add scanned packages to kept_debs list.
    for line in output:
        # if any(i in line for i in ['Filename: ']):
        if 'Filename: ' in line:
            deb = line.split(':')[1].strip().split('/')[-1]
            kept_debs.append(deb)
            logging.debug(f"{deb} added to list of kept packages.")
    ret = 3

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
    ret = 2

    # Update superseded_debs_file.
    with open(superseded_debs_file, 'w') as f:
        for deb in superseded_debs:
            f.write(f"{deb}\n")
    logging.debug(f"Superseded packages file: {superseded_debs_file}.")
    logging.info(f"{len(kept_debs)} packages in apt-lan cache. {len(superseded_debs)} others are listed as obsolete. {len(removed_debs)} were removed.")
    ret = 1

    # Rebuild Packages.gz file.
    logging.info(f"Creating Packages.gz file...")
    response = pkgs.create_packages_gz(dest_dir)
    if response == 0:
        logging.info(f"Packages.gz file created.")
        old_pkgs_gz.unlink(missing_ok=True)
        logging.debug(f"Packages.gz.old removed.")
        ret = 0
    else:
        # TODO: What to do if pkgs.create_packages_gz failed?
        logging.error(f"Packages.gz file creation failed. Falling back to previous version, if it exists.")
        if old_pkgs_gz.is_file():
            old_pkgs_gz.rename(pkgs_gz)

    # TODO: What do I do about unblocking APT at this point? I don't want to resort
    #   to anything that requires elevated privileges. This would be the only place
    #   they're needed.
    logging.info("System packages sync complete.\n")

    return ret

def run_client_sync(app):
    ret = 9
    # Outline:
    #   - Find LAN sources. (assumes a /24 IPv4 subnet for now)
    #   - Sync their packages locally.
    #       - only same release and arch
    #   - Rebuild local Packages.gz

    dest_dir = app.deb_archives.get('lan')
    local_debs = pkgs.list_archive_debs(dest_dir)

    # Find LAN sources.
    #   - Discover LAN IPs and subnet.
    own_ip, netmask = client.get_info()
    if not own_ip or not netmask:
        logging.error(f"LAN details not found; device: {device}, family: {conn_fam}, gateway: {conn_gw}")
        return ret

    # Loop through IPs and copy debs from each one.
    #   - List LAN IPs with samba shares.
    #   - Search IPs for shares called "apt-lan"
    ports = [139, 445] # SMB
    ports = [21021] # Wasta FTP
    lan_ips = client.get_lan_ips(own_ip, netmask, ports)
    logging.info(f"{len(lan_ips)} LAN samba IPs found.")
    logging.debug(f"LAN samba IPs: {lan_ips}")
    superseded_debs_own = pkgs.get_superseded_debs(dest_dir / 'superseded.txt')
    logging.debug(f"{len(superseded_debs_own)} superseded packages already identified.")
    for ip in lan_ips:
        # share_uri = f"smb://{ip}/apt-lan/{app.os_rel}/{app.arch_d}"
        share_uri = f"ftp://{ip}/local-cache/{app.os_rel}/{app.arch_d}"
        # Get file list from IP address.
        # ip_files = client.get_file_list_from_share(share_uri, ports[0])
        ip_files = client.get_files_from_share(share_uri, ports[0])
        logging.debug(f"{len(ip_files)} files found at {ip} for {app.os_rel}, {app.arch_d}.")

        # Update superseded_debs list from LAN share.
        if 'superseded.txt' in ip_files[:]:
            # Use tempdir because smbget file is downloaded to CWD.
            with Path(tempfile.mkdtemp()) as tempdir:
                client.get_files_from_share(share_uri, ports[0], ["superseded.txt"], tempdir)
                new_superseded = tempdir / 'superseded.txt'
                superseded_debs_ip = pkgs.get_superseded_debs(new_superseded)
            ip_files.remove('superseded.txt')
        for s in superseded_debs_ip:
            if s not in superseded_debs_own:
                superseded_debs_own.append(s)
        superseded_debs_own.sort()

        # Get new packages from LAN share.
        debs_to_get = [d for d in ip_files if d not in local_debs and d not in superseded_debs_own]
        logging.debug(f"Packages to get from {ip}: {debs_to_get}")
        client.get_files_from_share(share_uri, debs_to_get, dest_dir)

    # Take local share off the network while rebuilding cache.

    # Remove obsolete packages.

    # Rebuild Packages.gz

    # Put local share back on the network.

    logging.info("LAN packages sync complete.\n")
    return ret
