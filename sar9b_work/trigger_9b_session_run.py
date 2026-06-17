#!/usr/bin/env python3
"""Trigger the open ADC_9B_tb_best_q4 ADE session via maeRunSimulation."""

from __future__ import annotations

import json
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

from start_9b_maestro_best_run import LIB, OUT_DIR, TB_CELL


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def main() -> None:
    client = VirtuosoClient.from_env()
    session_expr = f'''
let((found)
  found = nil
  foreach(w hiGetWindowList()
    let((name s)
      name = hiGetWindowName(w)
      s = car(errset(axlGetWindowSession(w) nil))
      when(name && s && rexMatchp("{LIB} {TB_CELL} maestro" name)
        found = s)))
  found)
'''
    session_result = client.execute_skill(session_expr, timeout=20)
    print(f"session status={session_result.status.value}")
    print(f"session output={session_result.output}")
    if not skill_ok(session_result):
        raise RuntimeError(session_result.errors)
    session = (session_result.output or "").strip().strip('"')
    if not session or session == "nil":
        raise RuntimeError(f"No open ADE session found for {LIB}/{TB_CELL}")

    start_epoch = int(time.time())
    run_result = client.execute_skill(
        f'maeRunSimulation(?session "{session}")',
        timeout=30,
    )
    print(f"run status={run_result.status.value}")
    print(f"run output={run_result.output}")
    print(f"run errors={run_result.errors}")
    if not skill_ok(run_result):
        raise RuntimeError(run_result.errors)
    history = (run_result.output or "").strip().strip('"')
    run_log_remote = (
        f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/results/maestro/"
        f"{history}.log"
    )

    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "session": session,
        "run_output": run_result.output,
        "history": history,
        "run_log_remote": run_log_remote,
        "start_epoch": start_epoch,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "trigger_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
