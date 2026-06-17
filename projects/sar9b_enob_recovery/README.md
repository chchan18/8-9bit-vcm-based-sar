# SAR9B ENOB Recovery Project

Date: 2026-06-17

## Objective

Push the active `SAR9B_400MV/ADC_9B_tb_best_q4` 9-bit SAR ADC result beyond
the current Maestro `/out` value of ENOB `7.86` bits and recover the expected
near-9-bit behavior seen in the earlier q4-scaled binary experiment.

## Why ENOB Is Only 7.86 Today

The measurement chain itself is no longer the primary problem. The old
`decode_redun9to8 -> DAC8b_va` path has already been replaced by:

```text
biP<0..8> -> DAC9b_va -> /out
```

The important remaining issue is signal amplitude. The final SAR9B run was
netlisted with:

```spectre
parameters fs=400M Vpk=450m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

The earlier q4-scaled run that reached ENOB `8.7167` used `Vpk=800m` with the
same q4-scaled CDAC weights.

| Run | Vpk | Code range | Signal power | Noise/dist power | SINAD | ENOB |
|-----|-----|------------|--------------|------------------|-------|------|
| `scaled_binary_q4` | `800m` | `24..487` | `2.8062e10` | `1.0584e5` | 54.2347 dB | 8.7167 |
| `SAR9B_400MV/Interactive.10` raw `biP` | `450m` | `125..386` | `8.8976e9` | `1.0126e5` | 49.4385 dB | 7.9200 |
| `SAR9B_400MV/Interactive.11` DAC9 `/out` | `450m` | analog DAC9 | n/a | n/a | 49.08 dB | 7.86 |

The noise/distortion power is nearly unchanged, while signal power scales down
almost exactly as `(450/800)^2`. That alone predicts about `5 dB`, or `0.83`
bits, of ENOB loss. The observed raw-code loss is `8.7167 - 7.9200 = 0.7967`
bits.

So the current best explanation is:

```text
The SAR9B run is under-driven by a hidden Maestro Vpk=450m override.
```

There is also a setup consistency problem: `active.state` shows `Vpk=800m`,
but `maestro.sdb` still contains repeated active-run variable blocks where
`Vpk=450m`. The generated `Interactive.11` netlist proves that the 450m value
won the Maestro variable-precedence chain.

## First Experiment

Experiment name: `vpk800_p2200_baseline`

1. Start from the known-good `maestro_files_loaded_phase_p2200` setup.
2. Patch every active `Vpk` occurrence in both `active.state` and `maestro.sdb`
   to `800m`.
3. Upload the patched setup to
   `/home/IC/Desktop/Project/SAR9B_400MV/ADC_9B_tb_best_q4/maestro/`.
4. Generate or capture the new netlist and verify:

```spectre
parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

5. Run Maestro and measure:
   - default DAC9 `/out` `spectrum_enob/sinad`
   - raw `biP<8:0>` at the known-good `+1500 ps` phase
   - `/out` around the p2200 window

Expected result: if amplitude is the dominant issue, raw `biP<8:0>` should
move from ENOB `7.92` back near `8.7`, and DAC9 `/out` should follow after FFT
window verification.

## Follow-up Experiments

| Priority | Experiment | Purpose |
|----------|------------|---------|
| P0 | `vpk800_p2200_baseline` | Confirm the under-drive hypothesis. |
| P1 | `vpk_sweep_650_700_750_800m` | Find the highest SINAD before clipping/settling artifacts. |
| P2 | `phase_sweep_vpk800` | Re-select the best raw-code and DAC9 `/out` sample windows after increasing amplitude. |
| P3 | `dac9_trise_sweep` | Check whether finite DAC9 edge smoothing is still costing the `/out` metric. |
| P4 | `pvt_input_robustness` | Confirm the result is not a single nominal-corner point. |

## Project Files

| File | Purpose |
|------|---------|
| `analysis/2026-06-17_root_cause.md` | Detailed root-cause note and calculations. |
| `experiment_matrix.csv` | Experiment queue and expected pass criteria. |
| `scripts/patch_maestro_vpk.py` | Local patcher for `active.state` and `maestro.sdb`. |
| `scripts/upload_vpk800_setup.py` | Dry-run-by-default uploader that backs up the remote Maestro setup before applying the Vpk=800m setup. |
| `artifacts/maestro_files_vpk800_p2200/` | Generated patched Maestro setup after running the patcher. |

## Current State

The local patched setup has been generated. Its manifest shows:

```text
active.state: Vpk 800m -> 800m
maestro.sdb:  12 x 450m + 12 x 800m -> 24 x 800m
```

The next action is to upload this setup with:

```powershell
.\.venv\Scripts\python.exe projects\sar9b_enob_recovery\scripts\upload_vpk800_setup.py --apply
```

Then start a fresh `SAR9B_400MV/ADC_9B_tb_best_q4` Maestro run and verify the
captured netlist uses `Vpk=800m`.
