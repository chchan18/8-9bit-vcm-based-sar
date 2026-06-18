#!/usr/bin/env python3
"""Run SAR9B submodule robustness sweeps through Maestro."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import close_gui_session, open_gui_session, set_var

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_submodule_maestro_tests import (  # noqa: E402
    LIB,
    PROJECT_DIR,
    SAMPLE_STEP,
    TEST_NAME,
    download_if_exists,
    export_waveforms,
    offline_metric_values,
    parse_maestro_metrics,
    parse_time,
    quick_metrics,
    remote_epoch,
    run_skill,
    trigger_run,
    wait_for_completion,
)


SETUP_MANIFEST = PROJECT_DIR / "artifacts/submodule_maestro_setup_manifest.json"
RUN_ROOT = PROJECT_DIR / "runs"


TEST_MATRIX: dict[str, list[dict[str, object]]] = {
    "TB_SUBMOD_COMPARATOR_PERF": [
        {"id": "cmp_nominal", "vars": {}},
        {"id": "cmp_vdiff_2m", "vars": {"vdiff": "2m"}},
        {"id": "cmp_vdiff_5m", "vars": {"vdiff": "5m"}},
        {"id": "cmp_vdiff_20m", "vars": {"vdiff": "20m"}},
        {"id": "cmp_cload_5f", "vars": {"cload": "5f"}},
        {"id": "cmp_vdd_800m", "vars": {"vdd": "800m"}},
    ],
    "TB_SUBMOD_CLK_NOOVERLAP_PERF": [
        {"id": "clk_nominal", "vars": {}},
        {"id": "clk_cload_1f", "vars": {"cload": "1f"}},
        {"id": "clk_cload_5f", "vars": {"cload": "5f"}},
        {"id": "clk_vdd_800m", "vars": {"vdd": "800m"}},
    ],
    "TB_SUBMOD_ASYCTRL_9CLK_PERF": [
        {"id": "asy_nominal", "vars": {}},
        {"id": "asy_valid_per_2n", "vars": {"valid_per": "2n"}},
        {"id": "asy_valid_per_3n", "vars": {"valid_per": "3n"}},
        {"id": "asy_cload_3f", "vars": {"cload": "3f"}},
        {"id": "asy_vdd_800m", "vars": {"vdd": "800m"}},
    ],
    "TB_SUBMOD_BOOTSTRAP_DIFF_PERF": [
        {"id": "boot_nominal", "vars": {}},
        {"id": "boot_vdiff_50m", "vars": {"vdiff": "50m"}},
        {"id": "boot_vdiff_200m", "vars": {"vdiff": "200m"}},
        {"id": "boot_cload_10f", "vars": {"cload": "10f"}},
        {"id": "boot_vdd_800m", "vars": {"vdd": "800m"}},
    ],
}


def set_case_vars(
    client: VirtuosoClient,
    session: str,
    base_vars: dict[str, str],
    overrides: dict[str, str],
) -> dict[str, str]:
    merged = {**base_vars, **overrides}
    for name, value in merged.items():
        set_var(client, name, value, session=session)
        set_var(client, name, value, type_name="test", type_value=f'("{TEST_NAME}")', session=session)
    return merged


def export_case(
    client: VirtuosoClient,
    spec: dict[str, object],
    summary: dict[str, object],
    case_dir: Path,
) -> dict[str, object]:
    cell = str(spec["cell"])
    signals = [str(sig) for sig in spec["signals"]]
    history = str(summary["history"])
    local_log = case_dir / f"{history}.log"
    maestro_metrics = {}
    if local_log.exists():
        maestro_metrics = parse_maestro_metrics(local_log.read_text(encoding="utf-8", errors="replace"))
    summary["maestro_metrics"] = maestro_metrics

    if summary.get("run_errors") not in (0, None):
        summary["waveform_points"] = 0
        summary["metrics"] = {}
        summary["error"] = "Maestro reported simulation errors; waveform export skipped."
        return summary

    wave_defs = [(sig, f'VT("{sig}")') for sig in signals]
    offline_sources: dict[str, str] = {}
    for item in list(spec.get("offline_metrics", [])):
        source = str(item.get("source", ""))
        expr = str(item.get("waveform_expr", ""))
        if source and expr and source not in offline_sources:
            offline_sources[source] = expr
    wave_defs.extend((source, expr) for source, expr in offline_sources.items())

    times, waves = export_waveforms(
        client,
        str(summary["results_dir_remote"]),
        wave_defs,
        case_dir / "waveforms.txt",
        parse_time(str(spec["stop"])),
    )
    metrics = quick_metrics(cell, times, waves)
    offline_metrics = offline_metric_values(spec, times, waves)
    if offline_metrics:
        metrics["offline"] = offline_metrics
    summary["waveform_points"] = len(times)
    summary["metrics"] = metrics
    return summary


def run_case(
    client: VirtuosoClient,
    session: str,
    spec: dict[str, object],
    case: dict[str, object],
    out_root: Path,
    trigger: str,
) -> dict[str, object]:
    cell = str(spec["cell"])
    case_id = str(case["id"])
    overrides = {str(k): str(v) for k, v in dict(case.get("vars", {})).items()}
    actual_vars = set_case_vars(client, session, dict(spec["vars"]), overrides)
    run_skill(client, f"save {cell} {case_id}", f'maeSaveSetup(?session "{session}")', timeout=60)

    start_epoch = remote_epoch(client)
    history = trigger_run(client, session, cell, start_epoch, trigger)
    run_log_remote = f"/home/IC/Desktop/Project/{LIB}/{cell}/maestro/results/maestro/{history}.log"
    results_dir_remote = f"/home/IC/simulation/{LIB}/{cell}/maestro/results/maestro/{history}/1/{TEST_NAME}/psf"
    spectre_out_remote = f"{results_dir_remote}/spectre.out"
    netlist_remote = f"/home/IC/simulation/{LIB}/{cell}/maestro/results/maestro/{history}/1/{TEST_NAME}/netlist/input.scs"
    status = wait_for_completion(client, history, run_log_remote, spectre_out_remote)

    case_dir = out_root / cell / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    download_if_exists(client, run_log_remote, case_dir / f"{history}.log")
    download_if_exists(client, spectre_out_remote, case_dir / "spectre.out")
    download_if_exists(client, netlist_remote, case_dir / "input.scs")

    summary: dict[str, object] = {
        "cell": cell,
        "case_id": case_id,
        "history": history,
        "session": session,
        "variables": actual_vars,
        "overrides": overrides,
        "signals": [str(sig) for sig in spec["signals"]],
        "run_log_remote": run_log_remote,
        "results_dir_remote": results_dir_remote,
        "spectre_out_remote": spectre_out_remote,
        "netlist_remote": netlist_remote,
        "completed": status["completed"],
        "run_errors": status["run_errors"],
        "spectre_summary": status["spectre_summary"],
    }
    summary = export_case(client, spec, summary, case_dir)
    (case_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def select_specs(manifest: dict[str, object], cell: str | None) -> list[dict[str, object]]:
    specs = [dict(spec) for spec in manifest["testbenches"]]
    if cell:
        specs = [spec for spec in specs if spec["cell"] == cell]
    if not specs:
        raise SystemExit(f"Unknown --cell value: {cell}")
    return specs


def select_cases(cell: str, only_case: str | None) -> list[dict[str, object]]:
    cases = TEST_MATRIX[cell]
    if only_case:
        cases = [case for case in cases if case["id"] == only_case]
    if not cases:
        raise SystemExit(f"Unknown --case value for {cell}: {only_case}")
    return cases


def collect_case_summaries(out_root: Path) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for cell, cases in TEST_MATRIX.items():
        for case in cases:
            case_id = str(case["id"])
            path = out_root / cell / case_id / "summary.json"
            if not path.exists():
                continue
            summary = json.loads(path.read_text(encoding="utf-8"))
            key = (str(summary.get("cell", cell)), str(summary.get("case_id", case_id)))
            if key in seen:
                continue
            seen.add(key)
            summaries.append(summary)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", help="run only one testbench cell")
    parser.add_argument("--case", help="run only one case id for the selected cell")
    parser.add_argument(
        "--trigger",
        choices=["gui-button", "mae", "callback"],
        default="callback",
        help="run trigger method",
    )
    parser.add_argument("--tag", help="output tag under runs/; default is a timestamp")
    args = parser.parse_args()

    manifest = json.loads(SETUP_MANIFEST.read_text(encoding="utf-8"))
    specs = select_specs(manifest, args.cell)
    tag = args.tag or f"robustness_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_root = RUN_ROOT / tag
    out_root.mkdir(parents=True, exist_ok=True)

    client = VirtuosoClient.from_env()
    summaries: list[dict[str, object]] = []
    for spec in specs:
        cell = str(spec["cell"])
        cases = select_cases(cell, args.case)
        session = open_gui_session(client, LIB, cell, timeout=180)
        try:
            for case in cases:
                print(f"\n## Running {cell} / {case['id']} ##", flush=True)
                summaries.append(run_case(client, session, spec, case, out_root, args.trigger))
            set_case_vars(client, session, dict(spec["vars"]), {})
            run_skill(client, f"restore nominal {cell}", f'maeSaveSetup(?session "{session}")', timeout=60)
        finally:
            try:
                close_gui_session(client, session, save=True, timeout=90)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: close_gui_session failed for {cell}: {exc}", flush=True)

    all_summaries = collect_case_summaries(out_root)
    result = {
        "library": LIB,
        "test_name": TEST_NAME,
        "sample_step_s": SAMPLE_STEP,
        "trigger": args.trigger,
        "tag": tag,
        "matrix": TEST_MATRIX,
        "runs": all_summaries,
    }
    manifest_path = out_root / "robustness_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    latest_path = RUN_ROOT / "submodule_robustness_manifest.json"
    latest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print(f"Saved: {manifest_path}", flush=True)
    print(f"Saved latest: {latest_path}", flush=True)


if __name__ == "__main__":
    main()
