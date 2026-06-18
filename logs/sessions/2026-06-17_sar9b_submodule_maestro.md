# 2026-06-17 - SAR9B Submodule Maestro Testbenches

## Goal

Create separate Maestro simulations for several `SAR9B_400MV` submodules so
their local performance can be tested independently of the full SAR ADC.

## Created

- `TB_SUBMOD_COMPARATOR_PERF`
- `TB_SUBMOD_CLK_NOOVERLAP_PERF`
- `TB_SUBMOD_ASYCTRL_9CLK_PERF`
- `TB_SUBMOD_BOOTSTRAP_DIFF_PERF`

Each cell has a schematic and Maestro `TRAN` view in library `SAR9B_400MV`.

## Notes

- Symbol/source inspection artifacts were saved under
  `projects/sar9b_submodule_maestro/artifacts/`.
- Bridge-created schematics initially failed with `OSSHNL-108`/`OSSHNL-109`.
  The robust repair is `schCheck -> dbSave -> dbSetConnCurrent -> dbSave`,
  which keeps `connectivityLastUpdated == schGeometryLastUpdated`.
- Testbench references were rebuilt around an explicit `VSS_SRC (VSS 0)` path.
  Labeling a terminal `"0"` was not enough; it produced floating `_net0`.
- Public supply sources were moved left of the local stimulus sources to avoid
  accidental vertical-wire shorts.
- First four-testbench run completed through Maestro/Spectre with zero Spectre
  errors for all four cells.
- 2026-06-18 continuation: ASYCTRL stimulus was repaired after identifying
  `DFFRN.RN` as active-high reset. `CLKS` now starts high for reset and then
  stays low while `VALID` pulses advance the shift chain.
- Final four-testbench callback run completed with zero Spectre errors:
  - comparator `Interactive.9`: decision delay `3.923 ps`;
  - clock non-overlap `Interactive.4`: no simultaneous-high window, both-low
    total `176 ps`;
  - ASYCTRL `Interactive.9`: all nine `CLKO<0..8>` outputs reach rail; first
    rises progress from `CLKO<8>` at `542 ps` to `CLKO<0>` at `20543 ps`;
  - bootstrap `Interactive.5`: final differential output `100.000067 mV` for
    `100 mV` input.
- 2026-06-18 measurement update: online metric references were checked for
  comparator, sample/hold/bootstrap, timing generator, and asynchronous SAR
  control blocks. The mapping is saved in
  `projects/sar9b_submodule_maestro/docs/performance_metrics.md`.
- Maestro point outputs were added for the metrics that ADE evaluates
  reliably:
  - comparator clock/decision timing, output swing, and final differential;
  - non-overlap delay, gap, duty, and overlap-product checks;
  - ASYCTRL valid-to-clock delay, sequence span, per-clock rise time, and rail
    reach;
  - bootstrap final/track/settling error and complementary-clock overlap.
- Branch-current power/energy point outputs were tested in Maestro and rejected
  as `Error No`, even though the same OCEAN expressions work after opening PSF
  results. These metrics were moved to `offline_metrics`; the run helper now
  exports `getData("/VDD_SRC/PLUS" ?result "tran")` and computes supply power
  and energy from the same history.
- A `--reset-maestro` option was added to recreate generated Maestro views and
  remove stale ADE outputs. After resetting all four views, the callback run
  completed with zero ADE errors and zero Spectre errors:
  - comparator `Interactive.0`: `cmp_decision_delay_ps=4.483`, offline power
    `31.83 uW`;
  - clock non-overlap `Interactive.0`: both non-overlap gaps about `35 ps`,
    offline power `3.639 uW`;
  - ASYCTRL `Interactive.0`: sequence span `20 ns`, all nine `CLKO<8:0>` reach
    rail, offline power `8.261 uW`;
  - bootstrap `Interactive.0`: final differential output `100 mV`, settle
    error `86.49 uV`, offline power `2.188 uW`.

- 2026-06-18 robustness continuation: added ASYCTRL `valid_td`, `valid_pw`,
  and `valid_per` Maestro variables so the `VALID` stimulus can be swept
  without schematic edits.
- Added `run_submodule_robustness_sweeps.py`, a restartable matrix runner that
  keeps per-case `summary.json` files and rebuilds the merged manifest from
  completed cases after interruptions.
- Completed tag `robustness_20260618_full`: 20 Maestro cases, zero ADE run
  errors, and zero Spectre errors.
  - comparator: 6 cases, decision delay `4.482-4.514 ps` at 900 mV and
    `5.335 ps` at 800 mV;
  - clock non-overlap: 4 cases, offline simultaneous-high time `0 ps` and gap
    `34.4-44.86 ps`;
  - ASYCTRL: 5 cases, all nine `CLKO<8:0>` outputs reach rail and sequence
    span tracks `valid_per` as `16 ns`, `20 ns`, and `24 ns`;
  - bootstrap: 5 cases, final differential error stays in the raw Maestro
    range `-248.9u` to `438u` for the `_mv` output.
- Opening a fresh Maestro cell occasionally reset the bridge daemon. The
  affected cell was restarted after `scripts/reload_bridge_ciw.py`; no
  completed case was reused without its own `summary.json` and Spectre log.

## Next

Extend the same Maestro measurement outputs to PVT/corner coverage and compare
standalone ASYCTRL timing against the full SAR9B ADC run.
