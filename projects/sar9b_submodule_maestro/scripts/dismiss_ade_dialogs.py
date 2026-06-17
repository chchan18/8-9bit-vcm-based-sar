#!/usr/bin/env python3
"""Dismiss lingering ADE/Maestro modal dialogs on the remote X display."""

from __future__ import annotations

import re
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


HELPER = Path("sar9b_work/x11_type_text.py")
REMOTE_HELPER = "/tmp/x11_type_text.py"
PATTERNS = [
    "ADE Assembler Update and Run",
    "ADE Explorer Update and Run",
    "Save Setup",
]


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    client = VirtuosoClient.from_env()
    client.upload_file(str(HELPER), REMOTE_HELPER)
    tree = ssh(client, "DISPLAY=:0 xwininfo -root -tree", timeout=30)
    hits = []
    for line in tree.splitlines():
        if not any(pattern in line for pattern in PATTERNS):
            continue
        match = re.search(r"\b(0x[0-9a-fA-F]+)\b", line)
        if match:
            hits.append((match.group(1), line.strip()))
    for window, line in hits:
        print(f"Dismissing {window}: {line}", flush=True)
        ssh(client, f"DISPLAY=:0 python3 {REMOTE_HELPER} {window} '\\e'", timeout=30)
    if not hits:
        print("No ADE modal dialogs matched.", flush=True)


if __name__ == "__main__":
    main()
