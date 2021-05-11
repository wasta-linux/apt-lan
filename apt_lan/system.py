''' System functions '''

import logging
import os

from pathlib import Path


def get_home():
    return Path(os.environ['HOME'])

def get_hostname():
    return os.uname().nodename

def get_userid():
    return os.getuid()

def get_os_release():
    release = ''
    with open('/etc/os-release', 'r') as f:
        for line in f.readlines():
            if 'VERSION_CODENAME' in line:
                release = line.split('=')[1].strip()
    if not release:
        print("ERROR: release not found.")
        exit(1)
    return release

def ensure_smb_setup(file):
    '''
    Ensure proper samba share file and contents.
    '''
    home = get_home()
    userid = get_userid()
    file = Path(file)
    '''
    #VERSION 2
    path=/home/nate/.apt-lan/local-cache
    comment=Software updates over the LAN
    usershare_acl=S-1-1-0:R,S-1-22-1-1000:F # <- is that the user number?
    guest_ok=y
    sharename=apt-lan
    '''
    version = "#VERSION 2"
    path = f"path={home}/.apt-lan/local-cache"
    comment = "comment=Software updates over the LAN"
    acl = f"usershare_acl=S-1-1-0:R,S-1-22-1-{userid}:F"
    guest = "guest_ok=y"
    name = "sharename=apt-lan"
    end = '\n'
    parts = [version, path, comment, acl, guest, name, end]
    contents = '\n'.join(parts)
    file.write_text(contents)
    logging.debug(f"smb config written to {str(file)}")
