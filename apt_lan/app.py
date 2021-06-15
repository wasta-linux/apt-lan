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
        self.log_path = self.log_dir / f"{self.pkg_name}.log"

        self.os_rel = utils.get_os_release()
        self.arch_d = utils.get_arch_dir_name()
        self.deb_archives = {
            'system': Path('/var/cache/apt/archives'),
            'lan': self.share_path / self.os_rel / self.arch_d
        }
        self.ports = [22022] # custom rsyncd

    def run(self, cmdline):
        self.exe_path = Path(cmdline[0]).resolve()
        self.pkg_root = utils.get_pkg_root(self)

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

        self.args = parser.parse_args()
        if not any([self.args.apply, self.args.version, self.args.server_sync, self.args.client_sync]):
            # No command line args passed.
            parser.print_help()
            return 1

        if self.args.version:
            chlog = Path(f"/usr/share/doc/{self.pkg_name}/changelog.gz")
            fmt = chlog.suffix.lstrip('.')
            # parents = list(self.pkg_root.parents)
            parents = list(chlog.parents)
            if str(parents[-2]) != '/usr':
                chlog = self.pkg_root / 'debian' / 'changelog'
                fmt = 'txt'
            # Parse top line of changelog file.
            try:
                chlog.stat()
            except FileNotFoundError:
                print("No changelog found.")
                return 1

            if fmt == 'gz':
                f = gzip.decompress(chlog.read_bytes())
                head = f.readline().rstrip()
            else:
                with open(chlog) as f:
                    # head = f.read().splitlines()[0]
                    head = f.readline().rstrip()
            parts = head.split()
            version = parts[1].strip('(').strip(')')
            print(f"{parts[0]} {version}")
            return 0

        # Ensure root permissions.
        if not utils.check_if_root():
            if not self.runmode == 'test':
                print("Insufficient permissions. Try sudo or pkexec.")
            return 1

        # Set up logging.
        self.loglevel = logging.DEBUG if self.args.debug else logging.INFO
        utils.set_up_logging(self)
        logging.debug(f"runmode = {self.runmode}")

        # Run functions for passed option.
        if self.args.apply:
            if self.runmode == 'test':
                return 0
            # Apply current config.
            utils.apply_config(self)
            ret = 0

        elif self.args.server_sync:
            # Apply current config.
            utils.apply_config(self)

            # Run sync.
            logging.info(f"Starting server packages sync from system.")
            ret = cmd.run_server_sync(self)

        elif self.args.client_sync:
            # Apply current config.
            utils.apply_config(self)

            # Run sync.
            logging.info(f"Starting client packages sync from LAN.")
            ret = cmd.run_client_sync(self)

        else:
            # Unknown options are handled elsewhere.
            ret = 1

        return ret
