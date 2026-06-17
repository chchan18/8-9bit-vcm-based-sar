#!/usr/bin/env python3
"""Export decoder/DAC-side nodes from an existing ADC_redun1_tb Maestro run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import close_gui_session, open_gui_session

from dout9_offline_measure import LIB, TB_CELL, export_signal


DAC_INPUT_NET_BY_BIT = {
    0: "net18",
    1: "net17",
    2: "net16",
    3: "net15",
    4: "net14",
    5: "net13",
    6: "net11",
    7: "net10",
}

DECODER_OUTPUT_NET_BY_BIT = {
    0: "net18",
    1: "net17",
    2: "net16",
    3: "net15",
    4: "net14",
    5: "net13",
    6: "net11",
    7: "net10",
}


def export_nodes(history: str, out_dir: Path) -> dict:
    client = VirtuosoClient.from_env()
    session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    exports: dict[str, str] = {}
    errors: dict[str, str] = {}
    try:
        signals: list[tuple[str, str]] = [("out", 'VT("/out")')]
        for bit, net in DAC_INPUT_NET_BY_BIT.items():
            signals.append((f"DAC_B{bit}", f'VT("/{net}")'))
        for bit in range(9):
            signals.append((f"BIP{bit}", f'VT("/biP<{bit}>")'))

        for name, expr in signals:
            path = out_dir / f"{name}.txt"
            print(f"Exporting {name}: {expr}", flush=True)
            try:
                export_signal(client, session, history, expr, path)
            except Exception as exc:
                print(f"WARNING: {name} failed: {exc}", flush=True)
                errors[name] = str(exc)
            else:
                exports[name] = str(path)
    finally:
        try:
            close_gui_session(client, session, save=False, timeout=90)
        except Exception as exc:
            print(f"WARNING: close_gui_session failed: {exc}", flush=True)

    result = {"history": history, "exports": exports, "errors": errors}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "export_manifest.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", default="ExplorerRun.0")
    parser.add_argument(
        "--out-dir",
        default="sar9b_work/wave_exports_binary/ExplorerRun.0/decoder_nodes",
    )
    args = parser.parse_args()
    result = export_nodes(args.history, Path(args.out_dir).resolve())
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
