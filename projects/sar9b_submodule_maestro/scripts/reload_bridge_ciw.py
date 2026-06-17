#!/usr/bin/env python3
"""Reload virtuoso-bridge daemon by typing commands into the CIW."""

from __future__ import annotations

import re
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


HELPER = Path("sar9b_work/x11_type_text.py")
REMOTE_HELPER = "/tmp/x11_type_text.py"
REMOTE_CMD = "/tmp/reload_virtuoso_bridge.il"
SETUP_IL = "/tmp/virtuoso_bridge_IC/Chonghao_Chen/virtuoso_bridge/virtuoso_setup.il"


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def find_ciw_window(tree: str) -> str:
    excluded = [
        "update and run",
        "save setup",
        "add instance",
        "edit object properties",
        "open file",
        "descend",
        "graph tip",
        "tools",
    ]
    candidates = []
    for line in tree.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in excluded):
            continue
        if (
            "command interpreter" in lowered
            or "ciw" in lowered
            or ("virtuoso" in lowered and "browser" not in lowered)
        ):
            match = re.search(r"\b(0x[0-9a-fA-F]+)\b", line)
            if match:
                size = re.search(r"\s(\d+)x(\d+)[+-]", line)
                area = 0
                if size:
                    area = int(size.group(1)) * int(size.group(2))
                candidates.append((area, match.group(1), line.strip()))
    if not candidates:
        raise RuntimeError(f"could not find CIW window in tree:\n{tree}")
    candidates.sort(reverse=True)
    print("CIW candidates:", flush=True)
    for _, window, line in candidates:
        print(f"  {window}: {line}", flush=True)
    return candidates[0][1]


def main() -> None:
    client = VirtuosoClient.from_env()
    client.upload_file(str(HELPER), REMOTE_HELPER)
    command_text = f'RBStopAll()\nload("{SETUP_IL}")\n'
    local_cmd = Path("projects/sar9b_submodule_maestro/artifacts/reload_virtuoso_bridge.il")
    local_cmd.parent.mkdir(parents=True, exist_ok=True)
    local_cmd.write_text(command_text, encoding="ascii")
    client.upload_file(str(local_cmd), REMOTE_CMD)
    tree = ssh(client, "DISPLAY=:0 xwininfo -root -tree", timeout=30)
    window = find_ciw_window(tree)
    ssh(
        client,
        f"DISPLAY=:0 python3 {REMOTE_HELPER} {window} --file {REMOTE_CMD}",
        timeout=60,
    )
    print(f"Typed reload commands into {window}", flush=True)


if __name__ == "__main__":
    main()
