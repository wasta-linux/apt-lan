''' Utility functions '''

import logging
import os
import platform
import shutil
import time

from pathlib import Path


def apply_config(app):
    # Define script names.
    scripts = {
        'network': 'apt-lan-client',
        'system': 'apt-lan-server',
    }

    # Ensure proper location of scripts according to config.
    for k, v in scripts.items():
        # Define desired cron directory for the given script.
        freq = app.config.get(k, {}).get('frequency', 'none')
        freq = freq.lower()
        if freq == 'none':
            if k == 'network':
                dest_dir = Path('/etc/cron.hourly') # "hourly" by default
            elif k == 'system':
                dest_dir = Path('/etc/cron.daily') # "daily" by default
        elif freq == 'never':
            dest_dir = None
        else:
            dest_dir = Path(f"/etc/cron.{freq}")

        # Find current location of script, if any.
        posix_paths = find_script(v)
        script_path_set = False
        for p in posix_paths:
            if p.parent != dest_dir:
                print(f"Unlink {p}")
                p.unlink()
            else:
                print(f"{p} in correct location.")
                script_path_set = True

        # Add link to script in dest_dir.
        if not script_path_set:
            logging.debug(f"Copy {v} into {dest_dir}.")
            dest_path = dest_dir / v
            dest_path.symlink_to(f"/usr/share/{app.pkg_name}/{v}")

def find_script(script_name):
    etc_dir = Path('/etc')
    paths = list(etc_dir.rglob(f"cron.*/{script_name}"))
    return paths

def get_os_release():
    release = ''
    with open('/etc/os-release', 'r') as f:
        for line in f.readlines():
            if 'VERSION_CODENAME' in line:
                release = line.split('=')[1].strip()
    if not release:
        logging.error("Release not found.")
        exit(1)
    return release

def get_home():
    return Path(os.environ['HOME'])

def get_hostname():
    return os.uname().nodename

def get_pkg_root(app):
    """
    Get root folder of package, whether debian-installed or git repo.
    """
    pkg_root = None
    dir = app.exe_path
    while str(dir.parent) != app.exe_path.root:
        git = dir.glob('.git')
        for g in git:
            # git repo found.
            pkg_root = dir
            break
        dir = dir.parent
    if not pkg_root:
        pkg_root = app.exe_path.parents[1] / 'share' / app.pkg_name
    return pkg_root

def get_config(app):
    """
    Parse config from config files.
    """
    # Initialize config dictionary.
    config = {}

    # Get config root directory.
    if str(app.pkg_root.parent) == '/usr/share':
        # Installed package. Config in /etc/.
        config_root = Path('/etc')
    else:
        # Assume git package. Config in ./{app.pkg_root}/data/.
        config_root = Path(app.pkg_root) / 'data'
    logging.debug(f"Config root: {config_root}")

    config_lines = []
    # Get lines from config file.
    config_file = config_root / f"{app.pkg_name}.conf"
    with config_file.open() as c:
        logging.debug(f"Reading config from {config_file}")
        config_lines.extend(c.readlines())

    # Get lines from config directory files.
    config_dir = config_root / f"{app.pkg_name}.conf.d"
    for f in config_dir.iterdir():
        with f.open() as c:
            logging.debug(f"Reading config from {f}")
            config_lines.extend(c.readlines())

    # Parse lines into config dictionary.
    line = 0
    for l in config_lines:
        l = l.strip() # remove whitespace & newlines
        logging.debug(f"line: {l}")
        line += 1
        if l:
            if l[0] == '#': # skip commented line
                continue
            elif l[0] == '[': # section header
                section = l[1:-1].lower()
                if section == 'repositories':
                    config[section] = []
                else:
                    config[section] = {}
                continue

            parts = l.split('=')
            parts = [p.strip().lower() for p in parts]
            if section == 'repositories':
                config[section].append(l)
            else:
                config[section][parts[0]] = parts[1]
        else:
            section = None

    logging.debug('Full config:')
    logging.debug(config)
    return config

def set_up_logging(app):
    log_path = Path(app.log_dir)
    # log_path.mkdir(parents=True, exist_ok=True) # created during package install with mod=666
    log_file = f"{app.pkg_name}.log"
    file_path = log_path / log_file
    print(f"Log file: {file_path}")
    logging.basicConfig(
        filename=file_path,
        level=app.loglevel,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    ct = 54
    logging.info('=' * ct)
    # logging.info(f"{timestamp} {hostname} {app_name} started")
    logging.info(f"{app.pkg_name} started for {app.hostname}")
    logging.info('-' * ct)

def convert_bytes_to_human(bytes):
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    for i in range(1, 6):
        if bytes < 1024**i:
            human = round(bytes / (1024**(i-1)), 2)
            unit = units[i-1]
            break
    return {'Number': human, 'Unit': unit}

def get_arch_dir_name():
    os_proc = platform.machine()
    if os_proc == 'x86_64':
        arch_dir_name = 'binary-amd64'
    else:
        arch_dir_name = '-'.join(['binary', os_proc])
    return arch_dir_name

def delay_if_other_sync_in_progress(old_pkgs_gz):
    while old_pkgs_gz.is_file():
        # Another sync is in progress.
        logging.info(f"Another sync is in progress. Delaying for 30 s.")
        time.sleep(30)

def test_exit(ret=9):
    print("(Early exit for testing.)")
    exit(ret)
