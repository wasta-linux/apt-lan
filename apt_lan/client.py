import ipaddress
import logging
import netifaces
import os
import socket
import subprocess
import time

from ftplib import FTP


def lan_connect(hostname, port):
    logging.debug(f"Connecting to {hostname}:{port}...")
    timeout = 10 # milliseconds
    tos = timeout / 1000
    socket.setdefaulttimeout(tos)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((hostname, port))
    logging.debug(f"result: {result}; {os.strerror(result)}")
    return result == 0

def get_info():
    gws = netifaces.gateways()
    # Listed in order of priority. First one found wins.
    families = [
        netifaces.AF_BLUETOOTH,
        netifaces.AF_PPPOX,
        netifaces.AF_INET6,
        netifaces.AF_INET,
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
        for i in info_list:
            lan_ip = i['addr']
            netmask = i['netmask']
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

def get_smb_uri_smbget(uri):
    cmd = ['smbget', '--guest', uri] # smbget fails to retrieve files with "%" in them
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode == 0:
        logging.debug(f"smbget: {uri} downloaded.")
    else:
        logging.error(f"smbget: {result.stdout}")

def get_smb_uri_curl(uri):
    c = pycurl.Curl()
    # TODO: cURL needs login info, but what is it for a guest account?
    # $ net usershare info --long
    # "Everyone"?
    logging.debug(f"cURL: {uri}")
    with open(filename, 'wb') as f:
        c.setopt(c.URL, uri)
        c.setopt(c.WRITEDATA, f)
        c.perform()
    c.close()

def get_ftp_file(ftp, filename):
    logging.debug(f"Getting FTP file: {filename}")
    with open(filename, 'wb') as f:
        r = ftp.retrbinary(f'RETR {filename}', f.write)
    logging.debug(f"Result: {r}")

def get_files_from_share(share_uri, port, filenames=None, dst_dir=None):
    orig_cwd = os.getcwd()
    if dst_dir:
        os.chdir(dst_dir)
        logging.debug(f"cd to {dst_dir}")
    uri_parts = share_uri.split('/')
    share_ip = uri_parts[2]
    # Shared folder "local-cache" is parent. Only "focal", etc. are visible.
    dir_path = '/'.join(uri_parts[3:])
    logging.debug(f"Share IP: {share_ip}")
    logging.debug(f"Share subfolder path: {dir_path}")

    if port == 139: # SMB
        for filename in filenames:
            uri = f"{share_uri}/{filename}"
            get_smb_uri_smbget(uri) # doesn't work for files with "%" in URI.
            # get_smb_uri_curl(uri) # doesn't work with guest access
    elif port == 21021: # Wasta FTP
        ftp = FTP()
        try:
            r = ftp.connect(host=share_ip, port=port, timeout=120)
            logging.debug(f"ftp.connect: {r}")
        except ConnectionRefusedError as e:
            logging.debug(f"ftp.connect: {e}")
            return 1
        r = ftp.login()
        logging.debug(f"ftp.login: {r}")
        r = ftp.cwd(dir_path)
        logging.debug(f"ftp.cwd: {r}")
        if filenames == None:
            # Get file list.
            names = ftp.nlst()
            logging.debug(f"Files found at {share_ip}: {names}")
            return names
        else:
            # Get files.
            for filename in filenames:
                # uri = f"{share_uri}/{filename}"
                get_ftp_file(ftp, filename)
        ftp.quit()

    elif port == 22022: # Wasta rsync
        cmd = [
            'rsync', '--verbose', '--recursive', '--update',
            f'rsync://{share_ip}/apt-lan/',
            f'{dst_dir}/{dir_path}',
        ]
        r = subprocess.run(cmd, stdout=supbrocess.PIPE, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            logging.error(f"Failed to copy packages:")
            logging.error(r.stderr)
        logging.info(r.stdout)

    os.chdir(orig_cwd)
    logging.debug(f"cd to {orig_cwd}")
