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

def ensure_ftp_setup(port, share_path):
    """
    Ensure proper setup of FTP server and share.
    """
    share_path.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).parents[0] / 'serve-ftp.py'
    # Only start the server if the given port is closed.
    connections = psutil.net_connections()
    wasta_ftp = False
    for c in connections:
        if c.laddr.port == port:
            logging.debug(f"FTP check: {c}")
            wasta_ftp = True
            break
    if not wasta_ftp:
        ftp_proc = subprocess.Popen(
            [script, share_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        logging.debug(f"Started FTP server: {ftp_proc}")
