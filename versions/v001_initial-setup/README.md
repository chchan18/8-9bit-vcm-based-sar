# v001 — 项目初始化

**日期**: 2026-06-16  
**摘要**: 建立项目基础结构、日志系统和版本控制框架

## 变更内容

- 创建 `.gitignore`
- 创建 `logs/` 目录用于记录每次会话的 prompt 和运行过程
- 创建 `versions/` 目录用于管理每个版本的更新
- 配置 Claude Code hooks 实现自动会话日志记录
- 设置权限模式为 `acceptEdits`

## 文件结构

```
8bitvcmvirtuoso/
├── .claude/
│   ├── settings.json          # 项目配置（权限、hooks）
│   └── settings.local.json    # 个人覆盖配置
├── .gitignore
├── logs/
│   └── sessions/              # 每次会话的日志文件
├── versions/                  # 版本历史归档
│   └── v001_initial-setup/
└── .venv/                     # Python 虚拟环境
```
