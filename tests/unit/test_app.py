import sys
import unittest
#from pathlib import Path

from apt_lan import app

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class AppObj(unittest.TestCase):
    def setUp(self):
        self.obj = app.App()
        self.obj.runmode = 'test'

    def test_apply_option(self):
        sys.argv = ['', '--apply']
        self.obj.run(sys.argv)
        self.assertTrue(self.obj.args.apply)

    def tearDown(self):
        pass
