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

## First Experiment Result

Status: passed.

The patched XML files alone were not sufficient because an already-open ADE
session could still save stale in-memory `Vpk=450m` values back into
`maestro.sdb`. The successful flow therefore sets `Vpk=800m` in the live
Maestro session with `maeSetVar`, saves the setup, starts the run, and then
checks the generated netlist before trusting the result.

| Item | Value |
|------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| History | `Interactive.12` |
| Netlist Vpk evidence | `parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u` |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 36m 58.5s |
| Maestro default `/out` outputs | SINAD 54.01 dB, ENOB 8.678 bits |
| Raw `biP<8:0>` best | SINAD 54.2559 dB, ENOB 8.7203 bits |
| Raw best phase | `+1500 ps` relative to the original Maestro FFT grid |
| Raw code range | 24 to 487 |
| DAC9 `/out` phase-sweep best | SINAD 54.1370 dB, ENOB 8.7005 bits |
| DAC9 `/out` best phase | `+2250 ps` relative to the original Maestro FFT grid |
| DAC9 `/out` range | 42.27 mV to 857.73 mV |

The recovered result confirms the root-cause hypothesis: the SAR9B design and
the repaired 9-bit DAC measurement chain can both reach near-9-bit ENOB once
the hidden `Vpk=450m` Maestro override is removed.

Phase-sweep highlights:

| Path | Stable/Best Window | Result |
|------|--------------------|--------|
| Raw `biP<8:0>` | `+1500 ps` through `+2100 ps` | ENOB 8.7203 bits |
| DAC9 `/out` | best at `+2250 ps` | ENOB 8.7005 bits |

## Follow-up Experiments

| Priority | Experiment | Purpose |
|----------|------------|---------|
| P0 | `vpk800_p2200_baseline` | Done: confirmed the under-drive hypothesis and recovered ENOB. |
| P1 | `vpk_sweep_650_700_750_800m` | Find the highest SINAD before clipping/settling artifacts. |
| P2 | `phase_sweep_vpk800` | Done: raw best at `+1500 ps`, DAC9 `/out` best at `+2250 ps`. |
| P3 | `dac9_trise_sweep` | Lower priority: DAC9 `/out` is now within 0.02 bit of raw `biP`. |
| P4 | `pvt_input_robustness` | Confirm the result is not a single nominal-corner point. |

## Project Files

| File | Purpose |
|------|---------|
| `analysis/2026-06-17_root_cause.md` | Detailed root-cause note and calculations. |
| `experiment_matrix.csv` | Experiment queue and expected pass criteria. |
| `scripts/patch_maestro_vpk.py` | Local patcher for `active.state` and `maestro.sdb`. |
| `scripts/upload_vpk800_setup.py` | Dry-run-by-default uploader that backs up the remote Maestro setup before applying the Vpk=800m setup. |
| `scripts/start_vpk800_maestro_run.py` | Sets `Vpk=800m` in the live Maestro session, starts a run, and verifies the generated netlist. |
| `scripts/check_vpk800_run.py` | Polls the active Maestro/Spectre run and archives logs/netlist. |
| `artifacts/maestro_files_vpk800_p2200/` | Generated patched Maestro setup after running the patcher. |
| `runs/vpk800_p2200_baseline/` | Interactive.12 manifest, netlist, logs, and phase-sweep exports. |

## Current State

`vpk800_p2200_baseline` is complete. The best verified nominal result is now:

```text
raw biP<8:0>: ENOB 8.7203, SINAD 54.2559 dB
Maestro /out: ENOB 8.6780, SINAD 54.0100 dB
DAC9 /out:    ENOB 8.7005, SINAD 54.1370 dB phase-sweep best
```

The next useful work is robustness, not basic recovery: run a small Vpk/PVT
sweep and confirm the high-ENOB plateau is not a single nominal-corner point.
