#!/usr/bin/env python3
"""Inspect SAR9B_400MV ADC_9B_tb_best_q4 measurement-chain connectivity."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"
OUT = Path("sar9b_work/iterations/sar9b_maestro_best_q4/measure_chain_before.json")


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def main() -> None:
    client = VirtuosoClient.from_env()
    skill = f'''
let((cv) (rows) (instNames)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "r")
  unless(cv error("cannot open testbench schematic"))
  instNames = list("I0" "I14" "I15")
  rows = nil
  foreach(name instNames
    let((inst terms)
      inst = dbGetInstByName(cv name)
      terms = nil
      when(inst
        foreach(it inst~>instTerms
          terms = cons(list(
            it~>name
            if(it~>net it~>net~>name "nil")
            if(it~>term it~>term~>name "nil")
            if(it~>term it~>term~>direction "nil"))
            terms))
        rows = cons(list(
          name
          inst~>libName
          inst~>cellName
          inst~>viewName
          inst~>xy
          inst~>orient
          inst~>bBox
          reverse(terms))
          rows)))
  dbClose(cv)
  reverse(rows))
'''
    result = client.execute_skill(skill, timeout=60)
    if not skill_ok(result):
        raise RuntimeError(f"inspect failed: {result}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "raw_skill_output": result.output,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(result.output)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
