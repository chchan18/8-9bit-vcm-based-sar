# v005 - SAR9B Vpk=800m ENOB Recovery

Date: 2026-06-17

## Summary

This version records the recovery of the active
`SAR9B_400MV/ADC_9B_tb_best_q4` 9-bit SAR ADC result after resolving the hidden
Maestro `Vpk=450m` override.

The previous best repaired DAC9 `/out` run, `Interactive.11`, measured
ENOB `7.86` because the generated netlist used:

```spectre
parameters fs=400M Vpk=450m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

The successful recovery run, `Interactive.12`, used live-session `maeSetVar`
calls before saving and running Maestro. The captured netlist verifies:

```spectre
parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

## Final Validated Result

| Metric | Value |
|--------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| History | `Interactive.12` |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 36m 58.5s |
| Maestro default `/out` SINAD | 54.01 dB |
| Maestro default `/out` ENOB | 8.678 bits |
| Raw `biP<8:0>` SINAD | 54.2559 dB |
| Raw `biP<8:0>` ENOB | 8.7203 bits |
| Raw best phase | `+1500 ps` |
| Raw code range | 24 to 487 |
| DAC9 `/out` phase-sweep SINAD | 54.1370 dB |
| DAC9 `/out` phase-sweep ENOB | 8.7005 bits |
| DAC9 `/out` best phase | `+2250 ps` |
| DAC9 `/out` range | 42.27 mV to 857.73 mV |

## Updated Documents

- `PROJECT_STATUS.md`
- `README.md`
- `logs/sessions/2026-06-17_sar9b_enob_recovery_project.md`
- `projects/sar9b_enob_recovery/README.md`
- `projects/sar9b_enob_recovery/analysis/2026-06-17_root_cause.md`
- `projects/sar9b_enob_recovery/experiment_matrix.csv`

## Key Evidence

- `projects/sar9b_enob_recovery/scripts/start_vpk800_maestro_run.py`
- `projects/sar9b_enob_recovery/scripts/check_vpk800_run.py`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/run_start_manifest.json`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/run_complete_manifest.json`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/input.scs`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/logs/Interactive.12.log`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/logs/spectre.out`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/phase_sweep_bip/bip_phase_sweep.json`
- `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/out_phase_sweep/out_phase_sweep.json`

## Conclusion

The active SAR9B 9-bit path and repaired
`biP<0..8> -> DAC9b_va -> /out` measurement chain are now validated near
`8.7` ENOB at nominal. The next technical risk is robustness across Vpk/PVT
rather than basic measurement-chain correctness.
