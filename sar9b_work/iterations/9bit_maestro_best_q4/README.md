# Real 9-bit Maestro run: ADC_9B_tb_best_q4

Date: 2026-06-17

This iteration creates and runs a real 9-bit Maestro testbench instead of
reusing `ADC_redun1_tb`.

## Setup

- Library: `8BIT400MVcmredundancySAR`
- Maestro cell: `ADC_9B_tb_best_q4`
- DUT instance: `I0 -> TOP_9B_BINARY`
- Maestro template source: `ADC_9B_tb_v2/maestro`
- Schematic source: copied from `ADC_redun1_tb`, then `I0` master changed in place
- Legacy measurement chain still present:
  - `I14 -> decode_redun9to8`
  - `I15 -> DAC8b_va`

## CDAC weights on TOP_9B_BINARY

These are the best q4-scaled binary weights:

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

Per-side total: `127.75*Cunit`.

## Maestro run

History: `Interactive.1`

| Item | Value |
|------|-------|
| Start -> end | 2026-06-17 09:16:56 -> 09:42:42 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 25m 44.6s |
| Maestro legacy `/out` ENOB | 2.365 bits |
| Maestro legacy `/out` SINAD | 16 dB |

The legacy `/out` value is expected to be misleading because it still goes
through `decode_redun9to8` and `DAC8b_va`. The valid 9-bit measurement is the
raw top-level `biP<8:0>` export below.

Netlist evidence:

- `input.scs` contains `I0 (...) TOP_9B_BINARY`
- `TOP_9B_BINARY` subckt contains the q4 weights listed above

## Raw 9-bit result

Raw `biP<8:0>` was exported from:

`/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_9B_tb_best_q4/maestro/results/maestro/Interactive.1/1/Vcmbased_ADC_tb_1/psf`

Best phase:

| Offset | SINAD | ENOB | Code range |
|--------|-------|------|------------|
| `+1500 ps` | 49.451 dB | 7.922 bits | 125..386 |

The high-ENOB plateau is stable from `+1500 ps` through `+2250 ps` in the
fine sweep. The broad sweep also shows a matching stable window from
`-900 ps` through `-300 ps`.

## Artifacts

| File | Content |
|------|---------|
| `prepare_manifest.json` | Creation and verification of the real 9-bit Maestro cell |
| `run_complete_manifest.json` | Final run paths and key metrics |
| `input.scs` | Captured netlist for `Interactive.1` |
| `logs/Interactive.1.log` | Maestro run log |
| `logs/spectre.out` | Spectre run log |
| `phase_sweep/bip_phase_sweep.json` | Broad raw-code phase sweep |
| `phase_sweep_fine/bip_phase_sweep.json` | Fine raw-code phase sweep |
