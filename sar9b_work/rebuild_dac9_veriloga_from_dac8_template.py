#!/usr/bin/env python3
"""Rebuild DAC9b_va/veriloga by templating from the working DAC8b_va AHDL OA view."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "SAR9B_400MV"
SRC_CELL = "DAC8b_va"
DST_CELL = "DAC9b_va"
TB_CELL = "ADC_9B_tb_best_q4"
LOCAL_VA = Path("sar9b_work/DAC9b_va.va")
OUT = Path("sar9b_work/iterations/sar9b_maestro_best_q4/dac9_veriloga_from_dac8_template_manifest.json")

PORTS = ["out", "vdd", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
TERM_MAPPING_ORDER = ["b8", "b7", "b6", "b5", "b4", "b3", "b2", "b1", "b0", "vdd", "out"]
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
    if not LOCAL_VA.exists():
        raise FileNotFoundError(LOCAL_VA)
    client = VirtuosoClient.from_env()
    port_list = " ".join(f'"{p}"' for p in PORTS)
    term_mapping_terms = " ".join(f'"{p}"' for p in TERM_MAPPING_ORDER)
    param_symbols = " ".join(f"'{p}" for p in PARAMS)

    rebuild = run_skill(
        client,
        "copy working DAC8 Verilog-A OA view to DAC9",
        f'''
let((src dst oldSpec oldVa oldSchem)
  src = dbOpenCellViewByType("{LIB}" "{SRC_CELL}" "veriloga" "" "r")
  unless(src error("cannot open source {LIB}/{SRC_CELL}/veriloga"))
  oldSpec = ddGetObj("{LIB}" "{DST_CELL}" "spectre")
  when(oldSpec ddDeleteObj(oldSpec))
  oldSchem = ddGetObj("{LIB}" "{DST_CELL}" "schematic")
  when(oldSchem ddDeleteObj(oldSchem))
  oldVa = ddGetObj("{LIB}" "{DST_CELL}" "veriloga")
  when(oldVa ddDeleteObj(oldVa))
  dst = dbCopyCellView(src "{LIB}" "{DST_CELL}" "veriloga" "" t)
  unless(dst error("copy DAC8 veriloga template to DAC9 failed"))
  dbClose(dst)
  dbClose(src)
  ddGetObj("{LIB}" "{DST_CELL}")~>views~>name)
''',
        timeout=120,
    )

    lib_path = run_skill(client, "resolve SAR9B library path", f'ddGetObj("{LIB}")~>readPath').strip().strip('"')
    remote_va = f"{lib_path}/{DST_CELL}/veriloga/veriloga.va"
    client.upload_file(str(LOCAL_VA), remote_va)

    patch = run_skill(
        client,
        "patch DAC9 CDF/symbol/veriloga metadata after template copy",
        f'''
let((cell cdf sym va cv i15 termMapping viewProps updateResult)
  cell = ddGetObj("{LIB}" "{DST_CELL}")
  cdf = cdfGetBaseCellCDF(cell)
  unless(cdf cdf = cdfCreateBaseCellCDF(cell))
  termMapping = list(nil)
  foreach(term list({term_mapping_terms})
    termMapping = append(termMapping list(concat(term) strcat("\\\\:" term))))
  viewProps = list(nil)
  viewProps = append(viewProps list('termMapping termMapping))
  viewProps = append(viewProps list('moduleName "{DST_CELL}"))
  viewProps = append(viewProps list('namePrefix "ahdl"))
  viewProps = append(viewProps list('termOrder list({port_list})))
  viewProps = append(viewProps list('stringParameterList nil))
  viewProps = append(viewProps list('parameterList list({param_symbols})))
  cdf~>propList = list('viewInfo list(nil 'veriloga viewProps))
  cdfSaveCDF(cdf)

  sym = dbOpenCellViewByType("{LIB}" "{DST_CELL}" "symbol" "" "a")
  unless(sym error("cannot open DAC9 symbol"))
  dbReplaceProp(sym "portOrder" "ILList" list({port_list}))
  dbReplaceProp(sym "pin#" "int" length(list({port_list})))
  dbSave(sym)
  dbClose(sym)

  va = dbOpenCellViewByType("{LIB}" "{DST_CELL}" "veriloga" "" "a")
  when(va
    unless(member("b8" va~>terminals~>name)
      dbCreateTerm(dbMakeNet(va "b8") "b8" "input"))
    dbReplaceProp(va "portOrder" "ILList" list({port_list}))
    dbReplaceProp(va "nlAction" "string" "stop")
    dbReplaceProp(va "schHDLViewName" "string" "_veriloga")
    dbSave(va)
    dbClose(va))

  ddSetForcedLib("{LIB}")
  updateResult = errset(ahdlUpdateViewInfo("{DST_CELL}") nil)

  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  when(cv
    i15 = dbGetInstByName(cv "I15")
    when(i15 cdfUpdateInstParam(i15))
    schCheck(cv)
    dbSave(cv)
    dbClose(cv))
  list("ahdlUpdateViewInfo" updateResult "views" cell~>views~>name "cdf" cdf~>propList))
''',
        timeout=120,
    )

    verify = run_skill(
        client,
        "verify DAC9 templated Verilog-A OA view",
        f'''
let((cell cdf sym va spec)
  cell = ddGetObj("{LIB}" "{DST_CELL}")
  cdf = cdfGetBaseCellCDF(cell)
  sym = dbOpenCellViewByType("{LIB}" "{DST_CELL}" "symbol" "" "r")
  va = dbOpenCellViewByType("{LIB}" "{DST_CELL}" "veriloga" "" "r")
  spec = dbOpenCellViewByType("{LIB}" "{DST_CELL}" "spectre" "" "r")
  prog1(
    list("views" cell~>views~>name
         "cdf" cdf~>propList
         "symbol_portOrder" if(sym sym~>portOrder nil)
         "symbol_terms" if(sym sym~>terminals~>name nil)
         "veriloga_open" if(va t nil)
         "veriloga_props" if(va va~>prop~>name nil) if(va va~>prop~>value nil)
         "veriloga_terms" if(va va~>terminals~>name nil)
         "veriloga_portOrder" if(va va~>portOrder nil)
         "spectre_open" if(spec t nil))
    when(sym dbClose(sym))
    when(va dbClose(va))
    when(spec dbClose(spec))))
''',
        timeout=90,
    )

    payload = {
        "library": LIB,
        "source_cell": SRC_CELL,
        "destination_cell": DST_CELL,
        "remote_va": remote_va,
        "rebuild": rebuild,
        "patch": patch,
        "verify": verify,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)
    print(f"Saved {OUT}", flush=True)


if __name__ == "__main__":
    main()
