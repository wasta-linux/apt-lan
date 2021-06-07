''' Main app structure '''

# Required packages:
#   - dpkg-dev (/usr/bin/dpkg-scanpackages)
#   - python3-pyftpdlib (used to create FTP server)

import gi
import gzip
import logging
import subprocess
import sys

# gi.require_version("Gtk", "3.0")
# from gi.repository import Gio, GLib, Gtk
from pathlib import Path

from apt_lan import cmd, utils


class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='org.wasta.apps.apt-lan',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        self.add_main_option(
            'version', ord('V'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Print apt-lan version number.', None
        )
        self.add_main_option(
            'server-sync', ord('s'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Update apt-lan archive with system's APT archive.", None
        )
        self.add_main_option(
            'client-sync', ord('c'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Update apt-lan archive with LAN systems' apt-lan archives.", None
        )
        self.add_main_option(
            'debug', ord('d'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Log debug output.", None
        )

        # Define app-wide variables.
        self.pkg_name = 'apt-lan'
        self.hostname = utils.get_hostname()
        # home = utils.get_home()
        self.apt_lan_dir = Path('/var/cache/apt-lan')
        # self.share_path = self.apt_lan_dir / 'local-cache'
        self.share_path = self.apt_lan_dir
        # self.log_dir = self.apt_lan_dir / 'log'
        self.log_dir = Path('/var/log/apt-lan')

        self.os_rel = utils.get_os_release()
        self.arch_d = utils.get_arch_dir_name()
        self.deb_archives = {
            'system': Path('/var/cache/apt/archives'),
            'lan': self.share_path / self.os_rel / self.arch_d
        }
        self.ports = [139, 445] # SMB
        self.ports = [21021] # Wasta FTP
        self.ports = [22022] # Wasta rsyncd

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        pass

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if not options:
            # No command line args passed: print version? print help?.
            print("No options given.")
            return 1

        if 'version' in options:
            chlog = Path(f"/usr/share/{self.pkg_name}/changelog.gz")
            fmt = 'gz'
            if self.runmode == 'uninstalled':
                chlog = Path(f"../debian/changelog")
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
                head = f.read().splitlines()[0]
                print(head)
            else:
                with open(chlog) as f:
                    head = f.read().splitlines()[0]
                    print(head)

            return 0

        # Set log level.
        self.loglevel = logging.INFO
        if 'debug' in options:
            self.loglevel = logging.DEBUG

        # Set up logging.
        # TODO: Create '--log' option.
        utils.set_up_logging(self)
        logging.debug(f"runmode = {self.runmode}")

        # Run functions for passed option.
        if 'server-sync' in options:
            logging.info(f"Starting server packages sync from system.")
            ret = cmd.run_server_sync(self)
        elif 'client-sync' in options:
            logging.info(f"Starting client packages sync from LAN.")
            ret = cmd.run_client_sync(self)
        else:
            # Unknown options are handled elsewhere.
            ret = 1

        return ret

class App():
    def __init__(self, *args):
        self.cmdline = args

        # Define app-wide variables.
        self.pkg_name = 'apt-lan'
        self.hostname = utils.get_hostname()
        # home = utils.get_home()
        self.apt_lan_dir = Path('/var/cache/apt-lan')
        # self.share_path = self.apt_lan_dir / 'local-cache'
        self.share_path = self.apt_lan_dir
        # self.log_dir = self.apt_lan_dir / 'log'
        self.log_dir = Path('/var/log/apt-lan')

        self.os_rel = utils.get_os_release()
        self.arch_d = utils.get_arch_dir_name()
        self.deb_archives = {
            'system': Path('/var/cache/apt/archives'),
            'lan': self.share_path / self.os_rel / self.arch_d
        }
        self.ports = [139, 445] # SMB
        self.ports = [21021] # Wasta FTP
        self.ports = [22022] # Wasta rsyncd

    def run(self):
        print(self.cmdline)

app = App()
