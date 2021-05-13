''' System functions '''

import logging
import os

from pathlib import Path
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


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

def ensure_ftp_setup(share_path):
    """
    Ensure proper setup of FTP server and share.
    """
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(share_path, perm="elr")
    handler = FTPHandler
    handler.authorizer = authorizer
    server = FTPServer(("127.0.0.1", 21021), handler)
    server.serve_forever()
