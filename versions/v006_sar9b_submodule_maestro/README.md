# v006 - SAR9B Submodule Maestro Testbenches

Date: 2026-06-17

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
| `projects/sar9b_submodule_maestro/scripts/create_submodule_maestro_tests.py` | Creates the four testbenches and Maestro views. |
| `projects/sar9b_submodule_maestro/scripts/run_submodule_maestro_tests.py` | Run/export/metric automation attempt. |
| `projects/sar9b_submodule_maestro/artifacts/submodule_maestro_setup_manifest.json` | Setup manifest. |
| `projects/sar9b_submodule_maestro/artifacts/schematic_props_fix_manifest.json` | Schematic property fix manifest. |

## Run Status

Setup is complete, but automated performance measurement is still blocked by
ADE/Maestro run control rather than by a measured circuit failure:

1. Initial comparator histories `Interactive.0` and `Interactive.1` hit
   `OSSHNL-108` because `connectivityLastUpdated` was `nil`.
2. The property was repaired on all four new schematics.
3. A later background attempt, `Interactive.2`, was stopped immediately by
   Maestro and did not run Spectre.

The next validation pass should run the generated Maestro views through the GUI
`Update and Run` flow or improve the ADE modal handling before collecting
timing/performance metrics.
