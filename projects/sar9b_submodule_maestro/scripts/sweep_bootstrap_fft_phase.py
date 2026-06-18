#!/usr/bin/env python3
"""Sweep sampling phase on existing bootstrap FFT PSF histories."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_bootstrap_fft_test import (  # noqa: E402
    DEFAULT_FS,
    DEFAULT_FUND_BIN,
    DEFAULT_NSAMPLES,
    export_sampled_fft_points,
    fft_metrics,
    rms,
)


RUN_ROOT = Path("projects/sar9b_submodule_maestro/runs/bootstrap_fft_dynamic")


def load_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sweep_case(
    client: VirtuosoClient,
    summary_path: Path,
    out_dir: Path,
    base_start_s: float,
    phase_step_ps: float,
    phase_stop_ps: float,
) -> dict[str, object]:
    source = load_summary(summary_path)
    results_dir = str(source["results_dir_remote"])
    fs = float(source.get("sample_step_s", 1.0 / DEFAULT_FS))
    sample_step = fs if fs > 1e-12 else 1.0 / DEFAULT_FS
    sample_rate = 1.0 / sample_step
    fund_bin = int(source.get("output_metrics", {}).get("fundamental_bin", DEFAULT_FUND_BIN))
    nsamples = int(source.get("samples", DEFAULT_NSAMPLES))
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    phase_ps = 0.0
    while phase_ps <= phase_stop_ps + 1e-9:
        start_s = base_start_s + phase_ps * 1e-12
        samples_path = out_dir / f"phase_{phase_ps:07.1f}ps.txt"
        times, waves = export_sampled_fft_points(
            client,
            results_dir,
            samples_path,
            start_s,
            sample_step,
            nsamples,
        )
        input_metrics = fft_metrics(waves["vin_diff"], fund_bin, sample_rate)
        output_metrics = fft_metrics(waves["vout_diff"], fund_bin, sample_rate)
        errors = [out - vin for vin, out in zip(waves["vin_diff"], waves["vout_diff"])]
        gain = (
            output_metrics["signal_amp_peak_v"] / input_metrics["signal_amp_peak_v"]
            if input_metrics["signal_amp_peak_v"]
            else None
        )
        rows.append(
            {
                "phase_ps": phase_ps,
                "sample_start_s": start_s,
                "sample_stop_s": times[-1],
                "output_sndr_db": output_metrics["sndr_db"],
                "output_enob_bits": output_metrics["enob_bits"],
                "output_thd_db": output_metrics["thd_db"],
                "output_sfdr_db": output_metrics["sfdr_db"],
                "largest_spur_bin": output_metrics["largest_spur_bin"],
                "largest_spur_hz": output_metrics["largest_spur_hz"],
                "input_amp_peak_v": input_metrics["signal_amp_peak_v"],
                "output_amp_peak_v": output_metrics["signal_amp_peak_v"],
                "fundamental_gain_v_per_v": gain,
                "fundamental_gain_db": 20.0 * math.log10(gain) if gain and gain > 0 else None,
                "error_rms_v": rms(errors),
                "error_peak_v": max(abs(value) for value in errors),
                "sample_file": str(samples_path),
            }
        )
        print(json.dumps(rows[-1], indent=2), flush=True)
        phase_ps += phase_step_ps

    best = max(rows, key=lambda item: float(item["output_sndr_db"]))
    result = {
        "source_summary": str(summary_path),
        "history": source.get("history"),
        "variables": source.get("variables"),
        "results_dir_remote": results_dir,
        "base_start_s": base_start_s,
        "phase_step_ps": phase_step_ps,
        "phase_stop_ps": phase_stop_ps,
        "rows": rows,
        "best_by_sndr": best,
    }
    (out_dir / "phase_sweep_summary.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-start", type=float, default=50e-9)
    parser.add_argument("--phase-step-ps", type=float, default=100.0)
    parser.add_argument("--phase-stop-ps", type=float, default=2400.0)
    parser.add_argument(
        "--cases",
        nargs="*",
        default=[
            "nominal_p2200/summary.json",
            "nominal_vpk400/summary.json",
        ],
    )
    parser.add_argument(
        "--out-dir",
        default=str(RUN_ROOT / "phase_sweep_existing"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env()
    out_root = Path(args.out_dir)
    summaries = []
    for rel in args.cases:
        summary_path = RUN_ROOT / rel
        case_name = summary_path.parent.name
        summaries.append(
            sweep_case(
                client,
                summary_path,
                out_root / case_name,
                args.base_start,
                args.phase_step_ps,
                args.phase_stop_ps,
            )
        )
    merged = {
        "base_start_s": args.base_start,
        "phase_step_ps": args.phase_step_ps,
        "phase_stop_ps": args.phase_stop_ps,
        "summaries": summaries,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "summary.json").write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(json.dumps(merged, indent=2), flush=True)
    print(f"Saved: {out_root / 'summary.json'}", flush=True)


if __name__ == "__main__":
    main()
