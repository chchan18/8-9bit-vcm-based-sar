#!/usr/bin/env python3
"""Check, archive, and summarize the active SAR9B Maestro run."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


OUT_DIR = Path("sar9b_work/iterations/sar9b_maestro_best_q4")
MANIFEST = OUT_DIR / "run_start_manifest.json"


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def remote_file_exists(client: VirtuosoClient, path: str) -> bool:
    return ssh(client, f"test -f {path} && echo yes || echo no", timeout=20).strip() == "yes"


def remote_tail(client: VirtuosoClient, path: str, lines: int = 30) -> str:
    command = f"test -f {path} && tail -n {lines} {path} || true"
    return ssh(client, command, timeout=60)


def remote_processes(client: VirtuosoClient) -> str:
    return ssh(
        client,
        "ps -ef | grep -E 'spectre|runSimulation|maestro' | grep -v grep || true",
        timeout=60,
    )


def parse_spectre_summary(text: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    match = re.search(
        r"spectre completes with\s+(\d+)\s+errors,\s+(\d+)\s+warnings,\s+and\s+(\d+)\s+notices",
        text,
    )
    if match:
        summary.update(
            {
                "errors": int(match.group(1)),
                "warnings": int(match.group(2)),
                "notices": int(match.group(3)),
            }
        )
    elapsed = re.search(
        r"elapsed time \(wall clock\):.*?\(([^()]+)\)\.",
        text,
    )
    if elapsed:
        summary["elapsed"] = elapsed.group(1).strip()
    return summary


def parse_run_errors(text: str) -> int | None:
    match = re.search(r"Number of simulation errors:\s+(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def download_if_exists(client: VirtuosoClient, remote: str, local: Path) -> bool:
    if not remote_file_exists(client, remote):
        return False
    local.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(remote, str(local))
    return True


def check_once(client: VirtuosoClient, manifest: dict, archive: bool) -> dict:
    history = manifest["history"]
    run_log = manifest["run_log_remote"]
    results_dir = manifest["results_dir_remote"]
    spectre_out = f"{results_dir}/spectre.out"
    netlist = manifest["netlist_remote"]

    run_log_tail = remote_tail(client, run_log, lines=40)
    spectre_tail = remote_tail(client, spectre_out, lines=80)
    processes = remote_processes(client)
    netlist_exists = remote_file_exists(client, netlist)
    psf_exists = ssh(client, f"test -d {results_dir} && echo yes || echo no", timeout=20).strip() == "yes"
    completed = f"{history} completed." in run_log_tail
    run_errors = parse_run_errors(run_log_tail)
    spectre_summary = parse_spectre_summary(spectre_tail)
    spectre_errors = spectre_summary.get("errors")
    successful = (
        completed
        and run_errors == 0
        and isinstance(spectre_errors, int)
        and spectre_errors == 0
    )

    status = {
        "history": history,
        "run_log_remote": run_log,
        "results_dir_remote": results_dir,
        "netlist_remote": netlist,
        "spectre_out_remote": spectre_out,
        "psf_exists": psf_exists,
        "netlist_exists": netlist_exists,
        "completed": completed,
        "successful": successful,
        "run_errors": run_errors,
        "spectre_summary": spectre_summary,
        "active_processes": processes.strip(),
        "run_log_tail": run_log_tail,
        "spectre_tail": spectre_tail,
        "checked_epoch": int(time.time()),
    }

    if archive and completed:
        logs_dir = OUT_DIR / "logs"
        download_if_exists(client, run_log, logs_dir / f"{history}.log")
        download_if_exists(client, spectre_out, logs_dir / "spectre.out")
        download_if_exists(client, netlist, OUT_DIR / "input.scs")

    (OUT_DIR / "run_status.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )
    if successful:
        complete = {
            "library": manifest["library"],
            "testbench_cell": manifest["testbench_cell"],
            "top_cell": manifest["top_cell"],
            "history": history,
            "test_name": manifest["test_name"],
            "run_log_remote": run_log,
            "results_dir_remote": results_dir,
            "netlist_remote": netlist,
            "spectre_out_remote": spectre_out,
            "spectre": spectre_summary,
        }
        (OUT_DIR / "run_complete_manifest.json").write_text(
            json.dumps(complete, indent=2), encoding="utf-8"
        )
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--archive", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    client = VirtuosoClient.from_env()

    while True:
        status = check_once(client, manifest, archive=args.archive)
        print(
            json.dumps(
                {
                    "history": status["history"],
                    "completed": status["completed"],
                    "psf_exists": status["psf_exists"],
                    "netlist_exists": status["netlist_exists"],
                    "spectre_summary": status["spectre_summary"],
                    "active_processes": status["active_processes"],
                    "run_log_tail": status["run_log_tail"].splitlines()[-8:],
                    "spectre_tail": status["spectre_tail"].splitlines()[-8:],
                },
                indent=2,
            ),
            flush=True,
        )
        if not args.watch or status["completed"]:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
