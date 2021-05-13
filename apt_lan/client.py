import ipaddress
import logging
import netifaces
import os
# import pycurl
# import smbc
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
    logging.debug(f"result: {result}")
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

def get_lan_ips(own_ip, netmask, ports):
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
            logging.debug(f"LAN samba-share IP found: {ip}")
            lan_ips.append(str(ip))

    return lan_ips

def get_file_list_from_share(uri, port):
    if port == 139: # SMB share
        ctx = smbc.Context()
    elif port == 21021: # Wasta FTP

    ip_files = []
    try:
        logging.debug(f"Getting file list from {uri}...")
        items = ctx.opendir(uri).getdents()
    except Exception as e:
        # What happens if a samba share doesn't have the desired folder?
        logging.error(f"smbc.ctx: {e}")
        items = []
    filenames = [i.name for i in items]
    # Ignore any lan_cache that doesn't have Packages.gz file.
    #   Or consider delaying instead of ignoring.
    if 'Packages.gz' in filenames:
        # Only available for LAN sync if Packages.gz exists.
        ip_files = [n for n in filenames if n[-4:] == '.deb' or n == 'superseded.txt']
    else:
        logging.debug(f"No Packages.gz file. Skipping this apt-lan peer.")
    return ip_files

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
    with open(filename, 'wb') as f:
        r = ftp.retrbinary(f'RETR {filename}', f.write)
    logging.debug(f"Get FTP file: {r}")

def get_files_from_share(share_uri, port, filenames=None, dst_dir=None):
    orig_cwd = os.getcwd()
    os.chdir(dst_dir)
    uri_parts = share_uri.split('/')
    share_ip = uri_parts[2]
    dir_path = '/'.join(uri_parts[3:])
    logging.debug(f"Share IP: {share_ip}")
    logging.debug(f"cd to {dst_dir}")
    if port == 139: # SMB
        for filename in filenames:
            uri = f"{share_uri}/{filename}"
            get_smb_uri_smbget(uri) # doesn't work for files with "%" in URI.
            # get_smb_uri_curl(uri) # doesn't work with guest access
    elif port == 21021: # Wasta FTP
        ftp = FTP()
        r = ftp.connect(host=share_ip, port=port)
        logging.debug(f"ftp.connect: {r}")
        r = ftp.login()
        logging.debug(f"ftp.login: {r}")
        r = ftp.cwd(dir_path)
        logging.debug(f"ftp.cwd: {r}")
        if filenames == None:
            # Get file list.
            names = ftp.retrlines('NLST')
            logging.debug(names)
            return names
        else:
            # Get files.
            for filename in filenames:
                # uri = f"{share_uri}/{filename}"
                get_ftp_file(ftp, filename)
        ftp.quit()

    os.chdir(orig_cwd)
    logging.debug(f"cd to {orig_cwd}")
