#!/usr/bin/env python3
"""Create SAR9B submodule schematics and Maestro transient setups."""

from __future__ import annotations

import json
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


LIB = "SAR9B_400MV"
TEST_NAME = "TRAN"
OUT_DIR = Path("projects/sar9b_submodule_maestro/artifacts")
MODEL_FILE = (
    "/home/IC/Desktop/Project/project_tsmcN28_NEW/project_tsmcN28_NEW/"
    "iPDK_CRN28HPC+_v1.0_2p2a_20160226_all/CRN28HPCp/models/spectre/toplevel.scs"
)


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


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


def cell_exists(client: VirtuosoClient, cell: str, view: str) -> bool:
    out = run_skill(
        client,
        f"check {LIB}/{cell}/{view}",
        f'''
let((cv)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "{view}" "" "r")
  when(cv dbClose(cv))
  if(cv "yes" "no"))
''',
        timeout=30,
    )
    return '"yes"' in out


def set_instance_params(client: VirtuosoClient, cell: str, params: list[tuple[str, str, str]]) -> None:
    items = " ".join(f'list("{name}" "{param}" "{value}")' for name, param, value in params)
    run_skill(
        client,
        f"set schematic params {cell}",
        f'''
let((cv)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "a")
  unless(cv error("cannot open schematic"))
  foreach(item list({items})
    let((inst cdf par pname pval)
      inst = dbGetInstByName(cv car(item))
      pname = cadr(item)
      pval = caddr(item)
      unless(inst error(strcat("missing instance " car(item))))
      cdf = cdfGetInstCDF(inst)
      par = when(cdf cdfFindParamByName(cdf pname))
      if(par then
        par~>value = pval
      else
        inst~>pname = pval)))
  schCheck(cv)
  cv~>connectivityLastUpdated = 0
  dbSave(cv)
  dbClose(cv)
  "ok")
''',
        timeout=120,
    )


def create_common_supply(sch) -> None:
    sch.add(inst("analogLib", "vdc", "symbol", "VDD_SRC", -4.0, 3.0, "R0"))
    sch.add(inst("analogLib", "gnd", "symbol", "GND0", -4.0, 1.8, "R0"))
    sch.add(label_term("VDD_SRC", "PLUS", "VDD"))
    sch.add(label_term("VDD_SRC", "MINUS", "0"))
    sch.add(label_term("GND0", "gnd!", "0"))


def add_load_cap(sch, name: str, net: str, x: float, y: float) -> None:
    sch.add(inst("analogLib", "cap", "symbol", name, x, y, "R0"))
    sch.add(label_term(name, "PLUS", net))
    sch.add(label_term(name, "MINUS", "0"))


def create_comparator_tb(client: VirtuosoClient) -> dict[str, object]:
    cell = "TB_SUBMOD_COMPARATOR_PERF"
    if not cell_exists(client, cell, "schematic"):
        with client.schematic.edit(LIB, cell) as sch:
            create_common_supply(sch)
            sch.add(inst(LIB, "COMPARATOR", "symbol", "XCOMP", 0.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VCLK", -4.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vdc", "symbol", "VVP", -4.0, -2.0, "R0"))
            sch.add(inst("analogLib", "vdc", "symbol", "VVN", -4.0, -3.5, "R0"))
            add_load_cap(sch, "C_VOP", "VOP", 3.2, 0.7)
            add_load_cap(sch, "C_VON", "VON", 3.2, -0.7)
            for term, net in [
                ("CLKC", "CLKC"),
                ("VDD", "VDD"),
                ("VSS", "0"),
                ("VP", "VP"),
                ("VN", "VN"),
                ("VOP", "VOP"),
                ("VON", "VON"),
            ]:
                sch.add(label_term("XCOMP", term, net))
            for source, plus, minus in [
                ("VCLK", "CLKC", "0"),
                ("VVP", "VP", "0"),
                ("VVN", "VN", "0"),
            ]:
                sch.add(label_term(source, "PLUS", plus))
                sch.add(label_term(source, "MINUS", minus))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VCLK", "vdc", "0"),
            ("VCLK", "v2", "vdd"),
            ("VCLK", "td", "1n"),
            ("VCLK", "tr", "5p"),
            ("VCLK", "tf", "5p"),
            ("VCLK", "pw", "2n"),
            ("VCLK", "per", "5n"),
            ("VVP", "vdc", "vcm+vdiff/2"),
            ("VVN", "vdc", "vcm-vdiff/2"),
            ("C_VOP", "c", "cload"),
            ("C_VON", "c", "cload"),
        ],
    )
    return {
        "cell": cell,
        "stop": "8n",
        "vars": {"vdd": "900m", "vcm": "450m", "vdiff": "10m", "cload": "2f"},
        "signals": ["/CLKC", "/VP", "/VN", "/VOP", "/VON"],
    }


def create_clk_nooverlap_tb(client: VirtuosoClient) -> dict[str, object]:
    cell = "TB_SUBMOD_CLK_NOOVERLAP_PERF"
    if not cell_exists(client, cell, "schematic"):
        with client.schematic.edit(LIB, cell) as sch:
            create_common_supply(sch)
            sch.add(inst(LIB, "CLK_NOOVERLAP", "symbol", "XNO", 0.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VCLK", -4.0, 0.0, "R0"))
            add_load_cap(sch, "C_CLKOP", "CLKOP", 3.2, 0.7)
            add_load_cap(sch, "C_CLKON", "CLKON", 3.2, -0.7)
            for term, net in [
                ("CLKIN", "CLKIN"),
                ("CLKOP", "CLKOP"),
                ("CLKON", "CLKON"),
                ("VDD", "VDD"),
                ("VSS", "0"),
            ]:
                sch.add(label_term("XNO", term, net))
            sch.add(label_term("VCLK", "PLUS", "CLKIN"))
            sch.add(label_term("VCLK", "MINUS", "0"))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VCLK", "vdc", "0"),
            ("VCLK", "v2", "vdd"),
            ("VCLK", "td", "500p"),
            ("VCLK", "tr", "5p"),
            ("VCLK", "tf", "5p"),
            ("VCLK", "pw", "2n"),
            ("VCLK", "per", "5n"),
            ("C_CLKOP", "c", "cload"),
            ("C_CLKON", "c", "cload"),
        ],
    )
    return {
        "cell": cell,
        "stop": "12n",
        "vars": {"vdd": "900m", "cload": "2f"},
        "signals": ["/CLKIN", "/CLKOP", "/CLKON"],
    }


def create_asyctrl_tb(client: VirtuosoClient) -> dict[str, object]:
    cell = "TB_SUBMOD_ASYCTRL_9CLK_PERF"
    if not cell_exists(client, cell, "schematic"):
        with client.schematic.edit(LIB, cell) as sch:
            create_common_supply(sch)
            sch.add(inst(LIB, "Asycontrol_logic_9clk", "symbol", "XASY", 0.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vdc", "symbol", "VCLKS", -4.0, 0.8, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VVALID", -4.0, -0.8, "R0"))
            add_load_cap(sch, "C_CLKC", "CLKC", 3.2, 0.7)
            for bit in range(9):
                add_load_cap(sch, f"C_CLKO{bit}", f"CLKO<{bit}>", 3.2, -0.5 - 0.35 * bit)
            for term, net in [
                ("CLKS", "CLKS"),
                ("VALID", "VALID"),
                ("CLKC", "CLKC"),
                ("CLKO<8:0>", "CLKO<8:0>"),
                ("VDD", "VDD"),
                ("VSS", "0"),
            ]:
                sch.add(label_term("XASY", term, net))
            sch.add(label_term("VCLKS", "PLUS", "CLKS"))
            sch.add(label_term("VCLKS", "MINUS", "0"))
            sch.add(label_term("VVALID", "PLUS", "VALID"))
            sch.add(label_term("VVALID", "MINUS", "0"))
    params = [
        ("VDD_SRC", "vdc", "vdd"),
        ("VCLKS", "vdc", "vdd"),
        ("VVALID", "vdc", "0"),
        ("VVALID", "v2", "vdd"),
        ("VVALID", "td", "500p"),
        ("VVALID", "tr", "5p"),
        ("VVALID", "tf", "5p"),
        ("VVALID", "pw", "1n"),
        ("VVALID", "per", "2.5n"),
        ("C_CLKC", "c", "cload"),
    ]
    params.extend((f"C_CLKO{bit}", "c", "cload") for bit in range(9))
    set_instance_params(client, cell, params)
    return {
        "cell": cell,
        "stop": "28n",
        "vars": {"vdd": "900m", "cload": "1f"},
        "signals": ["/CLKS", "/VALID", "/CLKC"] + [f"/CLKO<{bit}>" for bit in range(9)],
    }


def create_bootstrap_tb(client: VirtuosoClient) -> dict[str, object]:
    cell = "TB_SUBMOD_BOOTSTRAP_DIFF_PERF"
    if not cell_exists(client, cell, "schematic"):
        with client.schematic.edit(LIB, cell) as sch:
            create_common_supply(sch)
            sch.add(inst(LIB, "BOOTSTRAP_DIFF", "symbol", "XBOOT", 0.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VCLKS", -4.0, 1.2, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VCLKSB", -4.0, -0.2, "R0"))
            sch.add(inst("analogLib", "vdc", "symbol", "VVIP", -4.0, -1.8, "R0"))
            sch.add(inst("analogLib", "vdc", "symbol", "VVIN", -4.0, -3.2, "R0"))
            add_load_cap(sch, "C_VOUTP", "VOUTP", 3.2, 0.7)
            add_load_cap(sch, "C_VOUTN", "VOUTN", 3.2, -0.7)
            for term, net in [
                ("CLKS", "CLKS"),
                ("CLKSB", "CLKSB"),
                ("VDD", "VDD"),
                ("VSS", "0"),
                ("VIP", "VIP"),
                ("VIN", "VIN"),
                ("VOUTP", "VOUTP"),
                ("VOUTN", "VOUTN"),
            ]:
                sch.add(label_term("XBOOT", term, net))
            for source, plus, minus in [
                ("VCLKS", "CLKS", "0"),
                ("VCLKSB", "CLKSB", "0"),
                ("VVIP", "VIP", "0"),
                ("VVIN", "VIN", "0"),
            ]:
                sch.add(label_term(source, "PLUS", plus))
                sch.add(label_term(source, "MINUS", minus))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VCLKS", "vdc", "0"),
            ("VCLKS", "v2", "vdd"),
            ("VCLKS", "td", "500p"),
            ("VCLKS", "tr", "5p"),
            ("VCLKS", "tf", "5p"),
            ("VCLKS", "pw", "2n"),
            ("VCLKS", "per", "5n"),
            ("VCLKSB", "vdc", "vdd"),
            ("VCLKSB", "v2", "0"),
            ("VCLKSB", "td", "500p"),
            ("VCLKSB", "tr", "5p"),
            ("VCLKSB", "tf", "5p"),
            ("VCLKSB", "pw", "2n"),
            ("VCLKSB", "per", "5n"),
            ("VVIP", "vdc", "vcm+vdiff/2"),
            ("VVIN", "vdc", "vcm-vdiff/2"),
            ("C_VOUTP", "c", "cload"),
            ("C_VOUTN", "c", "cload"),
        ],
    )
    return {
        "cell": cell,
        "stop": "12n",
        "vars": {"vdd": "900m", "vcm": "450m", "vdiff": "100m", "cload": "5f"},
        "signals": ["/CLKS", "/CLKSB", "/VIP", "/VIN", "/VOUTP", "/VOUTN"],
    }


def ensure_maestro_setup(client: VirtuosoClient, spec: dict[str, object]) -> dict[str, object]:
    cell = str(spec["cell"])
    session = open_session(client, LIB, cell)
    try:
        tests = run_skill(
            client,
            f"read Maestro tests {cell}",
            f'maeGetSetup(?session "{session}")',
            timeout=60,
        )
        if f'"{TEST_NAME}"' not in tests:
            create_test(client, TEST_NAME, lib=LIB, cell=cell, session=session)
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
            options=f'(("stop" "{spec["stop"]}") ("errpreset" "moderate"))',
            session=session,
        )
        for name, value in dict(spec["vars"]).items():
            set_var(client, name, value, session=session)
            set_var(client, name, value, type_name="test", type_value=f'("{TEST_NAME}")', session=session)

        # Add waveform outputs only if missing. Scalar metrics are derived offline
        # from exported waveforms to avoid fragile Maestro expression serialization.
        added_outputs: list[dict[str, str]] = []
        for signal in list(spec["signals"]):
            out_name = signal.strip("/").replace("<", "_").replace(">", "").replace(":", "_")
            try:
                raw = add_output(
                    client,
                    out_name,
                    TEST_NAME,
                    output_type="net",
                    signal_name=signal,
                    session=session,
                )
                added_outputs.append({"name": out_name, "signal": signal, "raw": raw})
            except Exception as exc:  # noqa: BLE001
                added_outputs.append({"name": out_name, "signal": signal, "error": str(exc)})
        save_setup(client, LIB, cell, session=session)
        views = run_skill(
            client,
            f"verify views {cell}",
            f'''
let((obj)
  obj = ddGetObj("{LIB}" "{cell}")
  if(obj obj~>views~>name nil))
''',
            timeout=30,
        )
        return {"cell": cell, "session": session, "views": views, "outputs": added_outputs}
    finally:
        close_session(client, session)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    specs = [
        create_comparator_tb(client),
        create_clk_nooverlap_tb(client),
        create_asyctrl_tb(client),
        create_bootstrap_tb(client),
    ]
    maestro = [ensure_maestro_setup(client, spec) for spec in specs]
    manifest = {
        "library": LIB,
        "test_name": TEST_NAME,
        "model_file": MODEL_FILE,
        "testbenches": specs,
        "maestro": maestro,
    }
    out_path = OUT_DIR / "submodule_maestro_setup_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
