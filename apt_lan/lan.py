import ipaddress
import logging
import netifaces
import smbc
import socket


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

    logging.debug(f"Connection gateway: {conn_gw}")
    if conn_gw:
        logging.debug(f"Searching for LAN IP and netmask...")
        info_list = netifaces.ifaddresses(device)[conn_fam]
        for i in info_list:
            lan_ip = i['addr']
            netmask = i['netmask']
            netw = ipaddress.ip_network(f"{lan_ip}/{netmask}", strict=False)
            logging.debug(f"Network: {lan_ip}/{netmask}")
            if ipaddress.ip_address(conn_gw) in netw:
                return lan_ip, netmask
    return None, None

def get_smb_ips(own_ip, netmask):
    """
    Search the local network for IPs with open samba ports.
    """
    lan_smb_ips = []
    smb_ports = [139, 445]
    timeout = 50 # milliseconds
    tos = timeout / 1000
    def connect(hostname, port):
        socket.setdefaulttimeout(tos)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex((hostname, port))
        return result == 0

    logging.debug(f"Checking LAN for IPs with open SMB port {smb_ports[0]}...")
    netw = ipaddress.ip_network(f"{own_ip}/{netmask}", strict=False)
    for ip in netw:
        if str(ip) == own_ip:
            logging.debug(f"Skipped own IP: {own_ip}.")
            continue
        # It takes too long to scan 2 ports for every IP, so only scanning :139.
        res = connect(str(ip), smb_ports[0])
        if res:
            logging.debug(f"LAN samba-share IP found: {ip}")
            lan_smb_ips.append(str(ip))

    return lan_smb_ips

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
        logging.error(e)
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
