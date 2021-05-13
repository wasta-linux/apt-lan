''' Main app structure '''

# Required packages:
#   - python3-pyftpdlib
# ---------------------------
#   - python3-pycurl
#   - python3-smbc
#   - samba
#   - smbclient, needed by smbc? (was needed for smbget, which doesn't work well enough)


import gi
import gzip
import logging
import subprocess


gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk
from pathlib import Path

from apt_lan import cmd, server, system, utils


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
            'system-sync', ord('s'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Synchronize APT archive with apt-lan archive.', None
        )
        self.add_main_option(
            'lan-sync', ord('l'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Synchronize LAN systems' apt-lan archives with this systems' apt-lan archive.", None
        )
        self.add_main_option(
            'debug', ord('d'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Log debug output.", None
        )

        # Define app-wide variables.
        self.pkg_name = 'apt-lan'
        self.hostname = utils.get_hostname()
        home = utils.get_home()
        self.apt_lan_dir = Path(home) / '.apt-lan'
        self.share_path = self.apt_lan_dir / 'local-cache'
        self.log_dir = self.apt_lan_dir / 'log'

        self.os_rel = utils.get_os_release()
        self.arch_d = utils.get_arch_dir_name()
        self.deb_archives = {
            'system': Path('/var/cache/apt/archives'),
            'lan': self.share_path / self.os_rel / self.arch_d
        }

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

        # if len(options) > 1:
        #     # Only one option accepted.
        #     print("Too many options passed. Only one is accepted at a time.")
        #     return 1

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
        if 'system-sync' in options:
            logging.info(f"Starting system packages sync.")
            ret = cmd.run_system_sync(self)
        elif 'lan-sync' in options:
            logging.info(f"Starting LAN packages sync.")
            ret = cmd.run_lan_sync(self)
        else:
            # Unknown options are handled elsewhere.
            ret = 1

        return ret

app = App()
