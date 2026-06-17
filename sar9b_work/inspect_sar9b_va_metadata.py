#!/usr/bin/env python3
"""Inspect raw CDF/view metadata for SAR9B Verilog-A cells."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"
CELLS = ["DAC8b_va", "decode_redun9to8"]


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==")
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}")
    print(f"output={result.output}")
    if result.errors:
        print(f"errors={result.errors}")
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def main() -> None:
    client = VirtuosoClient.from_env()
    for lib in [SRC_LIB, LIB]:
        for cell in CELLS:
            run_skill(
                client,
                f"metadata {lib}/{cell}",
                f'''
let((cellObj cdf sym va out)
  cellObj = ddGetObj("{lib}" "{cell}")
  cdf = when(cellObj cdfGetBaseCellCDF(cellObj))
  sym = dbOpenCellViewByType("{lib}" "{cell}" "symbol" "" "r")
  va = dbOpenCellViewByType("{lib}" "{cell}" "veriloga" "" "r")
  out = list(
    "cell_props" if(cellObj cellObj~>prop~>name nil) if(cellObj cellObj~>prop~>value nil)
    "cdf_simInfo_raw" if(cdf cdf~>simInfo nil)
    "cdf_formInitProc" if(cdf cdf~>formInitProc nil)
    "cdf_doneProc" if(cdf cdf~>doneProc nil)
    "symbol_props" if(sym sym~>prop~>name nil) if(sym sym~>prop~>value nil)
    "symbol_terms" if(sym sym~>terminals~>name nil)
    "veriloga_props" if(va va~>prop~>name nil) if(va va~>prop~>value nil)
    "veriloga_terms" if(va va~>terminals~>name nil))
  when(sym dbClose(sym))
  when(va dbClose(va))
  out)
''',
                timeout=60,
            )


if __name__ == "__main__":
    main()
