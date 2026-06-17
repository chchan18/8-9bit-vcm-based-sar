#!/usr/bin/env python3
"""Remove DAC9b_va placeholder schematic so Maestro uses the VA stop view."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
CELL = "DAC9b_va"
OUT = Path("sar9b_work/iterations/sar9b_maestro_best_q4/dac9_remove_placeholder_manifest.json")


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def main() -> None:
    client = VirtuosoClient.from_env()
    code = f'''
let((schem obj views sym va)
  schem = ddGetObj("{LIB}" "{CELL}" "schematic")
  when(schem ddDeleteObj(schem))
  obj = ddGetObj("{LIB}" "{CELL}")
  sym = dbOpenCellViewByType("{LIB}" "{CELL}" "symbol" "" "r")
  va = dbOpenCellViewByType("{LIB}" "{CELL}" "veriloga" "" "r")
  prog1(
    list("views" obj~>views~>name
         "symbol_terms" if(sym sym~>terminals~>name nil)
         "veriloga_exists" if(va t nil)
         "veriloga_terms" if(va va~>terminals~>name nil))
    when(sym dbClose(sym))
    when(va dbClose(va))))
'''
    result = client.execute_skill(code, timeout=60)
    payload = {
        "library": LIB,
        "cell": CELL,
        "status": result.status.value,
        "output": result.output,
        "errors": result.errors,
    }
    if not skill_ok(result):
        raise RuntimeError(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)
    print(f"Saved {OUT}", flush=True)


if __name__ == "__main__":
    main()
