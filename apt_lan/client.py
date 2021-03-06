import ipaddress
import logging
import netifaces
import os
import socket
import subprocess
import time


def lan_connect(hostname, port):
    logging.debug(f"Connecting to {hostname}:{port}...")
    timeout = 10 # milliseconds
    tos = timeout / 1000
    socket.setdefaulttimeout(tos)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((hostname, port))
    logging.debug(f"result: {result}; {os.strerror(result)}")
    return result == 0

def get_network_info():
    gws = netifaces.gateways()
    # Listed in order of priority. First one found wins.
    families = [
        netifaces.AF_BLUETOOTH,
        netifaces.AF_PPPOX,
        netifaces.AF_INET, # prefer IPv4 over IPv6
        netifaces.AF_INET6,
    ]
    conn_fam = None
    logging.debug(f"Searching for connection gateway...")
    for family in families:
        logging.debug(f"Checking interface family {family}.")
        try:
            device = gws['default'][family][1]
            conn_gw = gws['default'][family][0]
            conn_fam = family
            break
        except KeyError:
            conn_gw = None

    logging.info(f"Connection gateway: {conn_gw}")
    if device and conn_fam and conn_gw:
        logging.debug(f"Searching for LAN IP and netmask...")
        info_list = netifaces.ifaddresses(device)[conn_fam]
        logging.debug(f"iface info: {info_list}")
        for i in info_list:
            lan_ip = i['addr']
            netmask = i['netmask']
            # ipaddress v3.9.5 can't handle expanded IPv6 netmasks.
            # ref:
            #   https://docs.python.org/3/library/ipaddress.html?highlight=expanded%20netmasks#ipaddress.IPv6Network
            if netmask == 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff':
                netmask = 128
            netw = ipaddress.ip_network(f"{lan_ip}/{netmask}", strict=False)
            logging.info(f"Network: {lan_ip}/{netmask}")
            if ipaddress.ip_address(conn_gw) in netw:
                return lan_ip, netmask
    return None, None

def get_share_ips(own_ip, netmask, ports):
    """
    Search the local network for IPs with open share ports.
    """
    lan_ips = []

    logging.info(f"Checking LAN for IPs with open port {ports[0]}...")
    netw = ipaddress.ip_network(f"{own_ip}/{netmask}", strict=False)
    for ip in netw:
        if str(ip) == own_ip:
            logging.debug(f"Skipped own IP: {own_ip}.")
            continue
        # It takes too long to scan 2 ports for every IP, so only scanning :139.
        t_start = time.time()
        found = lan_connect(str(ip), ports[0])
        t_end = time.time()
        duration = t_end - t_start
        logging.debug(f"Search for {ip} lasted {duration} s.")
        if found:
            logging.debug(f"LAN share IP found: {ip}")
            lan_ips.append(str(ip))
    return lan_ips

def get_files_from_share(share_uri, port, filenames=None, dst_dir=None):
    orig_cwd = os.getcwd()
    logging.debug(f"share_uri: {share_uri}")
    # if dst_dir:
    #     os.chdir(dst_dir)
    #     logging.debug(f"cd to {dst_dir}")
    uri_parts = share_uri.split('/')
    share_ip = uri_parts[2]
    # Shared folder "local-cache" is parent. Only "focal", etc. are visible.
    dir_path = '/'.join(uri_parts[3:])
    logging.debug(f"Share IP: {share_ip}")
    logging.debug(f"Share subfolder path: {dir_path}")

    if port == 22022: # Wasta rsync
        # TODO: Need to verify that requested release and arch folders exist.
        #   See the verify_rsync_folder function below.
        cmd = ['rsync', f'--port={port}', f'{share_uri}/']
        if filenames == None:
            # Get file list.
            cmd.append('--list-only')
            # r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) # python3.7
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            logging.debug(f"cmd: {' '.join(r.args)}")
            if r.returncode == 23:
                logging.warning(f"Skipping missing folder at {share_uri}.")
                return []
            elif r.returncode != 0:
                logging.error(f"Failed to get file list:")
                logging.error(r.stdout)
                return []
            lines = r.stdout.splitlines()
            files = [l.split()[-1] for l in lines]
            logging.debug(f"File list:")
            for f in files:
                logging.debug(f"  {f}")
            return files
        else:
            # Update rsync command.
            cmd.append(str(dst_dir))
            src_dir = cmd[2]

            # Get files.
            if len(filenames) == 1:
                # Source is only one specific file (superseded.txt).
                cmd[2] = src_dir + filenames[0]
            else:
                cmd.append('--recursive')
            # r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) # python3.7
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            logging.debug(f"cmd: {' '.join(r.args)}")
            if r.returncode == 23:
                logging.warning(f"Skipping missing folder at {share_uri}.")
                return
            elif r.returncode != 0:
                logging.error(f"Failed to get file list:")
                logging.error(r.stdout)
                return

    # os.chdir(orig_cwd)
    # logging.debug(f"cd to {orig_cwd}")
