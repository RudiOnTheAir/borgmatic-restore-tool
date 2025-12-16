#!/usr/bin/env python3

import os
import subprocess
import sys
import yaml

# =========================
# CONFIGURATION
# =========================

CONFIG_DIR = "/root/borgmatic"
MOUNT_BASE = "/mnt/borgrestore"
BORG_BINARY = "borg"
DEFAULT_REMOTE_BORG = "borg14"

# =========================
# HELPER FUNCTIONS
# =========================

def die(msg):
    print(msg)
    sys.exit(1)

def run(cmd, extra_env=None):
    try:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("\nCommand failed:")
        print(" ".join(cmd))
        print(e.stderr)
        sys.exit(1)

def choose_from_list(items, prompt):
    for i, item in enumerate(items, 1):
        print(f"{i}) {item}")
    while True:
        choice = input(prompt)
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print("Invalid selection.")

# =========================
# ROOT CHECK
# =========================

if os.geteuid() != 0:
    die("This script must be run as root.")

# =========================
# CONFIG HANDLING
# =========================

def list_configs():
    if not os.path.isdir(CONFIG_DIR):
        die(f"{CONFIG_DIR} does not exist")

    configs = [
        os.path.join(CONFIG_DIR, f)
        for f in os.listdir(CONFIG_DIR)
        if f.endswith((".yml", ".yaml"))
    ]

    if not configs:
        die("No borgmatic config files found")

    return sorted(configs)

def extract_config_info(config_path):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    label = None
    repo = None
    remote = DEFAULT_REMOTE_BORG

    # New borgmatic schema
    if "location" in cfg:
        loc = cfg.get("location", {})
        remote = loc.get("remote_path", DEFAULT_REMOTE_BORG)

        repos = loc.get("repositories", [])
        if repos:
            r = repos[0]
            if isinstance(r, dict):
                repo = r.get("path")
                label = r.get("label")
            elif isinstance(r, str):
                repo = r

    # Old borgmatic schema
    if not repo and "repositories" in cfg:
        repos = cfg.get("repositories", [])
        if repos:
            r = repos[0]
            if isinstance(r, dict):
                repo = r.get("path")
                label = r.get("label")
            elif isinstance(r, str):
                repo = r

    return label, repo, remote

def extract_passphrase(config_path):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    if "storage" in cfg:
        return cfg.get("storage", {}).get("encryption_passphrase")

    return cfg.get("encryption_passphrase")

# =========================
# ARCHIVES
# =========================

def list_archives(repo, remote, env):
    output = run(
        [
            BORG_BINARY,
            "list",
            repo,
            "--short",
            "--remote-path", remote,
        ],
        extra_env=env,
    )

    archives = [l.strip() for l in output.splitlines() if l.strip()]
    if not archives:
        die("No archives found")

    return archives

# =========================
# MOUNT / UNMOUNT
# =========================

def get_mounted_dirs():
    if not os.path.isdir(MOUNT_BASE):
        return []

    mounted = []
    for root, dirs, _ in os.walk(MOUNT_BASE):
        for d in dirs:
            p = os.path.join(root, d)
            if os.path.ismount(p):
                mounted.append(p)
    return mounted

def print_status():
    mounted = get_mounted_dirs()

    print("\nSTATUS:")
    if not mounted:
        print(" - No archive mounted")
        return

    for m in mounted:
        # Expected layout: /mnt/borgrestore/<label>/<archive>
        rel = m.replace(MOUNT_BASE + "/", "")
        parts = rel.split("/", 1)

        if len(parts) == 2:
            label, archive = parts
            archive = archive.replace("_", ":", 2)
        else:
            label = "-"
            archive = os.path.basename(m)

        print(f" - Repo   : {label}")
        print(f"   Archive: {archive}")
        print(f"   Mount  : {m}")

def unmount_dir(path):
    print(f"\nUnmounting {path}")
    run(["umount", path])

    try:
        os.rmdir(path)
    except OSError:
        pass

    parent = os.path.dirname(path)
    try:
        if parent != MOUNT_BASE:
            os.rmdir(parent)
    except OSError:
        pass

def mount_archive(repo, archive, remote, label, env):
    safe_name = archive.replace(":", "_")

    if label:
        mount_point = os.path.join(MOUNT_BASE, label, safe_name)
    else:
        mount_point = os.path.join(MOUNT_BASE, safe_name)

    os.makedirs(mount_point, exist_ok=True)

    print(f"\nMounting archive: {archive}")
    print(f"Mount point     : {mount_point}")

    run(
        [
            BORG_BINARY,
            "mount",
            f"{repo}::{archive}",
            mount_point,
            "--remote-path", remote,
            "--umask", "022",
        ],
        extra_env=env,
    )

# =========================
# MAIN
# =========================

def main():
    print("\n=== Borgmatic Restore Tool (ROOT) ===")
    print_status()

    mounted = get_mounted_dirs()
    if mounted:
        ans = input("\nUnmount existing archives? (y/n): ").lower()
        if ans == "y":
            for m in mounted:
                unmount_dir(m)

            print_status()

            cont = input("\nMount another archive? (y/n): ").lower()
            if cont != "y":
                print("\nExiting.")
                return
        else:
            print("\nExiting.")
            return

    configs = list_configs()
    config = choose_from_list(configs, "\nSelect configuration: ")

    print(f"\nSelected config: {config}")

    label, repo, remote = extract_config_info(config)
    if not repo:
        die(f"No repository found in {config}")

    passphrase = extract_passphrase(config)
    env = {}
    if passphrase:
        env["BORG_PASSPHRASE"] = passphrase

    print("\nConfiguration overview:")
    print(f"Label       : {label or '-'}")
    print(f"Repository  : {repo}")
    print(f"Remote Borg : {remote}")

    print("\nNotice:")
    print(" - Archives are mounted READ-ONLY")
    print(" - Borg passphrase is used automatically")
    print(" - Repository data is NOT modified")

    archives = list_archives(repo, remote, env)
    archive = choose_from_list(archives, "\nSelect archive: ")

    mount_archive(repo, archive, remote, label, env)

    print("\nDone.")
    print("Re-run the script to unmount.")

# =========================

if __name__ == "__main__":
    main()

