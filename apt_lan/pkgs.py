''' Functions related to debian package manipulation '''

import re
import shutil
import subprocess

from pathlib import Path


def get_good_repos():
    # TODO: Store this list in a file for easier updating.
    good_repos = [
        'http://archive.ubuntu.com/ubuntu focal main',
        'http://archive.ubuntu.com/ubuntu focal-updates main',
        'http://archive.ubuntu.com/ubuntu focal universe',
        'http://archive.ubuntu.com/ubuntu focal-updates universe',
        'http://archive.ubuntu.com/ubuntu focal multiverse',
        'http://archive.ubuntu.com/ubuntu focal-updates multiverse',
        'http://archive.ubuntu.com/ubuntu focal-backports main universe multiverse',
        'http://archive.canonical.com/ubuntu focal partner',
        'http://archive.ubuntu.com/ubuntu focal-security main',
        'http://archive.ubuntu.com/ubuntu focal-security universe',
        'http://archive.ubuntu.com/ubuntu focal-security multiverse',
        'http://ppa.launchpad.net/keymanapp/keyman/ubuntu focal main',
        'http://packages.sil.org/ubuntu focal main',
        'https://repo.skype.com/deb stable main',
        'http://ppa.launchpad.net/wasta-linux/cinnamon-4-6/ubuntu focal main',
        'http://ppa.launchpad.net/wasta-linux/wasta-apps/ubuntu focal main',
        'http://ppa.launchpad.net/wasta-linux/wasta/ubuntu focal main',
        'http://ppa.launchpad.net/wasta-linux/wasta-wine/ubuntu focal main',
    ]
    return good_repos

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
    # List APT archive files.
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

def list_good_debs():
    repos = get_good_repos()
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