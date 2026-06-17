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
- `connectivityLastUpdated` had to be set to integer `0` on bridge-created
  schematics to avoid `OSSHNL-108`.
- No valid submodule performance metrics have been accepted yet. Existing
  archived histories document setup/run-control blockers, not DUT performance.

## Next

Run each generated Maestro view through the GUI `Update and Run` flow, then
archive/export waveforms for comparator delay, clock non-overlap, asynchronous
clock sequencing, and bootstrap tracking metrics.
