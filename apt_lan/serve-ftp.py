#!/usr/bin/env python3

import sys

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.servers import MultiprocessFTPServer

share_path = sys.argv[1]
authorizer = DummyAuthorizer()
authorizer.add_anonymous(share_path, perm="elr")
handler = FTPHandler
handler.authorizer = authorizer
# server = FTPServer(("127.0.0.1", 21021), handler)
server = MultiprocessFTPServer(("", 21021), handler)
server.serve_forever()
