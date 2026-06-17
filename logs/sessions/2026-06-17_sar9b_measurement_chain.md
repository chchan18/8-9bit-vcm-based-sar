# Session Log: SAR9B Measurement Chain Repair

Date: 2026-06-17

## Request

Continue the SAR9B_400MV optimization work, repair the Maestro legacy
measurement chain that still reported low ENOB through the old
`decode_redun9to8 -> DAC8b_va` path, run the correct 9-bit Maestro setup, and
update the repository logs before pushing to GitHub.

## Work Completed

- Confirmed the active target is `SAR9B_400MV/ADC_9B_tb_best_q4`.
- Replaced the old 8-bit measurement chain with direct
  `biP<0..8> -> DAC9b_va -> /out`.
- Repaired the Verilog-A include flow by using the Maestro wrapper
  `sar9b_va_ahdl.scs` with `ahdl_include` for `DAC9b_va`.
- Verified the captured SAR9B netlist contains `I0 -> TOP_9B_ADC` and
  `I15 -> DAC9b_va`, with no `decode_redun9to8`, no `DAC8b_va`, and no empty
  `DAC9b_va` subckt.
- Ran `Interactive.10` to validate the DAC9 chain structurally.
- Exported `/out` phase sweeps and selected the p2200 FFT window:
  `28.2 ns -> 2.5882 us`, 1024 samples.
- Patched the final Maestro setup so default `spectrum_enob` and
  `spectrum_sinad` use the p2200 `/out` window.
- Ran final Maestro history `Interactive.11`.

## Final Result

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

The old `ENOB=2.365` failure mode is fixed for the active SAR9B Maestro
measurement chain. The default Maestro outputs now report the corrected DAC9
`/out` result near the raw 9-bit reference measurement.

## Key Artifacts

- `PROJECT_STATUS.md`
- `sar9b_work/iterations/sar9b_maestro_best_q4/README.md`
- `sar9b_work/iterations/sar9b_maestro_best_q4/input.scs`
- `sar9b_work/iterations/sar9b_maestro_best_q4/logs/Interactive.11.log`
- `sar9b_work/iterations/sar9b_maestro_best_q4/measurement_chain_dac9_final_manifest.json`
- `sar9b_work/iterations/sar9b_maestro_best_q4/phase_outputs_manifest.json`
- `sar9b_work/iterations/sar9b_maestro_best_q4/maestro_files_loaded_phase_p2200/active.state`
