# 8-9bit VCM-Based SAR ADC

本仓库记录一个基于 Cadence Virtuoso/Explorer/Maestro 的 VCM-based SAR ADC
优化过程，重点是从原始 8-bit redundant SAR 迁移并验证 9-bit SAR ADC。

## 当前结论

最新有效结果来自 `SAR9B_400MV/ADC_9B_tb_best_q4` 的 `Interactive.12`
Maestro run。通过修复 9-bit `/out` measurement chain，并强制 live Maestro
session 使用 `Vpk=800m`，SAR9B nominal 结果已经恢复到接近 9-bit：

| Measurement | SINAD | ENOB |
|-------------|-------|------|
| Maestro default `/out` | 54.01 dB | 8.678 bits |
| Raw `biP<8:0>` phase sweep | 54.2559 dB | 8.7203 bits |
| DAC9 `/out` phase sweep | 54.1370 dB | 8.7005 bits |

之前看到的 `ENOB=7.86` 主要来自隐藏的 Maestro `Vpk=450m` override，而不是
9-bit SAR 核心或 DAC9 measurement chain 的根本限制。

## 关键目录

| Path | Content |
|------|---------|
| `PROJECT_STATUS.md` | 当前状态、历史结果、handoff 信息 |
| `projects/sar9b_enob_recovery/` | SAR9B ENOB recovery 项目、脚本、结果与分析 |
| `sar9b_work/` | 9-bit SAR 修复、仿真、导出与分析脚本 |
| `versions/` | 分阶段版本化文档快照 |
| `virtuoso-bridge-lite/` | 本地 Virtuoso bridge 工具 |

## 最新证据

核心证据位于：

```text
projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/
```

其中包含 `Interactive.12` 的 netlist、Maestro log、Spectre log、raw bit
phase sweep 和 DAC9 `/out` phase sweep。netlist 参数行为：

```spectre
parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

## 下一步

基础 recovery 已完成。后续重点应放在 Vpk/PVT/input robustness sweep，确认
`8.7` ENOB 不是单一 nominal corner 的偶然点。
