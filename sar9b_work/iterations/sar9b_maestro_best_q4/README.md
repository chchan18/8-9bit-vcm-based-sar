# SAR9B_400MV 9-bit Maestro validation and DAC9 measurement chain

Date: 2026-06-17

This is the current SAR9B library validation run after repairing the Maestro
`/out` measurement chain from the old 8-bit decoder/DAC path to a direct 9-bit
DAC path.

## Setup

| Item | Value |
|------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| DUT | `I0 -> SAR9B_400MV/TOP_9B_ADC` |
| Test | `Vcmbased_ADC_tb_1` |
| History | `Interactive.11` |
| CDAC weights | q4-scaled binary |
| Measurement chain | `biP<0..8> -> DAC9b_va -> /out` |
| Verilog-A include fix | `maestro/sar9b_va_ahdl.scs` wrapper, containing only `DAC9b_va` |

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
| Start -> end | 2026-06-17 14:32:29 -> 16:21:46 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 1h 49m 18s |
| Maestro `/out`, direct DAC9 chain with p2200 FFT window | SINAD 49.08 dB, ENOB 7.86 bits |

The original low `ENOB=2.365` problem is fixed: the captured `Interactive.11`
netlist no longer contains `decode_redun9to8`, `DAC8b_va`, or an empty
`subckt DAC9b_va`. The top testbench now instantiates:

```spectre
I15 (out VDD biP\<0\> biP\<1\> biP\<2\> biP\<3\> biP\<4\> biP\<5\> \
        biP\<6\> biP\<7\> biP\<8\>) DAC9b_va VFS=0.9 VTH=0.45 trise=1e-09 \
        tfall=1e-09 td=0 rout=1
```

and the wrapper contains:

```spectre
ahdl_include "/home/IC/Desktop/Project/SAR9B_400MV/DAC9b_va/veriloga/veriloga.va"
```

The remaining gap was closed by changing the Maestro ENOB/SINAD expressions
to the validated `/out` p2200 FFT window:

```skill
spectrumMeasurement(v("/out" ?result "tran") t 2.82e-08 2.5882e-06 1024 390600 2e+08 0 "Rectangular" 0 0 1 "enob")
spectrumMeasurement(v("/out" ?result "tran") t 2.82e-08 2.5882e-06 1024 390600 2e+08 0 "Rectangular" 0 0 1 "sinad")
```

`Interactive.11.log` reports both the p2200 aliases and the default Maestro
outputs at the same values:

```text
spectrum_enob_p2200  7.86
spectrum_sinad_p2200 49.08
spectrum_enob        7.86
spectrum_sinad       49.08
```

## Raw 9-bit Metric

`biP<8:0>` was exported directly from the repaired SAR9B PSF and measured
offline with the known-good sample phase.

| Metric | Value |
|--------|-------|
| Best sample phase | `+1500 ps` relative to the Maestro FFT grid |
| Best SINAD | 49.4385 dB |
| Best ENOB | 7.9200 bits |
| Code range | 125 to 386 |
| Midband analog bit values | 0 |

The `Interactive.10` phase sweep confirms `+1500 ps` through `+1800 ps` all
remain at the same 7.920-bit raw-code result. The analog `/out` DAC waveform
needs the later p2200 FFT window because the measurement DAC still uses a
finite `trise/tfall=1 ns`.

## Key Artifacts

| File | Content |
|------|---------|
| `run_complete_manifest.json` | Final remote paths and Spectre summary |
| `run_status.json` | Successful final status with run log and spectre tails |
| `input.scs` | Captured SAR9B netlist for `Interactive.11`, proving `DAC9b_va` on `/out` |
| `sar9b_va_ahdl.scs` | AHDL wrapper used by Maestro definitionFiles |
| `logs/Interactive.11.log` | Maestro run log with corrected `/out` SINAD/ENOB |
| `logs/spectre.out` | Spectre log |
| `phase_sweep/bip_phase_sweep.json` | Broad raw-code phase sweep |
| `phase_sweep_fine/bip_phase_sweep.json` | Fine raw-code phase sweep |
| `phase_sweep_interactive10/bip_phase_sweep.json` | Raw-code phase sweep from the repaired `Interactive.10` run |
| `out_phase_interactive10_fine/out_phase_sweep.json` | `/out` phase sweep selecting the p2200 FFT window |
| `maestro_files_loaded_phase_p2200/active.state` | Verified Maestro setup with p2200 `spectrum_enob/sinad` expressions |
