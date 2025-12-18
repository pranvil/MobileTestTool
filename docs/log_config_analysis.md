# 日志配置参数生效情况分析

## 概述
`debug_log_config.json` 中的配置参数在不同日志系统中的生效情况。

## 日志系统说明

程序中有两个日志系统：
1. **主程序日志系统** (`core/debug_logger.py`) - 用于 GUI 模式
2. **SIM Reader 日志系统** (`sim_reader/core/utils.py`) - 用于 CLI 模式

## 参数生效情况

| 参数 | 主程序日志系统 (GUI) | SIM Reader 日志系统 (CLI) | 说明 |
|------|---------------------|-------------------------|------|
| `enabled` | ✅ 生效 | ✅ 生效 | 控制是否启用日志 |
| `log_level` | ✅ 生效 | ✅ 生效 | 控制日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `max_file_size_mb` | ✅ 生效 | ❌ **不生效** | 主程序日志文件大小限制 |
| `max_files` | ✅ 生效 | ❌ **不生效** | 主程序日志文件数量限制 |
| `retention_days` | ✅ 生效 | ❌ **不生效** | 主程序日志保留天数 |
| `buffer_size` | ✅ 生效 | ❌ **不生效** | 主程序日志缓冲队列大小 |
| `flush_interval` | ✅ 生效 | ❌ **不生效** | 主程序日志刷新间隔 |
| `enable_rotation` | ❌ **不生效** | ❌ **不生效** | **代码中未使用此参数** |
| `rotation_by_size` | ✅ 生效 | ❌ **不生效** | 主程序按大小轮转 |
| `rotation_by_date` | ✅ 生效 | ❌ **不生效** | 主程序按日期轮转 |
| `include_module` | ✅ 生效 | ❌ **不生效** | 主程序日志包含模块名 |
| `include_function` | ✅ 生效 | ❌ **不生效** | 主程序日志包含函数名 |
| `include_line` | ✅ 生效 | ❌ **不生效** | 主程序日志包含行号 |

## 详细说明

### 主程序日志系统 (GUI 模式)
- **文件位置**: `core/debug_logger.py`
- **日志文件**: `logs/debug_YYYYMMDD.log`
- **生效参数**: 除了 `enable_rotation` 外，其他参数都生效
- **问题**: `enable_rotation` 参数在代码中定义但未实际使用

### SIM Reader 日志系统 (CLI 模式)
- **文件位置**: `sim_reader/core/utils.py`
- **日志文件**: `logs/log.txt` (使用 Python 标准 `TimedRotatingFileHandler`)
- **生效参数**: 只有 `enabled` 和 `log_level` 生效
- **问题**: 其他参数（如文件大小、轮转、保留天数等）都未使用

## 建议

1. **修复 `enable_rotation` 参数**: 在 `core/debug_logger.py` 中实现此参数的控制逻辑
2. **扩展 SIM Reader 日志系统**: 让 SIM Reader 的日志系统也支持更多配置参数
3. **统一日志系统**: 考虑让 SIM Reader 也使用主程序的日志系统，以保持一致性

