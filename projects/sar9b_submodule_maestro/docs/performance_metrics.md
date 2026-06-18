# SAR9B Submodule Performance Metrics

Date: 2026-06-18

This note maps common published block-level metrics to the measurements added
to the `SAR9B_400MV` standalone Maestro testbenches.

## Sources Checked

| Area | Source | Useful metric guidance |
|------|--------|------------------------|
| Dynamic comparator | [Design of a Strong-Arm Dynamic-Latch based comparator with high speed, low power and low offset for SAR-ADC](https://arxiv.org/abs/2209.07259) and [Strong-ARM Dynamic Latch Comparators](https://arxiv.org/abs/2402.14519) | Comparator speed/latency, power, offset, clock feedthrough, and kickback noise are common headline metrics. |
| Sample/hold and bootstrap switch | [Analog Devices MT-090: Sample-and-Hold Amplifiers](https://www.analog.com/media/en/training-seminars/tutorials/MT-090.pdf) plus [Sample and hold overview](https://en.wikipedia.org/wiki/Sample_and_hold) | Acquisition/track error, held-value error, aperture effects, droop/leakage, feedthrough, and bandwidth/noise are standard checks. |
| Non-overlap/timing generators | [Timing closure overview](https://en.wikipedia.org/wiki/Timing_closure) and [non-blocking programmable delay line characterization](https://arxiv.org/abs/2105.09183) | Delay, dead time, pulse overlap, jitter, pulse spreading, and power are the relevant timing-generator style metrics. |
| Asynchronous SAR control | [A 130-MS/s 10-Bit Asynchronous SAR ADC with 55.2 dB SNDR](https://arxiv.org/abs/1912.00530) and [dual-edge asynchronous pipelined SAR ADC](https://arxiv.org/abs/2601.21308) | Conversion sequence timing, available conversion window, reset/dead time, energy, and output logic swing matter for asynchronous SAR control. |

## Implemented Measurements

### Comparator

Maestro point outputs:

| Metric | Expression intent |
|--------|-------------------|
| `cmp_clk_rise_s` | First comparator clock 0.45 V rising crossing. |
| `cmp_decision_cross_s` | First `VOP-VON` zero crossing. |
| `cmp_decision_delay_ps` | Clock-to-decision delay. |
| `cmp_vop_max_v`, `cmp_von_min_v` | Output swing/rail reach. |
| `cmp_final_diff_v` | Final differential decision polarity and residue. |

Offline PSF metrics:

| Metric | Method |
|--------|--------|
| `cmp_avg_power_w`, `cmp_energy_j` | Integrate `getData("/VDD_SRC/PLUS" ?result "tran")` after the run. |

### Non-Overlap Clock

Maestro point outputs:

| Metric | Expression intent |
|--------|-------------------|
| `clk_clkop_delay_ps`, `clk_clkon_delay_ps` | Input-to-phase propagation delay. |
| `clk_gap_op_after_on_ps`, `clk_gap_on_after_op_ps` | Low-low non-overlap gaps between complementary phases. |
| `clk_clkop_duty_pct`, `clk_clkon_duty_pct` | First valid high-window duty cycle. |
| `clk_overlap_product_peak_v2` | Peak `CLKOP*CLKON`, near zero when both phases are never high together. |

Offline PSF metrics:

| Metric | Method |
|--------|--------|
| `clk_avg_power_w`, `clk_energy_j` | Integrate supply current after the run. |

### ASYCTRL 9-Clock Logic

Maestro point outputs:

| Metric | Expression intent |
|--------|-------------------|
| `asy_valid_to_clko8_ps` | First valid pulse to first MSB clock edge. |
| `asy_sequence_span_ps` | Time from `CLKO<8>` first rise to `CLKO<0>` first rise. |
| `asy_clkc_max_v` | Comparator strobe rail reach. |
| `asy_clko*_rise_ps` | First rising crossing for every `CLKO<8:0>`. |
| `asy_clko*_max_v` | Rail reach for every `CLKO<8:0>`. |

Offline PSF metrics:

| Metric | Method |
|--------|--------|
| `asy_avg_power_w`, `asy_energy_j` | Integrate supply current after the run. |

### Bootstrap Differential Sampler

Maestro point outputs:

| Metric | Expression intent |
|--------|-------------------|
| `boot_diff_final_v` | Final sampled differential output. |
| `boot_diff_final_error_mv` | Final `VOUTP-VOUTN` minus `VIP-VIN`. |
| `boot_track_error_on_avg_mv` | Average absolute tracking error during first on window. |
| `boot_track_error_on_max_mv` | Peak absolute tracking error during first on window. |
| `boot_settle_error_2p5n_mv` | Tracking error near end of first acquisition window. |
| `boot_clk_overlap_product_peak_v2` | Peak `CLKS*CLKSB`, used as a complementary-clock overlap check. |

Offline PSF metrics:

| Metric | Method |
|--------|--------|
| `boot_avg_power_w`, `boot_energy_j` | Integrate supply current after the run. |
| `boot_fft_sndr_db`, `boot_fft_enob_bits`, `boot_fft_thd_db`, `boot_fft_sfdr_db` | Run `TB_SUBMOD_BOOTSTRAP_DIFF_FFT`, export coherent `VOUTP-VOUTN` samples in the intended track/hold phase, and compute the FFT offline. |

Dynamic FFT is only assigned to the analog bootstrap sampler. The comparator,
clock, and ASYCTRL outputs are pulse/digital waveforms, so their FFTs are not
reported as SNDR/ENOB. Their dynamic performance is represented by the timing,
rail, overlap, and energy metrics above.

For bootstrap tracking linearity, use the corrected `50.2 ns` sample start
(`200 ps` into the 2.5 ns sampling period). The old p700-style export samples
the simplified hold node after turn-off and should be labeled as a
charge-injection/feedthrough diagnostic rather than tracking ENOB.

## ADE Current-Output Caveat

The IC618 Maestro point-output engine successfully evaluates the voltage and
timing expressions above. It rejects the branch-current based expressions
`average(getData("/VDD_SRC/PLUS" ?result "tran"))` and
`integ(getData("/VDD_SRC/PLUS" ?result "tran"))` when registered as Maestro
outputs, even though the same OCEAN expressions work after opening the PSF.

To keep Maestro runs green, supply power and energy are now computed by
`scripts/run_submodule_maestro_tests.py` from the same PSF history and stored
under each run summary's `metrics.offline` object.
