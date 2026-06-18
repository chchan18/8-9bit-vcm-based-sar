#!/usr/bin/env python3
"""Create a coherent-sine FFT Maestro test for the bootstrap sampler."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    add_output,
    close_session,
    create_test,
    open_session,
    save_setup,
    set_analysis,
    set_env_option,
    set_sim_option,
    set_var,
)
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as label_term,
)

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from create_submodule_maestro_tests import (  # noqa: E402
    LIB,
    MODEL_FILE,
    TEST_NAME,
    add_load_cap,
    cell_exists,
    clear_schematic,
    create_common_supply,
    run_skill,
    set_instance_params,
)


PROJECT_DIR = Path("projects/sar9b_submodule_maestro")
OUT_DIR = PROJECT_DIR / "artifacts"
CELL = "TB_SUBMOD_BOOTSTRAP_DIFF_FFT"


def create_schematic(client: VirtuosoClient, rebuild: bool = False) -> None:
    exists = cell_exists(client, CELL, "schematic")
    if rebuild and exists:
        clear_schematic(client, CELL)
        exists = False
    if exists:
        return

    with client.schematic.edit(LIB, CELL) as sch:
        create_common_supply(sch)
        sch.add(inst(LIB, "BOOTSTRAP_DIFF", "symbol", "XBOOT", 0.0, 0.0, "R0"))
        sch.add(inst("analogLib", "vpulse", "symbol", "VCLKS", -4.0, 1.2, "R0"))
        sch.add(inst("analogLib", "vpulse", "symbol", "VCLKSB", -4.0, -0.2, "R0"))
        sch.add(inst("analogLib", "vsource", "symbol", "VSIN", -4.0, -1.8, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VCM_SRC", -4.0, -3.2, "R0"))
        sch.add(inst("analogLib", "ideal_balun", "symbol", "IBAL", -1.8, -2.3, "R0"))
        add_load_cap(sch, "C_VOUTP", "VOUTP", 3.2, 0.7)
        add_load_cap(sch, "C_VOUTN", "VOUTN", 3.2, -0.7)

        for term, net in [
            ("CLKS", "CLKS"),
            ("CLKSB", "CLKSB"),
            ("VDD", "VDD"),
            ("VSS", "VSS"),
            ("VIP", "VIP"),
            ("VIN", "VIN"),
            ("VOUTP", "VOUTP"),
            ("VOUTN", "VOUTN"),
        ]:
            sch.add(label_term("XBOOT", term, net))

        for source, plus, minus in [
            ("VCLKS", "CLKS", "VSS"),
            ("VCLKSB", "CLKSB", "VSS"),
            ("VSIN", "VIN_DRV", "VSS"),
            ("VCM_SRC", "VCM", "VSS"),
        ]:
            sch.add(label_term(source, "PLUS", plus))
            sch.add(label_term(source, "MINUS", minus))

        for term, net in [("d", "VIN_DRV"), ("c", "VCM"), ("p", "VIP"), ("n", "VIN")]:
            sch.add(label_term("IBAL", term, net))


def configure_schematic_params(client: VirtuosoClient) -> None:
    set_instance_params(
        client,
        CELL,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VSS_SRC", "vdc", "0"),
            ("VCLKS", "v1", "0"),
            ("VCLKS", "v2", "vdd"),
            ("VCLKS", "td", "1p"),
            ("VCLKS", "tr", "1p"),
            ("VCLKS", "tf", "1p"),
            ("VCLKS", "pw", "0.2/fs"),
            ("VCLKS", "per", "1/fs"),
            ("VCLKSB", "v1", "vdd"),
            ("VCLKSB", "v2", "0"),
            ("VCLKSB", "td", "1p"),
            ("VCLKSB", "tr", "1p"),
            ("VCLKSB", "tf", "1p"),
            ("VCLKSB", "pw", "0.2/fs"),
            ("VCLKSB", "per", "1/fs"),
            ("VSIN", "srcType", "sine"),
            ("VSIN", "va", "Vpk"),
            ("VSIN", "freq", "(fft_bin/fft_n)*fs"),
            ("VSIN", "td", "50p"),
            ("VSIN", "sinedc", "0"),
            ("VSIN", "filenums", "none"),
            ("VCM_SRC", "vdc", "vcm"),
            ("C_VOUTP", "c", "cload"),
            ("C_VOUTN", "c", "cload"),
        ],
    )


def ensure_maestro(client: VirtuosoClient) -> dict[str, object]:
    session = open_session(client, LIB, CELL)
    outputs: list[dict[str, str]] = []
    try:
        tests = run_skill(client, f"read Maestro tests {CELL}", f'maeGetSetup(?session "{session}")')
        if f'"{TEST_NAME}"' not in tests:
            create_test(client, TEST_NAME, lib=LIB, cell=CELL, session=session)
        set_env_option(
            client,
            TEST_NAME,
            f'(("modelFiles" (("{MODEL_FILE}" "top_tt"))))',
            session=session,
        )
        set_sim_option(
            client,
            TEST_NAME,
            '(("temp" "27") ("reltol" "1e-3") ("maxnotes" "5") ("maxwarns" "5"))',
            session=session,
        )
        set_analysis(
            client,
            TEST_NAME,
            "tran",
            options='(("stop" "TSTOP") ("errpreset" "moderate"))',
            session=session,
        )
        for name, value in {
            "vdd": "900m",
            "vcm": "450m",
            "Vpk": "800m",
            "fs": "400M",
            "fft_bin": "7",
            "fft_n": "1024",
            "TSTOP": "2.7u",
            "cload": "5f",
        }.items():
            set_var(client, name, value, session=session)
            set_var(client, name, value, type_name="test", type_value=f'("{TEST_NAME}")', session=session)

        for signal in ["/CLKS", "/CLKSB", "/VIP", "/VIN", "/VOUTP", "/VOUTN"]:
            out_name = signal.strip("/").replace("<", "_").replace(">", "")
            try:
                raw = add_output(
                    client,
                    out_name,
                    TEST_NAME,
                    output_type="net",
                    signal_name=signal,
                    session=session,
                )
                outputs.append({"name": out_name, "signal": signal, "raw": raw})
            except Exception as exc:  # noqa: BLE001
                outputs.append({"name": out_name, "signal": signal, "error": str(exc)})
        save_setup(client, LIB, CELL, session=session)
        return {"cell": CELL, "session": session, "outputs": outputs}
    finally:
        close_session(client, session)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-schematic", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    create_schematic(client, rebuild=args.rebuild_schematic)
    configure_schematic_params(client)
    maestro = ensure_maestro(client)
    manifest = {
        "library": LIB,
        "cell": CELL,
        "test_name": TEST_NAME,
        "model_file": MODEL_FILE,
        "maestro": maestro,
        "variables": {
            "vdd": "900m",
            "vcm": "450m",
            "Vpk": "800m",
            "fs": "400M",
            "fft_bin": "7",
            "fft_n": "1024",
            "TSTOP": "2.7u",
            "cload": "5f",
        },
        "fft": {
            "sample_start_s": 28.2e-9,
            "sample_step_s": 2.5e-9,
            "samples": 1024,
            "fundamental_bin": 7,
            "input_frequency_hz": 7 / 1024 * 400e6,
        },
    }
    out_path = OUT_DIR / "bootstrap_fft_setup_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
