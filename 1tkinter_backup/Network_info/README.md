# Network_info 模块

## 概述
网络信息管理模块，负责获取和显示设备网络信息，支持CA/ENDC表格显示。

## 模块结构

### 核心模块
- `network_info_manager.py` - 主要的网络信息管理器（IO+UI）
- `telephony_parser.py` - 纯解析模块（≤220行）
- `utilities_ping.py` - 网络Ping测试工具
- `utilities_wifi_info.py` - WiFi信息解析工具

## 功能特性

### 蜂窝网络信息
- 支持LTE和NR载波解析
- 支持CA/ENDC组合显示
- 支持双SIM卡信息
- 支持IDLE状态信息显示

### WiFi信息
- WiFi连接状态检测
- 信号强度解析
- 频段识别（2.4GHz/5GHz/6GHz）

### Ping测试
- 网络连通性测试
- 实时状态显示
- 错误类型识别

## 使用方法

```python
from Network_info.network_info_manager import NetworkInfoManager

# 初始化管理器
manager = NetworkInfoManager(app_instance)

# 开始获取网络信息
manager.start_network_info()

# 开始Ping测试
manager.start_network_ping()
```

## 重构说明

本次重构按照`min_parser_refactor.json`规范实现：

1. **模块化设计**：将功能按类型分离到不同的工具模块
2. **纯解析模块**：`telephony_parser.py`实现≤220行的纯解析逻辑
3. **职责分离**：`network_info_manager.py`只负责IO+UI，调用纯解析模块
4. **保持兼容性**：对外接口保持不变，确保现有代码正常工作