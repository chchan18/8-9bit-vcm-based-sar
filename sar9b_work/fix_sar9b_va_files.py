#!/usr/bin/env python3
"""Place SAR9B Verilog-A source files where the Virtuoso netlister expects them."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
DST_LIB = "SAR9B_400MV"
CELLS = ("DAC8b_va", "decode_redun9to8")
OUT_DIR = Path("sar9b_work/iterations/sar9b_maestro_best_q4")


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    client = VirtuosoClient.from_env()
    manifest: dict[str, dict[str, str]] = {}
    for cell in CELLS:
        src = f"/home/IC/Desktop/Project/{SRC_LIB}/{cell}/veriloga/veriloga.va"
        dst_dir = f"/home/IC/Desktop/Project/{DST_LIB}/{cell}/veriloga"
        dst = f"{dst_dir}/veriloga.va"
        ssh(client, f"mkdir -p {dst_dir}", timeout=20)
        ssh(client, f"cp {src} {dst}", timeout=20)
        check = ssh(client, f"test -f {dst} && wc -l {dst}", timeout=20).strip()
        manifest[cell] = {"source": src, "destination": dst, "wc_l": check}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "va_file_fix_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
