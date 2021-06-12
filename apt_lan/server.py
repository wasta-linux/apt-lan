''' System functions '''

import logging
import os
import psutil
import subprocess

from pathlib import Path


def get_userid():
    return os.getuid()

def ensure_smb_setup(file, share_path):
    '''
    Ensure proper samba share file and contents.
    '''
    home = get_home()
    userid = get_userid()
    file = Path(file)
    f'''
    #VERSION 2
    path={share_path}
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

def ensure_rsyncd_setup(port, share_path, loglevel):
    """
    Ensure proper setup of rsyncd server and share.
    """
    # Ensure rsyncd is running.
    connections = psutil.net_connections()
    rsyncd = False
    for c in connections:
        if c.laddr.port == port:
            logging.debug(f"rsyncd: {c}")
            logging.info(f"rsyncd already running on port {c.laddr.port} with PID {c.pid}")
            rsyncd = True
            break
    if not rsyncd:
        cmd = ['pkexec', 'systemctl', 'enable', '--now', 'apt-lan-rsyncd.service']
        if loglevel == logging.DEBUG:
            # cmd.append('debug')
            pass
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if r.returncode == 0:
            logging.info(f"Started rsyncd with PID {r.pid}")
        else:
            logging.error(f"Failed to start apt-lan-rsyncd.service.")
