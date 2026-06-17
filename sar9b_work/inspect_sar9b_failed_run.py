#!/usr/bin/env python3
"""Inspect remote files for the failed SAR9B Maestro run."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


OUT_DIR = Path("sar9b_work/iterations/sar9b_maestro_best_q4")
MANIFEST = OUT_DIR / "run_start_manifest.json"


def ssh(client: VirtuosoClient, command: str, timeout: int = 60) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    client = VirtuosoClient.from_env()
    history = manifest["history"]
    sim_root = (
        f"/home/IC/simulation/{manifest['library']}/{manifest['testbench_cell']}"
        f"/maestro/results/maestro/{history}"
    )
    project_root = (
        f"/home/IC/Desktop/Project/{manifest['library']}/{manifest['testbench_cell']}"
        f"/maestro/results/maestro"
    )
    commands = {
        "sim_tree": f"find {sim_root} -maxdepth 8 -printf '%y %s %p\\n' | sort || true",
        "project_tree": f"find {project_root} -maxdepth 3 -printf '%y %s %p\\n' | sort || true",
        "key_files": (
            f"for f in "
            f"{sim_root}/1/{manifest['test_name']}/psf/Job.log "
            f"{sim_root}/1/{manifest['test_name']}/netlist/artSimEnvLog "
            f"{sim_root}/1/{manifest['test_name']}/netlist/si.foregnd.log "
            f"{sim_root}/1/{manifest['test_name']}/netlist/spectre.inp "
            f"{sim_root}/1/{manifest['test_name']}/netlist/spectre.sim "
            f"{sim_root}/1/{manifest['test_name']}/netlist/control "
            f"{sim_root}/1/{manifest['test_name']}/netlist/netlistHeader "
            f"{sim_root}/1/{manifest['test_name']}/netlist/ihnl/cds17/netlist "
            f"{sim_root}/1/{manifest['test_name']}/netlist/ihnl/cds18/netlist "
            f"{sim_root}/1/{manifest['test_name']}/netlist/ihnl/control "
            f"{sim_root}/1/{manifest['test_name']}/netlist/ihnl/blockdirmap; "
            "do echo ===== $f; test -f $f && cat $f || echo MISSING; done"
        ),
        "error_grep": (
            "grep -RIn "
            "'ERROR\\|Error\\|OSSHNL\\|failed\\|Failed\\|cannot\\|Cannot\\|undefined\\|Undefined\\|"
            "netlist\\|Netlist\\|simulator' "
            f"{sim_root} {project_root}/{history}.log 2>/dev/null || true"
        ),
    }
    report = {name: ssh(client, command, timeout=120) for name, command in commands.items()}
    out_path = OUT_DIR / "failed_run_inspection.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Saved {out_path}", flush=True)


if __name__ == "__main__":
    main()
