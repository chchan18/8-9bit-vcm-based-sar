#!/usr/bin/env python3
"""Inspect SAR9B submodule symbols and schematic hierarchy."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
OUT_DIR = Path("projects/sar9b_submodule_maestro/artifacts")
CANDIDATES = [
    "COMPARATOR",
    "BOOTSTRAP_DIFF",
    "CLK_NOOVERLAP",
    "Asycontrol_logic_9clk",
    "control",
    "DFF",
    "DFFRN",
    "DELAY_1",
]


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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    summary: dict[str, str] = {}

    for cell in CANDIDATES:
        summary[cell] = run_skill(
            client,
            f"inspect {LIB}/{cell}",
            f'''
let((obj views sym sch terms insts)
  obj = ddGetObj("{LIB}" "{cell}")
  views = if(obj obj~>views~>name nil)
  sym = dbOpenCellViewByType("{LIB}" "{cell}" "symbol" "" "r")
  terms = if(sym
    foreach(mapcar term sym~>terminals
      list(term~>name term~>direction))
    nil)
  when(sym dbClose(sym))
  sch = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")
  insts = if(sch
    foreach(mapcar inst sch~>instances
      list(inst~>name inst~>libName inst~>cellName inst~>viewName))
    nil)
  when(sch dbClose(sch))
  list("cell" "{cell}" "views" views "terms" terms "instances" insts))
''',
            timeout=60,
        )

    (OUT_DIR / "submodule_symbol_inspection_raw.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nSaved: {OUT_DIR / 'submodule_symbol_inspection_raw.json'}", flush=True)


if __name__ == "__main__":
    main()
