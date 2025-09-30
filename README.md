# 手机log辅助工具 v0.5

一个功能强大的Android设备日志管理和MTKLOG操作工具，支持实时日志过滤、MTKLOG管理、ADB Log操作和多设备支持。

## 📋 目录

- [功能概述](#-功能概述)
- [代码结构](#-代码结构)
- [系统要求](#️-系统要求)
- [安装和使用](#-安装和使用)
- [使用说明](#-使用说明)
- [代码维护指南](#-代码维护指南)
- [故障排除](#-故障排除)
- [更新日志](#-更新日志)
- [许可证](#-许可证)

## 🚀 功能概述

### 📱 日志过滤
- 🎯 **关键字过滤**: 支持普通文本和正则表达式过滤
- 🔤 **大小写敏感**: 可选择是否区分大小写
- 🌈 **彩色高亮**: 关键字高亮显示，便于快速定位
- 📜 **实时滚动**: 支持鼠标滚轮滚动浏览日志
- 💾 **日志保存**: 可将过滤后的日志保存为txt文件
- 📋 **复制功能**: 支持选择和复制日志内容
- ⚡ **实时过滤**: 实时显示过滤结果，无需等待

### 🔧 MTKLOG管理
- ▶️ **开启MTKLOG**: 完整的4步初始化序列（停止→清除→设置缓存→开启）
- ⏹️ **停止&导出**: 合并功能，停止logger并自动导出到本地
- 🗑️ **删除MTKLOG**: 清除设备上的MTKLOG日志
- 📁 **导出MTKLOG**: 单独导出MTKLOG到指定目录
- 🔄 **模式切换**: SD模式/USB模式切换

### 📊 ADB Log操作
- ▶️ **开启ADB Log**: 后台运行logcat进程
- 📤 **导出ADB Log**: 停止logcat并导出日志文件

### 🖥️ 多设备支持
- 📱 **设备选择**: 支持多设备连接时的设备选择
- 🔄 **设备刷新**: 实时检测连接的设备
- 🎯 **设备指定**: 所有操作都支持指定设备执行

### 📈 性能优化
- 📊 **性能监控**: 实时显示队列长度、处理速率、批次大小等指标
- ⚡ **自适应处理**: 根据负载自动调整处理参数
- 🎯 **智能裁剪**: 自动管理显示行数，防止内存溢出
- 🔄 **动态设置**: 可动态调整最大显示行数

### 🎥 媒体功能
- 📸 **设备截图**: 支持Android设备截图并保存到本地
- 🎬 **屏幕录制**: 支持设备屏幕录制功能
- 📁 **统一存储**: 所有文件按日期和模块分类存储

### 🌐 网络功能
- 📡 **网络信息**: 获取设备网络状态和连接信息
- 🔍 **Echolocate**: 支持Echolocate文件拉取和管理
- 📊 **TCPDump**: 网络抓包功能

## 🏗️ 代码结构

### 目录结构
```
adb_filter_key_words/
├── main.py                          # 主程序入口
├── ui_manager.py                    # UI界面管理
├── requirements.txt                 # 依赖包列表
├── build_onedir.bat                # 打包脚本
├── MobileTestTool.spec             # PyInstaller配置
├── log_control/                 # log控制模块
│   ├── __init__.py
│   ├── device_manager.py           # 设备管理
│   ├── mtklog_manager.py           # MTKLOG管理
│   ├── screenshot_manager.py       # 截图管理
│   └── video_manager.py            # 录制管理
├── Log_Filter/                     # 日志过滤模块
│   ├── __init__.py
│   ├── log_processor.py            # 日志处理
│   ├── search_manager.py           # 搜索管理
│   ├── adblog_manager.py           # ADB Log管理
│   └── google_log.py               # Google日志处理
├── Device_Settings/                # 设备设置模块
│   ├── __init__.py
│   ├── device_settings_manager.py  # 设备设置管理
│   ├── hera_config_manager.py      # 赫拉配置管理
│   └── tcpdump_capture.py          # TCPDump抓包
├── Network_info/                   # 网络信息模块
│   ├── __init__.py
│   ├── network_info_manager.py     # 网络信息管理
│   ├── telephony_parser.py         # 电话解析器
│   ├── utilities_ping.py           # Ping工具
│   └── utilities_wifi_info.py      # WiFi信息工具
├── Background_Data/                # 后台数据模块
│   ├── __init__.py
│   ├── background_config_manager.py # 后台配置管理
│   └── log_analysis_manager.py     # 日志分析管理
├── Echolocate/                     # Echolocate模块
│   ├── __init__.py
│   └── echolocate_manager.py       # Echolocate管理
├── TMO_CC/                         # TMO CC模块
│   ├── __init__.py
│   ├── pull_cc.py                  # 拉CC文件
│   ├── push_cc.py                  # 推CC文件
│   └── server_manager.py           # 服务器管理
└── build/                          # 构建输出目录
    └── MobileTestTool/             # 打包后的可执行文件
```

### 模块功能划分

#### 1. log控制模块 (log_control)
- **device_manager.py**: 设备连接、验证、选择管理
- **mtklog_manager.py**: MTKLOG开启、停止、导出、删除操作
- **screenshot_manager.py**: 设备截图功能
- **video_manager.py**: 屏幕录制功能

#### 2. 日志过滤模块 (Log_Filter)
- **log_processor.py**: 日志过滤、处理、性能优化
- **search_manager.py**: 搜索对话框、关键字高亮
- **adblog_manager.py**: ADB Log开启、导出操作
- **google_log.py**: Google日志特殊处理

#### 3. 设备设置模块 (Device_Settings)
- **device_settings_manager.py**: 设备设置、工具配置
- **hera_config_manager.py**: 赫拉配置管理
- **tcpdump_capture.py**: 网络抓包功能

#### 4. 网络信息模块 (Network_info)
- **network_info_manager.py**: 网络信息获取和管理
- **telephony_parser.py**: 电话信息解析
- **utilities_ping.py**: Ping工具
- **utilities_wifi_info.py**: WiFi信息工具

#### 5. 后台数据模块 (Background_Data)
- **background_config_manager.py**: 后台数据配置和导出
- **log_analysis_manager.py**: 日志分析功能

#### 6. Echolocate模块 (Echolocate)
- **echolocate_manager.py**: Echolocate文件拉取和管理

#### 7. TMO CC模块 (TMO_CC)
- **pull_cc.py**: 拉取CC文件
- **push_cc.py**: 推送CC文件
- **server_manager.py**: 服务器管理

### 文件存储结构
所有文件按以下统一格式保存：
```
c:\log\yyyymmdd\
├── screenshot\          # 截图文件
├── video\              # 视频文件
├── log_{name}\         # MTKLOG日志
├── tcpdump\            # TCPDump抓包文件
├── logcat\             # ADB日志文件
├── ccfile\             # TMO CC文件
└── {custom_name}\      # 其他自定义文件
```

## 🛠️ 系统要求

- Python 3.6+
- Android SDK (需要adb命令)
- Windows/Linux/macOS
- 推荐内存: 4GB+
- 推荐存储: 1GB+ (用于日志文件存储)

## 📦 安装和使用

### 1. 环境准备
```bash
# 确保已安装Android SDK
# 下载并安装 Android SDK: https://developer.android.com/studio
# 将adb命令添加到系统PATH环境变量

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 运行程序
```bash
# 直接运行Python脚本
python main.py

# 或使用打包好的可执行文件
.\build\MobileTestTool\MobileTestTool.exe
```

### 3. 打包程序
```bash
# 使用批处理文件打包
.\build_onedir.bat
```

#### APK文件打包说明
程序会自动将以下APK文件打包到exe中：
- `Heratest-trigger-com.example.test.apk` - 赫拉测试APK
- `app-uiautomator.apk` - UI自动化APK
- `app-uiautomator-test.apk` - UI自动化测试APK

打包后的程序会：
1. **自动检查APK安装状态**：启动时检查是否已安装所需APK
2. **自动安装APK**：如果未安装，会从打包资源中提取并自动安装
3. **安装失败才提示**：只有在自动安装失败时才会提示用户手动安装

## 📖 使用说明

### 🎯 日志过滤
1. **连接设备**: 连接Android设备并启用USB调试
2. **选择设备**: 如果连接多个设备，从下拉框选择目标设备
3. **设置过滤**: 输入关键字，选择过滤选项
4. **开始过滤**: 点击"开始过滤"按钮
5. **保存日志**: 使用"保存日志"按钮保存过滤结果

### 🔧 MTKLOG操作
1. **开启MTKLOG**: 点击"开启"按钮，执行完整的初始化序列
2. **停止&导出**: 点击"停止&导出"按钮，停止logger并导出日志
3. **删除日志**: 点击"删除"按钮，清除设备上的MTKLOG
4. **模式切换**: 使用"SD模式"/"USB模式"按钮切换工作模式

### 📊 ADB Log操作
1. **开启ADB Log**: 点击"开启"按钮，启动后台logcat进程
2. **导出ADB Log**: 点击"导出"按钮，停止logcat并导出日志

### ⚙️ 高级设置
- **设置行数**: 动态调整最大显示行数（默认5000行）
- **性能监控**: 状态栏实时显示性能指标
- **设备管理**: 支持多设备连接和设备选择

## 🔧 代码维护指南

### 开发环境设置
```bash
# 1. 克隆项目
git clone <repository-url>
cd adb_filter_key_words

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行开发版本
python main.py
```

### 代码规范
1. **命名规范**:
   - 文件名使用小写字母和下划线
   - 类名使用大驼峰命名法 (PascalCase)
   - 函数和变量名使用小写字母和下划线 (snake_case)

2. **注释规范**:
   - 每个模块文件开头包含模块说明
   - 每个类包含类说明
   - 每个函数包含参数和返回值说明
   - 复杂逻辑添加行内注释

3. **代码结构**:
   - 每个模块职责单一
   - 避免循环导入
   - 使用类型提示 (Python 3.6+)

### 添加新功能
1. **确定模块归属**: 根据功能确定应该添加到哪个模块
2. **创建功能类**: 在对应模块中创建功能类
3. **实现核心逻辑**: 实现主要功能逻辑
4. **添加UI接口**: 在ui_manager.py中添加UI控件
5. **集成到主程序**: 在main.py中初始化新功能
6. **测试验证**: 确保功能正常工作

### 添加新模块功能详细指南

#### 1. 创建新模块目录和文件
```bash
# 创建模块目录
mkdir New_Module_Name

# 创建模块文件
touch New_Module_Name/__init__.py
touch New_Module_Name/feature_class.py
```

#### 2. 编写模块的 `__init__.py`
```python
# New_Module_Name/__init__.py
from .feature_class import FeatureClass

__all__ = ['FeatureClass']
```

#### 3. 编写功能类
```python
# New_Module_Name/feature_class.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能模块说明
"""

import tkinter as tk
from tkinter import messagebox
import os
from datetime import datetime

class FeatureClass:
    def __init__(self, app_instance):
        """
        初始化功能类
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
    
    def feature_method(self):
        """功能方法"""
        # 创建统一的日志目录路径 c:\log\yyyymmdd\module_name
        date_str = datetime.now().strftime("%Y%m%d")
        log_dir = f"c:\\log\\{date_str}\\module_name"
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 实现功能逻辑
        messagebox.showinfo("成功", f"功能执行完成！\n保存位置: {log_dir}")
```

#### 4. 修改 `main.py` 文件
```python
# main.py 需要修改的部分

# 1. 在导入部分添加新模块
from New_Module_Name import FeatureClass

class LogcatFilterApp:
    def __init__(self, root):
        # ... 现有代码 ...
        
        # 2. 在初始化部分添加新管理器
        self.feature_manager = FeatureClass(self)
        
        # ... 现有代码 ...
    
    # 3. 添加新模块的方法
    def execute_feature(self):
        """执行新功能"""
        self.feature_manager.feature_method()
```

#### 5. 修改 `ui_manager.py` 文件
```python
# ui_manager.py 需要修改的部分

class UIManager:
    def __init__(self, root, app_instance):
        # ... 现有代码 ...
        
        # 添加新模块的UI控件
        self.setup_new_module_ui()
    
    def setup_new_module_ui(self):
        """设置新模块UI"""
        # 在适当的位置添加新模块相关的UI控件
        new_module_frame = ttk.Frame(self.device_control_frame)
        new_module_frame.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(new_module_frame, text="新功能:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(new_module_frame, text="执行功能", 
                  command=self.app.execute_feature).pack(side=tk.LEFT)
```

#### 6. 更新文档
- 更新 `README.md` 中的代码结构部分
- 更新 `CODE_STRUCTURE.md` 文件
- 如需要，更新 `requirements.txt`（添加新依赖）

#### 7. 文件存储规范
所有新模块的文件保存都应遵循统一格式：
```python
# 创建统一的日志目录路径 c:\log\yyyymmdd\module_name
date_str = datetime.now().strftime("%Y%m%d")
log_dir = f"c:\\log\\{date_str}\\module_name"

if not os.path.exists(log_dir):
    os.makedirs(log_dir)
```

#### 8. 需要修改的文件清单
添加新模块功能需要修改的文件：

1. **创建新文件**:
   - `新模块目录/__init__.py`
   - `新模块目录/功能类.py`

2. **修改现有文件**:
   - `main.py` - 添加导入、初始化和方法
   - `ui_manager.py` - 添加UI控件
   - `README.md` - 更新文档
   - `CODE_STRUCTURE.md` - 更新结构说明

3. **可选修改**:
   - `requirements.txt` - 添加新依赖
   - `build_onedir.bat` - 如影响打包

### 实际示例：添加数据分析模块

以下是一个完整的示例，展示如何添加一个数据分析模块：

#### 步骤1: 创建模块文件
```bash
# 创建模块目录
mkdir Data_Analysis

# 创建模块文件
touch Data_Analysis/__init__.py
touch Data_Analysis/data_analyzer.py
touch Data_Analysis/statistics_manager.py
```

#### 步骤2: 编写 `Data_Analysis/__init__.py`
```python
from .data_analyzer import DataAnalyzer
from .statistics_manager import StatisticsManager

__all__ = ['DataAnalyzer', 'StatisticsManager']
```

#### 步骤3: 编写 `Data_Analysis/data_analyzer.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析模块
负责日志数据分析和统计
"""

import tkinter as tk
from tkinter import messagebox, ttk
import os
from datetime import datetime

class DataAnalyzer:
    def __init__(self, app_instance):
        self.app = app_instance
        self.device_manager = app_instance.device_manager
    
    def analyze_logs(self):
        """分析日志数据"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建统一的日志目录路径
        date_str = datetime.now().strftime("%Y%m%d")
        log_dir = f"c:\\log\\{date_str}\\data_analysis"
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 执行分析逻辑
        messagebox.showinfo("成功", f"日志分析完成！\n保存位置: {log_dir}")
```

#### 步骤4: 修改 `main.py`
```python
# 在导入部分添加
from Data_Analysis import DataAnalyzer, StatisticsManager

class LogcatFilterApp:
    def __init__(self, root):
        # ... 现有代码 ...
        
        # 添加新管理器
        self.data_analyzer = DataAnalyzer(self)
        self.statistics_manager = StatisticsManager(self)
        
        # ... 现有代码 ...
    
    # 添加新方法
    def analyze_logs(self):
        """分析日志数据"""
        self.data_analyzer.analyze_logs()
```

#### 步骤5: 修改 `ui_manager.py`
```python
# 在 setup_ui() 方法中添加
def setup_data_analysis_ui(self):
    """设置数据分析UI"""
    data_frame = ttk.Frame(self.device_control_frame)
    data_frame.pack(side=tk.LEFT, padx=(5, 0))
    
    ttk.Label(data_frame, text="数据分析:").pack(side=tk.LEFT, padx=(0, 5))
    ttk.Button(data_frame, text="分析日志", 
              command=self.app.analyze_logs).pack(side=tk.LEFT)
```

### 修改现有功能
1. **定位代码**: 根据功能找到对应的模块和文件
2. **理解现有逻辑**: 仔细阅读现有代码逻辑
3. **制定修改方案**: 确定最小化修改方案
4. **实施修改**: 按照方案进行修改
5. **测试验证**: 确保修改不影响其他功能

### 调试技巧
1. **日志输出**: 使用print()或logging模块输出调试信息
2. **断点调试**: 使用IDE的断点功能
3. **异常处理**: 添加try-catch块捕获异常
4. **性能监控**: 使用time模块测量执行时间

### 模块开发最佳实践

#### 1. 模块设计原则
- **单一职责**: 每个模块只负责一个功能领域
- **低耦合**: 模块间依赖最小化
- **高内聚**: 模块内部功能紧密相关
- **可扩展**: 便于添加新功能

#### 2. 代码组织规范
```python
# 模块文件结构示例
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块说明文档
"""

# 标准库导入
import os
import sys
from datetime import datetime

# 第三方库导入
import tkinter as tk
from tkinter import messagebox

# 本地模块导入
from .base_manager import BaseManager

class FeatureManager(BaseManager):
    """功能管理器类"""
    
    def __init__(self, app_instance):
        """初始化方法"""
        super().__init__(app_instance)
        # 初始化代码
    
    def public_method(self):
        """公共方法"""
        pass
    
    def _private_method(self):
        """私有方法"""
        pass
```

#### 3. 错误处理规范
```python
def safe_operation(self):
    """安全操作示例"""
    try:
        # 主要操作逻辑
        result = self.perform_operation()
        return result
    except FileNotFoundError as e:
        messagebox.showerror("文件错误", f"文件未找到: {str(e)}")
        return None
    except PermissionError as e:
        messagebox.showerror("权限错误", f"权限不足: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("未知错误", f"操作失败: {str(e)}")
        return None
```

#### 4. 文件路径处理规范
```python
def create_module_directory(self, module_name):
    """创建模块目录"""
    # 使用统一的路径格式
    date_str = datetime.now().strftime("%Y%m%d")
    base_dir = f"c:\\log\\{date_str}"
    module_dir = os.path.join(base_dir, module_name)
    
    # 确保目录存在
    os.makedirs(module_dir, exist_ok=True)
    return module_dir
```

#### 5. UI控件命名规范
```python
def setup_module_ui(self):
    """设置模块UI"""
    # 使用描述性的变量名
    module_frame = ttk.Frame(self.parent_frame)
    module_label = ttk.Label(module_frame, text="模块名称:")
    module_button = ttk.Button(module_frame, text="执行操作", 
                              command=self.app.module_method)
    
    # 保存控件引用以便后续使用
    self.module_frame = module_frame
    self.module_button = module_button
```

#### 6. 配置管理规范
```python
class ModuleConfig:
    """模块配置类"""
    
    def __init__(self):
        self.config_file = "module_config.json"
        self.default_config = {
            "setting1": "default_value",
            "setting2": True,
            "setting3": 100
        }
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
        return self.default_config.copy()
    
    def save_config(self, config):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
```

#### 7. 测试和验证
```python
def test_module_functionality(self):
    """测试模块功能"""
    # 测试正常情况
    assert self.module_method() is not None
    
    # 测试异常情况
    try:
        self.module_method_with_invalid_input()
        assert False, "应该抛出异常"
    except ValueError:
        pass  # 预期的异常
    
    print("模块功能测试通过")
```

#### 8. 文档更新检查清单
添加新模块后，确保更新以下文档：
- [ ] README.md - 代码结构部分
- [ ] CODE_STRUCTURE.md - 模块说明
- [ ] 模块内部文档字符串
- [ ] 函数和方法的注释
- [ ] 使用示例和说明

### 常见问题解决
1. **导入错误**: 检查模块路径和__init__.py文件
2. **UI更新问题**: 确保在UI线程中更新界面
3. **设备连接问题**: 检查adb命令和设备权限
4. **文件路径问题**: 使用os.path.join()构建路径

### 版本管理
1. **功能分支**: 新功能在独立分支开发
2. **提交信息**: 使用清晰的提交信息
3. **代码审查**: 重要修改需要代码审查
4. **版本标记**: 重要版本使用Git标签标记

## ⌨️ 快捷键

- **Ctrl+F**: 打开搜索对话框
- **F3**: 查找下一个匹配项
- **Shift+F3**: 查找上一个匹配项
- **Ctrl+Shift+L**: 显示主窗口
- **Escape**: 关闭搜索对话框
- **Enter**: 在关键字输入框中按Enter键快速开始过滤

## 🎛️ 界面布局

### 第一行（log控制）
```
[设备:] [设备下拉框] [刷新设备] [MTKLOG:] [开启] [停止&导出] [删除] [SD模式] [USB模式] [ADB Log:] [开启] [导出]
```

### 第二行（过滤控制）
```
[关键字:] [输入框] [正则表达式] [区分大小写] [彩色高亮] [开始过滤/停止过滤] [清空日志] [清除缓存] [设置行数] [保存日志]
```

## ⚠️ 注意事项

- 确保Android设备已连接并启用USB调试模式
- 程序会自动限制显示行数以保持性能（默认5000行）
- 保存的日志文件使用UTF-8编码
- MTKLOG操作需要设备支持相应的logger服务
- 多设备操作时请确保选择正确的目标设备
- 所有文件按日期和模块分类存储在 `c:\log\yyyymmdd\` 目录下

## 🔧 故障排除

### 常见问题

1. **"未找到adb命令"错误**
   - 确保Android SDK已正确安装
   - 将adb命令路径添加到系统PATH环境变量

2. **设备未连接**
   - 检查USB连接
   - 确保设备已启用USB调试
   - 运行 `adb devices` 命令检查设备连接状态

3. **MTKLOG操作失败**
   - 确保设备支持MTKLOG服务
   - 检查设备权限设置
   - 尝试重新连接设备

4. **性能问题**
   - 调整最大显示行数设置
   - 检查系统资源使用情况
   - 关闭不必要的后台程序

5. **文件保存失败**
   - 检查 `c:\log\` 目录权限
   - 确保有足够的磁盘空间
   - 检查文件路径长度限制

## 📝 更新日志

### v0.5 (当前版本)
- 🧹 代码清理和优化
- 🗑️ 删除重复的函数定义
- 🗑️ 删除未使用的测试文件
- 🗑️ 清理未使用的导入语句
- 🔧 简化日志分析管理器
- 📚 更新文档结构
- 🎯 提高代码可维护性

### v0.3
- ✨ 新增MTKLOG管理功能
- ✨ 新增ADB Log操作功能
- ✨ 新增多设备支持
- ✨ 新增性能监控和优化
- ✨ 新增动态设置功能
- ✨ 新增截图和录制功能
- ✨ 新增网络信息监控
- ✨ 新增Echolocate支持
- ✨ 新增TCPDump抓包功能
- ✨ 统一文件存储路径格式
- 🔧 优化用户界面布局
- 🔧 改进错误处理机制
- 🔧 统一确认弹框逻辑
- 🏗️ 重构为模块化架构
- 🔄 合并开始/停止过滤按钮
- 🎯 优化UI响应性和用户体验

### v1.0
- 🎯 基础日志过滤功能
- 🌈 关键字高亮显示
- 💾 日志保存功能
- ⌨️ 快捷键支持

## 📄 许可证

本项目采用MIT许可证。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看 [故障排除](#-故障排除) 部分
2. 搜索现有的 Issues
3. 创建新的 Issue 描述问题
4. 提供详细的错误信息和复现步骤

---

**注意**: 本工具仅用于合法的测试和开发目的。请确保您有权限对目标设备进行操作。