#!/usr/bin/env python3
"""Patch DAC9b_va CDF/symbol AHDL metadata for Spectre netlisting."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
CELL = "DAC9b_va"
TB_CELL = "ADC_9B_tb_best_q4"
OUT = Path("sar9b_work/iterations/sar9b_maestro_best_q4/dac9_va_metadata_manifest.json")

PORTS = ["out", "vdd", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
PARAMS = ["VFS", "VTH", "trise", "tfall", "td", "rout"]


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 90) -> str:
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
    client = VirtuosoClient.from_env()
    port_list = " ".join(f'"{p}"' for p in PORTS)
    param_symbols = " ".join(f"'{p}" for p in PARAMS)
    term_order_desc = " ".join(
        f'"{p}"' for p in ["b8", "b7", "b6", "b5", "b4", "b3", "b2", "b1", "b0", "vdd", "out"]
    )
    param_create_forms = "\n".join(
        f'''
  unless(cdfFindParamByName(cdf "{param}")
    cdfCreateParam(
      cdf
      ?name "{param}"
      ?prompt "{param}"
      ?defValue "{default}"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('{param})"))'''
        for param, default in {
            "VFS": "0.9",
            "VTH": "0.45",
            "trise": "1e-09",
            "tfall": "1e-09",
            "td": "0",
            "rout": "1",
        }.items()
    )
    patch_skill = f'''
let((cell cdf sym sym2 cv i15 ahdlResult symPortOrder termMapping viewProps)
  cell = ddGetObj("{LIB}" "{CELL}")
  unless(cell error("missing {LIB}/{CELL}"))
  cdf = cdfGetBaseCellCDF(cell)
  unless(cdf cdf = cdfCreateBaseCellCDF(cell))
{param_create_forms}
  termMapping = list(nil)
  foreach(term list({term_order_desc})
    termMapping = append(termMapping list(concat(term) strcat("\\\\:" term))))
  viewProps = list(nil)
  viewProps = append(viewProps list('termMapping termMapping))
  viewProps = append(viewProps list('moduleName "{CELL}"))
  viewProps = append(viewProps list('namePrefix "ahdl"))
  viewProps = append(viewProps list('termOrder list({port_list})))
  viewProps = append(viewProps list('stringParameterList nil))
  viewProps = append(viewProps list('parameterList list({param_symbols})))
  cdf~>propList = list('viewInfo list(nil 'veriloga viewProps))
  cdfSaveCDF(cdf)
  sym = dbOpenCellViewByType("{LIB}" "{CELL}" "symbol" "" "a")
  unless(sym error("cannot open DAC9 symbol"))
  dbReplaceProp(sym "portOrder" "ILList" list({port_list}))
  dbReplaceProp(sym "pin#" "int" length(list({port_list})))
  dbSave(sym)
  dbClose(sym)
  ddSetForcedLib("{LIB}")
  ahdlResult = errset(ahdlUpdateViewInfo("{CELL}") nil)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  when(cv
    i15 = dbGetInstByName(cv "I15")
    when(i15 cdfUpdateInstParam(i15))
    schCheck(cv)
    dbSave(cv)
    dbClose(cv))
  sym2 = dbOpenCellViewByType("{LIB}" "{CELL}" "symbol" "" "r")
  symPortOrder = if(sym2 sym2~>portOrder nil)
  when(sym2 dbClose(sym2))
  list("cdf_propList" cdf~>propList
       "ahdlUpdate" ahdlResult
       "symbol_portOrder" symPortOrder))
'''
    skill_path = OUT.parent / "fix_dac9_va_metadata.il"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(patch_skill, encoding="utf-8")
    metadata = run_skill(
        client,
        "patch DAC9b_va CDF viewInfo and symbol portOrder",
        patch_skill,
        timeout=120,
    )
    verify = run_skill(
        client,
        "verify DAC9b_va metadata",
        f'''
let((cell cdf sym va)
  cell = ddGetObj("{LIB}" "{CELL}")
  cdf = cdfGetBaseCellCDF(cell)
  sym = dbOpenCellViewByType("{LIB}" "{CELL}" "symbol" "" "r")
  va = dbOpenCellViewByType("{LIB}" "{CELL}" "veriloga" "" "r")
  prog1(
    list("views" cell~>views~>name
         "cdf_propList" cdf~>propList
         "symbol_props" if(sym sym~>prop~>name nil) if(sym sym~>prop~>value nil)
         "symbol_terms" if(sym sym~>terminals~>name nil)
         "veriloga_exists" if(va t nil)
         "veriloga_props" if(va va~>prop~>name nil) if(va va~>prop~>value nil)
         "veriloga_terms" if(va va~>terminals~>name nil))
    when(sym dbClose(sym))
    when(va dbClose(va))))
''',
        timeout=90,
    )
    payload = {"metadata": metadata, "verify": verify}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)
    print(f"Saved {OUT}", flush=True)


if __name__ == "__main__":
    main()
