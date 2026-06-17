#!/usr/bin/env python3
"""Resample a Maestro /out waveform at phase offsets and measure SINAD/ENOB."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

from dout9_offline_measure import (
    NSAMPLES,
    SAMPLE_START,
    SAMPLE_STEP,
    _skill_ok,
    dft_metrics,
    parse_waveform,
)


DEFAULT_RESULTS_DIR = (
    "/home/IC/simulation/SAR9B_400MV/ADC_9B_tb_best_q4/maestro/results/"
    "maestro/Interactive.10/1/Vcmbased_ADC_tb_1/psf"
)


def export_out_phase(
    client: VirtuosoClient,
    results_dir: str,
    out_path: Path,
    offset_ps: float,
) -> tuple[list[float], list[float]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    remote_path = f"/tmp/out_phase_{uuid.uuid4().hex}.txt"
    start = SAMPLE_START + offset_ps * 1e-12
    last = start + (NSAMPLES - 1) * SAMPLE_STEP

    client.execute_skill(f'openResults("{results_dir}")', timeout=30)
    client.execute_skill('selectResults("tran")', timeout=30)
    cmd = (
        "ocnPrint("
        f'?output "{remote_path}" '
        "?numberNotation 'none "
        "?numSpaces 1 "
        "?precision 16 "
        f"?from {start:.16g} "
        f"?to {last:.16g} "
        f"?step {SAMPLE_STEP:.16g} "
        'VT("/out"))'
    )
    result = client.execute_skill(cmd, timeout=180)
    if not _skill_ok(result):
        raise RuntimeError(f"ocnPrint failed for offset {offset_ps} ps: {result}")
    client.download_file(remote_path, str(out_path))
    client.execute_skill(f'deleteFile("{remote_path}")', timeout=10)
    return parse_waveform(out_path)


def run_phase_sweep(
    history: str,
    results_dir: str,
    out_dir: Path,
    offsets_ps: list[float],
) -> dict:
    client = VirtuosoClient.from_env()
    results: list[dict] = []
    for offset_ps in offsets_ps:
        label = f"{offset_ps:+.0f}ps"
        safe = label.replace("+", "p").replace("-", "m")
        path = out_dir / f"out_phase_{safe}.txt"
        print(f"Exporting /out phase {label}", flush=True)
        times, values = export_out_phase(client, results_dir, path, offset_ps)
        results.append(
            {
                "offset_ps": offset_ps,
                "path": str(path),
                "time_start": times[0],
                "time_stop": times[-1],
                "v_min": min(values),
                "v_max": max(values),
                "v_mean": sum(values) / len(values),
                "metrics": dft_metrics(values),
            }
        )

    summary = {
        "history": history,
        "results_dir": results_dir,
        "offsets_ps": offsets_ps,
        "results": results,
        "best_by_sinad": max(results, key=lambda item: item["metrics"]["sinad_db"]),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "out_phase_sweep.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", default="Interactive.10")
    parser.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR)
    parser.add_argument(
        "--out-dir",
        default="sar9b_work/iterations/sar9b_maestro_best_q4/out_phase_interactive10",
    )
    parser.add_argument(
        "--offset-ps",
        nargs="*",
        type=float,
        default=[0, 1200, 1350, 1500, 1650, 1800],
    )
    args = parser.parse_args()
    summary = run_phase_sweep(
        args.history,
        args.results_dir,
        Path(args.out_dir).resolve(),
        args.offset_ps,
    )
    print(json.dumps(summary["best_by_sinad"], indent=2), flush=True)
    print(f"Saved: {Path(args.out_dir).resolve() / 'out_phase_sweep.json'}", flush=True)


if __name__ == "__main__":
    main()
