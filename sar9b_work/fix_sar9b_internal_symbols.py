#!/usr/bin/env python3
"""Copy missing symbol views into SAR9B_400MV and retarget TOP_9B_ADC internals."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"
TOP_CELL = "TOP_9B_ADC"

CELLS = [
    "Asycontrol_logic_9clk",
    "CLK_NOOVERLAP",
    "BOOTSTRAP_DIFF",
    "COMPARATOR",
    "NAND2X1",
    "NOR2X1",
    "control",
]


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

    for cell in CELLS:
        run_skill(
            client,
            f"ensure symbol {LIB}/{cell}",
            f'''
let((dstObj src dst)
  dstObj = ddGetObj("{LIB}" "{cell}" "symbol")
  if(dstObj then
    list("{cell}" "symbol_exists")
  else
    src = dbOpenCellViewByType("{SRC_LIB}" "{cell}" "symbol" "" "r")
    unless(src error("missing source symbol {cell}"))
    dst = dbCopyCellView(src "{LIB}" "{cell}" "symbol" "" t)
    unless(dst error("copy symbol failed {cell}"))
    dbClose(src)
    dbClose(dst)
    list("{cell}" "symbol_copied")))
''',
            timeout=60,
        )

    run_skill(
        client,
        "retarget TOP_9B_ADC internals after symbol copy",
        f'''
let((cv changed skipped)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "a")
  unless(cv error("cannot open TOP_9B_ADC schematic"))
  changed = nil
  skipped = nil
  foreach(inst cv~>instances
    when(inst~>libName == "{SRC_LIB}"
      let((m)
        m = dbOpenCellViewByType("{LIB}" inst~>cellName inst~>viewName "" "r")
        if(m then
          inst~>master = m
          changed = cons(strcat(inst~>name ":" inst~>cellName) changed)
          dbClose(m)
        else
          skipped = cons(strcat(inst~>name ":" inst~>cellName "/" inst~>viewName) skipped)))))
  schCheck(cv)
  dbSave(cv)
  dbClose(cv)
  list("changed" changed "skipped" skipped))
''',
        timeout=120,
    )

    run_skill(
        client,
        "verify TOP_9B_ADC reference libs",
        f'''
let((cv refs)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "r")
  refs = nil
  foreach(inst cv~>instances
    refs = cons(strcat(inst~>name ":" inst~>libName "/" inst~>cellName "/" inst~>viewName) refs))
  dbClose(cv)
  refs)
''',
        timeout=30,
    )


if __name__ == "__main__":
    main()
