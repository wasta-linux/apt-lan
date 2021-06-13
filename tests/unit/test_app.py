import sys
import unittest
#from pathlib import Path

from apt_lan import app

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class AppObj(unittest.TestCase):
    def setUp(self):
        self.orig_args = sys.argv[:]
        self.obj = app.App()
        self.obj.runmode = 'test'
        sys.argv = ['', '--apply']

    @unittest.skip("breaks later logging test")
    def test_apply_option(self):
        self.obj.run(sys.argv)
        self.assertTrue(self.obj.args.apply)

    def tearDown(self):
        sys.argv = self.orig_args
