#!/usr/bin/env python3
"""Probe the local IC618 ahdlUpdateViewInfo call signature."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
CELL = "DAC8b_va"
OUT = Path("sar9b_work/iterations/sar9b_maestro_best_q4/ahdl_update_probe.json")


FORMS = {
    "keywords_lib_cell_view": f'ahdlUpdateViewInfo(?lib "{LIB}" ?cell "{CELL}" ?view "veriloga")',
    "keywords_libName_cellName_viewName": f'ahdlUpdateViewInfo(?libName "{LIB}" ?cellName "{CELL}" ?viewName "veriloga")',
    "positional_strings_3": f'ahdlUpdateViewInfo("{LIB}" "{CELL}" "veriloga")',
    "positional_strings_4": f'ahdlUpdateViewInfo("{LIB}" "{CELL}" "veriloga" nil)',
    "dd_view_obj": f'let((obj) obj=ddGetObj("{LIB}" "{CELL}" "veriloga") ahdlUpdateViewInfo(obj))',
    "dd_cell_obj_view": f'let((obj) obj=ddGetObj("{LIB}" "{CELL}") ahdlUpdateViewInfo(obj "veriloga"))',
    "db_cv_read": f'let((cv out) cv=dbOpenCellViewByType("{LIB}" "{CELL}" "veriloga" "" "r") out=ahdlUpdateViewInfo(cv) when(cv dbClose(cv)) out)',
    "db_cv_append": f'let((cv out) cv=dbOpenCellViewByType("{LIB}" "{CELL}" "veriloga" "" "a") out=ahdlUpdateViewInfo(cv) when(cv dbSave(cv) dbClose(cv)) out)',
}


def main() -> None:
    client = VirtuosoClient.from_env()
    results: dict[str, dict[str, object]] = {}
    for name, code in FORMS.items():
        print(f"\n== {name} ==", flush=True)
        result = client.execute_skill(code, timeout=60)
        data = {
            "status": result.status.value,
            "output": result.output,
            "errors": result.errors,
        }
        results[name] = data
        print(json.dumps(data, indent=2), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved: {OUT}", flush=True)


if __name__ == "__main__":
    main()
