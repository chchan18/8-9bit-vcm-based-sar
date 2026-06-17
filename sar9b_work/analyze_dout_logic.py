#!/usr/bin/env python3
"""Explore SAR DOUT bit interpretation from sampled waveform exports.

This is intentionally local-only: it reads the already exported ocnPrint files
and compares the existing Maestro decoder path with direct 9-bit binary code
interpretations.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


VTH = 0.45
FUND_BIN = 7

DECODER_WEIGHTS_BY_BIT = {
    0: 1,
    1: 2,
    2: 4,
    3: 6,
    4: 10,
    5: 20,
    6: 36,
    7: 64,
    8: 112,
}


def parse_waveform(path: Path) -> tuple[list[float], list[float]]:
    times: list[float] = []
    values: list[float] = []
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    row_re = re.compile(rf"^\s*({number})\s+({number})(?:\s|$)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = row_re.match(line)
        if match:
            times.append(float(match.group(1)))
            values.append(float(match.group(2)))
    if len(times) < 2:
        raise RuntimeError(f"Could not parse waveform rows from {path}")
    return times, values


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


def logic_bits(bit_values: dict[int, list[float]], inverted_net7: bool) -> list[list[int]]:
    n = min(len(values) for values in bit_values.values())
    rows: list[list[int]] = []
    for i in range(n):
        row: list[int] = []
        for bit in range(9):
            high = bit_values[bit][i] > VTH
            if inverted_net7:
                row.append(0 if high else 1)
            else:
                row.append(1 if high else 0)
        rows.append(row)
    return rows


def binary_codes(rows: list[list[int]], reverse_order: bool = False) -> list[int]:
    codes: list[int] = []
    for row in rows:
        code = 0
        for bit, value in enumerate(row):
            weight_bit = 8 - bit if reverse_order else bit
            code += value << weight_bit
        codes.append(code)
    return codes


def binary_codes_width(rows: list[list[int]], width: int) -> list[int]:
    codes: list[int] = []
    for row in rows:
        code = 0
        for bit in range(width):
            code += row[bit] << bit
        codes.append(code)
    return codes


def decoder_codes(rows: list[list[int]]) -> list[int]:
    codes: list[int] = []
    for row in rows:
        code = sum(row[bit] * DECODER_WEIGHTS_BY_BIT[bit] for bit in range(9))
        codes.append(max(0, min(255, code)))
    return codes


def rows_from_values(
    bit_values: dict[int, list[float]], width: int, inverted: bool = False
) -> list[list[int]]:
    n = min(len(values) for values in bit_values.values())
    rows: list[list[int]] = []
    for i in range(n):
        row: list[int] = []
        for bit in range(width):
            high = bit_values[bit][i] > VTH
            if inverted:
                row.append(0 if high else 1)
            else:
                row.append(1 if high else 0)
        rows.append(row)
    return rows


def bit_stats(values: list[float]) -> dict[str, float | int]:
    mid = sum(1 for value in values if 0.1 < value < 0.8)
    highs = sum(1 for value in values if value > VTH)
    transitions = sum(
        1
        for prev, cur in zip(values, values[1:])
        if (prev > VTH) != (cur > VTH)
    )
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "high_count": highs,
        "midband_count": mid,
        "transitions": transitions,
    }


def rmse(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)) / n)


def best_code_shift(reference: list[int], candidate: list[int], max_shift: int = 16) -> dict:
    best: dict[str, int] | None = None
    for shift in range(-max_shift, max_shift + 1):
        mismatches = 0
        total = 0
        for i, ref_code in enumerate(reference):
            j = i + shift
            if 0 <= j < len(candidate):
                total += 1
                if candidate[j] != ref_code:
                    mismatches += 1
        item = {"shift": shift, "mismatches": mismatches, "total": total}
        if best is None or mismatches < best["mismatches"]:
            best = item
    return best or {"shift": 0, "mismatches": 0, "total": 0}


def analyze(export_dir: Path, decoder_dir: Path | None = None) -> dict:
    out_times, out_values = parse_waveform(export_dir / "out.txt")
    bit_waves = {
        bit: parse_waveform(export_dir / f"DOUTP{bit}.txt")
        for bit in range(9)
    }
    bit_values = {bit: values for bit, (_times, values) in bit_waves.items()}

    inv_rows = logic_bits(bit_values, inverted_net7=True)
    noninv_rows = logic_bits(bit_values, inverted_net7=False)

    decoder = decoder_codes(inv_rows)
    decoder_as_dac8 = [0.9 * code / 255.0 for code in decoder]
    binary = binary_codes(inv_rows)
    binary_reversed = binary_codes(inv_rows, reverse_order=True)
    noninv_binary = binary_codes(noninv_rows)
    noninv_reversed = binary_codes(noninv_rows, reverse_order=True)

    paths = {
        "maestro_out": [float(value) for value in out_values],
        "offline_decode_redun9to8_code": [float(code) for code in decoder],
        "offline_decode_redun9to8_as_dac8": decoder_as_dac8,
        "direct_binary_code": [float(code) for code in binary],
        "direct_binary_code_reversed_order": [float(code) for code in binary_reversed],
        "noninverted_binary_code": [float(code) for code in noninv_binary],
        "noninverted_binary_code_reversed_order": [
            float(code) for code in noninv_reversed
        ],
    }

    result = {
        "export_dir": str(export_dir),
        "samples": min(len(out_values), *(len(v) for v in bit_values.values())),
        "time_start": out_times[0],
        "time_stop": out_times[-1],
        "bit_stats_net7": {
            f"DOUTP{bit}_net7": bit_stats(bit_values[bit])
            for bit in range(9)
        },
        "path_metrics": {
            name: dft_metrics(values)
            for name, values in paths.items()
        },
        "code_ranges": {
            "decoder": {
                "min": min(decoder),
                "max": max(decoder),
                "mean": sum(decoder) / len(decoder),
            },
            "direct_binary": {
                "min": min(binary),
                "max": max(binary),
                "mean": sum(binary) / len(binary),
            },
            "direct_binary_reversed_order": {
                "min": min(binary_reversed),
                "max": max(binary_reversed),
                "mean": sum(binary_reversed) / len(binary_reversed),
            },
        },
        "decoder_vs_maestro_out": {
            "rmse_v": rmse(out_values, decoder_as_dac8),
            "max_abs_error_v": max(
                abs(out_values[i] - decoder_as_dac8[i])
                for i in range(min(len(out_values), len(decoder_as_dac8)))
            ),
        },
    }

    if decoder_dir and decoder_dir.exists():
        dac_values = {
            bit: parse_waveform(decoder_dir / f"DAC_B{bit}.txt")[1]
            for bit in range(8)
        }
        bip_values = {
            bit: parse_waveform(decoder_dir / f"BIP{bit}.txt")[1]
            for bit in range(9)
        }
        dac_rows = rows_from_values(dac_values, width=8)
        bip_rows = rows_from_values(bip_values, width=9)
        dac_code = binary_codes_width(dac_rows, width=8)
        bip_binary = binary_codes(bip_rows)
        bip_decoder = decoder_codes(bip_rows)
        dac_as_out = [0.9 * code / 255.0 for code in dac_code]

        internal_vs_bip_mismatches = {
            f"bit{bit}": sum(
                1
                for row_a, row_b in zip(inv_rows, bip_rows)
                if row_a[bit] != row_b[bit]
            )
            for bit in range(9)
        }

        result["decoder_node_checks"] = {
            "decoder_dir": str(decoder_dir),
            "path_metrics": {
                "dac_input_code": dft_metrics([float(code) for code in dac_code]),
                "dac_input_code_as_out": dft_metrics(dac_as_out),
                "bip_direct_binary_code": dft_metrics([float(code) for code in bip_binary]),
                "bip_decode_redun9to8_code": dft_metrics(
                    [float(code) for code in bip_decoder]
                ),
            },
            "code_ranges": {
                "dac_input_code": {
                    "min": min(dac_code),
                    "max": max(dac_code),
                    "mean": sum(dac_code) / len(dac_code),
                },
                "bip_direct_binary": {
                    "min": min(bip_binary),
                    "max": max(bip_binary),
                    "mean": sum(bip_binary) / len(bip_binary),
                },
                "bip_decode_redun9to8": {
                    "min": min(bip_decoder),
                    "max": max(bip_decoder),
                    "mean": sum(bip_decoder) / len(bip_decoder),
                },
            },
            "dac_input_vs_maestro_out": {
                "rmse_v": rmse(out_values, dac_as_out),
                "max_abs_error_v": max(
                    abs(out_values[i] - dac_as_out[i])
                    for i in range(min(len(out_values), len(dac_as_out)))
                ),
            },
            "internal_net7_inverse_vs_bip_mismatches": internal_vs_bip_mismatches,
            "bip_decoder_vs_dac_code_best_shift": best_code_shift(
                dac_code, bip_decoder
            ),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "export_dir",
        nargs="?",
        default="sar9b_work/wave_exports_binary/ExplorerRun.0",
        help="Directory containing out.txt and DOUTP0..8.txt",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path for the analysis JSON. Defaults under export_dir.",
    )
    parser.add_argument(
        "--decoder-dir",
        default="",
        help="Optional directory containing DAC_B0..7 and BIP0..8 exports.",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    decoder_dir = Path(args.decoder_dir) if args.decoder_dir else export_dir / "decoder_nodes"
    result = analyze(export_dir, decoder_dir=decoder_dir)
    json_path = Path(args.json_out) if args.json_out else export_dir / "dout_logic_analysis.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result["path_metrics"], indent=2), flush=True)
    if "decoder_node_checks" in result:
        print(json.dumps(result["decoder_node_checks"], indent=2), flush=True)
    print(json.dumps(result["decoder_vs_maestro_out"], indent=2), flush=True)
    print(f"Saved: {json_path}", flush=True)


if __name__ == "__main__":
    main()
