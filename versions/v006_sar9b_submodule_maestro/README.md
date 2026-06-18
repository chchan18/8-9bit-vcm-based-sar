# v006 - SAR9B Submodule Maestro Testbenches

Date: 2026-06-18

## Summary

This version records creation of standalone Maestro transient testbenches for
four key `SAR9B_400MV` submodules:

| Testbench | DUT | Metric target |
|-----------|-----|---------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `COMPARATOR` | Decision delay and output swing |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `CLK_NOOVERLAP` | Non-overlap timing |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Asycontrol_logic_9clk` | SAR clock sequencing |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `BOOTSTRAP_DIFF` | Sampling switch tracking |

The schematic testbenches and Maestro `TRAN` views were created in
`SAR9B_400MV`, with model file:

```text
/home/IC/Desktop/Project/project_tsmcN28_NEW/project_tsmcN28_NEW/iPDK_CRN28HPC+_v1.0_2p2a_20160226_all/CRN28HPCp/models/spectre/toplevel.scs
```

and section `top_tt`.

## Key Files

| File | Content |
|------|---------|
| `projects/sar9b_submodule_maestro/README.md` | Detailed submodule Maestro handoff. |
| `projects/sar9b_submodule_maestro/scripts/create_submodule_maestro_tests.py` | Creates the four testbenches and Maestro views; `--reset-maestro` rebuilds generated ADE outputs from scratch. |
| `projects/sar9b_submodule_maestro/scripts/run_submodule_maestro_tests.py` | Run/export/metric automation with Maestro point-output parsing and offline PSF supply metrics. |
| `projects/sar9b_submodule_maestro/docs/performance_metrics.md` | Online metric references and mapping to Maestro/offline measurements. |
| `projects/sar9b_submodule_maestro/artifacts/submodule_maestro_setup_manifest.json` | Setup manifest. |
| `projects/sar9b_submodule_maestro/artifacts/schematic_props_fix_manifest.json` | Schematic property fix manifest. |

## Run Status

The generated Maestro run/export flow now completes for all four rebuilt
submodule testbenches with zero ADE errors and zero Spectre errors. Latest
histories:

| Testbench | Latest history | Result | Highlight |
|-----------|----------------|--------|-----------|
| `TB_SUBMOD_COMPARATOR_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 5 warnings | Maestro `cmp_decision_delay_ps=4.483`; offline power `31.83 uW` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 30 warnings | Maestro non-overlap gaps about `35 ps`; offline power `3.639 uW` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 10 warnings | `CLKO<8>` to `CLKO<0>` span `20 ns`; offline power `8.261 uW` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 30 warnings | final differential output `100 mV`; offline power `2.188 uW` |

Key repair details:

1. `OSSHNL-109` was fixed by saving schematics with `dbSetConnCurrent`; manual
   property edits were insufficient because `dbSave` advances
   `schGeometryLastUpdated`.
2. The testbenches were rebuilt with a real `VSS_SRC (VSS 0)` reference using
   an `analogLib/gnd` wire. Plain `"0"` labels produced floating `_net0`.
3. ASYCTRL required an active-high reset interpretation for `DFFRN`: `CLKS`
   is high during startup reset and then held low. With that stimulus,
   `CLKO<8>` rises at `542 ps` and the chain advances down to `CLKO<0>` at
   `20543 ps`, with all nine outputs reaching about `0.9 V`.
4. Published-style Maestro point outputs were added for comparator delay/swing,
   non-overlap timing, ASYCTRL sequence timing/rail reach, and bootstrap
   tracking/settling error.
5. Supply power/energy remains part of the metric set, but is computed from
   PSF current exports after the run because IC618 ADE point outputs rejected
   branch-current expressions while OCEAN evaluation after `openResults` works.
