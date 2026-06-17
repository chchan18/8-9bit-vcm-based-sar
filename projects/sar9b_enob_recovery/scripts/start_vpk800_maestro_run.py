#!/usr/bin/env python3
"""Set SAR9B Vpk=800m in the live Maestro session and start a run."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session


LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"
TOP_CELL = "TOP_9B_ADC"
TEST_NAME = "Vcmbased_ADC_tb_1"
VPK_VALUE = "800m"
OUT_DIR = Path("projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline")
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


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 60) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def set_vpk_live(client: VirtuosoClient, session: str) -> dict[str, str]:
    commands = {
        "global": f'maeSetVar("Vpk" "{VPK_VALUE}" ?session "{session}")',
        "test": (
            f'maeSetVar("Vpk" "{VPK_VALUE}" ?typeName "test" '
            f'?typeValue \'("{TEST_NAME}") ?session "{session}")'
        ),
        "corner_nominal": (
            f'maeSetVar("Vpk" "{VPK_VALUE}" ?typeName "corner" '
            f'?typeValue \'("Nominal") ?session "{session}")'
        ),
        "corner_default": (
            f'maeSetVar("Vpk" "{VPK_VALUE}" ?typeName "corner" '
            f'?typeValue \'("_default") ?session "{session}")'
        ),
    }
    outputs: dict[str, str] = {}
    for label, command in commands.items():
        try:
            outputs[label] = run_skill(client, f"set Vpk {label}", command, timeout=60)
        except Exception as exc:
            outputs[label] = f"ERROR: {exc}"
            print(f"WARNING: {label} Vpk set failed: {exc}", flush=True)

    outputs["maeGetVar"] = run_skill(
        client,
        "read Vpk",
        f'maeGetVar("Vpk" ?session "{session}")',
        timeout=60,
    )
    outputs["asiDesignVars"] = run_skill(
        client,
        "read asi design vars",
        "asiGetDesignVarList(asiGetCurrentSession())",
        timeout=60,
    )
    run_skill(
        client,
        "save Maestro setup after Vpk=800m",
        f'maeSaveSetup(?lib "{LIB}" ?cell "{TB_CELL}" ?view "maestro" ?session "{session}")',
        timeout=120,
    )
    return outputs


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


def wait_for_netlist(client: VirtuosoClient, netlist_remote: str, timeout: int = 900) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        exists = ssh(client, f"test -f {netlist_remote} && echo yes || echo no", timeout=20).strip()
        if exists == "yes":
            print(f"Netlist exists: {netlist_remote}", flush=True)
            return True
        print("Waiting for netlist...", flush=True)
        time.sleep(20)
    return False


def trigger_run(client: VirtuosoClient, session: str) -> str:
    result = client.execute_skill(f'maeRunSimulation(?session "{session}")', timeout=30)
    if not skill_ok(result):
        raise RuntimeError(f"maeRunSimulation failed: {result}")
    history = (result.output or "").strip().strip('"')
    if not history or history == "nil":
        raise RuntimeError("maeRunSimulation returned nil")
    print(f"maeRunSimulation returned history={history}", flush=True)
    return history


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    ensure_x11_helper(client)
    start_epoch = int(time.time())

    try:
        session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    except Exception as exc:
        print(f"open_gui_session warning: {exc}", flush=True)
        press_first_window(client, "ADE Explorer Save Setup")
        session = open_gui_session(client, LIB, TB_CELL, timeout=90)

    vpk_set_outputs = set_vpk_live(client, session)
    history = trigger_run(client, session)
    run_log_remote = f"{MAESTRO_RESULTS_REMOTE}/{history}.log"
    results_dir_remote = f"{SIM_RESULTS_REMOTE}/{history}/1/{TEST_NAME}/psf"
    netlist_remote = f"{SIM_RESULTS_REMOTE}/{history}/1/{TEST_NAME}/netlist/input.scs"

    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "top_cell": TOP_CELL,
        "test_name": TEST_NAME,
        "target_vpk": VPK_VALUE,
        "session": session,
        "history": history,
        "start_epoch": start_epoch,
        "run_log_remote": run_log_remote,
        "results_dir_remote": results_dir_remote,
        "netlist_remote": netlist_remote,
        "vpk_set_outputs": vpk_set_outputs,
    }
    (OUT_DIR / "run_start_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    wait_for_run_log_update(client, run_log_remote, start_epoch)
    if wait_for_netlist(client, netlist_remote):
        local_netlist = OUT_DIR / "input.scs"
        client.download_file(netlist_remote, str(local_netlist))
        text = local_netlist.read_text(encoding="utf-8", errors="replace")
        manifest["netlist_parameters_line"] = next(
            (line for line in text.splitlines() if line.startswith("parameters ")),
            "",
        )
        manifest["netlist_has_vpk800"] = "Vpk=800m" in text
        manifest["netlist_has_vpk450"] = "Vpk=450m" in text
        (OUT_DIR / "run_start_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(json.dumps(manifest, indent=2), flush=True)
        if not manifest["netlist_has_vpk800"] or manifest["netlist_has_vpk450"]:
            raise RuntimeError("generated netlist did not use clean Vpk=800m")
    else:
        print(json.dumps(manifest, indent=2), flush=True)
        raise TimeoutError("netlist was not generated before timeout")


if __name__ == "__main__":
    main()

