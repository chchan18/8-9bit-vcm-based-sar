#!/usr/bin/env python3
"""Run the bootstrap coherent-sine FFT test and compute dynamic metrics."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import close_gui_session, open_gui_session, set_var

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from create_bootstrap_fft_test import CELL  # noqa: E402
from run_submodule_maestro_tests import (  # noqa: E402
    LIB,
    PROJECT_DIR,
    TEST_NAME,
    download_if_exists,
    parse_spectre_summary,
    parse_waveforms,
    remote_epoch,
    remote_tail,
    run_skill,
    skill_ok,
    trigger_run,
    wait_for_completion,
)


RUN_ROOT = PROJECT_DIR / "runs/bootstrap_fft_dynamic"
DEFAULT_SAMPLE_START = 50.2e-9
DEFAULT_SAMPLE_STEP = 2.5e-9
DEFAULT_NSAMPLES = 1024
DEFAULT_FUND_BIN = 7
DEFAULT_FS = 400e6


def db10(value: float) -> float:
    if value <= 0:
        return float("-inf")
    return 10.0 * math.log10(value)


def dft_powers(samples: list[float]) -> tuple[float, list[float]]:
    n = len(samples)
    mean = sum(samples) / n
    centered = [x - mean for x in samples]
    powers: list[float] = []
    for k in range(n // 2 + 1):
        real = 0.0
        imag = 0.0
        for i, x in enumerate(centered):
            angle = -2.0 * math.pi * k * i / n
            real += x * math.cos(angle)
            imag += x * math.sin(angle)
        power = real * real + imag * imag
        if k not in (0, n // 2):
            power *= 2.0
        powers.append(power)
    return mean, powers


def folded_bin(bin_index: int, n: int) -> int:
    wrapped = bin_index % n
    return n - wrapped if wrapped > n // 2 else wrapped


def fft_metrics(samples: list[float], fund_bin: int, fs: float) -> dict[str, object]:
    n = len(samples)
    mean, powers = dft_powers(samples)
    signal = powers[fund_bin]
    active_bins = list(range(1, n // 2))
    total_non_dc = sum(powers[idx] for idx in active_bins)
    noise_dist = max(total_non_dc - signal, 0.0)
    harmonic_bins: list[int] = []
    for harmonic in range(2, 10):
        idx = folded_bin(fund_bin * harmonic, n)
        if idx not in (0, fund_bin, n // 2) and idx not in harmonic_bins:
            harmonic_bins.append(idx)
    harmonic_power = sum(powers[idx] for idx in harmonic_bins)
    spur_candidates = [
        (idx, powers[idx])
        for idx in active_bins
        if idx != fund_bin
    ]
    spur_bin, spur_power = max(spur_candidates, key=lambda item: item[1])
    signal_amp_peak = math.sqrt(2.0 * signal) / n if signal > 0 else 0.0
    sndr = db10(signal / noise_dist) if noise_dist > 0 else float("inf")
    thd = db10(harmonic_power / signal) if signal > 0 and harmonic_power > 0 else float("-inf")
    sfdr = db10(signal / spur_power) if spur_power > 0 else float("inf")
    return {
        "sample_count": n,
        "fs_hz": fs,
        "fundamental_bin": fund_bin,
        "fundamental_hz": fund_bin * fs / n,
        "dc": mean,
        "signal_amp_peak_v": signal_amp_peak,
        "sndr_db": sndr,
        "enob_bits": (sndr - 1.76) / 6.02 if math.isfinite(sndr) else float("inf"),
        "thd_db": thd,
        "sfdr_db": sfdr,
        "largest_spur_bin": spur_bin,
        "largest_spur_hz": spur_bin * fs / n,
        "harmonic_bins": harmonic_bins,
        "signal_power": signal,
        "noise_dist_power": noise_dist,
        "harmonic_power": harmonic_power,
        "largest_spur_power": spur_power,
    }


def rms(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def parse_sampled(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    times, cols = parse_waveforms(path, 4)
    return times, {
        "vin_diff": cols["c0"],
        "vout_diff": cols["c1"],
        "voutp": cols["c2"],
        "voutn": cols["c3"],
    }


def export_sampled_fft_points(
    client: VirtuosoClient,
    results_dir: str,
    out_path: Path,
    sample_start: float,
    sample_step: float,
    nsamples: int,
) -> tuple[list[float], dict[str, list[float]]]:
    remote_path = f"/tmp/bootstrap_fft_{uuid.uuid4().hex}.txt"
    sample_last = sample_start + (nsamples - 1) * sample_step
    client.execute_skill(f'openResults("{results_dir}")', timeout=30)
    client.execute_skill('selectResults("tran")', timeout=30)
    cmd = (
        "ocnPrint("
        f'?output "{remote_path}" '
        "?numberNotation 'none "
        "?numSpaces 1 "
        "?precision 16 "
        f"?from {sample_start:.16g} "
        f"?to {sample_last:.16g} "
        f"?step {sample_step:.16g} "
        '(VT("/VIP")-VT("/VIN")) '
        '(VT("/VOUTP")-VT("/VOUTN")) '
        'VT("/VOUTP") '
        'VT("/VOUTN"))'
    )
    result = client.execute_skill(cmd, timeout=240)
    if not skill_ok(result):
        raise RuntimeError(f"ocnPrint failed for bootstrap FFT samples: {result}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(remote_path, str(out_path))
    client.execute_skill(f'deleteFile("{remote_path}")', timeout=10)
    return parse_sampled(out_path)


def run_fft_test(args: argparse.Namespace) -> dict[str, object]:
    client = VirtuosoClient.from_env()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = open_gui_session(client, LIB, CELL, timeout=180)
    try:
        variables = {
            "vdd": args.vdd,
            "vcm": args.vcm,
            "Vpk": args.vpk,
            "fs": args.fs,
            "fft_bin": str(args.fund_bin),
            "fft_n": str(args.nsamples),
            "TSTOP": args.tstop,
            "cload": args.cload,
        }
        for name, value in variables.items():
            set_var(client, name, value, session=session)
            set_var(client, name, value, type_name="test", type_value=f'("{TEST_NAME}")', session=session)
        run_skill(client, f"save {CELL}", f'maeSaveSetup(?session "{session}")', timeout=60)
        start_epoch = remote_epoch(client)
        history = trigger_run(client, session, CELL, start_epoch, args.trigger)

        run_log_remote = f"/home/IC/Desktop/Project/{LIB}/{CELL}/maestro/results/maestro/{history}.log"
        results_dir_remote = f"/home/IC/simulation/{LIB}/{CELL}/maestro/results/maestro/{history}/1/{TEST_NAME}/psf"
        spectre_out_remote = f"{results_dir_remote}/spectre.out"
        netlist_remote = f"/home/IC/simulation/{LIB}/{CELL}/maestro/results/maestro/{history}/1/{TEST_NAME}/netlist/input.scs"
        status = wait_for_completion(client, history, run_log_remote, spectre_out_remote, timeout=args.timeout)

        download_if_exists(client, run_log_remote, out_dir / f"{history}.log")
        download_if_exists(client, spectre_out_remote, out_dir / "spectre.out")
        download_if_exists(client, netlist_remote, out_dir / "input.scs")
        times, waves = export_sampled_fft_points(
            client,
            results_dir_remote,
            out_dir / "sampled_fft_points.txt",
            args.sample_start,
            1.0 / args.fs_float,
            args.nsamples,
        )
    finally:
        try:
            close_gui_session(client, session, save=True, timeout=90)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: close_gui_session failed for {CELL}: {exc}", flush=True)

    input_metrics = fft_metrics(waves["vin_diff"], args.fund_bin, args.fs_float)
    output_metrics = fft_metrics(waves["vout_diff"], args.fund_bin, args.fs_float)
    errors = [out - vin for vin, out in zip(waves["vin_diff"], waves["vout_diff"])]
    gain = (
        output_metrics["signal_amp_peak_v"] / input_metrics["signal_amp_peak_v"]
        if input_metrics["signal_amp_peak_v"]
        else None
    )
    summary = {
        "library": LIB,
        "cell": CELL,
        "test_name": TEST_NAME,
        "history": history,
        "variables": variables,
        "trigger": args.trigger,
        "run_log_remote": run_log_remote,
        "results_dir_remote": results_dir_remote,
        "spectre_out_remote": spectre_out_remote,
        "netlist_remote": netlist_remote,
        "completed": status["completed"],
        "run_errors": status["run_errors"],
        "spectre_summary": status["spectre_summary"],
        "sample_start_s": args.sample_start,
        "sample_stop_s": times[-1],
        "sample_step_s": 1.0 / args.fs_float,
        "samples": len(times),
        "input_metrics": input_metrics,
        "output_metrics": output_metrics,
        "transfer_metrics": {
            "fundamental_gain_v_per_v": gain,
            "fundamental_gain_db": 20.0 * math.log10(gain) if gain and gain > 0 else None,
            "error_rms_v": rms(errors),
            "error_peak_v": max(abs(value) for value in errors),
            "voutp_min_v": min(waves["voutp"]),
            "voutp_max_v": max(waves["voutp"]),
            "voutn_min_v": min(waves["voutn"]),
            "voutn_max_v": max(waves["voutn"]),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Saved: {out_dir / 'summary.json'}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trigger", choices=["gui-button", "mae", "callback"], default="callback")
    parser.add_argument("--out-dir", default=str(RUN_ROOT / "nominal_track_p200"))
    parser.add_argument("--vdd", default="900m")
    parser.add_argument("--vcm", default="450m")
    parser.add_argument("--vpk", default="800m")
    parser.add_argument("--fs", default="400M")
    parser.add_argument("--fs-float", type=float, default=DEFAULT_FS)
    parser.add_argument("--fund-bin", type=int, default=DEFAULT_FUND_BIN)
    parser.add_argument("--nsamples", type=int, default=DEFAULT_NSAMPLES)
    parser.add_argument("--sample-start", type=float, default=DEFAULT_SAMPLE_START)
    parser.add_argument("--tstop", default="2.7u")
    parser.add_argument("--cload", default="5f")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    run_fft_test(args)


if __name__ == "__main__":
    main()
