#!/usr/bin/env python3
"""Inspect I14/I15 instTerm net mappings in source and SAR9B testbenches."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
SRC_TB = "ADC_redun1_tb"
LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"


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


def inspect_tb(client: VirtuosoClient, lib: str, cell: str) -> None:
    run_skill(
        client,
        f"inspect {lib}/{cell} I14/I15 term nets",
        f'''
let((cv out)
  cv = dbOpenCellViewByType("{lib}" "{cell}" "schematic" "" "r")
  unless(cv error("cannot open schematic"))
  out = nil
  foreach(instName '("I14" "I15")
    let((inst pairs)
      inst = dbGetInstByName(cv instName)
      pairs = nil
      when(inst
        foreach(it inst~>instTerms
          pairs = cons(list(it~>name if(it~>net it~>net~>name nil)) pairs)))
      out = cons(list(instName if(inst inst~>libName nil) if(inst inst~>cellName nil) if(inst inst~>viewName nil) reverse(pairs)) out)))
  dbClose(cv)
  reverse(out))
''',
    )


def main() -> None:
    client = VirtuosoClient.from_env()
    inspect_tb(client, SRC_LIB, SRC_TB)
    inspect_tb(client, LIB, TB_CELL)


if __name__ == "__main__":
    main()
