#!/usr/bin/env python3
"""Import DAC9b_va into SAR9B_400MV as a Verilog-A measurement cell."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_pin


LIB = "SAR9B_400MV"
CELL = "DAC9b_va"
LOCAL_VA = Path("sar9b_work/DAC9b_va.va")
OUT_DIR = Path("sar9b_work/iterations/sar9b_maestro_best_q4")
INPUTS = ["vdd", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
OUTPUTS = ["out"]


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


def build_placeholder_schematic(client: VirtuosoClient) -> None:
    run_skill(
        client,
        "delete stale DAC9b_va cell if present",
        f'''
let((obj)
  obj = ddGetObj("{LIB}" "{CELL}")
  when(obj ddDeleteObj(obj))
  "deleted-or-absent")
''',
    )
    with client.schematic.edit(LIB, CELL) as sch:
        for i, name in enumerate(INPUTS):
            sch.add(schematic_create_pin(name, 0.0, -i * 0.5, "R0", direction="input"))
        for i, name in enumerate(OUTPUTS):
            sch.add(schematic_create_pin(name, 4.0, -i * 0.5, "R0", direction="output"))


def generate_symbol_and_veriloga(client: VirtuosoClient) -> None:
    run_skill(client, "set symbol pin sort", 'schSetEnv("ssgSortPins" "geometric")')
    run_skill(
        client,
        "generate DAC9b_va symbol",
        f'''
let((pl)
  pl = schSchemToPinList("{LIB}" "{CELL}" "schematic")
  schPinListToSymbol("{LIB}" "{CELL}" "symbol" pl))
''',
        timeout=90,
    )
    run_skill(
        client,
        "generate DAC9b_va veriloga skeleton",
        (
            f'schViewToView("{LIB}" "{CELL}" "{LIB}" "{CELL}" "symbol" "veriloga" '
            '"schSymbolToPinList" "ahdlPinListToveriloga")'
        ),
        timeout=90,
    )


def remote_va_path(client: VirtuosoClient) -> str:
    lib_path = run_skill(client, "resolve SAR9B library path", f'ddGetObj("{LIB}")~>readPath').strip().strip('"')
    if not lib_path or lib_path == "nil":
        raise RuntimeError(f"could not resolve {LIB} readPath")
    return f"{lib_path}/{CELL}/veriloga/veriloga.va"


def create_cdf(client: VirtuosoClient) -> str:
    params = {
        "VFS": "0.9",
        "VTH": "0.45",
        "trise": "1e-09",
        "tfall": "1e-09",
        "td": "0",
        "rout": "1",
    }
    param_forms = "\n".join(
        f'''
  unless(cdfFindParamByName(cdf "{name}")
    cdfCreateParam(
      cdf
      ?name "{name}"
      ?prompt "{name}"
      ?defValue "{default}"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('{name})"))'''
        for name, default in params.items()
    )
    return run_skill(
        client,
        "create DAC9b_va CDF params",
        f'''
let((cell cdf)
  cell = ddGetObj("{LIB}" "{CELL}")
  unless(cell error("missing {LIB}/{CELL}"))
  cdf = cdfGetBaseCellCDF(cell)
  unless(cdf cdf = cdfCreateBaseCellCDF(cell))
{param_forms}
  cdfSaveCDF(cdf)
  list("params" cdf~>parameters~>name))
''',
    )


def main() -> None:
    if not LOCAL_VA.exists():
        raise FileNotFoundError(LOCAL_VA)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    build_placeholder_schematic(client)
    generate_symbol_and_veriloga(client)
    remote_va = remote_va_path(client)
    client.upload_file(str(LOCAL_VA), remote_va)
    reparse_result = client.execute_skill(
        f'ahdlUpdateViewInfo(?lib "{LIB}" ?cell "{CELL}" ?view "veriloga")',
        timeout=90,
    )
    reparse = {
        "status": reparse_result.status.value,
        "output": reparse_result.output,
        "errors": reparse_result.errors,
        "note": (
            "This IC618 install rejects ahdlUpdateViewInfo signatures; "
            "Maestro uses sar9b_va_ahdl.scs ahdl_include to compile the real VA file."
        ),
    }
    print("\n== reparse DAC9b_va Verilog-A ==", flush=True)
    print(json.dumps(reparse, indent=2), flush=True)
    cdf = create_cdf(client)
    verify = run_skill(
        client,
        "verify DAC9b_va views and terms",
        f'''
let((obj sym va)
  obj = ddGetObj("{LIB}" "{CELL}")
  sym = dbOpenCellViewByType("{LIB}" "{CELL}" "symbol" "" "r")
  va = dbOpenCellViewByType("{LIB}" "{CELL}" "veriloga" "" "r")
  prog1(
    list("views" obj~>views~>name
         "symbol_terms" if(sym sym~>terminals~>name nil)
         "veriloga_terms" if(va va~>terminals~>name nil))
    when(sym dbClose(sym))
    when(va dbClose(va))))
''',
    )
    manifest = {
        "library": LIB,
        "cell": CELL,
        "local_va": str(LOCAL_VA),
        "remote_va": remote_va,
        "reparse": reparse,
        "cdf": cdf,
        "verify": verify,
    }
    path = OUT_DIR / "dac9b_va_import_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved {path}", flush=True)


if __name__ == "__main__":
    main()
