#!/usr/bin/env python3
"""Resample top-level biP<8:0> at several phase offsets from one Maestro run."""

from __future__ import annotations

import argparse
import json
import math
import re
import uuid
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

from dout9_offline_measure import (
    FUND_BIN,
    NSAMPLES,
    SAMPLE_START,
    SAMPLE_STEP,
    VTH,
    _skill_ok,
)


DEFAULT_RESULTS_DIR = (
    "/home/IC/Desktop/Project/8BIT400MVcmredundancySAR/ADC_redun1_tb/"
    "maestro/results/maestro/ExplorerRun.0/1/Vcmbased_ADC_tb_1/psf"
)


def dft_metrics(samples: list[float], fund_bin: int = FUND_BIN) -> dict[str, float]:
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
    signal = powers[fund_bin]
    noise_dist = sum(powers[1 : n // 2]) - signal
    sinad = 10.0 * math.log10(signal / noise_dist)
    return {
        "sinad_db": sinad,
        "enob_bits": (sinad - 1.76) / 6.02,
        "dc": mean,
        "signal_power": signal,
        "noise_dist_power": noise_dist,
    }


def parse_multi_waveform(path: Path, columns: int) -> tuple[list[float], list[list[float]]]:
    times: list[float] = []
    values: list[list[float]] = [[] for _ in range(columns)]
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    row_re = re.compile(rf"^\s*((?:{number}\s+)+{number})(?:\s|$)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        nums = [float(part) for part in match.group(1).split()]
        if len(nums) != columns + 1:
            continue
        times.append(nums[0])
        for idx in range(columns):
            values[idx].append(nums[idx + 1])
    if len(times) != NSAMPLES:
        raise RuntimeError(f"Expected {NSAMPLES} rows with {columns} columns, got {len(times)} in {path}")
    return times, values


def export_bip_phase(
    client: VirtuosoClient,
    results_dir: str,
    out_path: Path,
    offset_ps: float,
) -> tuple[list[float], list[list[float]]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    remote_path = f"/tmp/bip_phase_{uuid.uuid4().hex}.txt"
    if not results_dir or results_dir == "nil":
        raise RuntimeError("No valid results directory")

    start = SAMPLE_START + offset_ps * 1e-12
    last = start + (NSAMPLES - 1) * SAMPLE_STEP
    expressions = " ".join(f'VT("/biP<{bit}>")' for bit in range(9))

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
        f"{expressions})"
    )
    r = client.execute_skill(cmd, timeout=180)
    if not _skill_ok(r):
        raise RuntimeError(f"ocnPrint failed for offset {offset_ps} ps: {r}")
    client.download_file(remote_path, str(out_path))
    client.execute_skill(f'deleteFile("{remote_path}")', timeout=10)
    return parse_multi_waveform(out_path, columns=9)


def codes_from_bip(values: list[list[float]]) -> list[int]:
    codes: list[int] = []
    for sample_idx in range(NSAMPLES):
        code = 0
        for bit in range(9):
            if values[bit][sample_idx] > VTH:
                code += 1 << bit
        codes.append(code)
    return codes


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
        path = out_dir / f"bip_phase_{safe}.txt"
        print(f"Exporting biP phase {label}", flush=True)
        times, values = export_bip_phase(client, results_dir, path, offset_ps)
        codes = codes_from_bip(values)
        midband = sum(
            1
            for col in values
            for value in col
            if 0.1 < value < 0.8
        )
        results.append(
            {
                "offset_ps": offset_ps,
                "path": str(path),
                "time_start": times[0],
                "time_stop": times[-1],
                "code_min": min(codes),
                "code_max": max(codes),
                "code_mean": sum(codes) / len(codes),
                "midband_values": midband,
                "direct_binary_metrics": dft_metrics([float(code) for code in codes]),
            }
        )

    summary = {
        "history": history,
        "results_dir": results_dir,
        "offsets_ps": offsets_ps,
        "results": results,
        "best_by_sinad": max(results, key=lambda item: item["direct_binary_metrics"]["sinad_db"]),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bip_phase_sweep.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", default="ExplorerRun.0")
    parser.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR)
    parser.add_argument(
        "--out-dir",
        default="sar9b_work/wave_exports_binary/ExplorerRun.0/phase_sweep",
    )
    parser.add_argument(
        "--offset-ps",
        nargs="*",
        type=float,
        default=[-1200, -900, -600, -300, 0, 300, 600, 900, 1200],
        help="Phase offsets in ps relative to the Maestro FFT sample grid.",
    )
    args = parser.parse_args()
    summary = run_phase_sweep(
        args.history,
        args.results_dir,
        Path(args.out_dir).resolve(),
        args.offset_ps,
    )
    print(json.dumps(summary["best_by_sinad"], indent=2), flush=True)
    print(f"Saved: {Path(args.out_dir).resolve() / 'bip_phase_sweep.json'}", flush=True)


if __name__ == "__main__":
    main()
