''' Main command line processing '''

import gzip
import logging
import os

from pathlib import Path

from apt_lan import pkgs, system, utils


def create_packages_gz(dest_dir):
    # Rebuild Packages.gz file.
    cmd = ['dpkg-scanpackages', '--multiversion', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout
    pkg_file0 = dest_dir / 'Packages.0'
    pkg_file0.write_text(output)

    if pkg_file0.stat().st_size:
        # Packages.0 file is good.
        oldies = [dest_dir / 'Packages', dest_dir / 'Packages.gz']
        for oldie in oldies:
            oldie.unlink(missing_ok=True)
        pkg_file = dest_dir / 'Packages'
        pkg_file0.rename(pkg_file)
        pkg_gz = dest_dir / 'Packages.gz'
        pkg_gz.write_bytes(gzip.compress(pkg_file.read_bytes(), compresslevel=9))
        print(f"{pkg_gz} done.")
        ret = 0
    else:
        # Packages.0 file is bad.
        # TODO: Log this output.
        print("ERROR:  Probably a corrupt .deb file.")
        print("check dpkg-scanpackages log output.")
        print("Deleting Packages.0:")
        ret = 1
    pkg_file0.unlink(missing_ok=True)
    pkg_file.unlink(missing_ok=True)
    return ret

def run_system_sync(deb_archives):
    userid = system.get_userid()
    smb_share = Path('/var/lib/samba/usershares/apt-lan')
    # Ensure that samba share is properly configured.
    system.ensure_smb_setup(smb_share)
    # Create a list of approved debs to copy from archives to local-cache:
    system_debs = pkgs.list_archive_debs(deb_archives['system'])
    logging.info(f"System debs count: {len(system_debs)}")
    logging.debug(f"System debs: {', '.join(system_debs)}")
    good_debs = pkgs.list_good_debs()
    logging.debug(f"Good debs count: {len(good_debs)}")
    approved_debs = pkgs.list_approved_debs(system_debs, good_debs)
    logging.info(f"Approved debs count: {len(approved_debs)}")
    logging.debug(f"Approved debs: {', '.join(approved_debs)}")

    # Copy debs in the approved list to lan_archive if adequate space.
    # TODO: change this to initially copy to a "partial" sub-folder.
    dest_dir = deb_archives['lan']
    dest_stats = pkgs.ensure_destination(dest_dir)
    logging.info(f"LAN archive path: {dest_dir}")

    # List debs already in lan_archive and determine free space there.
    dest_debs = dest_stats['Packages']
    dest_bytes_free = dest_stats['Free Space']
    logging.info(f"LAN archive space: {dest_bytes_free} B")
    logging.info(f"LAN archive package count: {len(dest_debs)}")
    logging.debug(f"LAN archive packages: {', '.join(dest_debs)}")

    # Remove debs already in destination from copy list.
    debs_to_copy = pkgs.list_debs_to_copy(approved_debs, dest_debs)
    logging.info(f"Packages to copy count: {len(debs_to_copy)}")
    logging.debug(f"Packages to copy: {', '.join(debs_to_copy)}")
    copy_bytes = 0
    for deb in debs_to_copy:
        file = Path(deb_archives['system'] / deb)
        deb_bytes = file.stat().st_size
        copy_bytes += deb_bytes
    logging.debug(f"Bytes to copy: {copy_bytes} B")
    utils.test_exit()
    # TODO: Remove debs in "old_debs" list from copy list.

    copy_h = utils.convert_bytes_to_human(copy_bytes)
    dest_h = utils.convert_bytes_to_human(dest_bytes_free)
    if dest_bytes_free <= copy_bytes:
        # TODO: Log this error.
        print(f"Error: {copy_h['Number']:5.1f} {copy_h['Unit']} to copy, but only {dest_h['Number']:5.1f} {dest_h['Unit']} available in {dest_dir}")
        return 1

    ct = len(debs_to_copy)
    suffix = 's'
    if ct == 1:
        suffix = ''
    # TODO: Log this output.
    print(f"Copying {ct} package{suffix}, {copy_h['Number']:5.1f} {copy_h['Unit']}, to {dest_dir}")
    utils.test_exit()

    debs_copied = []
    for deb in debs_to_copy:
        if deb not in dest_debs:
            src_file = archive / deb
            copied = shutil.copy(src_file, dest_dir)
            debs_copied.append(copied)
    os.sync()

    # TODO: Remove Packages.gz file (if it exists) during file changes.
    #   This is the LAN "trigger" to know whether the cache is stable or not.

    # TODO: What do I do about blocking APT at this point? I don't want to resort
    #   to anything that requires elevated privileges. This would be the only
    #   they're needed.

    # TODO: Move files from "partial" sub-folder into true destination.

    # Remove superseded packages from local-cache.
    old_debs = []                                           # superseeded
    kept_debs = []                                          # newest
    dest_debs = ensure_destination(dest_dir)['Packages']    # existing in destination

    # List amd64 packages to keep.
    cmd = ['dpkg-scanpackages', '--arch', 'amd64', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout.splitlines()
    for line in output:
        if any(i in line for i in ['Filename: ']):
            kept_debs.append(line.split(':')[1].strip().split('/')[-1])

    # List i386 packages to keep.
    cmd = ['dpkg-scanpackages', '--arch', 'i386', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout.splitlines()
    for line in output:
        if any(i in line for i in ['Filename: ']):
            kept_debs.append(line.split(':')[1].strip().split('/')[-1])

    # Remove non-kept packages.
    kept_debs = list(set(kept_debs))
    for deb in dest_debs:
        if deb not in kept_debs:
            file = dest_dir / deb
            old_debs.append(file)
            file.unlink()

    # TODO: Make a list of "old_debs" that can be checked against in the future
    #   before adding a new package to the LAN repo.

    # TODO: Log this output.
    print(f"Kept {len(kept_debs)} packages, removed {len(old_debs)} obsolete ones")

    # Rebuild Packages.gz file.
    response = create_packages_gz(dest_dir)
    # TODO: What to do if create_packages_gz failed?

    # TODO: What do I do about unblocking APT at this point? I don't want to resort
    #   to anything that requires elevated privileges. This would be the only place
    #   they're needed.

    return 0

def run_lan_sync():
    # TODO: ignore any lan_cache that doesn't have Packages.gz file.
    #   This is the LAN "trigger" to know whether the cache is stable or not.
    pass
