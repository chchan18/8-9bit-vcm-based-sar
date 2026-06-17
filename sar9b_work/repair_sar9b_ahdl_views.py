#!/usr/bin/env python3
"""Reparse SAR9B Verilog-A views and remove plain Spectre definition-file includes."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session

from prepare_sar9b_maestro_best import LIB, OUT_DIR, TB_CELL
from start_sar9b_maestro_best_run import TEST_NAME


CELLS = ("DAC8b_va", "decode_redun9to8")


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    manifest: dict[str, object] = {"library": LIB, "cells": {}}

    for cell in CELLS:
        path = f"/home/IC/Desktop/Project/{LIB}/{cell}/veriloga/veriloga.va"
        exists = ssh(client, f"test -f {path} && echo yes || echo no", timeout=20).strip()
        if exists != "yes":
            raise RuntimeError(f"missing remote Verilog-A file: {path}")
        result = run_skill(
            client,
            f"ahdlUpdateViewInfo {LIB}/{cell}",
            f'ahdlUpdateViewInfo(?lib "{LIB}" ?cell "{cell}" ?view "veriloga")',
            timeout=90,
        )
        props = run_skill(
            client,
            f"inspect updated Verilog-A view {LIB}/{cell}",
            f'''
let((va cellObj cdf out)
  cellObj = ddGetObj("{LIB}" "{cell}")
  cdf = when(cellObj cdfGetBaseCellCDF(cellObj))
  va = dbOpenCellViewByType("{LIB}" "{cell}" "veriloga" "" "r")
  out = list(
    "cell_props" if(cellObj cellObj~>prop~>name nil) if(cellObj cellObj~>prop~>value nil)
    "cdf_propList" if(cdf cdf~>propList nil)
    "veriloga_props" if(va va~>prop~>name nil) if(va va~>prop~>value nil)
    "veriloga_terms" if(va va~>terminals~>name nil))
  when(va dbClose(va))
  out)
''',
            timeout=60,
        )
        manifest["cells"][cell] = {"path": path, "update": result, "props": props}

    session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    before = run_skill(
        client,
        "read definitionFiles before clearing",
        f'maeGetEnvOption("{TEST_NAME}" ?option "definitionFiles" ?session "{session}")',
        timeout=30,
    )
    run_skill(
        client,
        "clear plain definitionFiles",
        (
            f'maeSetEnvOption("{TEST_NAME}" ?options '
            f'`(("definitionFiles" nil) ("allDefinitionFiles" nil)) '
            f'?session "{session}")'
        ),
        timeout=60,
    )
    after = run_skill(
        client,
        "read definitionFiles after clearing",
        f'maeGetEnvOption("{TEST_NAME}" ?option "definitionFiles" ?session "{session}")',
        timeout=30,
    )
    run_skill(
        client,
        "save SAR9B Maestro setup after AHDL repair",
        f'maeSaveSetup(?lib "{LIB}" ?cell "{TB_CELL}" ?view "maestro" ?session "{session}")',
        timeout=60,
    )

    remote_maestro = f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro"
    grep = ssh(
        client,
        (
            "grep -R \"definitionFiles\\|allDefinitionFiles\\|DAC8b_va/veriloga\\|decode_redun9to8/veriloga\" -n "
            f"{remote_maestro}/active.state {remote_maestro}/maestro.sdb || true"
        ),
        timeout=30,
    )
    local_dir = OUT_DIR / "maestro_files_after_ahdl_repair"
    local_dir.mkdir(parents=True, exist_ok=True)
    client.download_file(f"{remote_maestro}/active.state", str(local_dir / "active.state"))
    client.download_file(f"{remote_maestro}/maestro.sdb", str(local_dir / "maestro.sdb"))

    manifest.update(
        {
            "testbench_cell": TB_CELL,
            "test_name": TEST_NAME,
            "session": session,
            "definition_files_before": before,
            "definition_files_after": after,
            "grep": grep,
        }
    )
    out_path = OUT_DIR / "ahdl_repair_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
