#!/usr/bin/env python3
"""Create a clean real 9-bit Maestro testbench for the best q4 point."""

from __future__ import annotations

import json
import textwrap
import argparse
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIB = "8BIT400MVcmredundancySAR"
SRC_TB = "ADC_redun1_tb"
MAESTRO_TEMPLATE_CELL = "ADC_9B_tb_v2"
TB_CELL = "ADC_9B_tb_best_q4"
TOP_CELL = "TOP_9B_BINARY"
REMOTE_LIB_DIR = f"/home/IC/Desktop/Project/{LIB}"
OUT_DIR = Path("sar9b_work/iterations/9bit_maestro_best_q4")

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


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"remote command failed ({result.returncode}): {command}\n{result.stderr}"
        )
    return result.stdout or ""


def target_exists(client: VirtuosoClient) -> bool:
    output = run_skill(
        client,
        "check target cell existence",
        f'''
let((obj)
  obj = ddGetObj("{LIB}" "{TB_CELL}")
  if(obj "EXISTS" "ABSENT"))
''',
        timeout=20,
    )
    return "EXISTS" in output


def ensure_fresh_cell_name(client: VirtuosoClient, resume_existing: bool) -> None:
    exists = target_exists(client)
    if exists and not resume_existing:
        raise RuntimeError(
            f"{LIB}/{TB_CELL} already exists; choose a new target or inspect it first"
        )
    if exists:
        print(f"{LIB}/{TB_CELL} already exists; resuming in-place.", flush=True)


def create_schematic(client: VirtuosoClient) -> None:
    views = run_skill(
        client,
        "read target views before schematic copy",
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
        "copy schematic into clean 9-bit TB cell",
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


def switch_i0(client: VirtuosoClient) -> None:
    run_skill(
        client,
        "switch I0 to TOP_9B_BINARY",
        f'''
let((cv inst newMaster out)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  unless(cv error("cannot open target schematic"))
  inst = dbGetInstByName(cv "I0")
  unless(inst error("I0 missing"))
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


def copy_and_patch_maestro(client: VirtuosoClient) -> None:
    src_dir = f"{REMOTE_LIB_DIR}/{MAESTRO_TEMPLATE_CELL}/maestro"
    dst_dir = f"{REMOTE_LIB_DIR}/{TB_CELL}/maestro"
    command = textwrap.dedent(
        f"""
        set -eu
        src={src_dir!r}
        dst={dst_dir!r}
        test -d "$src"
        if [ ! -e "$dst" ]; then
          cp -a "$src" "$dst"
        fi
        sed -i 's/{MAESTRO_TEMPLATE_CELL}/{TB_CELL}/g' "$dst/active.state" "$dst/maestro.sdb"
        find "$dst" -maxdepth 1 -type f -printf '%f\\n' | sort
        """
    ).strip()
    print("\n== copy and patch Maestro template ==", flush=True)
    print(ssh(client, command, timeout=60), flush=True)


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


def refresh_and_verify(client: VirtuosoClient) -> dict[str, str]:
    run_skill(
        client,
        "refresh library",
        f'''
let((lib)
  lib = ddGetObj("{LIB}")
  when(lib lib~>refresh)
  t)
''',
        timeout=20,
    )
    views = run_skill(
        client,
        "verify views",
        f'''
let((obj)
  obj = ddGetObj("{LIB}" "{TB_CELL}")
  if(obj obj~>views~>name nil))
''',
        timeout=20,
    )
    tb = run_skill(
        client,
        "verify 9-bit schematic references",
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
    state_refs = ssh(
        client,
        (
            f"grep -R \"{SRC_TB}\\|{MAESTRO_TEMPLATE_CELL}\\|{TB_CELL}\" -n "
            f"{REMOTE_LIB_DIR}/{TB_CELL}/maestro/active.state "
            f"{REMOTE_LIB_DIR}/{TB_CELL}/maestro/maestro.sdb"
        ),
        timeout=30,
    )
    return {
        "views": views,
        "testbench": tb,
        "weights": weights,
        "maestro_refs": state_refs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    ensure_fresh_cell_name(client, resume_existing=args.resume_existing)
    create_schematic(client)
    switch_i0(client)
    copy_and_patch_maestro(client)
    apply_q4_weights(client)
    manifest = {
        "library": LIB,
        "top_cell": TOP_CELL,
        "testbench_cell": TB_CELL,
        "source_testbench": SRC_TB,
        "maestro_template_cell": MAESTRO_TEMPLATE_CELL,
        "weights": SCALED_BINARY_Q4,
        "verification": refresh_and_verify(client),
    }
    (OUT_DIR / "prepare_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved {OUT_DIR / 'prepare_manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
