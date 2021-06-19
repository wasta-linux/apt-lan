import unittest
from pathlib import Path

from apt_lan import pkgs

# Assert*() methods here:
# https://docs.python.org/3/library/unittest.html?highlight=pytest#unittest.TestCase

class Basic(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_repos_to_pkg_files(self):
        repos = {
            'bionic': 'http://archive.ubuntu.com/ubuntu bionic main',
            'focal': 'http://archive.ubuntu.com/ubuntu focal main',
        }

        for release, repo in repos.items():
            # repo = 'http://archive.ubuntu.com/ubuntu focal main'
            arches_dict = {
                'x32': [
                    ['i386'],
                    [f'archive.ubuntu.com_ubuntu_dists_{release}_main_binary-i386_Packages'],
                ],
                'x64': [
                    ['amd64'],
                    [f'archive.ubuntu.com_ubuntu_dists_{release}_main_binary-amd64_Packages'],
                ],
                'x64+': [
                    ['amd64', 'i386'],
                    [
                        f'archive.ubuntu.com_ubuntu_dists_{release}_main_binary-amd64_Packages',
                        f'archive.ubuntu.com_ubuntu_dists_{release}_main_binary-i386_Packages',
                    ]
                ],
            }
            for arch, values in arches_dict.items():
                out = pkgs.convert_repo_to_package_files(repo, values[0])
                expected = values[1]
                try:
                    self.assertEqual(out, expected)
                except AssertionError:
                    print(out, expected)
                    raise AssertionError

    def test_list_good_debs(self):
        repos = [
            'http://archive.ubuntu.com/ubuntu focal main',
        ]
        good_debs = pkgs.list_good_debs(repos)
        self.assertTrue(good_debs)

    def test_match_filename(self):
        dir = Path('/var/lib/apt/lists')
        approved = 'archive.ubuntu.com_ubuntu_dists_focal-updates_main_binary-amd64_Packages'
        pkg_lists = [
            ['fr.archive.ubuntu.com_ubuntu_dists_focal-updates_main_binary-amd64_Packages'],
            ['archive.ubuntu.com_ubuntu_dists_focal-updates_main_binary-amd64_Packages'],
        ]
        for pkg_list in pkg_lists:
            match = pkgs.match_filename(approved, pkg_list)
            self.assertTrue(match)

    def tearDown(self):
        pass
