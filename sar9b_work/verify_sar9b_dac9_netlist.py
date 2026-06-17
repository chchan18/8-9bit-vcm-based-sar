#!/usr/bin/env python3
"""Generate a SAR9B Maestro netlist and verify the DAC9 measurement chain."""

from __future__ import annotations

import json
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session
from virtuoso_bridge.virtuoso.maestro.writer import create_netlist_for_corner, save_setup

from prepare_sar9b_maestro_best import LIB, OUT_DIR, TB_CELL
from start_sar9b_maestro_best_run import TEST_NAME


LOCAL_DIR = OUT_DIR / "dac9_netlist_check"


def ssh(client: VirtuosoClient, command: str, timeout: int = 60) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed ({result.returncode}): {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    save_setup(client, LIB, TB_CELL, session=session)
    remote_dir = f"/tmp/sar9b_dac9_netlist_{int(time.time())}"
    print(f"Generating netlist in {remote_dir}", flush=True)
    netlist_result = create_netlist_for_corner(client, TEST_NAME, "Nominal", remote_dir)
    print(f"maeCreateNetlistForCorner: {netlist_result}", flush=True)
    find = ssh(client, f"find {remote_dir} -type f \\( -name input.scs -o -name netlist \\) -print", timeout=60)
    candidates = [line.strip() for line in find.splitlines() if line.strip()]
    if not candidates:
        raise RuntimeError(f"no netlist file found under {remote_dir}")
    remote_netlist = next((p for p in candidates if p.endswith("input.scs")), candidates[0])
    local_netlist = LOCAL_DIR / "input.scs"
    client.download_file(remote_netlist, str(local_netlist))
    text = local_netlist.read_text(encoding="utf-8", errors="replace")
    checks = {
        "remote_dir": remote_dir,
        "remote_netlist": remote_netlist,
        "local_netlist": str(local_netlist),
        "has_DAC9b_va_instance": "DAC9b_va" in text,
        "has_DAC8b_va_instance": "DAC8b_va" in text,
        "has_decode_redun9to8_instance": "decode_redun9to8" in text,
        "has_DAC9b_ahdl_include": "DAC9b_va/veriloga/veriloga.va" in text,
        "has_legacy_DAC8_or_decoder_include": (
            "DAC8b_va/veriloga/veriloga.va" in text
            or "decode_redun9to8/veriloga/veriloga.va" in text
        ),
    }
    checks["dac9_lines"] = [
        line for line in text.splitlines()
        if "DAC9b_va" in line or "DAC8b_va" in line or "decode_redun9to8" in line
    ][:20]
    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "test_name": TEST_NAME,
        "session": session,
        "checks": checks,
    }
    path = LOCAL_DIR / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2), flush=True)
    print(f"Saved {path}", flush=True)
    if not checks["has_DAC9b_va_instance"]:
        raise RuntimeError("netlist does not contain DAC9b_va")
    if checks["has_DAC8b_va_instance"] or checks["has_decode_redun9to8_instance"]:
        raise RuntimeError("netlist still contains legacy DAC8/decoder chain")


if __name__ == "__main__":
    main()
