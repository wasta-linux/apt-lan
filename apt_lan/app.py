''' Main app structure '''

# Required packages:
#   - dpkg-dev (/usr/bin/dpkg-scanpackages)
#   - rsync (for rsyncd)
# --------------------------------------------------
#   - python3-pyftpdlib (used to create FTP server)

import argparse
import gzip
import logging
import subprocess
import sys

from pathlib import Path

from apt_lan import cmd, utils


class App():
    def __init__(self):
        # Define app-wide variables.
        self.pkg_name = 'apt-lan'
        self.hostname = utils.get_hostname()
        # TODO: consolidate the next two attributes into one.
        self.apt_lan_dir = Path(f'/var/cache/{self.pkg_name}')
        self.share_path = self.apt_lan_dir
        self.log_dir = Path(f'/var/log/{self.pkg_name}')

        self.os_rel = utils.get_os_release()
        self.arch_d = utils.get_arch_dir_name()
        self.deb_archives = {
            'system': Path('/var/cache/apt/archives'),
            'lan': self.share_path / self.os_rel / self.arch_d
        }
        self.ports = [139, 445] # SMB
        self.ports = [21021] # custom FTP
        self.ports = [22022] # custom rsyncd

    def run(self, cmdline):
        self.exe_path = Path(cmdline[0]).resolve()
        self.pkg_root = utils.get_pkg_root(self)
        self.config = utils.get_config(self)

        # Define options.
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--version', '-V',
            action='store_true',
            help='Print apt-lan version number.',
        )
        parser.add_argument(
            '--apply', '-a',
            action='store_true',
            help="Apply current configuration files.",
        )
        parser.add_argument(
            '--server-sync', '-s',
            action='store_true',
            help="Update apt-lan archive with system's APT archive.",
        )
        parser.add_argument(
            '--client-sync', '-c',
            action='store_true',
            help="Update apt-lan archive with LAN systems' apt-lan archives."
        )
        parser.add_argument(
            '--debug', '-d',
            action='store_true',
            help="Log debug output."
        )

        args = parser.parse_args()
        if not any([args.apply, args.version, args.server_sync, args.client_sync]):
            # No command line args passed.
            parser.print_help()
            return 1

        if args.version:
            chlog = Path(f"/usr/share/{self.pkg_name}/changelog.gz")
            fmt = 'gz'
            parents = list(self.pkg_root.parents)
            if str(parents[-2]) != '/usr':
                chlog = self.pkg_root / 'debian' / 'changelog'
                fmt = 'txt'
            # TODO: need to parse top line of changelog file.
            try:
                chlog.stat()
            except FileNotFoundError:
                print('0.0')
                return 0

            if fmt == 'gz':
                # TODO: This needs to be tested.
                contents = gzip.decompress(chlog.read_bytes())
                head = f.readline().rstrip()
            else:
                with open(chlog) as f:
                    # head = f.read().splitlines()[0]
                    head = f.readline().rstrip()
            parts = head.split()
            version = parts[1].strip('(').strip(')')
            print(f"{parts[0]} {version}")
            return 0

        # Set up logging.
        self.loglevel = logging.DEBUG if args.debug else logging.INFO
        utils.set_up_logging(self)
        logging.debug(f"runmode = {self.runmode}")

        # Run functions for passed option.
        if args.apply:
            # Apply current config.
            utils.apply_config(self)
            ret = 0

        elif args.server_sync:
            # Apply current config.
            utils.apply_config(self)

            # Run sync.
            logging.info(f"Starting server packages sync from system.")
            ret = cmd.run_server_sync(self)

        elif args.client_sync:
            # Apply current config.
            utils.apply_config(self)

            # Run sync.
            logging.info(f"Starting client packages sync from LAN.")
            ret = cmd.run_client_sync(self)

        else:
            # Unknown options are handled elsewhere.
            ret = 1

        return ret
