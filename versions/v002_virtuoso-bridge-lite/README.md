# v002 — 集成 virtuoso-bridge-lite

**日期**: 2026-06-16  
**摘要**: 克隆并安装 virtuoso-bridge-lite (v0.7.0)，注册 3 个 Claude Code skills

## 变更内容

- 克隆 `https://github.com/Arcadia-1/virtuoso-bridge-lite` 到项目根目录
- 在 `.venv` 中安装 virtuoso-bridge 及其依赖
- 通过 NTFS Junctions 注册 3 个 skills 到 `.claude/skills/`
- 项目级 skill 自动发现已启用

## 注册的 Skills

| Skill | 用途 | 触发关键词 |
|-------|------|-----------|
| `virtuoso` | Virtuoso 原理图/版图/Maestro 控制 | Virtuoso, Maestro, ADE, CIW, SKILL, layout, schematic |
| `spectre` | Spectre 仿真运行与结果解析 | Spectre, SPICE, transient, AC, PSS, pnoise, PSF |
| `optimizer` | 黑盒参数优化 (TuRBO/scipy) | 优化, 调参, sizing, sweep, FOM |
