# v005 Changes

Date: 2026-06-17

## Added

- Added the `SAR9B_400MV/ADC_9B_tb_best_q4` `Interactive.12` recovery result.
- Added project-specific scripts for live-session `Vpk=800m` setup, run
  launch, netlist verification, run polling, and log archival.
- Archived the `Interactive.12` netlist, Maestro log, Spectre log, and raw
  `biP<8:0>` plus DAC9 `/out` phase-sweep outputs.

## Updated

- Updated `PROJECT_STATUS.md` with the current best SAR9B result:
  raw ENOB `8.7203`, Maestro default `/out` ENOB `8.678`, and DAC9 `/out`
  phase-sweep ENOB `8.7005`.
- Updated the SAR9B ENOB recovery project README and root-cause note from
  hypothesis to verified result.
- Updated the experiment matrix: P0 and P2 are complete; DAC9 trise sweep is
  deferred because `/out` is within about `0.02` bit of raw `biP`.

## Resolved

- Confirmed that the earlier ENOB `7.86` value was primarily caused by a
  hidden Maestro `Vpk=450m` override.
- Confirmed that a pure XML upload can be overwritten by stale ADE session
  state, so the reliable run flow must set `Vpk=800m` in the live Maestro
  session before saving and running.
