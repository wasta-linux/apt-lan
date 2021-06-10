# apt-lan
This package installs **apt-lan** to share APT packages over the LAN and minimize downloads.

### Features
- Server: Synchronizes approved APT cache folder packages to a separate "apt-lan" folder and shares it over the LAN with rsync. This folder is added as an APT source archive.
- Client: Searches the LAN for other shared "apt-lan" folders and synchronizes them locally.
