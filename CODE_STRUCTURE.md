# 代码结构重构说明

## 重构目标
按照功能分模块，提高代码的可维护性和可扩展性。

## 新的目录结构

```
adb_filter_key_words/
├── Device_Control/           # 设备控制模块
│   ├── __init__.py
│   ├── device_manager.py     # 设备管理
│   ├── mtklog_manager.py     # MTKLOG管理
│   ├── screenshot_manager.py  # 截图管理
│   └── video_manager.py      # 录制管理
├── Log_Filter/               # 日志过滤模块
│   ├── __init__.py
│   ├── log_processor.py      # 日志处理
│   ├── search_manager.py     # 搜索管理
│   └── adblog_manager.py     # ADB Log管理
├── TMO_CC/                   # TMO CC模块
│   ├── __init__.py
│   └── pull_cc.py           # 拉CC文件功能
├── main.py                   # 主程序入口
├── ui_manager.py            # UI管理
└── ...                      # 其他文件
```

## 功能模块划分

### Tab 1: 设备控制 (Device_Control)
- **设备管理**: 设备选择、刷新、连接检查
- **MTKLOG**: 开启、停止&导出、删除、SD模式、USB模式
- **截图**: 设备截图功能
- **录制**: 屏幕录制功能

### Tab 2: 日志过滤 (Log_Filter)
- **关键字过滤**: 正则表达式、区分大小写、彩色高亮
- **ADB Log**: 开启、导出
- **日志处理**: 开始过滤/停止过滤、清空日志、清除缓存、设置行数、保存日志
- **搜索功能**: 搜索对话框、查找下一个/上一个、显示所有结果

### Tab 3: TMO CC (TMO_CC)
- **推CC文件**: 待实现
- **拉CC文件**: 已实现，包含完整的ADB操作流程
- **简单过滤**: 待实现
- **完全过滤**: 待实现
- **PROD服务器**: 待实现
- **STG服务器**: 待实现

## 主要改进

1. **模块化设计**: 按功能划分模块，每个模块职责单一
2. **代码复用**: 通过模块导入实现代码复用
3. **易于维护**: 功能模块独立，便于维护和扩展
4. **清晰结构**: 目录结构清晰，便于理解项目架构

## 导入关系

```python
# main.py
from Device_Control import DeviceManager, MTKLogManager, ScreenshotManager, VideoManager
from Log_Filter import LogProcessor, SearchManager, ADBLogManager
from TMO_CC import PullCCManager
from ui_manager import UIManager
```

## 使用方式

重构后的代码保持了原有的功能不变，只是将代码按功能模块重新组织。用户界面和操作方式完全一致，但代码结构更加清晰和易于维护。
