#!/usr/bin/env python3
"""Safely test changing a copied ADC testbench I0 master to TOP_9B_BINARY."""

from __future__ import annotations

from datetime import datetime

from virtuoso_bridge import VirtuosoClient


LIB = "8BIT400MVcmredundancySAR"
SRC_TB = "ADC_redun1_tb"
NEW_TOP = "TOP_9B_BINARY"
TEST_TB_PREFIX = "ADC_9B_tb_master_test"


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==")
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}")
    print(f"output={result.output}")
    if result.errors:
        print(f"errors={result.errors}")
    return result.output or ""


def main() -> None:
    client = VirtuosoClient.from_env()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_tb = f"{TEST_TB_PREFIX}_{stamp}"
    print(f"Creating disposable schematic: {LIB}/{test_tb}/schematic")

    run_skill(
        client,
        "copy original testbench schematic",
        f'''
let((src dst)
  src = dbOpenCellViewByType("{LIB}" "{SRC_TB}" "schematic" "" "r")
  unless(src error("cannot open source schematic"))
  dst = dbCopyCellView(src "{LIB}" "{test_tb}" "schematic" "" t)
  unless(dst error("copy failed"))
  dbClose(dst)
  dbClose(src)
  "{test_tb}")
''',
    )

    run_skill(
        client,
        "read copied I0 before replacement",
        f'''
let((cv inst terms)
  cv = dbOpenCellViewByType("{LIB}" "{test_tb}" "schematic" "" "r")
  inst = dbGetInstByName(cv "I0")
  terms = nil
  when(inst
    foreach(it inst~>instTerms
      terms = cons(it~>name terms)))
  let((out)
    out = list(inst~>libName inst~>cellName inst~>viewName length(terms) terms)
    dbClose(cv)
    out))
''',
    )

    run_skill(
        client,
        "try direct inst~>master assignment",
        f'''
let((cv inst newMaster out)
  cv = dbOpenCellViewByType("{LIB}" "{test_tb}" "schematic" "" "a")
  inst = dbGetInstByName(cv "I0")
  newMaster = dbOpenCellViewByType("{LIB}" "{NEW_TOP}" "symbol" "" "r")
  out = nil
  when(inst && newMaster
    inst~>master = newMaster
    dbSave(cv)
    out = list("ASSIGNED" inst~>libName inst~>cellName inst~>viewName length(inst~>instTerms)))
  when(newMaster dbClose(newMaster))
  dbClose(cv)
  out)
''',
        timeout=30,
    )

    run_skill(
        client,
        "verify copied I0 after replacement",
        f'''
let((cv inst terms insts)
  cv = dbOpenCellViewByType("{LIB}" "{test_tb}" "schematic" "" "r")
  inst = dbGetInstByName(cv "I0")
  terms = nil
  insts = nil
  when(inst
    foreach(it inst~>instTerms
      terms = cons(it~>name terms)))
  foreach(i cv~>instances
    insts = cons(strcat(i~>name ":" i~>libName "/" i~>cellName "/" i~>viewName) insts))
  let((out)
    out = list("I0" inst~>libName inst~>cellName inst~>viewName length(terms) terms "INSTANCES" insts)
    dbClose(cv)
    out))
''',
    )

    print(f"\nDisposable cell left in place for inspection: {LIB}/{test_tb}")


if __name__ == "__main__":
    main()
