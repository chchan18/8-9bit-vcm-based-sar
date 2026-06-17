#!/usr/bin/env python3
"""Archive a submodule Maestro history directory for debugging."""

from __future__ import annotations

import argparse
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cell")
    parser.add_argument("history")
    args = parser.parse_args()

    client = VirtuosoClient.from_env()
    local = Path("projects/sar9b_submodule_maestro/runs") / args.cell / args.history
    local.mkdir(parents=True, exist_ok=True)
    desktop_log = (
        f"/home/IC/Desktop/Project/{LIB}/{args.cell}/maestro/results/maestro/"
        f"{args.history}.log"
    )
    sim_hist = f"/home/IC/simulation/{LIB}/{args.cell}/maestro/results/maestro/{args.history}"
    remote_tar = f"/tmp/{args.cell}_{args.history}.tgz"
    print(
        ssh(
            client,
            f"tar czf {remote_tar} -C {sim_hist} . && ls -lh {remote_tar}",
            timeout=60,
        ),
        flush=True,
    )
    client.download_file(desktop_log, str(local / f"{args.history}.log"))
    client.download_file(remote_tar, str(local / "history.tgz"))
    print(
        ssh(
            client,
            f"find {sim_hist} -maxdepth 4 -type f -printf '%p\\n' | sort",
            timeout=30,
        ),
        flush=True,
    )
    print(f"Saved under {local}", flush=True)


if __name__ == "__main__":
    main()
