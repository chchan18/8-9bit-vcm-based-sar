# SAR9B Submodule Maestro Testbenches

Date: 2026-06-18

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
| `scripts/create_submodule_maestro_tests.py` | Creates/rebuilds the four schematic testbenches and corresponding Maestro `TRAN` views. Use `--cell` to update one testbench or `--rebuild-schematics` after changing stimulus wiring. |
| `scripts/run_submodule_maestro_tests.py` | Runs Maestro, downloads logs/netlists/waveforms, and computes quick metrics. Supports `--trigger callback`, `--trigger gui-button`, and `--trigger mae`. |
| `scripts/archive_submodule_history.py` | Copies an existing remote Maestro history into this project. |
| `scripts/inspect_fix_schematic_props.py` | Inspects/fixes schematic extraction metadata using `dbSetConnCurrent`; needed after bridge-created schematics. |
| `scripts/check_submodule_remote_status.py` | Polls remote Maestro histories, logs, and process state for a selected cell. |
| `scripts/dismiss_ade_dialogs.py` | Sends Escape to residual ADE modal dialogs. |
| `scripts/reload_bridge_ciw.py` | Experimental CIW bridge reload helper; use carefully because X11 focus can be fragile. |
| `scripts/inspect_extraction_metadata.py` | Compares extraction metadata against known-good SAR9B/legacy testbenches. |

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
| `runs/submodule_run_manifest.json` | Latest four-testbench Maestro run summary. |

## Current Run Status

The four Maestro testbenches now run through Spectre with zero errors. Latest
run manifest: `runs/submodule_run_manifest.json`.

| Testbench | Latest history | Spectre | Quick metric |
|-----------|----------------|---------|--------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `Interactive.9` | 0 errors, 5 warnings | `CLKC` rise to decision crossing: `3.923 ps` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `Interactive.4` | 0 errors, 30 warnings | no simultaneous-high time; total both-low window `176 ps` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Interactive.9` | 0 errors, 10 warnings | all nine `CLKO<0..8>` reach rail; first rises step from `CLKO<8>` at `542 ps` to `CLKO<0>` at `20543 ps` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `Interactive.5` | 0 errors, 30 warnings | final differential tracking: `100.000067 mV` for `100 mV` input |

Important fixes made during this pass:

1. `OSSHNL-109` was resolved by running `schCheck`, `dbSave`,
   `dbSetConnCurrent`, then `dbSave`; this keeps `connectivityLastUpdated`
   equal to `schGeometryLastUpdated`.
2. The generated testbenches now use an explicit `VSS_SRC (VSS 0)` style
   reference, with `VSS_SRC` wired to an `analogLib/gnd` symbol. Plain `"0"`
   wire labels were not sufficient and produced floating `_net0` references.
3. Public supply/ground source placement was moved away from local stimulus
   sources to avoid accidental wire shorts through vertical connection lines.
4. ASYCTRL uses an active-high `DFFRN` reset. `CLKS` is now driven high only
   during the initial reset window, then held low so `VALID` pulses advance
   the 9-bit shift chain.

## Recommended Next Step

Continue with robustness checks: sweep ASYCTRL `VALID` pulse spacing, compare
the standalone `CLKS`/`VALID` timing against the full ADC run, and add corner
runs for the comparator and clock blocks.
