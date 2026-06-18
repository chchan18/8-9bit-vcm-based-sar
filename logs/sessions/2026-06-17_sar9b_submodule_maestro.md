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

## Next

Continue with robustness checks: sweep ASYCTRL `VALID` timing, compare the
standalone startup timing against the full ADC run, and add PVT/corner coverage
for comparator, non-overlap clock, and bootstrap switch behavior.
