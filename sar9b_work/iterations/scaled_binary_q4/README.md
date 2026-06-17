# scaled_binary_q4 Iteration

Date: 2026-06-17

Goal: keep 9-bit binary CDAC ratios while reducing total CDAC load back near
the original redundant design.

## CDAC Point

Per side total: 127.75 * Cunit, with Cunit=1f.

| Bit | P cap | N cap | Weight |
|-----|-------|-------|--------|
| 8 | C2 | C17 | Cunit*64 |
| 7 | C0 | C14 | Cunit*32 |
| 6 | C1 | C13 | Cunit*16 |
| 5 | C4 | C11 | Cunit*8 |
| 4 | C3 | C12 | Cunit*4 |
| 3 | C5 | C10 | Cunit*2 |
| 2 | C6 | C9 | Cunit*1 |
| 1 | C7 | C8 | Cunit*0.5 |
| 0 | C15 | C16 | Cunit*0.25 |

## Simulation

| Item | Value |
|------|-------|
| Run history | ExplorerRun.0 |
| Start/end | 2026-06-17 00:58:53 -> 01:26:54 |
| Spectre elapsed | 27m 49.0s |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Maestro legacy `/out` path | SINAD 23.18 dB, ENOB 3.558 bits |

The Maestro `/out` result still uses the old `decode_redun9to8` + `DAC8b_va`
path and is not the raw 9-bit binary measurement.

## Raw biP Measurement

Top-level `biP<8:0>` was exported directly from PSF and decoded as an unsigned
9-bit binary code.

| Sample offset | SINAD | ENOB | Notes |
|---------------|-------|------|-------|
| +1200 ps | 43.936 dB | 7.006 bits | First sampled point above 7-bit target |
| +1350 ps | 46.587 dB | 7.446 bits | Stable logic levels |
| +1500 ps | 54.235 dB | 8.717 bits | Best point |
| +1650 ps | 54.235 dB | 8.717 bits | Same plateau |
| +1800 ps | 54.235 dB | 8.717 bits | Same plateau |
| +1950 ps | 54.235 dB | 8.717 bits | Same plateau |
| +2100 ps | 54.235 dB | 8.717 bits | Same plateau |

Best raw-code result:

| Metric | Value |
|--------|-------|
| SINAD | 54.2347 dB |
| ENOB | 8.7167 bits |
| Code range | 24 to 487 |
| Code mean | 255.501 |
| Midband values | 0 |

## Artifacts

| File | Content |
|------|---------|
| `input.scs` | Captured Maestro netlist for this CDAC point |
| `logs/ExplorerRun.0.log` | Maestro run log |
| `logs/spectre.out` | Spectre run log |
| `phase_sweep/bip_phase_sweep.json` | Coarse phase sweep |
| `phase_sweep_fine/bip_phase_sweep.json` | Fine phase sweep around the good window |

## Interpretation

The previous full-scale binary CDAC used 511 fF per side and reached only about
4.55 ENOB at its best sampled phase. Scaling the same binary ratios to about
128 fF per side restores enough settling margin to exceed the 7-bit target.
This points to CDAC load/switch settling, not bit mapping or code polarity, as
the dominant issue in the first binary experiment.
