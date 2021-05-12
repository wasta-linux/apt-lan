''' Utility functions '''

import logging
import platform
import time

from pathlib import Path
from apt_lan import system


def set_up_logging(app_name, base_path, loglevel):
    log_path = Path(base_path)
    log_path.mkdir(parents=True, exist_ok=True)
    #shutil.chown(log_path, user=user, group=user)
    timestamp = time.strftime('%Y-%m-%d-%H%M%S')
    hostname = system.get_hostname()
    log_file = f"{timestamp}-{hostname}.log"
    filename = log_path / log_file
    logging.basicConfig(
        filename=filename,
        level=loglevel,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    #shutil.chown(filename, user=user, group=user)
    logging.info('='*65)
    logging.info(f"{timestamp} {hostname} {app_name} started")
    logging.info('-'*65)
    print(f"{app_name} log: {filename}")

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
