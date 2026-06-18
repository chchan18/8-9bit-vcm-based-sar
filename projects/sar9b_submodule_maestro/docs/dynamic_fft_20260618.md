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
| Sample window | `28.2 ns` to `2.5857 us`, step `2.5 ns` |
| Load | `cload=5f` on each bootstrap output |

The testbench uses the same `analogLib/vsource` sine source and
`analogLib/ideal_balun` differential drive style as the validated ADC
testbench, then exports `VIP-VIN` and `VOUTP-VOUTN` from the PSF with OCEAN.

## Results

Both runs completed with zero ADE run errors and zero Spectre errors.

| Case | History | Input Vpk | Output amp | SNDR | ENOB | THD | SFDR | Largest spur |
|------|---------|-----------|------------|------|------|-----|------|--------------|
| Full-scale stress | `Interactive.0` | `800m` | `0.7101 Vpk` | `41.895 dB` | `6.667 bit` | `-41.896 dB` | `41.987 dB` | bin 21, `8.203 MHz` |
| Mid-scale linearity | `Interactive.1` | `400m` | `0.3620 Vpk` | `50.346 dB` | `8.071 bit` | `-50.398 dB` | `50.400 dB` | bin 21, `8.203 MHz` |

Transfer checks:

| Case | Fundamental gain | Error RMS | Error peak | Output single-ended range |
|------|------------------|-----------|------------|---------------------------|
| `Vpk=800m` | `-1.036 dB` | `63.73 mV` | `94.77 mV` | `14.35 mV` to `719.61 mV` |
| `Vpk=400m` | `-0.866 dB` | `26.87 mV` | `39.10 mV` | `198.44 mV` to `559.36 mV` |

## Interpretation

The bootstrap sampler is clearly amplitude limited in the standalone 5 fF-load
test. At `Vpk=400m`, the differential output reaches `8.07 bit` ENOB, so the
small/mid-signal path is already compatible with an 8-bit-class dynamic target.
At the intended full-scale ADC stress point, `Vpk=800m`, SNDR falls to
`41.9 dB` (`6.67 bit`) and the largest spur is the third harmonic. The
single-ended output range also approaches the rails, which makes headroom and
bootstrapped switch linearity the likely full-scale limiters.

For a follow-up optimization, the useful knobs are bootstrap switch sizing,
bootstrap capacitor/clock-boost strength, load seen by the sampler, and the
exact sampling phase used by the ADC decision path. The comparator, clock, and
ASYCTRL blocks should continue to be judged by timing/energy/noise metrics
rather than ENOB.

## Artifacts

| Artifact | Content |
|----------|---------|
| `artifacts/bootstrap_fft_setup_manifest.json` | Created Maestro FFT testbench variables and sample plan |
| `runs/bootstrap_fft_dynamic/nominal_p2200/summary.json` | `Vpk=800m` FFT metrics and run paths |
| `runs/bootstrap_fft_dynamic/nominal_vpk400/summary.json` | `Vpk=400m` FFT metrics and run paths |
| `runs/bootstrap_fft_dynamic/*/sampled_fft_points.txt` | Exported coherent sample points for input/output FFT |
| `runs/bootstrap_fft_dynamic/*/input.scs` | Captured Spectre netlist proving stimulus and DUT wiring |
