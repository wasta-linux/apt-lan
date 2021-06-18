"""
This test module has to go first so that logging setup is testing before any
other calls to the logging module.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from apt_lan import app, utils

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class Basic(unittest.TestCase):
    def setUp(self):
        pass

    def test_root(self):
        self.assertFalse(utils.check_if_root())

    def test_convert_bytes_to_human(self):
        bytes = [
            0,
            1024,
            1025,
            102389,
            1044480,
            1048576,
            123456789,
        ]

        human = [
            {'Number': 0.0, 'Unit': 'B'},
            {'Number': 1.0, 'Unit': 'KiB'},
            {'Number': 1.0, 'Unit': 'KiB'},
            {'Number': 99.99, 'Unit': 'KiB'},
            {'Number': 1020, 'Unit': 'KiB'},
            {'Number': 1.0, 'Unit': 'MiB'},
            {'Number': 117.74, 'Unit': 'MiB'},
        ]
        for i in range(len(bytes)):
            result = utils.convert_bytes_to_human(bytes[i])
            self.assertEqual(human[i], result)

    def tearDown(self):
        pass

class AppObj(unittest.TestCase):
    def setUp(self):
        import logging
        self.obj = app.App()
        self.obj.exe_path = Path(__file__).resolve()
        self.obj.loglevel = logging.DEBUG
        self.obj.runmode = 'test'

    def test_0setup_logging(self):
        # Create temp log_dir.
        self.obj.log_dir = Path(tempfile.mkdtemp())
        self.obj.log_path = self.obj.log_dir / 'temp.log'

        # Create log file.
        utils.set_up_logging(self.obj)
        self.assertTrue(self.obj.log_path.exists())

        # Remove temp files.
        self.obj.log_path.unlink()
        self.obj.log_dir.rmdir()

    def test_get_config1_root(self):
        self.obj.pkg_root = utils.get_pkg_root(self.obj)
        config_root = utils.get_config_root(self.obj)
        self.assertEqual(config_root, self.obj.pkg_root / 'data' / 'etc')

    def test_get_config2(self):
        self.obj.pkg_root = utils.get_pkg_root(self.obj)
        self.obj.config = utils.get_config(self.obj)
        self.assertTrue(self.obj.config)

    def test_get_pkg_root(self):
        repo_base = Path(__file__).parents[2]
        self.obj.pkg_root = utils.get_pkg_root(self.obj)
        self.assertEqual(self.obj.pkg_root, repo_base)

    def tearDown(self):
        pass
