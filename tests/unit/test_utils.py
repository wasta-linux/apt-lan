import unittest
from pathlib import Path

from apt_lan import utils

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class B(unittest.TestCase):
    def setUp(self):
        pass

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
