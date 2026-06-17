#!/usr/bin/env python3
"""Inspect/fix schematic OA properties that block incremental netlisting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
CELLS = [
    "TB_SUBMOD_COMPARATOR_PERF",
    "TB_SUBMOD_CLK_NOOVERLAP_PERF",
    "TB_SUBMOD_ASYCTRL_9CLK_PERF",
    "TB_SUBMOD_BOOTSTRAP_DIFF_PERF",
]
OUT_DIR = Path("projects/sar9b_submodule_maestro/artifacts")


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 60) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    manifest: dict[str, object] = {"fix": args.fix, "cells": {}}
    for cell in CELLS:
        before = run_skill(
            client,
            f"inspect before {cell}",
            f'''
let((cv out)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")
  unless(cv error("open failed"))
  out = list(
    "propNames" cv~>prop~>name
    "propValues" cv~>prop~>value
    "connectivityLastUpdated" cv~>connectivityLastUpdated
    "lastSchematicExtraction" cv~>lastSchematicExtraction)
  dbClose(cv)
  out)
''',
            timeout=60,
        )
        after = ""
        if args.fix:
            after = run_skill(
                client,
                f"fix/check/save {cell}",
                f'''
let((cv out)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "a")
  unless(cv error("open failed"))
  schCheck(cv)
  dbReplaceProp(cv "instance#" 'int length(cv~>instances))
  dbSave(cv)
  dbSetConnCurrent(cv)
  dbSave(cv)
  out = list(
    "propNames" cv~>prop~>name
    "propValues" cv~>prop~>value
    "connectivityLastUpdated" cv~>connectivityLastUpdated
    "schGeometryLastUpdated" cv~>schGeometryLastUpdated
    "lastSchematicExtraction" cv~>lastSchematicExtraction)
  dbClose(cv)
  out)
''',
                timeout=120,
            )
        manifest["cells"][cell] = {"before": before, "after": after}

    out_path = OUT_DIR / "schematic_props_fix_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
