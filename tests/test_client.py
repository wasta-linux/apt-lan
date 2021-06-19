import psutil
import subprocess
import tempfile
import unittest

from pathlib import Path

from apt_lan import client

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class Basic(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass
