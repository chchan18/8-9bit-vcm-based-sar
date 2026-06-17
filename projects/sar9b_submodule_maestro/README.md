# SAR9B Submodule Maestro Testbenches

Date: 2026-06-17

This project creates standalone Maestro transient testbenches for key
`SAR9B_400MV` submodules, so each block can be checked independently before the
full 9-bit SAR ADC run.

## Created Maestro Views

All testbenches are in library `SAR9B_400MV` and use Maestro test name `TRAN`
with the TSMC 28nm HPC+ `top_tt` model section.

| Testbench cell | DUT | Purpose | Stop time | Saved signals |
|----------------|-----|---------|-----------|---------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `COMPARATOR` | Clocked comparator decision delay and output swing | `8n` | `/CLKC`, `/VP`, `/VN`, `/VOP`, `/VON` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `CLK_NOOVERLAP` | Non-overlap clock phase timing | `12n` | `/CLKIN`, `/CLKOP`, `/CLKON` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Asycontrol_logic_9clk` | 9-step asynchronous SAR clock sequencing | `28n` | `/CLKS`, `/VALID`, `/CLKC`, `/CLKO<0..8>` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `BOOTSTRAP_DIFF` | Differential bootstrap sampling switch tracking | `12n` | `/CLKS`, `/CLKSB`, `/VIP`, `/VIN`, `/VOUTP`, `/VOUTN` |

Nominal variables:

| Testbench cell | Variables |
|----------------|-----------|
| `TB_SUBMOD_COMPARATOR_PERF` | `vdd=900m`, `vcm=450m`, `vdiff=10m`, `cload=2f` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `vdd=900m`, `cload=2f` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `vdd=900m`, `cload=1f` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `vdd=900m`, `vcm=450m`, `vdiff=100m`, `cload=5f` |

## Scripts

| Script | Role |
|--------|------|
| `scripts/inspect_submodule_symbols.py` | Reads DUT symbol terminals and selected schematic instances. |
| `scripts/inspect_adc_tb_sources.py` | Reads known ADC testbench source parameter names for reuse. |
| `scripts/create_schematic_smoke.py` | Creates a small RC schematic to verify schematic creation APIs. |
| `scripts/create_submodule_maestro_tests.py` | Creates the four schematic testbenches and corresponding Maestro `TRAN` views. |
| `scripts/run_submodule_maestro_tests.py` | Attempts Maestro runs, archives histories, exports waveforms, and computes quick metrics. |
| `scripts/archive_submodule_history.py` | Copies an existing remote Maestro history into this project. |
| `scripts/inspect_fix_schematic_props.py` | Inspects/fixes schematic `connectivityLastUpdated`; needed after bridge-created schematics. |
| `scripts/check_submodule_remote_status.py` | Polls remote Maestro histories, logs, and process state for a selected cell. |
| `scripts/dismiss_ade_dialogs.py` | Sends Escape to residual ADE modal dialogs. |
| `scripts/reload_bridge_ciw.py` | Experimental CIW bridge reload helper; use carefully because X11 focus can be fragile. |

## Artifacts

| File | Content |
|------|---------|
| `artifacts/submodule_symbol_inspection_raw.json` | Symbol terminal/instance inspection for candidate submodules. |
| `artifacts/adc_tb_sources_raw.json` | Reusable source parameter names from the validated SAR9B ADC testbench. |
| `artifacts/submodule_maestro_setup_manifest.json` | Manifest proving the four schematic and Maestro views were created. |
| `artifacts/schematic_props_fix_manifest.json` | Manifest showing `connectivityLastUpdated` was repaired for all four new schematics. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.0` | Archived pre-fix failed run: `OSSHNL-108`. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.1` | Archived pre-fix failed run: `OSSHNL-108`. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.2` | Background run attempt stopped immediately by Maestro. |

## Current Run Status

The testbench and Maestro setup stage is complete. Automated execution is not
yet producing valid performance metrics:

1. `Interactive.0` and `Interactive.1` failed during netlisting because the
   bridge-created schematics had `connectivityLastUpdated=nil`.
2. `scripts/inspect_fix_schematic_props.py --fix` repaired that property and
   re-saved all four schematics.
3. A background `maeRunSimulation` attempt generated `Interactive.2`, but the
   Maestro log reports `Received stop signal from user`; no Spectre performance
   run was completed.
4. GUI-mode `maeRunSimulation` still destabilized the bridge around ADE modal
   handling, so no submodule timing metrics should be treated as measured yet.

## Recommended Next Step

Open each generated Maestro view in Virtuoso and run through the GUI
`Update and Run` path:

```text
SAR9B_400MV/TB_SUBMOD_COMPARATOR_PERF/maestro
SAR9B_400MV/TB_SUBMOD_CLK_NOOVERLAP_PERF/maestro
SAR9B_400MV/TB_SUBMOD_ASYCTRL_9CLK_PERF/maestro
SAR9B_400MV/TB_SUBMOD_BOOTSTRAP_DIFF_PERF/maestro
```

After each successful run, use `scripts/archive_submodule_history.py` to capture
the remote history locally, then use `scripts/run_submodule_maestro_tests.py`
or a follow-up export script to compute delay, overlap, sequencing, and
bootstrap tracking metrics from PSF waveforms.
