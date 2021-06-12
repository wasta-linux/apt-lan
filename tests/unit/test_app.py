import sys
import unittest
#from pathlib import Path

from apt_lan import app, utils

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class Gen(unittest.TestCase):
    def setUp(self):
        self.obj = app.App()
        self.obj.runmode = 'test'

    def test_root(self):
        self.assertFalse(utils.check_if_root(self.obj))

    def tearDown(self):
        pass

class Opts(unittest.TestCase):
    def setUp(self):
        self.obj = app.App()
        self.obj.runmode = 'test'

    def test_apply_option(self):
        sys.argv = ['', '--apply']
        self.obj.run(sys.argv)
        self.assertTrue(self.obj.args.apply)

    def tearDown(self):
        pass
