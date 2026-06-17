#!/usr/bin/env python3
"""Apply a scaled binary CDAC point and start an ADE Explorer run.

The script intentionally starts the run and exits after the run log updates.
Do not restore the CDAC immediately; Maestro must finish netlisting/running
with this point first. Run restore.py after waveform export/analysis.
"""

from __future__ import annotations

import json
import argparse
import re
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session


LIB = "8BIT400MVcmredundancySAR"
TOP_CELL = "TOP_redun1_ADC"
TB_CELL = "ADC_redun1_tb"
RUN_LOG_REMOTE = (
    f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/results/maestro/ExplorerRun.0.log"
)

ITERATION = "scaled_binary_q4"
OUT_DIR = Path("sar9b_work/iterations") / ITERATION

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


def apply_weights(client: VirtuosoClient, weights: dict[str, str]) -> None:
    for cap, value in weights.items():
        result = client.execute_skill(
            f'''
let((cv inst)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "a")
  inst = dbGetInstByName(cv "{cap}")
  unless(inst error("Missing cap {cap}"))
  inst~>c = "{value}"
  dbSave(cv)
  dbClose(cv)
  t)
''',
            timeout=20,
        )
        if not skill_ok(result):
            raise RuntimeError(f"Failed to set {cap}={value}: {result}")
    print(f"Applied {len(weights)} weights for {ITERATION}", flush=True)


def read_weights(client: VirtuosoClient) -> dict[str, str]:
    result = client.execute_skill(
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
        timeout=20,
    )
    weights: dict[str, str] = {}
    for item in (result.output or "").replace("(", " ").replace(")", " ").replace('"', "").split():
        if "=" in item:
            name, value = item.split("=", 1)
            weights[name] = value
    return weights


def run_log_mtime(client: VirtuosoClient) -> int:
    text = ssh(
        client,
        f"test -f {RUN_LOG_REMOTE} && stat -c %Y {RUN_LOG_REMOTE} || echo 0",
        timeout=20,
    ).strip()
    try:
        return int(text)
    except ValueError:
        return 0


def trigger_run(client: VirtuosoClient) -> None:
    ensure_x11_helper(client)
    try:
        open_gui_session(client, LIB, TB_CELL, timeout=60)
    except Exception as exc:
        print(f"open_gui_session warning: {exc}", flush=True)
        press_first_window(client, "ADE Explorer Save Setup")
        open_gui_session(client, LIB, TB_CELL, timeout=60)

    try:
        result = client.execute_skill(
            '''
let((s)
  s = sevSession(hiGetCurrentWindow())
  unless(s error("No sevSession on current window"))
  sevRun(s))
''',
            timeout=20,
        )
        if skill_ok(result):
            print(f"sevRun returned: {(result.output or '').strip()}", flush=True)
            return
        print(f"sevRun non-success: {result}", flush=True)
    except Exception as exc:
        print(f"sevRun warning: {exc}", flush=True)

    if press_first_window(client, "ADE Explorer Update and Run"):
        return
    if press_first_window(client, "ADE Explorer Save Setup"):
        time.sleep(2)
        if press_first_window(client, "ADE Explorer Update and Run"):
            return
    raise RuntimeError("Could not confirm ADE Explorer run trigger")


def wait_for_run_log_update(client: VirtuosoClient, start_epoch: int, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        mtime = run_log_mtime(client)
        if mtime >= start_epoch:
            print(f"Run log updated: mtime={mtime}", flush=True)
            return
        print("Waiting for run log update...", flush=True)
        time.sleep(10)
    raise TimeoutError("Run log did not update after triggering ADE run")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iteration", default=ITERATION)
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path("sar9b_work/iterations") / args.iteration
    out_dir.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    start_epoch = int(time.time())

    apply_weights(client, SCALED_BINARY_Q4)
    weights = read_weights(client)
    manifest = {
        "iteration": args.iteration,
        "start_epoch": start_epoch,
        "run_log_remote": RUN_LOG_REMOTE,
        "target": "binary CDAC scaled to 1/4 total load, about 127.75 Cunit per side",
        "weights": {name: weights.get(name, "") for name in sorted(SCALED_BINARY_Q4)},
    }
    (out_dir / "start_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    trigger_run(client)
    wait_for_run_log_update(client, start_epoch)
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Started {args.iteration}; monitor {RUN_LOG_REMOTE}", flush=True)


if __name__ == "__main__":
    main()
