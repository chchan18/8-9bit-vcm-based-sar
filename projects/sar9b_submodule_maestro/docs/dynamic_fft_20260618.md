# SAR9B Submodule Dynamic FFT Report

Date: 2026-06-18

This note adds coherent-sine FFT dynamic measurements for the standalone
`SAR9B_400MV` submodule work. The FFT run is meaningful for the analog
bootstrap sampler. For the clock generator, asynchronous control logic, and
clocked comparator, FFT of the existing pulse/digital outputs is only a
frequency-content diagnostic and should not be reported as ADC-style ENOB.

## FFT Applicability

| Submodule | FFT status | Dynamic performance metric to use |
|-----------|------------|-----------------------------------|
| `BOOTSTRAP_DIFF` | Valid analog coherent-sine FFT on `VOUTP-VOUTN` | SNDR, ENOB, THD, SFDR, gain, tracking error |
| `COMPARATOR` | Not an ADC-style FFT target in the current pulse/DC TB | Decision delay, metastability/error probability, offset, kickback, output swing, energy |
| `CLK_NOOVERLAP` | Square-wave FFT is harmonic content only | Propagation delay, non-overlap gap, simultaneous-high time, duty cycle, jitter, energy |
| `Asycontrol_logic_9clk` | Digital sequence FFT is not a useful ENOB metric | Sequence span, per-bit clock timing, rail reach, reset/valid margin, energy |

## Maestro Setup

| Item | Value |
|------|-------|
| Library / cell | `SAR9B_400MV/TB_SUBMOD_BOOTSTRAP_DIFF_FFT` |
| DUT | `BOOTSTRAP_DIFF` |
| Maestro test | `TRAN` |
| Model section | TSMC 28nm HPC+ `top_tt` |
| Supply/common mode | `vdd=900m`, `vcm=450m` |
| Sampling rate | `fs=400M` |
| Input frequency | `(7/1024)*fs = 2.734375 MHz` |
| FFT points | `1024` |
| Sample window | `50.2 ns` to `2.6077 us`, step `2.5 ns` |
| Load | `cload=5f` on each bootstrap output |

The testbench uses the same `analogLib/vsource` sine source and
`analogLib/ideal_balun` differential drive style as the validated ADC
testbench, then exports `VIP-VIN` and `VOUTP-VOUTN` from the PSF with OCEAN.
The corrected headline measurement samples inside the bootstrap track window,
at `200 ps` after the 2.5 ns sampling-clock period boundary.

## Corrected Track-Phase Results

Both corrected runs completed with zero ADE run errors and zero Spectre errors.

| Case | History | Input Vpk | Output amp | SNDR | ENOB | THD | SFDR | Largest spur |
|------|---------|-----------|------------|------|------|-----|------|--------------|
| Full-scale track | `Interactive.2` | `800m` | `0.8000 Vpk` | `128.974 dB` | `21.132 bit` | `-129.621 dB` | `131.308 dB` | bin 21, `8.203 MHz` |
| Mid-scale track | `Interactive.3` | `400m` | `0.4000 Vpk` | `128.886 dB` | `21.117 bit` | `-129.004 dB` | `131.814 dB` | bin 21, `8.203 MHz` |

Transfer checks:

| Case | Fundamental gain | Error RMS | Error peak | Output single-ended range |
|------|------------------|-----------|------------|---------------------------|
| `Vpk=800m` | `0.000001 dB` | `10.90 uV` | `15.57 uV` | `50.00 mV` to `850.00 mV` |
| `Vpk=400m` | `-0.000003 dB` | `5.47 uV` | `7.78 uV` | `250.00 mV` to `650.00 mV` |

## Phase-Sweep Check

The earlier `nominal_p2200` and `nominal_vpk400` results sampled at about
`700 ps` into the 2.5 ns clock period. That is outside the track window and
therefore measured the small 5 fF standalone hold node after switch turn-off,
not the bootstrap tracking linearity. A phase sweep on the same PSF histories
confirmed the issue:

| Vpk | Best phase | Best SNDR | Best ENOB | Previous 700 ps ENOB |
|-----|------------|-----------|-----------|----------------------|
| `800m` | `200 ps` | `128.974 dB` | `21.132 bit` | `6.667 bit` |
| `400m` | `100 ps` | `129.270 dB` | `21.181 bit` | `8.073 bit` |

## Interpretation

The original low ENOB was a measurement-window error. It used the ADC `/out`
p2200 FFT timing convention for a standalone bootstrap node. That convention is
valid for the final reconstructed DAC output, but not for a sampler tracking
test. When sampled during the actual track interval, the standalone bootstrap
path is not the limiting source of the full ADC's `8.7 bit` ENOB at nominal.

The post-track 5 fF hold-node FFT is still a useful diagnostic for
charge-injection/feedthrough behavior under a simplified load, but it should be
reported separately from dynamic tracking ENOB. A more ADC-faithful hold test
should use the actual CDAC/comparator top-plate load and the real
`CLK_NOOVERLAP`-generated `CLKON` waveform rather than an ideal inverse clock.
The comparator, clock, and ASYCTRL blocks should continue to be judged by
timing/energy/noise metrics rather than ENOB.

## Artifacts

| Artifact | Content |
|----------|---------|
| `artifacts/bootstrap_fft_setup_manifest.json` | Created Maestro FFT testbench variables and sample plan |
| `runs/bootstrap_fft_dynamic/nominal_track_p200/summary.json` | Corrected `Vpk=800m` track-phase FFT metrics and run paths |
| `runs/bootstrap_fft_dynamic/nominal_vpk400_track_p200/summary.json` | Corrected `Vpk=400m` track-phase FFT metrics and run paths |
| `runs/bootstrap_fft_dynamic/phase_sweep_existing/summary.json` | PSF re-export phase sweep proving the old p700 result was a windowing error |
| `runs/bootstrap_fft_dynamic/nominal_p2200/summary.json` | Legacy `Vpk=800m` hold-phase diagnostic, not headline ENOB |
| `runs/bootstrap_fft_dynamic/nominal_vpk400/summary.json` | Legacy `Vpk=400m` hold-phase diagnostic, not headline ENOB |
| `runs/bootstrap_fft_dynamic/*/sampled_fft_points.txt` | Exported coherent sample points for input/output FFT |
| `runs/bootstrap_fft_dynamic/*/input.scs` | Captured Spectre netlist proving stimulus and DUT wiring |
