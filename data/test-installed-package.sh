#!/bin/bash

# ------------------------------------------------------------------------------
# Test apt-lan-rsync
# ------------------------------------------------------------------------------
NAME="apt-lan-rsync"

# Verify that service is started and enabled.
stats=$(systemctl show apt-lan-rsync.service)
# LoadState=loaded
load_state=$(echo "$stats" | grep LoadState | awk -F'=' '{print $2}')
if [[ "$load_state" == 'loaded' ]]; then
    echo "${NAME}.service loaded"
else
    echo "Error: ${NAME}.service not loaded. LoadState=$load_state"
    exit 1
fi
# ActiveState=active
active_state=$(echo "$stats" | grep ActiveState | awk -F'=' '{print $2}')
if [[ "$active_state" == 'active' ]]; then
    echo "${NAME}.service active"
else
    echo "Error: ${NAME}.service not active. ActiveState=$active_state"
    exit 1
fi
# SubState=running
sub_state=$(echo "$stats" | grep SubState | awk -F'=' '{print $2}')
if [[ "$sub_state" == 'running' ]]; then
    echo "${NAME}.service running"
else
    echo "Error: ${NAME}.service not running. SubState=$sub_state"
    exit 1
fi

# Verify that the rsyncd process is running with the correct config file.
rsyncd_conf=$(pgrep -a '.*rsync.*' | cut -d' ' -f5 | cut -d'=' -f2)
if [[ "$rsyncd_conf" == '/etc/apt-lan-rsyncd.conf' ]]; then
    echo "rsyncd running with config at ${rsyncd_conf}"
elif [[ -z "$rsyncd_conf" ]]; then
    echo "Error: rsyncd not running."
    exit 1
else
    echo "Error: rsyncd using wrong config at ${rsyncd_conf}."
    exit 1
fi

# Verify that the proper port is open.
ports=$(ss -nlt | grep 22022)
if [[ "$ports" ]]; then
    echo "rsyncd listening on port 22022"
else
    echo "Error: rsyncd not listening on port 22022."
    exit 1
fi
echo -e "apt-lan-rsync is installed properly.\n"

# ------------------------------------------------------------------------------
# Test apt-lan
# ------------------------------------------------------------------------------
NAME='apt-lan'
RELEASE=$(grep VERSION_CODENAME /etc/os-release | cut -d'=' -f2)
ARCH='amd64'
if [[ $(uname -p) == 'i386' ]]; then
    ARCH='i386'
fi

# Ensure that Packages.gz exists.
pkg_gz="/var/cache/apt-lan/${RELEASE}/binary-${ARCH}/Packages.gz"
if [[ ! -e $pkg_gz ]]; then
    echo "Error: $pkg_gz does not exist."
    exit 1
fi

# Ensure valid Packages.gz file in apt-lan cache.
apt_update=$(sudo apt-get update)
if [[ $? -eq 0 ]]; then
    # Update successful, Pachages.gz file is good.
    echo "$pkg_gz is good."
else
    echo "Error: apt-get update error. Maybe bad Packages.gz file?:"
    echo "$apt_update"
    exit 1
fi

# Ensure that the cron scripts are found in default locations.
client_sync="/etc/cron.hourly/apt-lan-client"
if [[ -x "$client_sync" ]]; then
    echo "$client_sync found"
else
    echo "Error: $client_sync not found."
    exit 1
fi
server_sync="/etc/cron.daily/apt-lan-server"
if [[ -x "$server_sync" ]]; then
    echo "$server_sync found"
else
    echo "Error: $server_sync not found."
    exit 1
fi

# Ensure that other apt-lan peers can be found.
#   Create 2nd system running bionic.
#   Allow bionic and focal packages into this system's apt-lan cache.

# Ensure that only approved peer packages are copied locally?
