import ipaddress
import logging
import netifaces
import os
import pycurl
import smbc
import socket
import subprocess
import time


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

def get_smb_ips(own_ip, netmask):
    """
    Search the local network for IPs with open samba ports.
    """
    smb_ips = []
    smb_ports = [139, 445]
    timeout = 10 # milliseconds
    tos = timeout / 1000
    def connect(hostname, port):
        # logging.debug(f"Connecting to {hostname}:{port}...")
        socket.setdefaulttimeout(tos)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex((hostname, port))
        logging.debug(f"result: {result}")
        return result == 0

    logging.info(f"Checking LAN for IPs with open SMB port {smb_ports[0]}...")
    netw = ipaddress.ip_network(f"{own_ip}/{netmask}", strict=False)
    for ip in netw:
        if str(ip) == own_ip:
            logging.debug(f"Skipped own IP: {own_ip}.")
            continue
        # It takes too long to scan 2 ports for every IP, so only scanning :139.
        t_start = time.time()
        found = connect(str(ip), smb_ports[0])
        t_end = time.time()
        duration = t_end - t_start
        logging.debug(f"Search for {ip} lasted {duration} s.")
        if found:
            logging.debug(f"LAN samba-share IP found: {ip}")
            smb_ips.append(str(ip))

    return smb_ips

def get_apt_lan_ips(lan_ips):
    apt_lan_ips = []
    share_name = 'apt-lan'
    ctx = smbc.Context()
    for ip in lan_ips:
        uri = f"smb://{ip}"
        entries = ctx.opendir(uri).getdents()
        for e in entries:
            if e.name == share_name:
                apt_lan_ips.append(ip)
    return apt_lan_ips

def get_files_from_ip(ip, release, arch_dir):
    share_name = 'apt-lan'
    ctx = smbc.Context()
    uri = f"smb://{ip}/{share_name}/{release}/{arch_dir}"
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

def get_smb_files_from_share(share_uri, filenames, dst_dir):
    orig_cwd = os.getcwd()
    os.chdir(dst_dir)
    logging.debug(f"cd to {dst_dir}")

    for filename in filenames:
        uri = f"{share_uri}/{filename}"
        get_smb_uri_smbget(uri) # doesn't work for files with "%" in URI.
        # get_smb_uri_curl(uri) # doesn't work with guest access
    os.chdir(orig_cwd)
    logging.debug(f"cd to {orig_cwd}")
