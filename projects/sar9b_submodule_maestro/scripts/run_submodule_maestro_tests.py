#!/usr/bin/env python3
"""Run SAR9B submodule Maestro tests, archive logs, and compute quick metrics."""

from __future__ import annotations

import json
import math
import re
import time
import uuid
import argparse
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import close_gui_session, open_gui_session, run_and_wait


LIB = "SAR9B_400MV"
TEST_NAME = "TRAN"
PROJECT_DIR = Path("projects/sar9b_submodule_maestro")
SETUP_MANIFEST = PROJECT_DIR / "artifacts/submodule_maestro_setup_manifest.json"
RUN_ROOT = PROJECT_DIR / "runs"
SAMPLE_STEP = 2e-12
VTH = 0.45
X11_HELPER_LOCAL = Path("sar9b_work/x11_type_text.py")
X11_HELPER_REMOTE = "/tmp/x11_type_text.py"


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def ensure_x11_helper(client: VirtuosoClient) -> None:
    if X11_HELPER_LOCAL.exists():
        client.upload_file(str(X11_HELPER_LOCAL), X11_HELPER_REMOTE)


def press_first_window(client: VirtuosoClient, title: str) -> bool:
    tree = ssh(client, "DISPLAY=:0 xwininfo -root -tree", timeout=20)
    for line in tree.splitlines():
        if title not in line:
            continue
        match = re.search(r"\b(0x[0-9a-fA-F]+)\b", line)
        if not match:
            continue
        window = match.group(1)
        print(f"Pressing Enter on {title}: {window}", flush=True)
        ssh(client, f"DISPLAY=:0 python3 {X11_HELPER_REMOTE} {window} '\\n'", timeout=20)
        time.sleep(2)
        return True
    return False


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 60) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def remote_file_exists(client: VirtuosoClient, path: str) -> bool:
    return ssh(client, f"test -f {path} && echo yes || echo no", timeout=20).strip() == "yes"


def remote_tail(client: VirtuosoClient, path: str, lines: int = 80) -> str:
    return ssh(client, f"test -f {path} && tail -n {lines} {path} || true", timeout=60)


def remote_epoch(client: VirtuosoClient) -> int:
    return int(ssh(client, "date +%s", timeout=20).strip())


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
    elapsed = re.search(r"elapsed time \(wall clock\):.*?\(([^()]+)\)\.", text)
    if elapsed:
        summary["elapsed"] = elapsed.group(1).strip()
    return summary


def parse_run_errors(text: str) -> int | None:
    match = re.search(r"Number of simulation errors:\s+(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def parse_maestro_metrics(text: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    in_specs = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Design specs"):
            in_specs = True
            continue
        if stripped.startswith("Design parameters"):
            break
        if not in_specs or not stripped:
            continue
        parts = [part.strip() for part in line.split("\t") if part.strip()]
        if len(parts) < 2 or parts[0] in {"TRAN", "corner"}:
            continue
        metrics[parts[0]] = " ".join(parts[1:])
    return metrics


def latest_history_after(client: VirtuosoClient, cell: str, start_epoch: int) -> str | None:
    base = f"/home/IC/Desktop/Project/{LIB}/{cell}/maestro/results/maestro"
    text = ssh(
        client,
        (
            f"find {base} -maxdepth 1 -type f -name 'Interactive.*.log' "
            "-printf '%T@ %f\\n' 2>/dev/null | "
            "sort -n | tail -1"
        ),
        timeout=30,
    ).strip()
    if not text:
        return None
    stamp, filename = text.split(maxsplit=1)
    if float(stamp) < start_epoch:
        return None
    return filename.removesuffix(".log")


def wait_for_history_after(
    client: VirtuosoClient,
    cell: str,
    start_epoch: int,
    timeout: int = 180,
) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        history = latest_history_after(client, cell, start_epoch)
        if history:
            print(f"Detected new history={history}", flush=True)
            return history
        print(f"Waiting for new history for {cell}...", flush=True)
        time.sleep(10)
    raise TimeoutError(f"no new Maestro history appeared for {cell}")


def trigger_run_mae(client: VirtuosoClient, session: str, cell: str, start_epoch: int) -> str:
    result = client.execute_skill(f'maeRunSimulation(?session "{session}")', timeout=300)
    if not skill_ok(result):
        history = latest_history_after(client, cell, start_epoch)
        if history:
            print(f"maeRunSimulation returned error but history appeared: {history}", flush=True)
            return history
        raise RuntimeError(f"maeRunSimulation failed: {result}")
    history = (result.output or "").strip().strip('"')
    if not history or history == "nil":
        fallback = latest_history_after(client, cell, start_epoch)
        if fallback:
            print(f"maeRunSimulation returned nil but history appeared: {fallback}", flush=True)
            return fallback
        raise RuntimeError("maeRunSimulation returned nil")
    print(f"maeRunSimulation returned history={history}", flush=True)
    return history


def trigger_run_gui_button(
    client: VirtuosoClient,
    session: str,
    cell: str,
    start_epoch: int,
) -> str:
    ensure_x11_helper(client)
    try:
        result = client.execute_skill(
            '''
let((s)
  s = sevSession(hiGetCurrentWindow())
  unless(s error("No sevSession on current window"))
  sevRun(s))
''',
            timeout=20,
        )
        if skill_ok(result):
            print(f"sevRun returned: {(result.output or '').strip()}", flush=True)
        else:
            print(f"sevRun non-success: {result}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"sevRun warning: {exc}", flush=True)

    for title in [
        "ADE Assembler Update and Run",
        "ADE Explorer Update and Run",
        "ADE Assembler Save Setup",
        "ADE Explorer Save Setup",
        "Save Setup",
    ]:
        if press_first_window(client, title):
            break
    time.sleep(2)
    for title in ["ADE Assembler Update and Run", "ADE Explorer Update and Run"]:
        press_first_window(client, title)
    return wait_for_history_after(client, cell, start_epoch)


def trigger_run_callback(
    client: VirtuosoClient,
    session: str,
    cell: str,
    start_epoch: int,
) -> str:
    try:
        history, status = run_and_wait(client, session=session, timeout=900)
        history_name = (history or "").strip().strip('"')
        print(f"run_and_wait returned history={history_name} status={status}", flush=True)
        if not history_name or history_name == "nil":
            raise RuntimeError("run_and_wait returned no history")
        return history_name
    except Exception as exc:  # noqa: BLE001
        print(f"run_and_wait warning: {exc}", flush=True)
        ensure_x11_helper(client)
        for title in [
            "ADE Assembler Update and Run",
            "ADE Explorer Update and Run",
            "ADE Assembler Save Setup",
            "ADE Explorer Save Setup",
            "Save Setup",
        ]:
            if press_first_window(client, title):
                break
        time.sleep(2)
        for title in ["ADE Assembler Update and Run", "ADE Explorer Update and Run"]:
            press_first_window(client, title)
        return wait_for_history_after(client, cell, start_epoch, timeout=90)


def trigger_run(
    client: VirtuosoClient,
    session: str,
    cell: str,
    start_epoch: int,
    trigger: str,
) -> str:
    if trigger == "mae":
        return trigger_run_mae(client, session, cell, start_epoch)
    if trigger == "gui-button":
        return trigger_run_gui_button(client, session, cell, start_epoch)
    if trigger == "callback":
        return trigger_run_callback(client, session, cell, start_epoch)
    raise ValueError(f"unsupported trigger mode: {trigger}")


def wait_for_completion(
    client: VirtuosoClient,
    history: str,
    run_log_remote: str,
    spectre_out_remote: str,
    timeout: int = 900,
) -> dict[str, object]:
    deadline = time.time() + timeout
    status: dict[str, object] = {}
    while time.time() < deadline:
        run_tail = remote_tail(client, run_log_remote, lines=80)
        spectre_tail = remote_tail(client, spectre_out_remote, lines=120)
        completed = f"{history} completed." in run_tail
        run_errors = parse_run_errors(run_tail)
        spectre_summary = parse_spectre_summary(spectre_tail)
        status = {
            "completed": completed,
            "run_errors": run_errors,
            "spectre_summary": spectre_summary,
            "run_log_tail": run_tail,
            "spectre_tail": spectre_tail,
        }
        print(
            json.dumps(
                {
                    "completed": completed,
                    "run_errors": run_errors,
                    "spectre_summary": spectre_summary,
                    "spectre_tail": spectre_tail.splitlines()[-6:],
                },
                indent=2,
            ),
            flush=True,
        )
        if completed:
            return status
        time.sleep(20)
    raise TimeoutError(f"{history} did not complete within timeout")


def download_if_exists(client: VirtuosoClient, remote: str, local: Path) -> bool:
    if not remote_file_exists(client, remote):
        return False
    local.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(remote, str(local))
    return True


def parse_waveforms(path: Path, columns: int) -> tuple[list[float], dict[str, list[float]]]:
    names = ["time"] + [f"c{idx}" for idx in range(columns)]
    times: list[float] = []
    waves = {name: [] for name in names[1:]}
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    row_re = re.compile(rf"^\s*((?:{number}\s+)+{number})(?:\s|$)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        values = [float(part) for part in match.group(1).split()]
        if len(values) != columns + 1:
            continue
        times.append(values[0])
        for idx in range(columns):
            waves[f"c{idx}"].append(values[idx + 1])
    if not times:
        raise RuntimeError(f"no waveform rows parsed from {path}")
    return times, waves


def crossing_time(times: list[float], values: list[float], threshold: float = VTH, edge: str = "rising") -> float | None:
    for idx in range(1, len(times)):
        prev = values[idx - 1] - threshold
        curr = values[idx] - threshold
        if edge == "rising" and prev < 0 <= curr:
            pass
        elif edge == "falling" and prev > 0 >= curr:
            pass
        else:
            continue
        denom = values[idx] - values[idx - 1]
        if denom == 0:
            return times[idx]
        frac = (threshold - values[idx - 1]) / denom
        return times[idx - 1] + frac * (times[idx] - times[idx - 1])
    return None


def all_crossings(times: list[float], values: list[float], threshold: float = VTH, edge: str = "rising") -> list[float]:
    out: list[float] = []
    for idx in range(1, len(times)):
        prev = values[idx - 1] - threshold
        curr = values[idx] - threshold
        if edge == "rising" and not (prev < 0 <= curr):
            continue
        if edge == "falling" and not (prev > 0 >= curr):
            continue
        denom = values[idx] - values[idx - 1]
        if denom == 0:
            out.append(times[idx])
        else:
            frac = (threshold - values[idx - 1]) / denom
            out.append(times[idx - 1] + frac * (times[idx] - times[idx - 1]))
    return out


def export_waveforms(
    client: VirtuosoClient,
    results_dir: str,
    wave_defs: list[tuple[str, str]],
    out_path: Path,
    tstop: float,
) -> tuple[list[float], dict[str, list[float]]]:
    remote_path = f"/tmp/submod_wave_{uuid.uuid4().hex}.txt"
    expressions = " ".join(expr for _, expr in wave_defs)
    client.execute_skill(f'openResults("{results_dir}")', timeout=30)
    client.execute_skill('selectResults("tran")', timeout=30)
    cmd = (
        "ocnPrint("
        f'?output "{remote_path}" '
        "?numberNotation 'none "
        "?numSpaces 1 "
        "?precision 16 "
        f"?from 0 "
        f"?to {tstop:.16g} "
        f"?step {SAMPLE_STEP:.16g} "
        f"{expressions})"
    )
    result = client.execute_skill(cmd, timeout=240)
    if not skill_ok(result):
        raise RuntimeError(f"ocnPrint failed for {signals}: {result}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(remote_path, str(out_path))
    client.execute_skill(f'deleteFile("{remote_path}")', timeout=10)
    times, cols = parse_waveforms(out_path, len(wave_defs))
    return times, {wave_defs[idx][0]: cols[f"c{idx}"] for idx in range(len(wave_defs))}


def parse_time(value: str) -> float:
    match = re.fullmatch(r"\s*([0-9.]+)\s*([fpnum]?)s?\s*", value)
    if not match:
        raise ValueError(f"unsupported time literal: {value}")
    scale = {"": 1.0, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}[match.group(2)]
    return float(match.group(1)) * scale


def quick_metrics(cell: str, times: list[float], waves: dict[str, list[float]]) -> dict[str, object]:
    if cell == "TB_SUBMOD_COMPARATOR_PERF":
        clk = crossing_time(times, waves["/CLKC"], edge="rising")
        diff = [a - b for a, b in zip(waves["/VOP"], waves["/VON"])]
        decision = crossing_time(times, diff, threshold=0.0, edge="rising")
        final_diff = diff[-1]
        return {
            "clk_rise_s": clk,
            "decision_cross_s": decision,
            "decision_delay_ps": None if clk is None or decision is None else (decision - clk) * 1e12,
            "final_vop": waves["/VOP"][-1],
            "final_von": waves["/VON"][-1],
            "final_diff_v": final_diff,
        }
    if cell == "TB_SUBMOD_CLK_NOOVERLAP_PERF":
        clk_rise = all_crossings(times, waves["/CLKIN"], edge="rising")
        op_rise = all_crossings(times, waves["/CLKOP"], edge="rising")
        on_rise = all_crossings(times, waves["/CLKON"], edge="rising")
        op_fall = all_crossings(times, waves["/CLKOP"], edge="falling")
        on_fall = all_crossings(times, waves["/CLKON"], edge="falling")
        both_high = sum(1 for a, b in zip(waves["/CLKOP"], waves["/CLKON"]) if a > VTH and b > VTH) * SAMPLE_STEP
        both_low = sum(1 for a, b in zip(waves["/CLKOP"], waves["/CLKON"]) if a < VTH and b < VTH) * SAMPLE_STEP
        return {
            "clkin_rise_ps": [x * 1e12 for x in clk_rise[:3]],
            "clkop_rise_ps": [x * 1e12 for x in op_rise[:3]],
            "clkon_rise_ps": [x * 1e12 for x in on_rise[:3]],
            "clkop_fall_ps": [x * 1e12 for x in op_fall[:3]],
            "clkon_fall_ps": [x * 1e12 for x in on_fall[:3]],
            "both_high_total_ps": both_high * 1e12,
            "both_low_total_ps": both_low * 1e12,
        }
    if cell == "TB_SUBMOD_ASYCTRL_9CLK_PERF":
        rises = {}
        falls = {}
        clko_min = {}
        clko_max = {}
        clko_final = {}
        for bit in range(9):
            sig = f"/CLKO<{bit}>"
            rises[sig] = [x * 1e12 for x in all_crossings(times, waves[sig], edge="rising")[:3]]
            falls[sig] = [x * 1e12 for x in all_crossings(times, waves[sig], edge="falling")[:3]]
            clko_min[sig] = min(waves[sig])
            clko_max[sig] = max(waves[sig])
            clko_final[sig] = waves[sig][-1]
        return {
            "valid_rise_ps": [x * 1e12 for x in all_crossings(times, waves["/VALID"], edge="rising")[:5]],
            "clko_first_rise_ps": {sig: (vals[0] if vals else None) for sig, vals in rises.items()},
            "clko_rises_ps": rises,
            "clko_first_fall_ps": {sig: (vals[0] if vals else None) for sig, vals in falls.items()},
            "clko_falls_ps": falls,
            "clko_min_v": clko_min,
            "clko_max_v": clko_max,
            "clko_final_v": clko_final,
            "clko_rail_count": sum(1 for value in clko_max.values() if value > VTH),
            "clkc_min": min(waves["/CLKC"]),
            "clkc_max": max(waves["/CLKC"]),
        }
    if cell == "TB_SUBMOD_BOOTSTRAP_DIFF_PERF":
        diff_in = [a - b for a, b in zip(waves["/VIP"], waves["/VIN"])]
        diff_out = [a - b for a, b in zip(waves["/VOUTP"], waves["/VOUTN"])]
        on_errors = [
            abs(o - i)
            for clk, i, o in zip(waves["/CLKS"], diff_in, diff_out)
            if clk > VTH
        ]
        return {
            "vip": waves["/VIP"][-1],
            "vin": waves["/VIN"][-1],
            "voutp_final": waves["/VOUTP"][-1],
            "voutn_final": waves["/VOUTN"][-1],
            "diff_in_v": diff_in[-1],
            "diff_out_final_v": diff_out[-1],
            "max_on_diff_error_mv": max(on_errors) * 1e3 if on_errors else None,
            "mean_on_diff_error_mv": (sum(on_errors) / len(on_errors)) * 1e3 if on_errors else None,
        }
    return {}


def trapz(times: list[float], values: list[float]) -> float:
    total = 0.0
    for idx in range(1, len(times)):
        total += 0.5 * (values[idx] + values[idx - 1]) * (times[idx] - times[idx - 1])
    return total


def offline_metric_values(
    spec: dict[str, object],
    times: list[float],
    waves: dict[str, list[float]],
) -> dict[str, object]:
    values: dict[str, object] = {}
    duration = times[-1] - times[0] if len(times) > 1 else 0.0
    for item in list(spec.get("offline_metrics", [])):
        if str(item.get("source", "")) != "vdd_current_a":
            continue
        current = waves.get("vdd_current_a")
        if not current or duration <= 0:
            values[str(item["name"])] = None
            continue
        vdd = float(str(item.get("vdd", "0.9")))
        current_integral = trapz(times, current)
        energy = -vdd * current_integral
        operation = str(item.get("operation", ""))
        if operation == "avg_power_from_supply_current":
            values[str(item["name"])] = energy / duration
        elif operation == "energy_from_supply_current":
            values[str(item["name"])] = energy
    return values


def run_one(client: VirtuosoClient, spec: dict[str, object], trigger: str) -> dict[str, object]:
    cell = str(spec["cell"])
    signals = [str(sig) for sig in spec["signals"]]
    tstop = parse_time(str(spec["stop"]))
    run_dir = RUN_ROOT / cell
    run_dir.mkdir(parents=True, exist_ok=True)
    session = open_gui_session(client, LIB, cell, timeout=180)
    try:
        run_skill(client, f"save {cell}", f'maeSaveSetup(?session "{session}")', timeout=60)
        start_epoch = remote_epoch(client)
        history = trigger_run(client, session, cell, start_epoch, trigger)
        run_log_remote = f"/home/IC/Desktop/Project/{LIB}/{cell}/maestro/results/maestro/{history}.log"
        results_dir_remote = f"/home/IC/simulation/{LIB}/{cell}/maestro/results/maestro/{history}/1/{TEST_NAME}/psf"
        spectre_out_remote = f"{results_dir_remote}/spectre.out"
        netlist_remote = f"/home/IC/simulation/{LIB}/{cell}/maestro/results/maestro/{history}/1/{TEST_NAME}/netlist/input.scs"
        status = wait_for_completion(client, history, run_log_remote, spectre_out_remote)

        local_history_dir = run_dir / history
        download_if_exists(client, run_log_remote, local_history_dir / f"{history}.log")
        download_if_exists(client, spectre_out_remote, local_history_dir / "spectre.out")
        download_if_exists(client, netlist_remote, local_history_dir / "input.scs")
        local_run_log = local_history_dir / f"{history}.log"
        maestro_metrics = {}
        if local_run_log.exists():
            maestro_metrics = parse_maestro_metrics(
                local_run_log.read_text(encoding="utf-8", errors="replace")
            )
        if status["run_errors"] not in (0, None):
            summary = {
                "cell": cell,
                "history": history,
                "session": session,
                "signals": signals,
                "run_log_remote": run_log_remote,
                "results_dir_remote": results_dir_remote,
                "spectre_out_remote": spectre_out_remote,
                "netlist_remote": netlist_remote,
                "completed": status["completed"],
                "run_errors": status["run_errors"],
                "spectre_summary": status["spectre_summary"],
                "maestro_metrics": maestro_metrics,
                "waveform_points": 0,
                "metrics": {},
                "error": "Maestro reported simulation errors; waveform export skipped.",
            }
            (local_history_dir / "summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
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
            results_dir_remote,
            wave_defs,
            local_history_dir / "waveforms.txt",
            tstop,
        )
        metrics = quick_metrics(cell, times, waves)
        offline_metrics = offline_metric_values(spec, times, waves)
        if offline_metrics:
            metrics["offline"] = offline_metrics
        summary = {
            "cell": cell,
            "history": history,
            "session": session,
            "signals": signals,
            "run_log_remote": run_log_remote,
            "results_dir_remote": results_dir_remote,
            "spectre_out_remote": spectre_out_remote,
            "netlist_remote": netlist_remote,
            "completed": status["completed"],
            "run_errors": status["run_errors"],
            "spectre_summary": status["spectre_summary"],
            "maestro_metrics": maestro_metrics,
            "waveform_points": len(times),
            "metrics": metrics,
        }
        (local_history_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary
    finally:
        try:
            close_gui_session(client, session, save=True, timeout=90)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: close_gui_session failed for {cell}: {exc}", flush=True)


def merge_run_manifest(base: dict[str, object], summaries: list[dict[str, object]], trigger: str) -> dict[str, object]:
    merged = {str(item["cell"]): item for item in list(base.get("runs", []))}
    for item in summaries:
        merged[str(item["cell"])] = item
    return {
        **base,
        "library": LIB,
        "test_name": TEST_NAME,
        "sample_step_s": SAMPLE_STEP,
        "trigger": trigger,
        "runs": list(merged.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", help="run only one testbench cell")
    parser.add_argument(
        "--trigger",
        choices=["gui-button", "mae", "callback"],
        default="gui-button",
        help="run trigger method; callback uses maeRunSimulation(?callback ...)",
    )
    args = parser.parse_args()

    manifest = json.loads(SETUP_MANIFEST.read_text(encoding="utf-8"))
    client = VirtuosoClient.from_env()
    summaries = []
    for spec in manifest["testbenches"]:
        if args.cell and spec["cell"] != args.cell:
            continue
        summaries.append(run_one(client, spec, args.trigger))
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = RUN_ROOT / "submodule_run_manifest.json"
    base_manifest: dict[str, object] = {}
    if args.cell and out_path.exists():
        base_manifest = json.loads(out_path.read_text(encoding="utf-8"))
    run_manifest = merge_run_manifest(base_manifest, summaries, args.trigger)
    out_path.write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    print(json.dumps(run_manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
