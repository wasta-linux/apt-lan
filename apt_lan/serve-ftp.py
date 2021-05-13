#!/usr/bin/env python3

import logging
import sys

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.servers import MultiprocessFTPServer


args = sys.argv

# Setup logging.
loglevel = logging.INFO
if 'debug' in args:
    loglevel = logging.DEBUG
    args.remove('debug')
logging.basicConfig(filename='/var/log/pyftpd.log', level=loglevel)

# Define share path.
share_path = sys.argv[1]

# Start server.
authorizer = DummyAuthorizer()
authorizer.add_anonymous(share_path, perm="elr")
handler = FTPHandler
handler.authorizer = authorizer
# server = FTPServer(("127.0.0.1", 21021), handler)
server = MultiprocessFTPServer(("", 21021), handler)
server.serve_forever()
