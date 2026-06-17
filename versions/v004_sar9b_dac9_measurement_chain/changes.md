# v004 Changes

Date: 2026-06-17

## Added

- Added a versioned documentation snapshot for the SAR9B DAC9 measurement-chain
  repair.
- Documented final `Interactive.11` Maestro result:
  `ENOB=7.86 bits`, `SINAD=49.08 dB`.

## Updated

- Updated `versions/v003_ADC_documentation/README_TOP_redun1_ADC.md` with the
  current `SAR9B_400MV/ADC_9B_tb_best_q4` flow.
- Marked the old original-library 9-bit Maestro result as a reference rather
  than the active target.
- Recorded the validated p2200 FFT expressions used by default Maestro
  `spectrum_enob` and `spectrum_sinad`.
- Added a supersession note pointing to
  `versions/v005_sar9b_vpk800_enob_recovery/`, where the hidden `Vpk=450m`
  override is resolved; Maestro default `/out` ENOB recovers to `8.678` bits
  and DAC9 `/out` phase-sweep ENOB reaches `8.7005` bits.
