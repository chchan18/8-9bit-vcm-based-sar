#!/usr/bin/env python3
"""Start the SAR9B_400MV 9-bit Maestro run for ADC_9B_tb_best_q4."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session

from prepare_sar9b_maestro_best import LIB, OUT_DIR, SCALED_BINARY_Q4, TB_CELL, TOP_CELL
from retarget_sar9b_all import SKILL_CELL_LIST, SRC_LIB


TEST_NAME = "Vcmbased_ADC_tb_1"
MAESTRO_RESULTS_REMOTE = (
    f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/results/maestro"
)
SIM_RESULTS_REMOTE = f"/home/IC/simulation/{LIB}/{TB_CELL}/maestro/results/maestro"


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def ensure_x11_helper(client: VirtuosoClient) -> None:
    local = Path("sar9b_work/x11_type_text.py")
    if local.exists():
        client.upload_file(str(local), "/tmp/x11_type_text.py")


def press_first_window(client: VirtuosoClient, title: str) -> bool:
    tree = ssh(client, "DISPLAY=:0 xwininfo -root -tree", timeout=20)
    for line in tree.splitlines():
        if title not in line:
            continue
        match = re.search(r"\b(0x[0-9a-fA-F]+)\b", line)
        if not match:
            continue
        window = match.group(1)
        print(f"Pressing Enter on {title}: {window}", flush=True)
        ssh(client, f"DISPLAY=:0 python3 /tmp/x11_type_text.py {window} '\\n'", timeout=20)
        time.sleep(2)
        return True
    return False


def run_log_mtime(client: VirtuosoClient, run_log_remote: str) -> int:
    text = ssh(
        client,
        f"test -f {run_log_remote} && stat -c %Y {run_log_remote} || echo 0",
        timeout=20,
    ).strip()
    try:
        return int(text)
    except ValueError:
        return 0


def verify_setup(client: VirtuosoClient) -> dict[str, str]:
    tb = client.execute_skill(
        f'''
let((cv i0 i14 i15 out)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "r")
  unless(cv error("cannot open SAR9B TB schematic"))
  i0 = dbGetInstByName(cv "I0")
  i14 = dbGetInstByName(cv "I14")
  i15 = dbGetInstByName(cv "I15")
  out = list(
    "I0" i0~>libName i0~>cellName i0~>viewName length(i0~>instTerms)
    "I14" if(i14 list(i14~>libName i14~>cellName) "ABSENT")
    "I15" i15~>libName i15~>cellName i15~>instTerms~>name i15~>instTerms~>net~>name)
  dbClose(cv)
  out)
''',
        timeout=30,
    )
    if not skill_ok(tb):
        raise RuntimeError(f"TB verification failed: {tb}")
    tb_output = tb.output or ""
    for expected in [
        f'"I0" "{LIB}" "{TOP_CELL}"',
        '"I14" "ABSENT"',
        f'"I15" "{LIB}" "DAC9b_va"',
        '"b8"',
        '"biP<8>"',
    ]:
        if expected not in tb_output:
            raise RuntimeError(f"unexpected SAR9B TB reference: {tb_output}")

    caps = client.execute_skill(
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
    if not skill_ok(caps):
        raise RuntimeError(f"cap verification failed: {caps}")
    caps_output = caps.output or ""
    for cap, value in SCALED_BINARY_Q4.items():
        if f"{cap}={value}" not in caps_output:
            raise RuntimeError(f"cap weight mismatch for {cap}: expected {value}")

    source_refs = client.execute_skill(
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
    if not skill_ok(source_refs):
        raise RuntimeError(f"source-lib reference verification failed: {source_refs}")
    if (source_refs.output or "").strip() != "nil":
        raise RuntimeError(f"stale source-lib schematic refs remain: {source_refs.output}")

    maestro_refs = ssh(
        client,
        (
            f"grep -R \"{SRC_LIB}\\|ADC_redun1_tb\\|ADC_9B_tb_v2\" -n "
            f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/active.state "
            f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/maestro.sdb || true"
        ),
        timeout=30,
    )
    if maestro_refs.strip():
        raise RuntimeError(f"stale Maestro references remain:\n{maestro_refs}")

    target_refs = ssh(
        client,
        (
            f"grep -R \"{LIB}\\|{TB_CELL}\" -n "
            f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/active.state "
            f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/maestro.sdb"
        ),
        timeout=30,
    )

    return {
        "testbench": tb_output,
        "caps": caps_output,
        "source_refs": source_refs.output or "",
        "target_maestro_refs": target_refs,
    }


def trigger_run(client: VirtuosoClient) -> tuple[str, str]:
    ensure_x11_helper(client)
    try:
        session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    except Exception as exc:
        print(f"open_gui_session warning: {exc}", flush=True)
        press_first_window(client, "ADE Explorer Save Setup")
        session = open_gui_session(client, LIB, TB_CELL, timeout=90)

    result = client.execute_skill(
        f'maeRunSimulation(?session "{session}")',
        timeout=30,
    )
    if not skill_ok(result):
        raise RuntimeError(f"maeRunSimulation failed: {result}")
    history = (result.output or "").strip().strip('"')
    if not history or history == "nil":
        raise RuntimeError("maeRunSimulation returned nil")
    print(f"maeRunSimulation returned history={history}", flush=True)
    return session, history


def wait_for_run_log_update(
    client: VirtuosoClient,
    run_log_remote: str,
    start_epoch: int,
    timeout: int = 300,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        mtime = run_log_mtime(client, run_log_remote)
        if mtime >= start_epoch:
            print(f"Run log updated: {run_log_remote} mtime={mtime}", flush=True)
            return
        print("Waiting for run log update...", flush=True)
        time.sleep(10)
    raise TimeoutError("Run log did not update after triggering ADE run")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    start_epoch = int(time.time())
    setup = verify_setup(client)
    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "top_cell": TOP_CELL,
        "test_name": TEST_NAME,
        "start_epoch": start_epoch,
        "setup": setup,
    }
    (OUT_DIR / "run_start_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    session, history = trigger_run(client)
    run_log_remote = f"{MAESTRO_RESULTS_REMOTE}/{history}.log"
    results_dir_remote = f"{SIM_RESULTS_REMOTE}/{history}/1/{TEST_NAME}/psf"
    netlist_remote = f"{SIM_RESULTS_REMOTE}/{history}/1/{TEST_NAME}/netlist/input.scs"
    manifest.update(
        {
            "session": session,
            "history": history,
            "run_log_remote": run_log_remote,
            "results_dir_remote": results_dir_remote,
            "netlist_remote": netlist_remote,
        }
    )
    (OUT_DIR / "run_start_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    wait_for_run_log_update(client, run_log_remote, start_epoch)
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Started SAR9B Maestro run for {LIB}/{TB_CELL}", flush=True)


if __name__ == "__main__":
    main()
