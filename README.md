# Borgmatic Restore Tool

A simple Python tool to browse and mount Borg repositories managed via borgmatic.  

Designed to run **as root** on Alpine Linux (or similar systems).  

## Features
- List borgmatic configurations
- Show all available archives
- Mount selected archives **read-only**
- Automatic passphrase handling from borgmatic config
- Cleanup mount directories on unmount
- Status display with repository label and archive name
- Supports multiple repositories

## Requirements
- Python 3.8+
- PyYAML (`pip install PyYAML`)
- Borg backup binary (`borg`) installed locally
- Root privileges
- Access to configured SSH keys for remote repositories

## Installation
1. Copy `borgmatic-restore.py` to your server.
2. Ensure it is executable:
```bash
chmod +x borgmatic-restore.py
```
3. Adjust the configuration directory if needed:
```python
CONFIG_DIR = "/root/borgmatic"
MOUNT_BASE = "/mnt/borgrestore"
BORG_BINARY = "borg"
DEFAULT_REMOTE_BORG = "borg14"
```
4. Make sure your SSH keys have access to remote repositories.

## Usage
Run the script as root:
```bash
sudo python3 borgmatic-restore.py
```

## Status & Mount Layout (ASCII Diagram)
Example of mounted archives:
```
/mnt/borgrestore
├─ cloud
│  ├─ container-os-2025-12-15T02:01:11
│  └─ container-os-2025-12-16T02:05:12
├─ web
│  └─ web-2025-12-16T02:24:15
└─ mail
   └─ mail-2025-12-10T22:01:43
```

STATUS output in the tool:
```
STATUS:
 - Repo   : cloud
   Archive: container-os-2025-12-15T02:01:11
   Mount  : /mnt/borgrestore/cloud/container-os-2025-12-15T02:01:11
 - Repo   : web
   Archive: web-2025-12-16T02:24:15
   Mount  : /mnt/borgrestore/web/web-2025-12-16T02:24:15
```

## Notes
- Mounts are **read-only**; no changes are made to the repository.
- If multiple archives are mounted, separate directories are created automatically.
- The script sets `BORG_PASSPHRASE` automatically for the session.
- SSH agent integration is **not required**; run the script as root with proper key access.

## Example Run
```text
=== Borgmatic Restore Tool (ROOT) ===

STATUS:
 - No archive mounted

Select configuration:
1) /root/borgmatic/cloud.yaml
2) /root/borgmatic/mail.yaml
3) /root/borgmatic/web.yaml
```
