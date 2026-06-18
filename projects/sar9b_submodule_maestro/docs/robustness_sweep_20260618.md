# SAR9B Submodule Robustness Sweep

Date: 2026-06-18

This note records the first complete robustness sweep of the standalone
`SAR9B_400MV` submodule Maestro testbenches. The run used the generated
`TRAN` Maestro views and the callback trigger path:

```powershell
.venv\Scripts\python.exe projects\sar9b_submodule_maestro\scripts\run_submodule_robustness_sweeps.py --trigger callback --tag robustness_20260618_full
```

The sweep manifest is saved at:

```text
projects/sar9b_submodule_maestro/runs/submodule_robustness_manifest.json
projects/sar9b_submodule_maestro/runs/robustness_20260618_full/robustness_manifest.json
```

## Result Summary

All 20 Maestro cases completed successfully:

| Cell | Cases | ADE run errors | Spectre errors | Result |
|------|-------|----------------|----------------|--------|
| `TB_SUBMOD_COMPARATOR_PERF` | 6 | 0 | 0 | PASS |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | 4 | 0 | 0 | PASS |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | 5 | 0 | 0 | PASS |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | 5 | 0 | 0 | PASS |

Bridge note: opening a fresh Maestro cell sometimes reset the bridge daemon.
The case runs themselves were not corrupted; the daemon was recovered with
`scripts/reload_bridge_ciw.py`, then the affected cell sweep was restarted.

## Case Results

### Comparator

| Case | Overrides | History | Spectre errors | Key Maestro metric | Offline power |
|------|-----------|---------|----------------|--------------------|---------------|
| `cmp_nominal` | nominal | `Interactive.1` | 0 | `cmp_decision_delay_ps=4.483` | 31.829 uW |
| `cmp_vdiff_2m` | `vdiff=2m` | `Interactive.2` | 0 | `cmp_decision_delay_ps=4.482` | 32.072 uW |
| `cmp_vdiff_5m` | `vdiff=5m` | `Interactive.3` | 0 | `cmp_decision_delay_ps=4.483` | 31.924 uW |
| `cmp_vdiff_20m` | `vdiff=20m` | `Interactive.4` | 0 | `cmp_decision_delay_ps=4.484` | 31.744 uW |
| `cmp_cload_5f` | `cload=5f` | `Interactive.5` | 0 | `cmp_decision_delay_ps=4.514` | 32.131 uW |
| `cmp_vdd_800m` | `vdd=800m` | `Interactive.6` | 0 | `cmp_decision_delay_ps=5.335` | 15.882 uW |

### Non-Overlap Clock

| Case | Overrides | History | Spectre errors | Key Maestro metric | Offline power |
|------|-----------|---------|----------------|--------------------|---------------|
| `clk_nominal` | nominal | `Interactive.1` | 0 | `clk_gap_op_after_on_ps=35.08`, overlap product `6.792u` | 3.639 uW |
| `clk_cload_1f` | `cload=1f` | `Interactive.2` | 0 | `clk_gap_op_after_on_ps=35.29`, overlap product `8.221u` | 3.287 uW |
| `clk_cload_5f` | `cload=5f` | `Interactive.3` | 0 | `clk_gap_op_after_on_ps=34.4`, overlap product `5.883u` | 4.677 uW |
| `clk_vdd_800m` | `vdd=800m` | `Interactive.4` | 0 | `clk_gap_op_after_on_ps=44.86`, overlap product `5.103u` | 3.177 uW |

All four clock cases also report `both_high_total_ps=0.0` in offline metrics.

### ASYCTRL 9-Clock Sequencer

| Case | Overrides | History | Spectre errors | Key Maestro metric | Offline power |
|------|-----------|---------|----------------|--------------------|---------------|
| `asy_nominal` | nominal | `Interactive.1` | 0 | `asy_sequence_span_ps=20K`, `clko_rail_count=9` | 8.261 uW |
| `asy_valid_per_2n` | `valid_per=2n` | `Interactive.2` | 0 | `asy_sequence_span_ps=16K`, `clko_rail_count=9` | 9.897 uW |
| `asy_valid_per_3n` | `valid_per=3n` | `Interactive.3` | 0 | `asy_sequence_span_ps=24K`, `clko_rail_count=9` | 7.373 uW |
| `asy_cload_3f` | `cload=3f` | `Interactive.4` | 0 | `asy_sequence_span_ps=20K`, `clko_rail_count=9` | 8.770 uW |
| `asy_vdd_800m` | `vdd=800m` | `Interactive.5` | 0 | `asy_valid_to_clko8_ps=50.16`, `clko_rail_count=9` | 7.212 uW |

The `valid_per` sweep confirms that the 9-clock sequence span tracks the
spacing: about 16 ns at 2 ns, 20 ns at 2.5 ns, and 24 ns at 3 ns.

### Differential Bootstrap

| Case | Overrides | History | Spectre errors | Key Maestro metric | Offline power |
|------|-----------|---------|----------------|--------------------|---------------|
| `boot_nominal` | nominal | `Interactive.1` | 0 | `boot_diff_final_error_mv=67.51u`, `boot_settle_error_2p5n_mv=86.49u` | 2.188 uW |
| `boot_vdiff_50m` | `vdiff=50m` | `Interactive.2` | 0 | `boot_diff_final_error_mv=-30.75u`, `boot_settle_error_2p5n_mv=6.122u` | 2.187 uW |
| `boot_vdiff_200m` | `vdiff=200m` | `Interactive.3` | 0 | `boot_diff_final_error_mv=438u`, `boot_settle_error_2p5n_mv=87.75u` | 2.178 uW |
| `boot_cload_10f` | `cload=10f` | `Interactive.4` | 0 | `boot_diff_final_error_mv=-248.9u`, `boot_settle_error_2p5n_mv=8.482u` | 2.190 uW |
| `boot_vdd_800m` | `vdd=800m` | `Interactive.5` | 0 | `boot_diff_final_error_mv=-189.9u`, `boot_settle_error_2p5n_mv=226.5u` | 1.929 uW |

## Interpretation

The current standalone block-level Maestro tests are healthy at nominal and
through the first variable robustness matrix. The next useful test expansion is
PVT/corner coverage and a focused timing-margin sweep that reuses the same
measurement outputs.
