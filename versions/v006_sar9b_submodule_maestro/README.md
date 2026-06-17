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

The generated Maestro run/export flow now completes for all four submodule
testbenches. Latest histories:

| Testbench | Latest history | Spectre result | Quick result |
|-----------|----------------|----------------|--------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `Interactive.8` | 0 errors, 5 warnings | decision crossing delay `3.923 ps` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `Interactive.3` | 0 errors, 30 warnings | no simultaneous-high window; both-low total `176 ps` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Interactive.7` | 0 errors, 10 warnings | `VALID` and `CLKC` active; `CLKO<0..8>` still not rail-to-rail |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `Interactive.4` | 0 errors, 30 warnings | final differential output `100.000067 mV` for `100 mV` input |

Key repair details:

1. `OSSHNL-109` was fixed by saving schematics with `dbSetConnCurrent`; manual
   property edits were insufficient because `dbSave` advances
   `schGeometryLastUpdated`.
2. The testbenches were rebuilt with a real `VSS_SRC (VSS 0)` reference using
   an `analogLib/gnd` wire. Plain `"0"` labels produced floating `_net0`.
3. ASYCTRL still needs a functional stimulus/initialization pass. The current
   result proves the Maestro/Spectre chain, but not the 9-step sequence.
