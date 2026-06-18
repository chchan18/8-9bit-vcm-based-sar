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
| `TB_SUBMOD_BOOTSTRAP_DIFF_FFT` | `BOOTSTRAP_DIFF` | Coherent-sine dynamic FFT for the analog sampler path | `2.7u` | `/CLKS`, `/CLKSB`, `/VIP`, `/VIN`, `/VOUTP`, `/VOUTN` |

Nominal variables:

| Testbench cell | Variables |
|----------------|-----------|
| `TB_SUBMOD_COMPARATOR_PERF` | `vdd=900m`, `vcm=450m`, `vdiff=10m`, `cload=2f` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `vdd=900m`, `cload=2f` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `vdd=900m`, `cload=1f`, `valid_td=500p`, `valid_pw=1n`, `valid_per=2.5n` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `vdd=900m`, `vcm=450m`, `vdiff=100m`, `cload=5f` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_FFT` | `vdd=900m`, `vcm=450m`, `Vpk=800m`, `fs=400M`, `fft_bin=7`, `fft_n=1024`, `TSTOP=2.7u`, `cload=5f` |

## Scripts

| Script | Role |
|--------|------|
| `scripts/inspect_submodule_symbols.py` | Reads DUT symbol terminals and selected schematic instances. |
| `scripts/inspect_adc_tb_sources.py` | Reads known ADC testbench source parameter names for reuse. |
| `scripts/create_schematic_smoke.py` | Creates a small RC schematic to verify schematic creation APIs. |
| `scripts/create_submodule_maestro_tests.py` | Creates/rebuilds the four schematic testbenches and corresponding Maestro `TRAN` views. Use `--cell` to update one testbench, `--rebuild-schematics` after changing stimulus wiring, or `--reset-maestro` to rebuild generated ADE outputs from scratch. |
| `scripts/run_submodule_maestro_tests.py` | Runs Maestro, downloads logs/netlists/waveforms, records Maestro point outputs, exports PSF waveforms, and computes quick/offline metrics. Supports `--trigger callback`, `--trigger gui-button`, and `--trigger mae`. |
| `scripts/run_submodule_robustness_sweeps.py` | Runs the nominal plus robustness matrix for the four submodule testbenches and writes one merged manifest. Supports `--cell` and `--case` for restartable partial reruns. |
| `scripts/create_bootstrap_fft_test.py` | Creates `TB_SUBMOD_BOOTSTRAP_DIFF_FFT`, configures its Maestro `TRAN` view, and records the coherent-sine FFT sample plan. |
| `scripts/run_bootstrap_fft_test.py` | Runs the bootstrap FFT Maestro test, exports coherent PSF sample points with OCEAN, and computes input/output SNDR, ENOB, THD, SFDR, gain, and tracking error. |
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
| `artifacts/bootstrap_fft_setup_manifest.json` | Manifest proving the bootstrap coherent-sine FFT Maestro setup and sample plan. |
| `artifacts/schematic_props_fix_manifest.json` | Manifest showing `connectivityLastUpdated` was repaired for all four new schematics. |
| `docs/performance_metrics.md` | Online metric references and mapping to Maestro/offline measurements. |
| `docs/robustness_sweep_20260618.md` | First complete submodule robustness sweep report. |
| `docs/dynamic_fft_20260618.md` | Dynamic FFT applicability and bootstrap FFT results. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.0` | Archived pre-fix failed run: `OSSHNL-108`. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.1` | Archived pre-fix failed run: `OSSHNL-108`. |
| `runs/TB_SUBMOD_COMPARATOR_PERF/Interactive.2` | Background run attempt stopped immediately by Maestro. |
| `runs/submodule_run_manifest.json` | Latest four-testbench Maestro run summary. |
| `runs/submodule_robustness_manifest.json` | Latest 20-case robustness sweep manifest. |
| `runs/bootstrap_fft_dynamic/nominal_p2200/summary.json` | Full-scale `Vpk=800m` bootstrap FFT dynamic metrics. |
| `runs/bootstrap_fft_dynamic/nominal_vpk400/summary.json` | Mid-scale `Vpk=400m` bootstrap FFT dynamic metrics. |

## Current Run Status

The four rebuilt Maestro testbenches now run through Maestro with zero ADE
errors and through Spectre with zero simulator errors. Latest run manifest:
`runs/submodule_run_manifest.json`.

| Testbench | Latest history | ADE/Spectre | Maestro point-output highlights | Offline metric |
|-----------|----------------|-------------|---------------------------------|----------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 5 warnings | `cmp_decision_delay_ps=4.483`, `cmp_vop_max_v=940m`, `cmp_von_min_v=-7.177m` | `cmp_avg_power_w=31.83 uW`, `cmp_energy_j=254.63 fJ` |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 30 warnings | `clk_gap_op_after_on_ps=35.08`, `clk_gap_on_after_op_ps=35.27`, `clk_overlap_product_peak_v2=6.792u` | `clk_avg_power_w=3.639 uW`, `clk_energy_j=43.66 fJ` |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 10 warnings | `asy_sequence_span_ps=20K`; all `CLKO<8:0>` reach about 0.905-0.907 V | `asy_avg_power_w=8.261 uW`, `asy_energy_j=231.30 fJ` |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 30 warnings | `boot_diff_final_v=100m`, `boot_settle_error_2p5n_mv=86.49u`, `boot_clk_overlap_product_peak_v2=202.5m` | `boot_avg_power_w=2.188 uW`, `boot_energy_j=26.25 fJ` |

## Robustness Sweep Status

The first restartable robustness matrix has also completed. Tag:
`robustness_20260618_full`. All 20 cases finished with zero ADE run errors
and zero Spectre errors:

| Testbench | Cases | Sweep variables | Highlights |
|-----------|-------|-----------------|------------|
| `TB_SUBMOD_COMPARATOR_PERF` | 6 | `vdiff=2m/5m/20m`, `cload=5f`, `vdd=800m` | Decision delay stayed at `4.482-4.514 ps` at 900 mV and became `5.335 ps` at 800 mV. |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | 4 | `cload=1f/5f`, `vdd=800m` | Offline simultaneous-high time stayed `0 ps`; non-overlap gap was `34.4-44.86 ps`. |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | 5 | `valid_per=2n/3n`, `cload=3f`, `vdd=800m` | All cases reached `clko_rail_count=9`; sequence span tracked `valid_per` as `16 ns`, `20 ns`, and `24 ns`. |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | 5 | `vdiff=50m/200m`, `cload=10f`, `vdd=800m` | Final differential error stayed in the raw Maestro range `-248.9u` to `438u` for the `_mv` output. |

Detailed per-case results and artifact paths are in
`docs/robustness_sweep_20260618.md`.

## Dynamic FFT Status

The analog bootstrap path now has a coherent-sine FFT Maestro testbench:
`TB_SUBMOD_BOOTSTRAP_DIFF_FFT`. It uses `fs=400M`, `fft_bin=7`,
`fft_n=1024`, and exports `VIP-VIN` plus `VOUTP-VOUTN` for offline dynamic
metrics.

| Case | History | ADE/Spectre | Output SNDR | Output ENOB | THD | SFDR |
|------|---------|-------------|-------------|-------------|-----|------|
| `Vpk=800m` | `Interactive.0` | 0 ADE errors; 0 Spectre errors, 35 warnings | `41.895 dB` | `6.667 bit` | `-41.896 dB` | `41.987 dB` |
| `Vpk=400m` | `Interactive.1` | 0 ADE errors; 0 Spectre errors, 35 warnings | `50.346 dB` | `8.071 bit` | `-50.398 dB` | `50.400 dB` |

The full-scale result is third-harmonic limited; the largest spur is bin 21
(`8.203 MHz`). The comparator, non-overlap clock, and ASYCTRL outputs are
not ADC-style FFT/ENOB targets in their present standalone pulse/digital
testbenches; their dynamic behavior is covered by timing, rail, and energy
metrics. Details are in `docs/dynamic_fft_20260618.md`.

## Maestro Measurements Added

The Maestro setup now includes published-style block metrics for each module:
comparator clock-to-decision delay and swing; non-overlap propagation, gap,
duty, and overlap checks; ASYCTRL conversion-sequence timing and per-clock rail
reach; and bootstrap final/track/settling error. The metric rationale and
source links are captured in `docs/performance_metrics.md`.

Supply power and energy are intentionally not registered as Maestro point
outputs. IC618 accepts the branch-current OCEAN expression after opening PSF
results, but reports `Error No` when the same expression is stored as an ADE
point output. The run helper therefore exports the supply current from the same
history and records power/energy under `metrics.offline`.

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
5. A `--reset-maestro` flow was added to recreate generated Maestro views and
   remove stale ADE outputs; this was used for the latest clean `Interactive.0`
   run on all four testbenches.

## Recommended Next Step

Extend the same measurement matrix to PVT/corner coverage, then compare the
standalone `CLKS`/`VALID` timing against the full ADC run to close the block to
top-level timing link.
