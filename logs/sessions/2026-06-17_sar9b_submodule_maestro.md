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
- Final four-testbench run completed through Maestro/Spectre with zero Spectre
  errors for all four cells:
  - comparator `Interactive.8`: decision delay `3.923 ps`;
  - clock non-overlap `Interactive.3`: no simultaneous-high window, both-low
    total `176 ps`;
  - ASYCTRL `Interactive.7`: Spectre-clean, `VALID`/`CLKC` active, but
    `CLKO<0..8>` still do not reach rail;
  - bootstrap `Interactive.4`: final differential output `100.000067 mV` for
    `100 mV` input.

## Next

Investigate ASYCTRL reset/seed conditions with a smaller `DFFRN` unit test or
by replaying top-level ADC startup timing. The Maestro run/export pipeline is
now healthy enough for repeated block-level iterations.
