try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


import glob
import re
from pathlib import Path


# Define directories.
repo_home = Path(__file__).resolve().parent
debian_path = repo_home / 'debian'

# Get long_description from README.md.
readme_path = repo_home / 'README.md'
with readme_path.open('rb') as f:
    readme = f.read().decode('utf8')

# Get version number from debian/changelog.
chlog_path = debian_path / 'changelog'
with chlog_path.open() as f:
    first_line = f.readline()
version = re.match('.*\((.*)\).*', first_line).group(1)

# Get variables from debian/control.
control_path = debian_path / 'control'
with control_path.open() as f:
    lines = f.readlines()
for line in lines:
    if line[:7] == 'Source:':
        name = line.split(':')[1].strip()
    if line[:11] == 'Maintainer:':
        parts = line.split(':')
        info = parts[1].split('<')
        author = info[0].strip()
        author_email = info[1].strip()[:-1] # remove trailing '>'
    elif line[:9] == 'Homepage:':
        homepage = line.split(':')[1].strip()
    elif line[:12] == 'Description:':
        description = line.split(':')[1].strip()

setup(
    long_description=readme,
    name=name,
    version=version,
    description=description,
    url=homepage,
    author=author,
    author_email=author_email,
    license="GPLv3",
    keywords="APT debian package LAN sync",
    packages=["apt_lan"],
    package_dir={"apt_lan": "apt_lan"},
    scripts=[
        'bin/apt-lan',
    ],
    data_files=[
        # Keep APT packages.
        ('/etc/apt/apt.conf.d', ['data/etc/20keep-debs-apt-lan']),
        # Set base default configuration and user config folder.
        ('/etc/apt-lan', [
            'data/etc/apt-lan.conf',
            'data/etc/apt-lan.conf.d',
        ]),
        # Ensure custom configuration folder.
        # ('/etc/apt-lan/apt-lan.conf.d', ['data/apt-lan.conf.d/.placeholder']),
        # Put system scripts under /usr/lib.
        ('/usr/lib/apt-lan', [
            'data/libs/apt-lan-client',
            'data/libs/apt-lan-server',
            'data/libs/test-installed-package.sh',
        ]),
        # Put repo lists under /usr/share.
        ('/usr/share/apt-lan', [
            'data/share/00-bionic-repos.conf',
            'data/share/00-focal-repos.conf',
        ])
    ],
)
