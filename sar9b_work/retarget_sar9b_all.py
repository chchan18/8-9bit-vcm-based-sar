#!/usr/bin/env python3
"""Retarget all SAR9B_400MV schematic refs that still point at the source lib."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"

CELLS = [
    "INVX1",
    "INVX2",
    "INVX4",
    "INVX8",
    "NAND2X1",
    "NOR2X1",
    "TRIGATEX1",
    "DELAY_1",
    "OR3X1",
    "DFF",
    "DFFRN",
    "BOOTSTRAP_DIFF",
    "CLK_NOOVERLAP",
    "COMPARATOR",
    "Asycontrol_logic_9clk",
    "control",
    "TOP_9B_ADC",
    "ADC_9B_tb_best_q4",
]

SKILL_CELL_LIST = "'(" + " ".join(f'"{cell}"' for cell in CELLS) + ")"


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

    # Copy symbol views for every copied schematic cell when a source symbol exists.
    for cell in CELLS:
        run_skill(
            client,
            f"ensure symbol view {cell}",
            f'''
let((dstObj src dst)
  dstObj = ddGetObj("{LIB}" "{cell}" "symbol")
  if(dstObj then
    list("{cell}" "symbol_exists")
  else
    src = dbOpenCellViewByType("{SRC_LIB}" "{cell}" "symbol" "" "r")
    if(src then
      dst = dbCopyCellView(src "{LIB}" "{cell}" "symbol" "" t)
      dbClose(src)
      when(dst dbClose(dst))
      list("{cell}" "symbol_copied")
    else
      list("{cell}" "no_source_symbol"))))
''',
            timeout=60,
        )

    # Retarget all source-lib instances whose symbol now exists in SAR9B.
    run_skill(
        client,
        "retarget all SAR9B schematic refs",
        f'''
let((changed skipped missing)
  changed = nil
  skipped = nil
  missing = nil
  foreach(cellName {SKILL_CELL_LIST}
    let((cv)
      cv = dbOpenCellViewByType("{LIB}" cellName "schematic" "" "a")
      if(cv then
        foreach(inst cv~>instances
          when(inst~>libName == "{SRC_LIB}"
            let((m)
              m = dbOpenCellViewByType("{LIB}" inst~>cellName inst~>viewName "" "r")
              if(m then
                inst~>master = m
                changed = cons(strcat(cellName "/" inst~>name ":" inst~>cellName) changed)
                dbClose(m)
              else
                skipped = cons(strcat(cellName "/" inst~>name ":" inst~>cellName "/" inst~>viewName) skipped)))))
        schCheck(cv)
        dbSave(cv)
        dbClose(cv)
      else
        missing = cons(cellName missing))))
  list("changed" changed "skipped" skipped "missing" missing))
''',
        timeout=240,
    )

    run_skill(
        client,
        "verify remaining source-lib refs",
        f'''
let((remaining)
  remaining = nil
  foreach(cellName {SKILL_CELL_LIST}
    let((cv)
      cv = dbOpenCellViewByType("{LIB}" cellName "schematic" "" "r")
      when(cv
        foreach(inst cv~>instances
          when(inst~>libName == "{SRC_LIB}"
            remaining = cons(strcat(cellName "/" inst~>name ":" inst~>cellName "/" inst~>viewName) remaining)))
        dbClose(cv))))
  remaining)
''',
        timeout=120,
    )


if __name__ == "__main__":
    main()
