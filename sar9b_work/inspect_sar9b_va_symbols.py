#!/usr/bin/env python3
"""Inspect SAR9B Verilog-A symbol terminals and TB instTerms."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"
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
                f"inspect {lib}/{cell}",
                f'''
let((sym va out)
  out = nil
  sym = dbOpenCellViewByType("{lib}" "{cell}" "symbol" "" "r")
  out = append(out list("symbol_terms" if(sym sym~>terminals~>name nil)))
  when(sym dbClose(sym))
  va = dbOpenCellViewByType("{lib}" "{cell}" "veriloga" "" "r")
  out = append(out list("veriloga_terms" if(va va~>terminals~>name nil)))
  when(va dbClose(va))
  out)
''',
            )
    run_skill(
        client,
        f"inspect {LIB}/{TB_CELL} VA instTerms",
        f'''
let((cv i14 i15)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "r")
  unless(cv error("cannot open TB"))
  i14 = dbGetInstByName(cv "I14")
  i15 = dbGetInstByName(cv "I15")
  prog1(
    list(
      "I14" i14~>libName i14~>cellName i14~>viewName length(i14~>instTerms) i14~>instTerms~>name
      "I15" i15~>libName i15~>cellName i15~>viewName length(i15~>instTerms) i15~>instTerms~>name)
    dbClose(cv)))
''',
    )


if __name__ == "__main__":
    main()
