# 手机测试辅助工具 (MobileTestTool)

<div align="center">

![Version](https://img.shields.io/badge/version-0.9-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

一个功能强大的Android设备测试和日志管理工具，基于PyQt5构建的现代化界面，支持实时日志过滤、MTKLOG管理、网络信息监控等多种功能。

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [使用指南](#-使用指南) • [项目结构](#️-项目结构) • [故障排除](#-故障排除)

</div>

---

## 🚀 快速开始

### 系统要求
- **操作系统**: Windows 10/11
- **Python版本**: Python 3.6+
- **Android SDK**: 需要安装adb命令并添加到系统PATH
- **推荐配置**: 4GB+ 内存，1GB+ 可用磁盘空间

### 安装运行

```bash
# 1. 克隆项目
git clone <repository-url>
cd MobileTestTool

# 2. 安装依赖
pip install -r requirements_pyqt.txt

# 3. 运行程序
python main.py
```

### 打包程序

```bash
# 使用批处理文件打包（推荐）
build_pyqt.bat

# 或手动打包
pyinstaller --clean MobileTestTool_pyqt.spec
```

打包后的程序会生成在 `dist/MobileTestTool_PyQt5/` 目录中。

---

## ✨ 功能特性

### 📱 设备管理
- **多设备支持**: 同时连接和管理多个Android设备
- **设备信息查询**: IMEI、ICCID、IMSI等设备信息一键获取
- **应用管理**: 应用安装、卸载、查询等操作
- **截图录制**: 支持设备截图和屏幕录制功能

### 📊 日志管理
- **实时日志过滤**: 支持正则表达式和关键字过滤，实时显示过滤结果
- **MTKLOG控制**: 完整的MTKLOG开启、停止、导出、删除功能
- **ADB Log管理**: 后台运行logcat，支持导出和分析
- **Google Log**: 支持Google日志的收集和管理
- **AEE Log**: 支持异常日志的收集
- **Bugreport**: 一键生成系统bugreport

### 🌐 网络测试
- **网络信息监控**: 实时显示蜂窝网络和WiFi信息
- **Telephony日志**: 启用和管理Telephony日志
- **TCPDump抓包**: 网络数据包捕获和分析
- **Ping测试**: 网络连通性测试

### 🏢 TMO专用功能
- **TMO CC配置**: CC文件的拉取、推送和管理
- **Echolocate**: Echolocate文件的收集和管理
- **背景数据配置**: 后台数据配置和日志分析
- **赫拉配置**: 赫拉测试相关配置管理

### 🎨 界面特性
- **双主题支持**: 暗色/亮色主题一键切换
- **现代化界面**: 基于PyQt5的美观界面设计
- **流畅动画**: 丰富的交互动画效果
- **分组卡片**: 功能模块化，操作清晰直观
- **多语言支持**: 中英文双语切换

### 🔧 自定义功能
- **🆕 自定义按钮**: 支持5种类型的自定义按钮（ADB命令、Python脚本、文件操作、运行程序、系统命令）
- **🆕 Tab管理**: 支持Tab拖拽排序、显示/隐藏、自定义Tab和Card
- **Python脚本执行**: 支持执行自定义Python代码，输出显示在日志区域
- **文件操作**: 快速打开PC文件或文件夹
- **系统命令**: 执行系统命令行指令
- **配置管理**: 支持配置导入导出和备份恢复

### 📡 SIM卡工具
- **🆕 SIM APDU解析器**: 专业的SIM卡APDU消息解析工具
  - 支持MTK原始日志、MTK表格格式和通用APDU文本格式
  - 自动识别和分类eSIM消息、CAT命令和普通SIM卡消息
  - 详细的TLV结构解析，图形化界面展示
  - 支持正则表达式搜索和过滤
  - 支持复制消息内容和解析结果
- **🆕 SIM卡读写工具**: 完整的SIM卡数据读写和管理工具
  - **GUI模式**: 通过主界面的SIM标签页启动，提供图形化操作界面
  - **CLI模式**: 支持命令行批量写入和PIN验证
  - **读取功能**: 读取SIM卡EF文件数据，支持多种EF类型（IMSI、ICCID、IMPI、IMPU等）
  - **写入功能**: 支持单条记录写入和批量JSON文件写入
  - **文件管理**: 支持EF文件的创建、删除和结构调整
  - **端口管理**: 智能端口选择，自动测试和连接
  - **多线程操作**: 后台线程执行，不阻塞UI
  - **错误处理**: 完整的错误提示和异常处理机制

---

## 📖 使用指南

### 设备连接
1. 连接Android设备并启用USB调试
2. 在工具栏选择设备（如连接多个设备）
3. 点击"刷新"按钮更新设备列表

### 日志过滤
1. 在"日志过滤"标签页输入关键字
2. 选择过滤选项（正则表达式、大小写敏感等）
3. 点击"开始过滤"按钮
4. 使用"保存日志"保存过滤结果

### MTKLOG操作
1. 在"日志控制"标签页找到MTKLOG控制区域
2. 点击"开启"按钮启动MTKLOG（会执行完整初始化序列）
3. 点击"停止&导出"按钮停止并导出日志
4. 使用"SD模式"/"USB模式"切换存储模式

### 网络监控
1. 在"网络信息"标签页
2. 点击"开始获取网络信息"
3. 实时查看蜂窝网络和WiFi信息

### 🆕 在线更新
1. 在工具栏点击右侧的“检查更新”按钮可手动检测新版本，工具会在背景线程中拉取 `latest.json` 并显示下载进度。
2. 首次使用前，请在“工具配置”对话框中填写版本描述 URL、可选的下载目录以及网络超时时间，支持下载完成后自动启动安装包。
3. 下载成功时会显示保存路径和 SHA-256 校验值，可选择自动打开安装包或在资源管理器中定位文件。

#### 版本描述 `latest.json` 示例
`config/latest.json.example` 提供了一个完整示例，可直接复制后按需修改：

```json
{
  "version": "0.9.4",
  "download_url": "https://example.com/releases/MobileTestTool_0.9.4.exe",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "file_name": "MobileTestTool_0.9.4.exe",
  "file_size": 123456789,
  "release_notes": "- 修复已知问题\n- 优化日志处理性能",
  "published_at": "2025-10-31T08:00:00Z",
  "mandatory": false
}
```

#### 发布流程建议
- 将最新安装包上传至可公开访问的静态存储（如对象存储、Nginx 静态站点、GitHub Releases）。
- 更新 `latest.json` 的 `version`、`download_url`、`sha256` 等字段并上传到同一静态位置。
- 推荐在发布流程中生成安装包的 SHA-256 校验值，填写至 `latest.json`，以便客户端完成完整性校验。
- 如需灰度或版本存档，可在静态目录中同时保留历史版本的 JSON 与安装包。

### 🆕 SIM APDU解析器
1. 在"SIM"标签页点击"启动 APDU 解析器"按钮
2. **加载数据**：
   - 点击"加载 MTK 原始日志"选择MTK日志文件
   - 或点击"加载 APDU 文本（每行）"选择APDU文本文件
3. **筛选和搜索**：
   - 使用"筛选类别"下拉菜单选择APDU类型
   - 在搜索框中输入正则表达式进行搜索
   - 勾选"搜索右侧详情"可在解析结果中搜索
4. **查看详情**：点击左侧列表查看详细解析结果
5. **复制功能**：右键点击项目可复制内容

详细功能说明请参考 [SIM_APDU_Parser/README.md](SIM_APDU_Parser/README.md)

### 🆕 SIM卡读写工具

#### GUI模式使用
1. 在"SIM"标签页点击"启动 SIM 卡读写工具"按钮
2. **选择端口**：
   - 从下拉框选择串口（默认不自动选择）
   - 选择端口后自动测试和连接
   - 连接成功后可开始操作
3. **读取数据**：
   - 在左侧文件树中选择EF文件
   - 点击"Read"按钮读取数据
   - 数据会显示在表格中
4. **写入数据**：
   - 在表格中编辑数据
   - 点击"Update"按钮写入修改
5. **批量操作**：
   - 点击"Load JSON"加载JSON文件
   - 支持批量读取和写入多个EF文件
6. **PIN管理**：
   - 在"PINs管理"标签页输入PIN码
   - 点击"Verify"验证PIN码

#### CLI模式使用
支持命令行批量写入和PIN验证：

```bash
# 查看帮助
python main.py --help

# 验证PIN并批量写入
python main.py -p 55555555 -w data.json

# 仅验证PIN
python main.py -p 55555555

# 仅批量写入（需要先验证PIN）
python main.py -w data.json
```

**JSON格式**：
```json
{
  "EF_list": [
    {
      "ef_id": "6F07",
      "adf_type": "USIM",
      "records": [
        {
          "field1": "value1",
          "field2": "value2"
        }
      ]
    }
  ]
}
```

### 🆕 Tab管理功能

**支持Tab拖拽排序、显示/隐藏、自定义Tab和Card！**

#### 基本操作
1. **拖拽排序**: 直接拖拽Tab标题即可调整顺序
2. **隐藏Tab**: 
   - 切换到"其他"标签页
   - 点击"📋 Tab管理"按钮
   - 在"Tab排序和显示"中取消勾选不需要的Tab
   - 点击"保存"

#### 高级功能
1. **创建自定义Tab**:
   - 打开Tab管理对话框
   - 切换到"自定义Tab"标签页
   - 点击"添加Tab"
   - 填写Tab信息并保存

2. **创建自定义Card**:
   - 在Tab管理对话框中切换到"自定义Card"标签页
   - 点击"添加Card"
   - 选择所属Tab并填写Card信息
   - 保存配置

#### 详细文档
- [Tab管理功能完整指南.md](Tab管理功能完整指南.md) - 完整功能指南和问题修复记录

### 🆕 自定义按钮功能

#### 快速配置
1. 切换到"其他"标签页
2. 点击"🔧 管理自定义按钮"（绿色按钮）
3. 点击"➕ 添加"按钮
4. 填写按钮信息：
   - **按钮名称**: 显示在界面上的文字
   - **按钮类型**: 选择操作类型
   - **命令/路径**: 根据类型填写相应内容
   - **所在Tab**: 选择按钮显示在哪个标签页
   - **所在卡片**: 选择按钮显示在哪个功能卡片
   - **描述**: 按钮功能说明
5. 点击"保存"，按钮立即生效

#### 支持的类型
- **📱 ADB命令**: `reboot`、`shell getprop ro.product.model`
- **🐍 Python脚本**: 执行自定义Python代码，输出显示在日志区域
- **📁 打开文件**: 快速打开PC文件或文件夹
- **🖥️ 运行程序**: 启动PC上的程序
- **💻 系统命令**: 执行系统命令行指令

#### 配置管理
- **📤 导出**: 保存配置到文件
- **📥 导入**: 从文件加载配置

#### 详细文档
- [自定义按钮功能完整指南.md](自定义按钮功能完整指南.md) - 完整功能指南
- [Tab管理功能完整指南.md](Tab管理功能完整指南.md) - Tab管理功能
- [Python脚本功能使用指南.md](Python脚本功能使用指南.md) - Python脚本
- [MTKlogger_Debug_使用说明.md](MTKlogger_Debug_使用说明.md) - 调试说明

---

## 🏗️ 项目结构

```
MobileTestTool/
├── main.py                    # 程序入口
├── requirements_pyqt.txt      # Python依赖
├── build_pyqt.bat            # 打包脚本
├── MobileTestTool_pyqt.spec  # PyInstaller配置
├── translations.json         # 多语言翻译文件
├── config/                   # 配置文件
│   └── language.conf         # 语言配置
│
├── core/                     # 核心管理器
│   ├── device_manager.py        # 设备管理
│   ├── mtklog_manager.py        # MTKLOG管理
│   ├── adblog_manager.py        # ADB Log管理
│   ├── log_processor.py         # 日志过滤处理
│   ├── network_info_manager.py  # 网络信息管理
│   ├── screenshot_manager.py    # 截图管理
│   ├── video_manager.py         # 录制管理
│   ├── theme_manager.py         # 主题管理
│   ├── language_manager.py      # 语言管理
│   ├── custom_button_manager.py # 自定义按钮管理
│   ├── tab_config_manager.py    # Tab配置管理
│   └── ...                      # 其他管理器
│
├── ui/                       # 界面组件
│   ├── main_window.py           # 主窗口
│   ├── toolbar.py               # 工具栏
│   ├── menu_bar.py              # 菜单栏
│   ├── custom_button_dialog.py  # 自定义按钮配置对话框
│   ├── tab_manager_dialog.py    # Tab管理对话框
│   ├── unified_manager_dialog.py # 统一管理对话框
│   ├── tabs/                    # 功能标签页
│   │   ├── log_control_tab.py
│   │   ├── log_filter_tab.py
│   │   ├── network_info_tab.py
│   │   └── ...
│   ├── widgets/                 # 自定义控件
│   │   └── log_viewer.py        # 日志查看器
│   └── resources/               # 资源文件
│       ├── icons/               # 图标
│       └── themes/              # 主题样式
│
├── Network_info/             # 网络信息解析模块
│   ├── telephony_parser.py     # 电话信息解析
│   └── utilities_wifi_info.py  # WiFi信息解析
│
├── SIM_APDU_Parser/         # SIM APDU解析器模块
│   ├── main.py                 # 独立运行入口
│   ├── README.md               # 详细功能说明
│   ├── app/                    # 应用层
│   ├── core/                   # 核心模块
│   ├── parsers/                # 消息解析器
│   └── ...
│
├── sim_reader/              # SIM卡读写工具模块
│   ├── main.py                 # 独立运行入口
│   ├── cli.py                  # CLI命令行接口
│   ├── ui.py                   # GUI界面
│   ├── core/                   # 核心功能
│   │   ├── serial_comm.py      # 串口通信
│   │   ├── sim_service.py      # SIM服务
│   │   └── ...
│   ├── parsers/                # EF数据解析器
│   └── ...
│
├── tools/                    # 工具脚本
│   └── audit_translations.py   # 翻译审计工具
│
└── resources/                # 应用资源
    └── apk/                     # APK文件
        ├── app-uiautomator.apk
        └── Heratest-trigger-com.example.test.apk
```

---

## 📁 文件存储

所有生成的文件都统一存储在 `c:\log\yyyymmdd\` 目录下，按功能模块分类：

```
c:\log\20241016\
├── screenshot\          # 截图文件
├── video\              # 视频文件
├── log_xxx\            # MTKLOG日志
├── tcpdump\            # TCPDump抓包文件
├── logcat\             # ADB日志文件
└── ccfile\             # TMO CC文件
```

---

## ⚙️ 配置说明

### Android SDK配置
确保adb命令已添加到系统PATH环境变量：

```bash
# 测试adb是否可用
adb version
```

### USB调试
在Android设备上启用USB调试：
1. 设置 → 关于手机 → 连续点击"版本号"7次
2. 设置 → 开发者选项 → 启用"USB调试"

### 多语言配置
- 支持中英文双语切换
- 语言偏好自动保存
- 翻译文件：`translations.json`
- 配置文件：`config/language.conf`

---

## 🔧 故障排除

### 常见问题

**问题1：未找到adb命令**
- 确保Android SDK已正确安装
- 将adb路径添加到系统PATH环境变量

**问题2：设备未连接**
- 检查USB连接
- 确保已启用USB调试
- 运行 `adb devices` 检查设备状态

**问题3：MTKLOG操作失败**
- 确保设备支持MTKLOG服务
- 检查设备权限设置
- 尝试重新连接设备

**问题4：文件保存失败**
- 检查 `c:\log\` 目录权限
- 确保有足够的磁盘空间

**问题5：自定义按钮不工作**
- 检查命令语法是否正确
- 确保ADB命令路径正确
- 查看日志区域的错误信息

**问题6：Tab管理功能异常**
- 检查配置文件权限
- 尝试重置Tab配置
- 查看Tab管理功能完整指南中的问题修复记录

**问题7：Python脚本执行失败**
- 检查脚本语法是否正确
- 确认使用的模块是否在允许列表中
- 查看日志区域的错误信息

**问题8：SIM卡读写工具端口连接失败**
- 确认设备已连接并正确识别
- 检查端口是否被其他程序占用
- 确认设备驱动已正确安装
- 尝试手动点击"Reconnect Port"按钮重新连接

**问题9：SIM卡操作权限不足**
- 确保已正确输入PIN码（测试SIM通常为55555555或11111111）
- 某些EF文件可能需要管理员权限（ADM）
- 查看错误提示中的状态码说明

### 调试模式
如需调试，可参考 [MTKlogger_Debug_使用说明.md](MTKlogger_Debug_使用说明.md)

---

## 📝 更新日志

### v0.9.3 (当前版本)
- 🔧 **修复打包问题**: 修复SIM Reader在EXE环境下的模块导入问题
  - 修复 `pyserial` 模块打包问题，添加自定义hook确保正确包含
  - 修复 `concurrent.futures` 模块缺失问题
  - 隐藏控制台窗口，解决EXE运行时黑色控制台闪烁问题
- ✨ **改进端口管理**: 
  - 将"Reconnect Port"改为"Refresh Port"，仅刷新端口列表，不自动连接
  - 优化端口刷新功能和用户提示

### v0.10
- 🆕 **SIM卡工具集成**: 集成SIM APDU解析器和SIM卡读写工具
  - **SIM APDU解析器**: 专业的SIM卡APDU消息解析工具
    - 支持MTK原始日志、MTK表格格式和通用APDU文本格式
    - 自动识别和分类eSIM消息、CAT命令和普通SIM卡消息
    - 详细的TLV结构解析，图形化界面展示
  - **SIM卡读写工具**: 完整的SIM卡数据读写和管理工具
    - GUI模式：通过主界面启动，提供图形化操作界面
    - CLI模式：支持命令行批量写入和PIN验证
    - 智能端口管理：默认不自动选择端口，用户选择后自动测试和连接
    - 支持EF文件的读取、写入、创建、删除等完整操作
    - 多线程操作，完整的错误处理机制
- 🧹 **代码优化和清理**:
  - 清理了重复的文件（如重复的JSON文件）
  - 优化了模块导入和路径管理
  - 改进了错误处理和日志记录

### v0.9
- 🆕 **Tab管理功能**: 完整的Tab管理解决方案
  - Tab拖拽排序功能
  - Tab显示/隐藏控制
  - 自定义Tab和Card创建
  - 配置自动保存和恢复
  - 修复了所有已知的Tab相关问题
- 🆕 **自定义按钮功能**: 支持多种类型的自定义按钮
  - 可视化配置界面
  - 支持5种按钮类型：ADB命令、Python脚本、打开文件、运行程序、系统命令
  - 灵活的位置选择（任意Tab和卡片）
  - 命令安全验证和执行
  - 支持配置导入导出和备份恢复
  - 动态加载，无需重启
- 📖 **文档整合优化**: 整合了所有功能文档
  - 创建了完整的功能指南
  - 删除了重复的文档文件
  - 优化了文档结构和可读性
- 🧹 **代码清理**: 清理了项目中的临时文件和开发工具
  - 删除了未使用的测试文件
  - 删除了重复的文档文件
  - 优化了项目结构

### v0.8
- 🆕 **自定义按钮功能**: 支持多种类型的自定义按钮
  - 可视化配置界面
  - 支持5种按钮类型：ADB命令、Python脚本、打开文件、运行程序、系统命令
  - 灵活的位置选择（任意Tab和卡片）
  - 命令安全验证和执行
  - 支持配置导入导出
  - 动态加载，无需重启
- 📖 新增详细的功能说明文档
- 🧹 清理了项目中的临时文件和开发工具

### v0.7
- ✨ 完成PyQt5重构，提供现代化UI
- 🎨 新增双主题支持（暗色/亮色）
- 🌐 新增多语言支持（中英文切换）
- 🚀 模块化架构，代码结构更清晰
- 💡 所有核心功能完整实现
- 📦 完整的打包配置

### v0.6
- ✨ 新增多设备支持
- ✨ 新增性能监控和优化
- ✨ 新增截图和录制功能
- ✨ 统一文件存储路径格式

---

## 📄 许可证

本项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发规范
- 遵循PEP 8代码风格
- 添加适当的注释和文档
- 确保新功能有对应的测试
- 更新相关文档

---

## 📞 技术支持

如遇到问题：
1. 查看上方的"故障排除"部分
2. 搜索现有的Issues
3. 创建新的Issue描述问题

### 联系方式
- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 文档Wiki: [项目Wiki](https://github.com/your-repo/wiki)

---

<div align="center">

**注意**: 本工具仅用于合法的测试和开发目的。请确保您有权限对目标设备进行操作。

Made with ❤️ by MobileTestTool Team

</div>