#!/usr/bin/env python3
"""Prepare the real 9-bit Maestro testbench ADC_9B_tb_v2.

This repairs the existing 9-bit Maestro cell by adding a complete schematic
copied from ADC_redun1_tb, switching I0 to TOP_9B_BINARY, and applying the
best q4-scaled binary CDAC weights to TOP_9B_BINARY.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "8BIT400MVcmredundancySAR"
SRC_TB = "ADC_redun1_tb"
TB_CELL = "ADC_9B_tb_v2"
TOP_CELL = "TOP_9B_BINARY"
OUT_DIR = Path("sar9b_work/iterations/9bit_maestro_v2_q4")

SCALED_BINARY_Q4 = {
    "C2": "Cunit*64",
    "C17": "Cunit*64",
    "C0": "Cunit*32",
    "C14": "Cunit*32",
    "C1": "Cunit*16",
    "C13": "Cunit*16",
    "C4": "Cunit*8",
    "C11": "Cunit*8",
    "C3": "Cunit*4",
    "C12": "Cunit*4",
    "C5": "Cunit*2",
    "C10": "Cunit*2",
    "C6": "Cunit*1",
    "C9": "Cunit*1",
    "C7": "Cunit*0.5",
    "C8": "Cunit*0.5",
    "C15": "Cunit*0.25",
    "C16": "Cunit*0.25",
}


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def ensure_schematic(client: VirtuosoClient, force: bool = False) -> None:
    if force:
        run_skill(
            client,
            "delete existing schematic view",
            f'''
let((cv)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  when(cv dbDelete(cv))
  "OK")
''',
            timeout=30,
        )

    views = run_skill(
        client,
        "read target cell views",
        f'''
let((obj views)
  obj = ddGetObj("{LIB}" "{TB_CELL}")
  views = if(obj obj~>views~>name nil)
  views)
''',
        timeout=20,
    )
    if '"schematic"' in views:
        print(f"{LIB}/{TB_CELL}/schematic already exists; keeping it.", flush=True)
        return

    run_skill(
        client,
        "copy source schematic into 9-bit Maestro cell",
        f'''
let((src dst)
  src = dbOpenCellViewByType("{LIB}" "{SRC_TB}" "schematic" "" "r")
  unless(src error("cannot open source schematic"))
  dst = dbCopyCellView(src "{LIB}" "{TB_CELL}" "schematic" "" t)
  unless(dst error("schematic copy failed"))
  dbClose(dst)
  dbClose(src)
  "{TB_CELL}/schematic")
''',
        timeout=60,
    )


def switch_i0_to_9b(client: VirtuosoClient) -> None:
    run_skill(
        client,
        "switch I0 master to TOP_9B_BINARY",
        f'''
let((cv inst newMaster out)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  unless(cv error("cannot open target schematic"))
  inst = dbGetInstByName(cv "I0")
  unless(inst error("I0 missing in target schematic"))
  newMaster = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "symbol" "" "r")
  unless(newMaster error("cannot open TOP_9B_BINARY symbol"))
  inst~>master = newMaster
  dbSave(cv)
  out = list(inst~>libName inst~>cellName inst~>viewName length(inst~>instTerms))
  dbClose(newMaster)
  dbClose(cv)
  out)
''',
        timeout=30,
    )


def apply_q4_weights(client: VirtuosoClient) -> None:
    for cap, value in SCALED_BINARY_Q4.items():
        run_skill(
            client,
            f"set {TOP_CELL}/{cap}",
            f'''
let((cv inst)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "a")
  unless(cv error("cannot open TOP_9B_BINARY schematic"))
  inst = dbGetInstByName(cv "{cap}")
  unless(inst error("missing cap {cap}"))
  inst~>c = "{value}"
  dbSave(cv)
  dbClose(cv)
  list("{cap}" "{value}"))
''',
            timeout=20,
        )


def verify(client: VirtuosoClient) -> dict:
    tb = run_skill(
        client,
        "verify 9-bit testbench references",
        f'''
let((cv i0 i14 i15 insts out)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "r")
  unless(cv error("cannot open target schematic for verify"))
  i0 = dbGetInstByName(cv "I0")
  i14 = dbGetInstByName(cv "I14")
  i15 = dbGetInstByName(cv "I15")
  insts = nil
  foreach(inst cv~>instances
    insts = cons(strcat(inst~>name ":" inst~>libName "/" inst~>cellName "/" inst~>viewName) insts))
  out = list(
    "I0" i0~>libName i0~>cellName i0~>viewName length(i0~>instTerms)
    "I14" i14~>libName i14~>cellName
    "I15" i15~>libName i15~>cellName
    "INSTANCES" insts)
  dbClose(cv)
  out)
''',
        timeout=30,
    )
    weights = run_skill(
        client,
        "verify TOP_9B_BINARY cap weights",
        f'''
let((cv caps)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "r")
  caps = nil
  foreach(inst cv~>instances
    when(inst~>cellName == "cap"
      caps = cons(strcat(inst~>name "=" inst~>c) caps)))
  dbClose(cv)
  caps)
''',
        timeout=30,
    )
    maestro = run_skill(
        client,
        "verify Maestro view presence",
        f'''
let((obj views)
  obj = ddGetObj("{LIB}" "{TB_CELL}")
  views = if(obj obj~>views~>name nil)
  views)
''',
        timeout=20,
    )
    return {"testbench": tb, "weights": weights, "views": maestro}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-schematic", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    ensure_schematic(client, force=args.force_schematic)
    switch_i0_to_9b(client)
    apply_q4_weights(client)
    manifest = {
        "library": LIB,
        "top_cell": TOP_CELL,
        "testbench_cell": TB_CELL,
        "source_testbench": SRC_TB,
        "weights": SCALED_BINARY_Q4,
        "verification": verify(client),
    }
    (OUT_DIR / "prepare_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved {OUT_DIR / 'prepare_manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
