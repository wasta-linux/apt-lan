''' Utility functions '''

import logging
import os
import platform
import time

from pathlib import Path


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

def set_up_logging(app):
    log_path = Path(app.apt_lan_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    #shutil.chown(log_path, user=user, group=user)
    # timestamp = time.strftime('%Y-%m-%d-%H%M%S')
    # date = time.strftime('%Y-%m-%d')
    # log_file = f"{timestamp}-{hostname}.log"
    log_file = f"{app.pkg_name}-{app.hostname}.log"
    file_path = log_path / log_file
    logging.basicConfig(
        filename=file_path,
        level=app.loglevel,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    #shutil.chown(filename, user=user, group=user)
    logging.info('='*65)
    # logging.info(f"{timestamp} {hostname} {app_name} started")
    logging.info(f"{app.pkg_name} started for {app.hostname}")
    logging.info('-'*65)

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
