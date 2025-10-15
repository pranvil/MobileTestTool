# Log 过滤功能使用说明

## 功能概述

本模块实现了完整的日志过滤和搜索功能，基于原 Tkinter 版本的 `log_processor.py` 和 `search_manager.py` 重新实现为 PyQt5 版本。

## 主要功能

### 1. 日志过滤 (LogFilterProcessor)

#### 核心功能
- ✅ 实时日志过滤（通过 adb logcat）
- ✅ 正则表达式支持
- ✅ 区分大小写选项
- ✅ 关键字彩色高亮
- ✅ 自适应性能优化
- ✅ 自动重连机制
- ✅ 性能监控和统计

#### 自适应性能优化
- **基础批次大小**: 50 行
- **最大批次大小**: 200 行
- **高负荷阈值**: 100 行（启用采样模式）
- **中等负荷阈值**: 50 行
- **最大显示行数**: 5000 行（可配置）
- **裁剪阈值**: 250 行（5%）

#### 特殊过滤模式
- **简单过滤**: 用于 TMO CC 的简化关键字过滤
- **完全过滤**: 用于 TMO CC 的完整关键字过滤
- **加载关键字文件**: 从文件加载过滤关键字

### 2. 搜索功能 (SearchManager)

#### 核心功能
- ✅ 全文搜索
- ✅ 正则表达式支持
- ✅ 区分大小写选项
- ✅ 下一个/上一个导航
- ✅ 显示所有搜索结果
- ✅ 搜索结果高亮
- ✅ 复制和保存搜索结果

#### 搜索对话框
- 支持快捷键：Enter 搜索、Escape 关闭
- 实时状态显示
- 循环导航（到达末尾自动回到开头）

#### 搜索结果窗口
- 显示所有匹配行（带行号）
- 关键字高亮显示
- 全选、复制、保存功能
- 支持快捷键操作

## 使用方法

### 基本使用

```python
from core.log_processor import PyQtLogProcessor
from core.search_manager import PyQtSearchManager
from core.device_manager import DeviceManager

# 1. 初始化管理器
device_manager = DeviceManager()
log_processor = PyQtLogProcessor(device_manager)
search_manager = PyQtSearchManager(log_viewer)

# 2. 连接信号
log_processor.log_received.connect(log_viewer.append_log)
log_processor.status_message.connect(status_bar.setText)
log_processor.performance_update.connect(performance_label.setText)

# 3. 开始过滤
log_processor.start_filtering(
    keyword="your_keyword",
    use_regex=True,
    case_sensitive=False,
    color_highlight=True
)

# 4. 显示搜索对话框
search_manager.show_search_dialog()

# 5. 停止过滤
log_processor.stop_filtering()
```

### 在 UI 中集成

```python
# 在 MainWindow 中
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化管理器
        self.device_manager = DeviceManager()
        self.log_processor = PyQtLogProcessor(self.device_manager)
        self.search_manager = PyQtSearchManager(self.log_viewer)
        
        # 连接信号
        self.log_processor.log_received.connect(self.log_viewer.append_log)
        self.log_processor.status_message.connect(self.status_bar.setText)
        self.log_processor.performance_update.connect(self.performance_label.setText)
        
        # 连接 UI 信号
        self.log_filter_tab.start_filtering.connect(
            lambda: self.log_processor.start_filtering(
                self.log_filter_tab.get_keyword(),
                self.log_filter_tab.is_use_regex(),
                self.log_filter_tab.is_case_sensitive(),
                self.log_filter_tab.is_color_highlight()
            )
        )
        
        self.log_filter_tab.stop_filtering.connect(
            self.log_processor.stop_filtering
        )
        
        # 搜索功能
        self.search_action.triggered.connect(
            self.search_manager.show_search_dialog
        )
```

## 性能优化特性

### 1. 自适应批次处理
- 根据队列大小自动调整批次大小
- 高负荷时启用采样模式（每3行取1行）
- 动态调整处理间隔

### 2. 高效行数裁剪
- 使用 trim_threshold 避免频繁操作
- 批量删除超出的行
- 维护行计数器

### 3. 性能监控
- 实时显示处理速率（行/秒）
- 队列大小监控
- 内存使用估算
- 批次大小和间隔显示

### 4. 缓存机制
- 内存使用缓存（每2秒更新一次）
- 减少重复计算

## 配置选项

### 最大显示行数
```python
# 通过对话框设置
log_processor.show_display_lines_dialog()

# 或直接设置
log_processor.adaptive_params['max_display_lines'] = 10000
log_processor.adaptive_params['trim_threshold'] = 500
```

### 自适应参数
```python
# 调整批次大小
log_processor.adaptive_params['base_batch_size'] = 100
log_processor.adaptive_params['max_batch_size'] = 300

# 调整阈值
log_processor.adaptive_params['high_load_threshold'] = 150
log_processor.adaptive_params['medium_load_threshold'] = 75
```

## 快捷键

### 搜索对话框
- `Enter`: 执行搜索
- `Escape`: 关闭对话框
- `Ctrl+F`: 打开搜索对话框（需要在主窗口绑定）

### 搜索结果窗口
- `Ctrl+A`: 全选
- `Ctrl+C`: 复制
- `Ctrl+S`: 保存

## 注意事项

1. **设备连接**: 确保设备已通过 adb 连接
2. **性能**: 大量日志时建议使用采样模式或增加 trim_threshold
3. **内存**: 建议设置合理的 max_display_lines
4. **正则表达式**: 复杂正则可能影响性能

## 故障排除

### 问题：日志过滤不工作
- 检查设备连接状态
- 确认 adb 命令可用
- 检查关键字是否正确

### 问题：性能问题
- 减少 max_display_lines
- 增加 trim_threshold
- 使用采样模式

### 问题：搜索无结果
- 检查关键字拼写
- 确认是否启用正则表达式
- 检查区分大小写选项

## 更新日志

### v1.0.0 (2024-01-XX)
- ✅ 完整的日志过滤功能
- ✅ 搜索和导航功能
- ✅ 自适应性能优化
- ✅ 性能监控和统计
- ✅ 自动重连机制
- ✅ 关键字高亮显示

## 参考

- 原 Tkinter 版本: `tkinter_backup/Log_Filter/log_processor.py`
- 原 Tkinter 版本: `tkinter_backup/Log_Filter/search_manager.py`
- PyQt5 版本: `core/log_processor.py`
- PyQt5 版本: `core/search_manager.py`

