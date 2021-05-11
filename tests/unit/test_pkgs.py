import unittest
#from pathlib import Path

from apt_lan import pkgs

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class A(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_repos_to_pkg_files(self):
        repo = 'http://archive.ubuntu.com/ubuntu focal main'
        arches_dict = {
            'x32': [
                ['i386'],
                ['archive.ubuntu.com_ubuntu_dists_focal_main_binary-i386_Packages'],
            ],
            'x64': [
                ['amd64'],
                ['archive.ubuntu.com_ubuntu_dists_focal_main_binary-amd64_Packages'],
            ],
            'x64+': [
                ['amd64', 'i386'],
                [
                    'archive.ubuntu.com_ubuntu_dists_focal_main_binary-amd64_Packages',
                    'archive.ubuntu.com_ubuntu_dists_focal_main_binary-i386_Packages'
                ]
            ],
        }
        for arch, values in arches_dict.items():
            out = pkgs.convert_repo_to_package_files(repo, values[0])
            expected = values[1]
            self.assertEqual(out, expected)

    def tearDown(self):
        pass