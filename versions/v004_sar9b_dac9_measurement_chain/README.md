# v004 — SAR9B DAC9 Measurement Chain Documentation

**Date**: 2026-06-17

## Summary

This version records the final documentation update for the active
`SAR9B_400MV/ADC_9B_tb_best_q4` 9-bit Maestro validation flow.

Superseded by `versions/v005_sar9b_vpk800_enob_recovery/`: the measurement
chain documented here was correct, but the run was under-driven by a hidden
`Vpk=450m` Maestro override. The recovered `Vpk=800m` run reports Maestro
default `/out` ENOB `8.678` bits and DAC9 `/out` phase-sweep ENOB `8.7005`
bits.

The old Maestro `/out` measurement path:

```text
decode_redun9to8 -> DAC8b_va
```

has been replaced in the active SAR9B testbench by:

```text
biP<0..8> -> DAC9b_va -> /out
```

The default Maestro `spectrum_enob` and `spectrum_sinad` outputs now use the
validated p2200 FFT window for the finite-rise DAC9 `/out` waveform.

## Final Validated Result

| Metric | Value |
|--------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| History | `Interactive.11` |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 1h 49m 18s |
| Maestro `/out` SINAD | 49.08 dB |
| Maestro `/out` ENOB | 7.86 bits |
| Raw `biP<8:0>` SINAD | 49.4385 dB |
| Raw `biP<8:0>` ENOB | 7.9200 bits |

## Updated Documents

- `versions/v003_ADC_documentation/README_TOP_redun1_ADC.md`
- `PROJECT_STATUS.md`
- `logs/sessions/2026-06-17_sar9b_measurement_chain.md`

## Key Evidence

- `sar9b_work/iterations/sar9b_maestro_best_q4/input.scs`
- `sar9b_work/iterations/sar9b_maestro_best_q4/logs/Interactive.11.log`
- `sar9b_work/iterations/sar9b_maestro_best_q4/measurement_chain_dac9_final_manifest.json`
- `sar9b_work/iterations/sar9b_maestro_best_q4/phase_outputs_manifest.json`
- `sar9b_work/iterations/sar9b_maestro_best_q4/maestro_files_loaded_phase_p2200/active.state`
