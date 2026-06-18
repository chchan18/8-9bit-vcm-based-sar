#!/usr/bin/env python3
"""Create SAR9B submodule schematics and Maestro transient setups."""

from __future__ import annotations

import argparse
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
    schematic_create_wire_between_instance_terms as wire_between,
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


def clear_schematic(client: VirtuosoClient, cell: str) -> None:
    run_skill(
        client,
        f"clear schematic {cell}",
        f'''
let((cv)
  cv = dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "a")
  unless(cv error("cannot open schematic"))
  foreach(obj cv~>instances dbDeleteObject(obj))
  foreach(obj cv~>shapes dbDeleteObject(obj))
  dbSave(cv)
  dbClose(cv)
  "cleared")
''',
        timeout=120,
    )


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
  dbReplaceProp(cv "instance#" 'int length(cv~>instances))
  dbSave(cv)
  dbSetConnCurrent(cv)
  dbSave(cv)
  dbClose(cv)
  "ok")
''',
        timeout=120,
    )


def create_common_supply(sch) -> None:
    sch.add(inst("analogLib", "vdc", "symbol", "VDD_SRC", -7.0, 3.0, "R0"))
    sch.add(inst("analogLib", "vdc", "symbol", "VSS_SRC", -7.0, 1.8, "R0"))
    sch.add(inst("analogLib", "gnd", "symbol", "GND0", -7.0, 0.6, "R0"))
    sch.add(label_term("VDD_SRC", "PLUS", "VDD"))
    sch.add(label_term("VDD_SRC", "MINUS", "VSS"))
    sch.add(label_term("VSS_SRC", "PLUS", "VSS"))
    sch.add(wire_between("VSS_SRC", "MINUS", "GND0", "gnd!"))


def add_load_cap(sch, name: str, net: str, x: float, y: float, ref: str = "VSS") -> None:
    sch.add(inst("analogLib", "cap", "symbol", name, x, y, "R0"))
    sch.add(label_term(name, "PLUS", net))
    sch.add(label_term(name, "MINUS", ref))


def skill_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def metric(name: str, expr: str, unit: str, description: str) -> dict[str, str]:
    return {"name": name, "expr": expr, "unit": unit, "description": description}


def offline_supply_metrics(prefix: str) -> list[dict[str, str]]:
    return [
        {
            "name": f"{prefix}_avg_power_w",
            "unit": "W",
            "description": "Average positive supply power over the transient run",
            "source": "vdd_current_a",
            "waveform_expr": 'getData("/VDD_SRC/PLUS" ?result "tran")',
            "operation": "avg_power_from_supply_current",
            "vdd": "0.9",
        },
        {
            "name": f"{prefix}_energy_j",
            "unit": "J",
            "description": "Positive supply energy over the transient run",
            "source": "vdd_current_a",
            "waveform_expr": 'getData("/VDD_SRC/PLUS" ?result "tran")',
            "operation": "energy_from_supply_current",
            "vdd": "0.9",
        },
    ]


def add_point_output(client: VirtuosoClient, session: str, name: str, expr: str) -> str:
    return run_skill(
        client,
        f"add/update metric {name}",
        (
            f"maeAddOutput({skill_string(name)} {skill_string(TEST_NAME)} "
            f'?outputType "point" ?expr {skill_string(expr)} '
            f"?session {skill_string(session)})"
        ),
        timeout=90,
    )


def create_comparator_tb(client: VirtuosoClient, rebuild: bool = False) -> dict[str, object]:
    cell = "TB_SUBMOD_COMPARATOR_PERF"
    exists = cell_exists(client, cell, "schematic")
    if rebuild and exists:
        clear_schematic(client, cell)
        exists = False
    if not exists:
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
                ("VSS", "VSS"),
                ("VP", "VP"),
                ("VN", "VN"),
                ("VOP", "VOP"),
                ("VON", "VON"),
            ]:
                sch.add(label_term("XCOMP", term, net))
            for source, plus, minus in [
                ("VCLK", "CLKC", "VSS"),
                ("VVP", "VP", "VSS"),
                ("VVN", "VN", "VSS"),
            ]:
                sch.add(label_term(source, "PLUS", plus))
                sch.add(label_term(source, "MINUS", minus))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VSS_SRC", "vdc", "0"),
            ("VCLK", "v1", "0"),
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
        "metrics": [
            metric(
                "cmp_clk_rise_s",
                'cross(VT("/CLKC") 0.45 1 "rising" nil nil)',
                "s",
                "First comparator clock rising threshold crossing",
            ),
            metric(
                "cmp_decision_cross_s",
                'cross((VT("/VOP")-VT("/VON")) 0 1 "rising" nil nil)',
                "s",
                "First differential output zero crossing",
            ),
            metric(
                "cmp_decision_delay_ps",
                (
                    '(cross((VT("/VOP")-VT("/VON")) 0 1 "rising" nil nil)'
                    '-cross(VT("/CLKC") 0.45 1 "rising" nil nil))*1e12'
                ),
                "ps",
                "Clock-to-decision delay",
            ),
            metric("cmp_vop_max_v", 'ymax(VT("/VOP"))', "V", "Maximum VOP swing"),
            metric("cmp_von_min_v", 'ymin(VT("/VON"))', "V", "Minimum VON swing"),
            metric(
                "cmp_final_diff_v",
                'value((VT("/VOP")-VT("/VON")) 8e-09)',
                "V",
                "Final differential output at stop time",
            ),
        ],
        "offline_metrics": offline_supply_metrics("cmp"),
    }


def create_clk_nooverlap_tb(client: VirtuosoClient, rebuild: bool = False) -> dict[str, object]:
    cell = "TB_SUBMOD_CLK_NOOVERLAP_PERF"
    exists = cell_exists(client, cell, "schematic")
    if rebuild and exists:
        clear_schematic(client, cell)
        exists = False
    if not exists:
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
                ("VSS", "VSS"),
            ]:
                sch.add(label_term("XNO", term, net))
            sch.add(label_term("VCLK", "PLUS", "CLKIN"))
            sch.add(label_term("VCLK", "MINUS", "VSS"))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VSS_SRC", "vdc", "0"),
            ("VCLK", "v1", "0"),
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
        "metrics": [
            metric(
                "clk_clkop_delay_ps",
                (
                    '(cross(VT("/CLKOP") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/CLKIN") 0.45 1 "rising" nil nil))*1e12'
                ),
                "ps",
                "CLKIN rising to CLKOP rising delay",
            ),
            metric(
                "clk_clkon_delay_ps",
                (
                    '(cross(VT("/CLKON") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/CLKIN") 0.45 1 "rising" nil nil))*1e12'
                ),
                "ps",
                "CLKIN rising to CLKON rising delay",
            ),
            metric(
                "clk_gap_op_after_on_ps",
                (
                    '(cross(VT("/CLKOP") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/CLKON") 0.45 1 "falling" nil nil))*1e12'
                ),
                "ps",
                "Low-low non-overlap gap before CLKOP turns on",
            ),
            metric(
                "clk_gap_on_after_op_ps",
                (
                    '(cross(VT("/CLKON") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/CLKOP") 0.45 1 "falling" nil nil))*1e12'
                ),
                "ps",
                "Low-low non-overlap gap before CLKON turns on",
            ),
            metric(
                "clk_clkop_duty_pct",
                (
                    '(cross(VT("/CLKOP") 0.45 1 "falling" nil nil)'
                    '-cross(VT("/CLKOP") 0.45 1 "rising" nil nil))/5e-09*100'
                ),
                "%",
                "First full CLKOP high-window duty cycle",
            ),
            metric(
                "clk_clkon_duty_pct",
                (
                    '(cross(VT("/CLKON") 0.45 2 "falling" nil nil)'
                    '-cross(VT("/CLKON") 0.45 1 "rising" nil nil))/5e-09*100'
                ),
                "%",
                "First full CLKON high-window duty cycle",
            ),
            metric(
                "clk_overlap_product_peak_v2",
                'ymax(VT("/CLKOP")*VT("/CLKON"))',
                "V^2",
                "Peak product of both phase clocks; near zero indicates no simultaneous high state",
            ),
        ],
        "offline_metrics": offline_supply_metrics("clk"),
    }


def create_asyctrl_tb(client: VirtuosoClient, rebuild: bool = False) -> dict[str, object]:
    cell = "TB_SUBMOD_ASYCTRL_9CLK_PERF"
    exists = cell_exists(client, cell, "schematic")
    if rebuild and exists:
        clear_schematic(client, cell)
        exists = False
    if not exists:
        with client.schematic.edit(LIB, cell) as sch:
            create_common_supply(sch)
            sch.add(inst(LIB, "Asycontrol_logic_9clk", "symbol", "XASY", 0.0, 0.0, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VCLKS", -4.0, 0.8, "R0"))
            sch.add(inst("analogLib", "vpulse", "symbol", "VVALID", -4.0, -0.8, "R0"))
            add_load_cap(sch, "C_CLKC", "CLKC", 3.2, 0.7)
            for term, net in [
                ("CLKS", "CLKS"),
                ("VALID", "VALID"),
                ("CLKC", "CLKC"),
                ("CLKO<8:0>", "CLKO<8:0>"),
                ("VDD", "VDD"),
                ("VSS", "VSS"),
            ]:
                sch.add(label_term("XASY", term, net))
            sch.add(label_term("VCLKS", "PLUS", "CLKS"))
            sch.add(label_term("VCLKS", "MINUS", "VSS"))
            sch.add(label_term("VVALID", "PLUS", "VALID"))
            sch.add(label_term("VVALID", "MINUS", "VSS"))
    params = [
        ("VDD_SRC", "vdc", "vdd"),
        ("VSS_SRC", "vdc", "0"),
        # DFFRN reset is active-high in this library. Start with a short reset
        # pulse, then hold CLKS low so VALID pulses can advance the shift chain.
        ("VCLKS", "v1", "vdd"),
        ("VCLKS", "v2", "0"),
        ("VCLKS", "td", "100p"),
        ("VCLKS", "tr", "5p"),
        ("VCLKS", "tf", "5p"),
        ("VCLKS", "pw", "99n"),
        ("VCLKS", "per", "100n"),
        ("VVALID", "v1", "0"),
        ("VVALID", "v2", "vdd"),
        ("VVALID", "td", "500p"),
        ("VVALID", "tr", "5p"),
        ("VVALID", "tf", "5p"),
        ("VVALID", "pw", "1n"),
        ("VVALID", "per", "2.5n"),
        ("C_CLKC", "c", "cload"),
    ]
    set_instance_params(client, cell, params)
    clko_rise_metrics = [
        metric(
            f"asy_clko{bit}_rise_ps",
            f'cross(VT("/CLKO<{bit}>") 0.45 1 "rising" nil nil)*1e12',
            "ps",
            f"First CLKO<{bit}> rising threshold crossing",
        )
        for bit in range(8, -1, -1)
    ]
    clko_max_metrics = [
        metric(
            f"asy_clko{bit}_max_v",
            f'ymax(VT("/CLKO<{bit}>"))',
            "V",
            f"Maximum CLKO<{bit}> output level",
        )
        for bit in range(8, -1, -1)
    ]
    return {
        "cell": cell,
        "stop": "28n",
        "vars": {"vdd": "900m", "cload": "1f"},
        "signals": ["/CLKS", "/VALID", "/CLKC"] + [f"/CLKO<{bit}>" for bit in range(9)],
        "metrics": [
            metric(
                "asy_valid_to_clko8_ps",
                (
                    '(cross(VT("/CLKO<8>") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/VALID") 0.45 1 "rising" nil nil))*1e12'
                ),
                "ps",
                "First VALID edge to MSB clock output delay",
            ),
            metric(
                "asy_sequence_span_ps",
                (
                    '(cross(VT("/CLKO<0>") 0.45 1 "rising" nil nil)'
                    '-cross(VT("/CLKO<8>") 0.45 1 "rising" nil nil))*1e12'
                ),
                "ps",
                "Time from CLKO<8> first rise to CLKO<0> first rise",
            ),
            metric("asy_clkc_max_v", 'ymax(VT("/CLKC"))', "V", "Maximum comparator strobe level"),
        ]
        + clko_rise_metrics
        + clko_max_metrics,
        "offline_metrics": offline_supply_metrics("asy"),
    }


def create_bootstrap_tb(client: VirtuosoClient, rebuild: bool = False) -> dict[str, object]:
    cell = "TB_SUBMOD_BOOTSTRAP_DIFF_PERF"
    exists = cell_exists(client, cell, "schematic")
    if rebuild and exists:
        clear_schematic(client, cell)
        exists = False
    if not exists:
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
                ("VVIP", "VIP", "VSS"),
                ("VVIN", "VIN", "VSS"),
            ]:
                sch.add(label_term(source, "PLUS", plus))
                sch.add(label_term(source, "MINUS", minus))
    set_instance_params(
        client,
        cell,
        [
            ("VDD_SRC", "vdc", "vdd"),
            ("VSS_SRC", "vdc", "0"),
            ("VCLKS", "v1", "0"),
            ("VCLKS", "v2", "vdd"),
            ("VCLKS", "td", "500p"),
            ("VCLKS", "tr", "5p"),
            ("VCLKS", "tf", "5p"),
            ("VCLKS", "pw", "2n"),
            ("VCLKS", "per", "5n"),
            ("VCLKSB", "v1", "vdd"),
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
        "metrics": [
            metric(
                "boot_diff_final_v",
                'value((VT("/VOUTP")-VT("/VOUTN")) 12e-09)',
                "V",
                "Final sampled differential output",
            ),
            metric(
                "boot_diff_final_error_mv",
                (
                    '(value((VT("/VOUTP")-VT("/VOUTN")) 12e-09)'
                    '-value((VT("/VIP")-VT("/VIN")) 12e-09))*1e3'
                ),
                "mV",
                "Final differential tracking error",
            ),
            metric(
                "boot_track_error_on_avg_mv",
                (
                    'average(abs(clip((VT("/VOUTP")-VT("/VOUTN"))'
                    '-(VT("/VIP")-VT("/VIN")) 0.55e-09 2.5e-09)))*1e3'
                ),
                "mV",
                "Average absolute tracking error during the first on window",
            ),
            metric(
                "boot_track_error_on_max_mv",
                (
                    'ymax(abs(clip((VT("/VOUTP")-VT("/VOUTN"))'
                    '-(VT("/VIP")-VT("/VIN")) 0.55e-09 2.5e-09)))*1e3'
                ),
                "mV",
                "Peak absolute tracking error during the first on window",
            ),
            metric(
                "boot_settle_error_2p5n_mv",
                (
                    'value(abs((VT("/VOUTP")-VT("/VOUTN"))'
                    '-(VT("/VIP")-VT("/VIN"))) 2.5e-09)*1e3'
                ),
                "mV",
                "Tracking error near the end of the first on window",
            ),
            metric(
                "boot_clk_overlap_product_peak_v2",
                'ymax(VT("/CLKS")*VT("/CLKSB"))',
                "V^2",
                "Peak product of complementary bootstrap clocks",
            ),
        ],
        "offline_metrics": offline_supply_metrics("boot"),
    }


def reset_maestro_view(client: VirtuosoClient, cell: str) -> None:
    run_skill(
        client,
        f"reset Maestro view {cell}",
        f'''
let((obj)
  obj = ddGetObj("{LIB}" "{cell}" "maestro")
  when(obj ddDeleteObj(obj))
  "ok")
''',
        timeout=120,
    )


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

        # Add waveform outputs plus scalar point measurements. The scalar
        # measurements mirror common block-level performance metrics. Supply
        # current based power/energy is computed by the run helper from PSF,
        # because this ADE point-output path rejects branch-current expressions
        # in IC618 while the same OCEAN expressions work after the run.
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
        for item in list(spec.get("metrics", [])):
            name = str(item["name"])
            expr = str(item["expr"])
            try:
                raw = add_point_output(client, session, name, expr)
                added_outputs.append(
                    {
                        "name": name,
                        "type": "point",
                        "unit": str(item.get("unit", "")),
                        "description": str(item.get("description", "")),
                        "expr": expr,
                        "raw": raw,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                added_outputs.append({"name": name, "type": "point", "expr": expr, "error": str(exc)})
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


def merge_manifest_entries(
    base: dict[str, object],
    specs: list[dict[str, object]],
    maestro: list[dict[str, object]],
) -> dict[str, object]:
    def merge_by_cell(old: list[dict[str, object]], new: list[dict[str, object]]) -> list[dict[str, object]]:
        merged = {str(item["cell"]): item for item in old}
        for item in new:
            merged[str(item["cell"])] = item
        return list(merged.values())

    return {
        **base,
        "library": LIB,
        "test_name": TEST_NAME,
        "model_file": MODEL_FILE,
        "testbenches": merge_by_cell(list(base.get("testbenches", [])), specs),
        "maestro": merge_by_cell(list(base.get("maestro", [])), maestro),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild-schematics",
        action="store_true",
        help="clear and rebuild generated submodule schematics before saving Maestro setup",
    )
    parser.add_argument("--cell", help="only create/update one generated testbench cell")
    parser.add_argument(
        "--reset-maestro",
        action="store_true",
        help="delete and recreate the generated Maestro views before adding outputs",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    creators = [
        ("TB_SUBMOD_COMPARATOR_PERF", create_comparator_tb),
        ("TB_SUBMOD_CLK_NOOVERLAP_PERF", create_clk_nooverlap_tb),
        ("TB_SUBMOD_ASYCTRL_9CLK_PERF", create_asyctrl_tb),
        ("TB_SUBMOD_BOOTSTRAP_DIFF_PERF", create_bootstrap_tb),
    ]
    specs = [
        creator(client, rebuild=args.rebuild_schematics)
        for cell, creator in creators
        if args.cell in (None, cell)
    ]
    if not specs:
        raise SystemExit(f"Unknown --cell value: {args.cell}")
    if args.reset_maestro:
        for spec in specs:
            reset_maestro_view(client, str(spec["cell"]))
    maestro = [ensure_maestro_setup(client, spec) for spec in specs]
    out_path = OUT_DIR / "submodule_maestro_setup_manifest.json"
    base_manifest: dict[str, object] = {}
    if args.cell and out_path.exists():
        base_manifest = json.loads(out_path.read_text(encoding="utf-8"))
    manifest = merge_manifest_entries(base_manifest, specs, maestro)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
