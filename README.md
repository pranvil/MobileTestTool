# 手机测试辅助工具 (MobileTestTool)

一个功能强大的Android设备测试和日志管理工具，支持实时日志过滤、MTKLOG管理、网络信息监控等多种功能。

## 🚀 主要特性

### 日志管理
- **实时日志过滤**：支持正则表达式和关键字过滤，实时显示过滤结果
- **MTKLOG控制**：完整的MTKLOG开启、停止、导出、删除功能
- **ADB Log管理**：后台运行logcat，支持导出和分析
- **Google Log**：支持Google日志的收集和管理
- **AEE Log**：支持异常日志的收集
- **Bugreport**：一键生成系统bugreport

### 网络测试
- **网络信息监控**：实时显示蜂窝网络和WiFi信息
- **Telephony日志**：启用和管理Telephony日志
- **TCPDump抓包**：网络数据包捕获和分析
- **Ping测试**：网络连通性测试

### 设备操作
- **多设备支持**：支持同时连接多个Android设备
- **截图录制**：支持设备截图和屏幕录制
- **设备信息查询**：IMEI、ICCID、IMSI等设备信息
- **应用管理**：应用安装、卸载、查询等操作

### TMO专用功能
- **TMO CC配置**：CC文件的拉取、推送和管理
- **Echolocate**：Echolocate文件的收集和管理
- **背景数据配置**：后台数据配置和日志分析
- **赫拉配置**：赫拉测试相关配置管理

### UI特性
- **双主题支持**：暗色/亮色主题一键切换
- **现代化界面**：基于PyQt5的美观界面
- **流畅动画**：丰富的交互动画效果
- **分组卡片**：功能模块化，操作清晰直观
- **🆕 自定义按钮**：用户可自行添加ADB命令按钮，无需修改代码

## 📋 系统要求

- **操作系统**：Windows 10/11
- **Python版本**：Python 3.6+
- **Android SDK**：需要安装adb命令并添加到系统PATH
- **推荐配置**：4GB+ 内存，1GB+ 可用磁盘空间

## 📦 安装使用

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd MobileTestTool

# 安装Python依赖
pip install -r requirements_pyqt.txt
```

### 2. 运行程序

```bash
# 直接运行
python main.py
```

### 3. 打包程序

```bash
# 使用批处理文件打包（Windows）
build_pyqt.bat

# 手动打包
pyinstaller --clean MobileTestTool_pyqt.spec
```

打包后的程序会生成在`dist/MobileTestTool_PyQt5/`目录中。

## 🎯 使用说明

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

### 🆕 自定义按钮（新功能）

**打包成EXE后用户可自行添加ADB命令按钮！**

1. 切换到"其他"标签页
2. 点击"🔧 管理自定义按钮"（绿色按钮）
3. 点击"➕ 添加"按钮
4. 填写按钮信息：
   - **按钮名称**：显示在界面上的文字
   - **ADB命令**：要执行的命令（如：`shell getprop`）
   - **所在Tab**：选择按钮显示在哪个标签页
   - **所在卡片**：选择按钮显示在哪个功能卡片
   - **描述**：按钮功能说明
5. 点击"保存"，按钮立即生效

**示例命令：**
- `reboot` - 重启设备
- `shell getprop ro.product.model` - 查看设备型号
- `shell pm clear com.android.chrome` - 清除Chrome缓存

**配置管理：**
- 📤 **导出**：保存配置到文件
- 📥 **导入**：从文件加载配置

**详细说明**：
- 功能使用：[自定义按钮功能说明.md](自定义按钮功能说明.md)
- 升级迁移：[自定义按钮配置迁移指南.md](自定义按钮配置迁移指南.md)

## 🏗️ 项目结构

```
MobileTestTool/
├── main.py                    # 程序入口
├── requirements_pyqt.txt      # Python依赖
├── build_pyqt.bat            # 打包脚本
├── MobileTestTool_pyqt.spec  # PyInstaller配置
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
│   ├── custom_button_manager.py # 🆕 自定义按钮管理
│   └── ...                      # 其他管理器
│
├── ui/                       # 界面组件
│   ├── main_window.py           # 主窗口
│   ├── toolbar.py               # 工具栏
│   ├── menu_bar.py              # 菜单栏
│   ├── custom_button_dialog.py  # 🆕 自定义按钮配置对话框
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
└── resources/                # 应用资源
    └── apk/                     # APK文件
        ├── app-uiautomator.apk
        └── Heratest-trigger-com.example.test.apk
```

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

## 📝 更新日志

### v0.8 (当前版本)
- 🆕 **自定义按钮功能**：打包后用户可自行添加ADB命令按钮
  - 可视化配置界面
  - 灵活的位置选择（任意Tab和卡片）
  - 命令安全验证
  - 支持配置导入导出
  - **配置备份和恢复**（升级时保留用户配置）
  - 动态加载，无需重启
- 📖 新增《自定义按钮功能说明.md》文档
- 📖 新增《自定义按钮配置迁移指南.md》文档

### v0.7
- ✨ 完成PyQt5重构，提供现代化UI
- 🎨 新增双主题支持（暗色/亮色）
- 🚀 模块化架构，代码结构更清晰
- 💡 所有核心功能完整实现
- 📦 完整的打包配置
- 🧹 清理旧代码和文档

### v0.6
- ✨ 新增多设备支持
- ✨ 新增性能监控和优化
- ✨ 新增截图和录制功能
- ✨ 统一文件存储路径格式

## 📄 许可证

本项目采用MIT许可证。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📞 技术支持

如遇到问题：
1. 查看上方的"故障排除"部分
2. 搜索现有的Issues
3. 创建新的Issue描述问题

---

**注意**：本工具仅用于合法的测试和开发目的。请确保您有权限对目标设备进行操作。
