#!/usr/bin/env python3
"""Check remote Maestro/Spectre status for a submodule testbench."""

from __future__ import annotations

import argparse

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cell")
    args = parser.parse_args()

    client = VirtuosoClient.from_env()
    cmd = f'''
set -eu
base=/home/IC/Desktop/Project/{LIB}/{args.cell}/maestro/results/maestro
sim=/home/IC/simulation/{LIB}/{args.cell}/maestro/results/maestro
printf "desktop histories:\\n"
find "$base" -maxdepth 1 -type f -name "*.log" -printf "%f %TY-%Tm-%Td %TH:%TM:%TS\\n" 2>/dev/null | sort || true
printf "simulation dirs:\\n"
find "$sim" -maxdepth 1 -type d -name "Interactive.*" -printf "%f %TY-%Tm-%Td %TH:%TM:%TS\\n" 2>/dev/null | sort || true
printf "processes:\\n"
ps -ef | grep -E "{args.cell}|spectre|runSimulation" | grep -v grep || true
printf "latest log tail:\\n"
latest=$(find "$base" -maxdepth 1 -type f -name "*.log" -printf "%T@ %p\\n" 2>/dev/null | sort -n | tail -1 | cut -d" " -f2- || true)
if [ -n "$latest" ]; then tail -n 80 "$latest"; fi
printf "latest spectre tail:\\n"
latest_hist=$(find "$sim" -maxdepth 1 -type d -name "Interactive.*" -printf "%T@ %p\\n" 2>/dev/null | sort -n | tail -1 | cut -d" " -f2- || true)
if [ -n "$latest_hist" ]; then
  sout=$(find "$latest_hist" -path "*/psf/spectre.out" -type f | head -1 || true)
  if [ -n "$sout" ]; then tail -n 100 "$sout"; fi
fi
'''
    result = client.ssh_runner.run_command(cmd, timeout=30)
    print(result.stdout or "")
    if result.stderr:
        print(result.stderr)


if __name__ == "__main__":
    main()
