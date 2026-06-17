#!/usr/bin/env python3
"""Inspect analog source instances in the validated SAR9B ADC testbench."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
CELL = "ADC_9B_tb_best_q4"
OUT_DIR = Path("projects/sar9b_submodule_maestro/artifacts")


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    code = f'''
let((cv out)
  cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "r")
  unless(cv error("cannot open ADC testbench schematic"))
  out = foreach(mapcar inst cv~>instances
    when(inst~>libName == "analogLib"
      list(inst~>name inst~>cellName inst~>viewName
        foreach(mapcar prop inst~>prop
          list(prop~>name prop~>value)))))
  dbClose(cv)
  out)
'''
    result = client.execute_skill(code, timeout=60)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError("source inspection failed")
    (OUT_DIR / "adc_tb_sources_raw.json").write_text(
        json.dumps({"raw": result.output or ""}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
