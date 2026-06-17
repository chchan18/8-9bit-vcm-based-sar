#!/usr/bin/env python3
"""Run schCheck/dbSave on the repaired 9-bit Maestro schematic and top cell."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


LIB = "8BIT400MVcmredundancySAR"
CELLS = ["ADC_9B_tb_best_q4", "TOP_9B_BINARY"]


def main() -> None:
    client = VirtuosoClient.from_env()
    for cell in CELLS:
        code = f'''
let((cv out)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "a")
  unless(cv error("open failed: {cell}"))
  out = schCheck(cv)
  dbSave(cv)
  dbClose(cv)
  list("{cell}" out))
'''
        result = client.execute_skill(code, timeout=120)
        print(f"{cell}: status={result.status.value}")
        print(f"{cell}: output={result.output}")
        if result.errors:
            print(f"{cell}: errors={result.errors}")
        if result.status.value != "success":
            raise RuntimeError(f"schCheck/dbSave failed for {cell}")


if __name__ == "__main__":
    main()
