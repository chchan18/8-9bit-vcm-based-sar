# SAR9B_400MV 9-bit Maestro validation

Date: 2026-06-17

This is the SAR9B library validation run requested after the earlier
original-library `ADC_9B_tb_best_q4` result.

## Setup

| Item | Value |
|------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| DUT | `I0 -> SAR9B_400MV/TOP_9B_ADC` |
| Test | `Vcmbased_ADC_tb_1` |
| History | `Interactive.5` |
| CDAC weights | q4-scaled binary |
| Verilog-A include fix | `maestro/sar9b_va_ahdl.scs` wrapper |

q4-scaled binary weights:

| Bit | P cap | N cap | Weight |
|-----|-------|-------|--------|
| 8 | C2 | C17 | `Cunit*64` |
| 7 | C0 | C14 | `Cunit*32` |
| 6 | C1 | C13 | `Cunit*16` |
| 5 | C4 | C11 | `Cunit*8` |
| 4 | C3 | C12 | `Cunit*4` |
| 3 | C5 | C10 | `Cunit*2` |
| 2 | C6 | C9 | `Cunit*1` |
| 1 | C7 | C8 | `Cunit*0.5` |
| 0 | C15 | C16 | `Cunit*0.25` |

Per-side total: `127.75*Cunit`, with `Cunit=1f` in the Maestro design point.

## Maestro/Spectre Result

| Metric | Value |
|--------|-------|
| Start -> end | 2026-06-17 10:34:06 -> 11:06:37 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 32m 31.3s |
| Maestro legacy `/out` | SINAD 16 dB, ENOB 2.365 bits |

The legacy `/out` result still uses the old `decode_redun9to8 -> DAC8b_va`
measurement path, so it is not the valid 9-bit metric.

## Raw 9-bit Metric

`biP<8:0>` was exported directly from the SAR9B PSF and measured offline.

| Metric | Value |
|--------|-------|
| Best sample phase | `+1500 ps` relative to the Maestro FFT grid |
| Best SINAD | 49.451 dB |
| Best ENOB | 7.922 bits |
| Code range | 125 to 386 |
| Midband analog bit values | 0 |

Fine sweep confirmed `+1500 ps` through `+1800 ps` all remained at the same
7.922-bit result.

## Key Artifacts

| File | Content |
|------|---------|
| `run_complete_manifest.json` | Final remote paths and Spectre summary |
| `run_status.json` | Successful final status with run log and spectre tails |
| `input.scs` | Captured SAR9B netlist for `Interactive.5` |
| `sar9b_va_ahdl.scs` | AHDL wrapper used by Maestro definitionFiles |
| `logs/Interactive.5.log` | Maestro run log |
| `logs/spectre.out` | Spectre log |
| `phase_sweep/bip_phase_sweep.json` | Broad raw-code phase sweep |
| `phase_sweep_fine/bip_phase_sweep.json` | Fine raw-code phase sweep |

