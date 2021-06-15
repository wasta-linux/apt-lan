''' Functions related to debian package manipulation '''

import gzip
import logging
import re
import shutil
import subprocess

from pathlib import Path


def get_dpkg_arches():
    arches = []
    cmd_native = ['dpkg', '--print-architecture']
    cmd_foreign = ['dpkg', '--print-foreign-architectures']
    res_native = subprocess.run(cmd_native, stdout=subprocess.PIPE, encoding='UTF-8')
    res_foreign = subprocess.run(cmd_foreign, stdout=subprocess.PIPE, encoding='UTF-8')
    native = res_native.stdout.splitlines()[0]
    foreigns = res_foreign.stdout.splitlines()
    arches.append(native)
    arches.extend(foreigns)
    return arches

def list_archive_debs(dir):
    """
    List APT archive files.
    """
    archive = Path(dir)
    files = list(archive.glob('*.deb'))
    debs = [d.name for d in files]
    debs.sort()
    return debs

def convert_repo_to_package_files(repo, dpkg_arches):
    """
    Example:
    IN:  'http://archive.ubuntu.com/ubuntu focal main'
    OUT: ['archive.ubuntu.com_ubuntu_dists_focal_main_binary-amd64_Packages',
         'archive.ubuntu.com_ubuntu_dists_focal_main_binary-i386_Packages']
    """
    pkg_files = []
    list_dir = Path('/var/lib/apt/lists')
    urlparts = repo.split('/')
    endparts = urlparts[-1].split()
    binaries = ['binary-' + arch for arch in dpkg_arches]

    for binary in binaries:
        url = '_'.join(urlparts[2:-1])
        file_parts = [
            url,
            endparts[0],
            'dists',
            endparts[1],
            endparts[2],
            binary,
            'Packages'
        ]
        pkg_files.append('_'.join(file_parts))
    return pkg_files

def list_good_debs(repos):
    """
    List packages provided by given repositories.
    """
    arches = get_dpkg_arches()
    approved_pkgs_list = []
    approved_lists = []
    parent_dir = Path('/var/lib/apt/lists')
    for repo in repos:
        approved_lists.extend(convert_repo_to_package_files(repo, arches))

    for l in approved_lists:
        file = parent_dir / l
        try:
            with open(file, 'r') as f:
                kwds = ['Package: ', 'Architecture: ', 'Version: ']
                package = ''
                version = ''
                arch = ''
                for line in f:
                    if package and version and arch:
                        version = version.replace(':', '%3a') # convert colons
                        debparts = [package, version, arch]
                        debfile = '_'.join(debparts) + '.deb'
                        approved_pkgs_list.append(debfile)
                        package = ''
                        version = ''
                        arch = ''

                    elif any(kwd in line for kwd in kwds):
                        lparts = re.split(':\s', line)
                        package = (lparts[1].strip() if lparts[0] == 'Package' else package)
                        arch = (lparts[1].strip() if lparts[0] == 'Architecture' else arch)
                        version = (lparts[1].strip() if lparts[0] == 'Version' else version)

        except FileNotFoundError:
            pass

    return approved_pkgs_list

def list_approved_debs(archive_debs, good_debs):
    approved_debs = [deb for deb in archive_debs if deb in good_debs]
    return approved_debs

def ensure_destination(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    dest_debs = list_archive_debs(dest)
    dest_bytes_free = shutil.disk_usage(dest).free
    return {'Packages': dest_debs, 'Free Space': dest_bytes_free}

def list_debs_to_copy(approved_debs, dest_debs):
    debs_to_copy = [d for d in approved_debs if d not in dest_debs]
    return debs_to_copy

def create_packages_gz(dest_dir):
    # Rebuild Packages.gz file.
    cmd = ['dpkg-scanpackages', '--multiversion', dest_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    output = result.stdout

    # Remove empty line and summary line from end of output.
    output_lines = output.splitlines()
    output = '\n'.join(output_lines[:-2])

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
        logging.debug(f"{pkg_gz} done.")
        ret = 0
    else:
        # Packages.0 file is zero size.
        logging.error(f"{pkg_file0} not populated. Check dpkg-scanpackages log output.")
        ret = 1
    pkg_file0.unlink(missing_ok=True)
    pkg_file.unlink(missing_ok=True)
    return ret

def get_superseded_debs(file):
    superseded_debs = []
    if file.is_file():
        # Get list from file.
        with open(file) as f:
            superseded_debs = f.readlines()
    return superseded_debs

def rebuild_pkgs_gz(dest_dir, pkgs_gz, old_pkgs_gz):
    # Rebuild Packages.gz file.
    logging.info(f"Creating Packages.gz file...")
    r = create_packages_gz(dest_dir)
    if r == 0:
        logging.info(f"Packages.gz file created.")
        old_pkgs_gz.unlink(missing_ok=True)
        logging.debug(f"Packages.gz.old removed.")
        ret = 0
    else:
        # Fall back if pkgs.create_packages_gz failed.
        logging.error(f"Packages.gz file creation failed. Falling back to previous version, if it exists.")
        if old_pkgs_gz.is_file():
            old_pkgs_gz.rename(pkgs_gz)
        ret = 1
    return ret
