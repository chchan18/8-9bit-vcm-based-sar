#!/usr/bin/env python3
"""Replace legacy SAR9B 8-bit measurement chain with direct 9-bit DAC output."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic import (
    schematic_create_inst_by_master_name,
    schematic_label_instance_term,
)
from virtuoso_bridge.virtuoso.schematic.reader import read_schematic


LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"
BACKUP_CELL = "ADC_9B_tb_best_q4_pre_dac9"
DAC_CELL = "DAC9b_va"
OUT_DIR = Path("sar9b_work/iterations/sar9b_maestro_best_q4")
OLD_MEAS_NETS = ["net10", "net11", "net13", "net14", "net15", "net16", "net17", "net18"]


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 90) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def backup_schematic(client: VirtuosoClient) -> str:
    return run_skill(
        client,
        "backup pre-DAC9 measurement schematic",
        f'''
let((src dstObj dst)
  dstObj = ddGetObj("{LIB}" "{BACKUP_CELL}")
  if(dstObj then
    list("backup_exists" "{LIB}" "{BACKUP_CELL}")
  else
    src = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "r")
    unless(src error("cannot open source TB schematic"))
    dst = dbCopyCellView(src "{LIB}" "{BACKUP_CELL}" "schematic" "" t)
    unless(dst error("backup copy failed"))
    dbClose(dst)
    dbClose(src)
    list("backup_created" "{LIB}" "{BACKUP_CELL}")))
''',
    )


def remove_legacy_chain(client: VirtuosoClient) -> str:
    net_list = " ".join(f'"{n}"' for n in OLD_MEAS_NETS)
    return run_skill(
        client,
        "remove old decode_redun9to8 -> DAC8b_va chain",
        f'''
let((cv removed removedFigs)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  unless(cv error("cannot open target TB schematic"))
  removed = nil
  foreach(name list("I14" "I15")
    let((inst)
      inst = dbGetInstByName(cv name)
      when(inst
        removed = cons(strcat(name ":" inst~>cellName) removed)
        dbDeleteObject(inst))))
  removedFigs = nil
  foreach(netName list({net_list})
    let((net)
      net = car(setof(n cv~>nets n~>name == netName))
      when(net
        foreach(fig net~>figs
          removedFigs = cons(netName removedFigs)
          dbDeleteObject(fig)))))
  schCheck(cv)
  dbSave(cv)
  dbClose(cv)
  list("removed_instances" reverse(removed) "removed_fig_nets" reverse(removedFigs)))
''',
        timeout=120,
    )


def add_dac9_chain(client: VirtuosoClient) -> str:
    commands = [
        schematic_create_inst_by_master_name(LIB, DAC_CELL, "symbol", "I15", 2.1, 1.1, "R0"),
        schematic_label_instance_term("I15", "out", "out", cosmetic="clean", auto_rotation=True),
        schematic_label_instance_term("I15", "vdd", "VDD", cosmetic="clean", auto_rotation=True),
    ]
    for bit in range(9):
        commands.append(
            schematic_label_instance_term(
                "I15",
                f"b{bit}",
                f"biP<{bit}>",
                cosmetic="clean",
                auto_rotation=True,
            )
        )
    batched = "\n  ".join(commands)
    return run_skill(
        client,
        "add direct DAC9b_va measurement chain",
        f'''
let((cv i15)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  unless(cv error("cannot open target TB schematic"))
  {batched}
  i15 = dbGetInstByName(cv "I15")
  unless(i15 error("new I15 missing"))
  cdfUpdateInstParam(i15)
  schCheck(cv)
  dbSave(cv)
  prog1(
    list("I15" i15~>libName i15~>cellName i15~>viewName
         "terms" i15~>instTerms~>name
         "nets" i15~>instTerms~>net~>name
         "params" i15~>prop~>name i15~>prop~>value)
    dbClose(cv)))
''',
        timeout=120,
    )


def verify(client: VirtuosoClient) -> dict[str, object]:
    data = read_schematic(client, LIB, TB_CELL, include_positions=True, param_filters=None)
    interesting = {}
    for inst in data.get("instances", []):
        if inst["name"] in {"I0", "I14", "I15"}:
            interesting[inst["name"]] = inst
    nets = {
        name: data.get("nets", {}).get(name)
        for name in ["out", "VDD", *[f"biP<{i}>" for i in range(9)]]
    }
    checks = {
        "I14_removed": "I14" not in interesting,
        "I15_is_DAC9b_va": interesting.get("I15", {}).get("cell") == DAC_CELL,
        "I15_terms": interesting.get("I15", {}).get("terms", {}),
    }
    expected_terms = {"out": "out", "vdd": "VDD", **{f"b{i}": f"biP<{i}>" for i in range(9)}}
    checks["I15_expected_terms_match"] = checks["I15_terms"] == expected_terms
    return {
        "interesting_instances": interesting,
        "interesting_nets": nets,
        "checks": checks,
        "schematic": data,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    before = read_schematic(client, LIB, TB_CELL, include_positions=True, param_filters=None)
    backup = backup_schematic(client)
    removed = remove_legacy_chain(client)
    added = add_dac9_chain(client)
    after = verify(client)
    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "backup_cell": BACKUP_CELL,
        "dac_cell": DAC_CELL,
        "backup": backup,
        "removed": removed,
        "added": added,
        "before_instances": {
            inst["name"]: inst
            for inst in before.get("instances", [])
            if inst["name"] in {"I0", "I14", "I15"}
        },
        "after": after,
    }
    path = OUT_DIR / "measure_chain_dac9_patch_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["after"]["checks"], indent=2), flush=True)
    print(f"Saved {path}", flush=True)


if __name__ == "__main__":
    main()
