#!/usr/bin/env python3
"""Offline 9-bit measurement from SAR output bits.

This avoids editing the ADC testbench schematic.  The script can either
reuse an existing Maestro history or temporarily apply binary CDAC weights,
run the existing ADC_redun1_tb Maestro setup, export DOUTP<8:0> waveforms,
and restore the original redundant weights.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import uuid
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    close_gui_session,
    open_gui_session,
)


LIB = "8BIT400MVcmredundancySAR"
TOP_CELL = "TOP_redun1_ADC"
TB_CELL = "ADC_redun1_tb"
TEST = "Vcmbased_ADC_tb_1"
RUN_LOG_REMOTE = (
    f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/results/maestro/ExplorerRun.0.log"
)

SAMPLE_START = 26e-9
SAMPLE_STOP = 2.586e-6
NSAMPLES = 1024
FUND_BIN = 7
VTH = 0.45
SAMPLE_STEP = (SAMPLE_STOP - SAMPLE_START) / NSAMPLES
SAMPLE_LAST = SAMPLE_START + (NSAMPLES - 1) * SAMPLE_STEP

# DOUTP pins are not present as top-level saved PSF signals.  Each bit is the
# Q port of control/I5 (DFF), whose final inverter is I12(net7 -> Q), so the
# saved internal net7 is the inverted bit.
DOUTP_NET7_BY_BIT = {
    0: "I31",
    1: "I7",
    2: "I6",
    3: "I5",
    4: "I4",
    5: "I3",
    6: "I2",
    7: "I1",
    8: "I43",
}

BINARY_WEIGHTS = {
    "C2": "Cunit*256",
    "C17": "Cunit*256",
    "C0": "Cunit*128",
    "C14": "Cunit*128",
    "C1": "Cunit*64",
    "C13": "Cunit*64",
    "C4": "Cunit*32",
    "C11": "Cunit*32",
    "C3": "Cunit*16",
    "C12": "Cunit*16",
    "C5": "Cunit*8",
    "C10": "Cunit*8",
    "C6": "Cunit*4",
    "C9": "Cunit*4",
    "C7": "Cunit*2",
    "C8": "Cunit*2",
    "C15": "Cunit*1",
    "C16": "Cunit*1",
}

ORIGINAL_WEIGHTS = {
    "C2": "Cunit*56",
    "C17": "Cunit*56",
    "C0": "Cunit*32",
    "C14": "Cunit*32",
    "C1": "Cunit*18",
    "C13": "Cunit*18",
    "C4": "Cunit*10",
    "C11": "Cunit*10",
    "C3": "Cunit*5",
    "C12": "Cunit*5",
    "C5": "Cunit*3",
    "C10": "Cunit*3",
    "C6": "Cunit*2",
    "C9": "Cunit*2",
    "C7": "Cunit*1",
    "C8": "Cunit*1",
    "C15": "Cunit*1",
    "C16": "Cunit*1",
}


def _skill_ok(result) -> bool:
    return getattr(result, "status", None) and result.status.value == "success"


def read_weights(client: VirtuosoClient) -> dict[str, str]:
    r = client.execute_skill(
        f'''
let((cv caps)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "r")
  caps = nil
  when(cv
    foreach(inst cv~>instances
      when(inst~>cellName == "cap"
        caps = cons(strcat(inst~>name "=" inst~>c) caps)))
    dbClose(cv))
  caps)
''',
        timeout=20,
    )
    weights: dict[str, str] = {}
    for item in (r.output or "").replace("(", " ").replace(")", " ").replace('"', "").split():
        if "=" in item:
            name, value = item.split("=", 1)
            weights[name.strip()] = value.strip()
    return weights


def apply_weights(client: VirtuosoClient, weights: dict[str, str], label: str) -> None:
    print(f"{label}: applying {len(weights)} CDAC weights", flush=True)
    for cap, value in weights.items():
        r = client.execute_skill(
            f'''
let((cv inst)
  cv = dbOpenCellViewByType("{LIB}" "{TOP_CELL}" "schematic" "" "a")
  inst = dbGetInstByName(cv "{cap}")
  when(inst inst~>c = "{value}")
  dbSave(cv)
  dbClose(cv)
  t)
''',
            timeout=20,
        )
        if not _skill_ok(r):
            raise RuntimeError(f"Failed to set {cap}={value}: {r}")


def get_scalar_outputs(client: VirtuosoClient, history: str) -> dict[str, str]:
    outputs: dict[str, str] = {}
    client.execute_skill(f'maeOpenResults(?history "{history}")', timeout=30)
    try:
        for name in ("spectrum_enob", "spectrum_sinad", "vtime"):
            r = client.execute_skill(
                f'maeGetOutputValue("{name}" "{TEST}" ?history "{history}")',
                timeout=30,
            )
            outputs[name] = (r.output or "").strip()
    finally:
        client.execute_skill("maeCloseResults()", timeout=10)
    return outputs


def _remote_cmd(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("Remote SSH runner is required for this workflow")
    r = client.ssh_runner.run_command(command, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{r.stderr}")
    return r.stdout or ""


def run_explorer_and_wait(client: VirtuosoClient, timeout: int) -> str:
    start_epoch = int(time.time())
    r = client.execute_skill(
        '''
let((s)
  s = sevSession(hiGetCurrentWindow())
  unless(s error("No sevSession on current window"))
  sevRun(s))
''',
        timeout=60,
    )
    if not _skill_ok(r) or (r.output or "").strip() == "nil":
        raise RuntimeError(f"sevRun failed: {r}")

    print("Explorer run started; polling ExplorerRun.0.log", flush=True)
    deadline = time.time() + timeout
    last_status = ""
    while time.time() < deadline:
        stat = _remote_cmd(
            client,
            f'test -f {RUN_LOG_REMOTE} && stat -c %Y {RUN_LOG_REMOTE} || echo 0',
            timeout=20,
        ).strip()
        try:
            mtime = int(stat)
        except ValueError:
            mtime = 0
        if mtime >= start_epoch:
            text = _remote_cmd(client, f'cat {RUN_LOG_REMOTE}', timeout=20)
            if text != last_status:
                last_status = text
                tail = "\\n".join(text.splitlines()[-8:])
                print(tail, flush=True)
            if "ExplorerRun.0 completed." in text:
                if "Number of simulation errors: 0" not in text:
                    raise RuntimeError(f"ExplorerRun.0 completed with errors:\n{text}")
                return "ExplorerRun.0"
        time.sleep(30)
        print("still running...", flush=True)
    raise TimeoutError(f"Explorer run did not complete within {timeout}s")


def parse_waveform(path: Path) -> tuple[list[float], list[float]]:
    times: list[float] = []
    values: list[float] = []
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    row_re = re.compile(rf"^\s*({number})\s+({number})(?:\s|$)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = row_re.match(line)
        if not m:
            continue
        times.append(float(m.group(1)))
        values.append(float(m.group(2)))
    if len(times) < 2:
        raise RuntimeError(f"Could not parse waveform data from {path}")
    return times, values


def interp(times: list[float], values: list[float], t: float) -> float:
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    lo = 0
    hi = len(times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            lo = mid
        else:
            hi = mid
    t0, t1 = times[lo], times[hi]
    y0, y1 = values[lo], values[hi]
    if t1 == t0:
        return y0
    return y0 + (y1 - y0) * ((t - t0) / (t1 - t0))


def sample_times() -> list[float]:
    step = (SAMPLE_STOP - SAMPLE_START) / NSAMPLES
    return [SAMPLE_START + k * step for k in range(NSAMPLES)]


def dft_metrics(samples: list[float], fund_bin: int = FUND_BIN) -> dict[str, float]:
    n = len(samples)
    mean = sum(samples) / n
    centered = [x - mean for x in samples]
    powers: list[float] = []
    for k in range(n // 2 + 1):
        real = 0.0
        imag = 0.0
        for i, x in enumerate(centered):
            a = -2.0 * math.pi * k * i / n
            real += x * math.cos(a)
            imag += x * math.sin(a)
        p = real * real + imag * imag
        if k not in (0, n // 2):
            p *= 2.0
        powers.append(p)
    signal = powers[fund_bin]
    noise = sum(powers[1 : n // 2]) - signal
    sinad = 10.0 * math.log10(signal / noise)
    enob = (sinad - 1.76) / 6.02
    return {
        "sinad_db": sinad,
        "enob_bits": enob,
        "dc": mean,
        "signal_power": signal,
        "noise_dist_power": noise,
    }


def export_signal(
    client: VirtuosoClient,
    session: str,
    history: str,
    expression: str,
    out_path: Path,
) -> tuple[list[float], list[float]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    remote_path = f"/tmp/dout9_{history}_{uuid.uuid4().hex}.txt"

    client.execute_skill(f'maeOpenResults(?history "{history}")', timeout=30)
    try:
        r = client.execute_skill('asiGetResultsDir(asiGetCurrentSession())', timeout=30)
        results_dir = (r.output or "").strip('"')
    finally:
        client.execute_skill("maeCloseResults()", timeout=10)

    if not results_dir or results_dir == "nil":
        raise RuntimeError(f"No valid results directory for {history}")

    client.execute_skill(f'openResults("{results_dir}")', timeout=30)
    client.execute_skill('selectResults("tran")', timeout=30)
    cmd = (
        "ocnPrint("
        f'?output "{remote_path}" '
        "?numberNotation 'none "
        "?numSpaces 1 "
        "?precision 16 "
        f"?from {SAMPLE_START:.16g} "
        f"?to {SAMPLE_LAST:.16g} "
        f"?step {SAMPLE_STEP:.16g} "
        f"{expression})"
    )
    r = client.execute_skill(cmd, timeout=120)
    if not _skill_ok(r):
        raise RuntimeError(f"ocnPrint failed for {expression}: {r}")
    client.download_file(remote_path, str(out_path))
    client.execute_skill(f'deleteFile("{remote_path}")', timeout=10)
    return parse_waveform(out_path)


def get_results_dir(client: VirtuosoClient, history: str) -> str:
    client.execute_skill(f'maeOpenResults(?history "{history}")', timeout=30)
    try:
        r = client.execute_skill('asiGetResultsDir(asiGetCurrentSession())', timeout=30)
        return (r.output or "").strip('"')
    finally:
        client.execute_skill("maeCloseResults()", timeout=10)


def capture_netlist(client: VirtuosoClient, history: str, out_dir: Path) -> str:
    results_dir = get_results_dir(client, history)
    m = re.search(r"(.*/maestro/results/maestro/[^/]+)/1/([^/]+)/psf/?$", results_dir)
    if not m:
        return ""
    remote_netlist = f"{m.group(1)}/psf/{m.group(2)}/netlist/input.scs"
    local_netlist = out_dir / "input.scs"
    try:
        client.download_file(remote_netlist, str(local_netlist))
    except Exception as exc:
        print(f"WARNING: could not capture netlist {remote_netlist}: {exc}", flush=True)
        return ""
    return str(local_netlist)


def export_all(client: VirtuosoClient, session: str, history: str, out_dir: Path) -> dict[str, Path]:
    exports: dict[str, Path] = {}
    signals = [("out", 'VT("/out")')]
    signals.extend(
        (f"DOUTP{i}", f'VT("/I0/{DOUTP_NET7_BY_BIT[i]}/I5/net7")')
        for i in range(9)
    )
    for name, expr in signals:
        path = out_dir / f"{name}.txt"
        print(f"Exporting {name}: {expr}", flush=True)
        export_signal(client, session, history, expr, path)
        exports[name] = path
    return exports


def code_from_bits(bit_waves: dict[int, tuple[list[float], list[float]]]) -> list[int]:
    codes: list[int] = []
    for t in sample_times():
        code = 0
        for bit, (times, values) in bit_waves.items():
            if interp(times, values, t) < VTH:
                code += 1 << bit
        codes.append(code)
    return codes


def analog_samples(wave: tuple[list[float], list[float]]) -> list[float]:
    times, values = wave
    return [interp(times, values, t) for t in sample_times()]


def run_measurement(args: argparse.Namespace) -> dict:
    client = VirtuosoClient.from_env()
    session = ""
    history = args.history
    original_snapshot = read_weights(client)
    restored = False

    try:
        if args.run:
            apply_weights(client, BINARY_WEIGHTS, "binary")
        session = open_gui_session(client, LIB, TB_CELL, timeout=90)
        print(f"Maestro session: {session}", flush=True)

        if args.run:
            print("Running Maestro simulation via ADE Explorer; this normally takes about 25 minutes.", flush=True)
            t0 = time.time()
            history = run_explorer_and_wait(client, timeout=args.timeout)
            elapsed = time.time() - t0
            print(f"Simulation done: history={history}, elapsed={elapsed:.1f}s", flush=True)

        if not history:
            history = "ExplorerRun.0"

        out_dir = Path(args.out_dir).resolve() / history.replace("/", "_")
        exports = export_all(client, session, history, out_dir)
        netlist_path = capture_netlist(client, history, out_dir)
        scalar = get_scalar_outputs(client, history)

        out_wave = parse_waveform(exports["out"])
        out_samples = analog_samples(out_wave)
        out_metrics = dft_metrics(out_samples)

        bit_waves: dict[int, tuple[list[float], list[float]]] = {}
        for bit in range(9):
            bit_waves[bit] = parse_waveform(exports[f"DOUTP{bit}"])
        codes = code_from_bits(bit_waves)
        code_metrics = dft_metrics([float(c) for c in codes])

        result = {
            "history": history,
            "sample_start": SAMPLE_START,
            "sample_stop": SAMPLE_STOP,
            "nsamples": NSAMPLES,
            "fund_bin": FUND_BIN,
            "maestro_scalar_outputs": scalar,
            "dac8_out_offline": out_metrics,
            "doutp9_code_offline": code_metrics,
            "code_min": min(codes),
            "code_max": max(codes),
            "code_mean": sum(codes) / len(codes),
            "bit_source": "DOUTP = inverse of saved control/I5/net7 nodes",
            "captured_netlist": netlist_path,
            "exports": {k: str(v) for k, v in exports.items()},
        }
        result_path = out_dir / "measurement.json"
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        print(f"Saved: {result_path}", flush=True)
        return result
    finally:
        if args.run:
            try:
                apply_weights(client, ORIGINAL_WEIGHTS, "restore")
                restored = True
            except Exception as exc:
                print(f"ERROR: restore failed: {exc}", file=sys.stderr, flush=True)
                try:
                    apply_weights(client, original_snapshot, "restore-snapshot")
                    restored = True
                except Exception as exc2:
                    print(f"ERROR: snapshot restore failed: {exc2}", file=sys.stderr, flush=True)
        if session:
            try:
                close_gui_session(client, session, save=False, timeout=90)
            except Exception as exc:
                print(f"WARNING: close_gui_session failed: {exc}", file=sys.stderr, flush=True)
        if args.run and not restored:
            print("WARNING: CDAC restore was not confirmed.", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="apply binary weights and run Maestro first")
    parser.add_argument("--history", default="", help="Maestro history to export; default ExplorerRun.0")
    parser.add_argument("--out-dir", default="sar9b_work/wave_exports", help="local output directory")
    parser.add_argument("--timeout", type=int, default=2400, help="simulation timeout in seconds")
    args = parser.parse_args()
    run_measurement(args)


if __name__ == "__main__":
    main()
