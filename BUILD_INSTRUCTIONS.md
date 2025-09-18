# ADB Logcat 过滤工具 - 打包说明

## 快速打包

### 方法1：使用简单脚本（推荐）
```bash
# 双击运行
build_simple.bat
```

### 方法2：使用高级脚本
```bash
# 双击运行
build_advanced.bat
```

### 方法3：onedir模式打包
```bash
# 双击运行
build_onedir_simple.bat
```

### 方法4：手动打包
```bash
# 1. 安装PyInstaller
pip install pyinstaller

# 2. 执行打包命令
pyinstaller --onefile --windowed --name "ADB_Logcat_Filter" main.py
```

## 打包选项说明

### 基本选项
- `--onefile`: 打包成单个EXE文件
- `--onedir`: 打包成目录模式（推荐）
- `--windowed`: 不显示控制台窗口（GUI模式）
- `--name`: 指定输出文件名

### 打包模式对比

#### onefile模式
- **优点**: 单个文件，便于分发
- **缺点**: 启动较慢，文件较大
- **适用**: 需要单文件分发的场景

#### onedir模式
- **优点**: 启动快，文件结构清晰，便于调试
- **缺点**: 包含多个文件
- **适用**: 开发调试，需要快速启动的场景

### 高级选项
- `--add-data`: 添加额外文件到打包中
- `--hidden-import`: 显式导入隐藏的模块
- `--clean`: 清理临时文件

## 输出文件

### onefile模式
打包完成后，可执行文件位于：
```
dist/ADB_Logcat_Filter.exe
```

### onedir模式
打包完成后，可执行文件位于：
```
dist/ADB_Logcat_Filter/ADB_Logcat_Filter.exe
```

目录结构：
```
dist/ADB_Logcat_Filter/
├── ADB_Logcat_Filter.exe    # 主程序
├── _internal/               # 依赖文件
│   ├── python312.dll
│   ├── tkinter相关文件
│   └── 其他依赖文件
└── README.md               # 说明文档
```

## 文件大小优化

如果EXE文件过大，可以尝试以下优化：

1. **使用UPX压缩**（如果已安装UPX）：
```bash
pyinstaller --onefile --windowed --upx-dir="C:\upx" main.py
```

2. **排除不需要的模块**：
```bash
pyinstaller --onefile --windowed --exclude-module matplotlib --exclude-module numpy main.py
```

## 常见问题

### 1. 打包失败
- 确保Python环境正确
- 检查是否有语法错误
- 确保所有依赖已安装

### 2. EXE文件无法运行
- 检查是否缺少依赖
- 尝试在命令行运行查看错误信息
- 确保目标系统有必要的运行时库

### 3. 文件过大
- 使用虚拟环境减少依赖
- 排除不需要的模块
- 使用UPX压缩

## 系统要求

### 开发环境
- Python 3.6+
- PyInstaller 5.0+
- Windows 10/11

### 运行环境
- Windows 7/8/10/11
- Android SDK（需要adb命令）
- 无需安装Python

## 测试建议

1. 在干净的Windows系统上测试
2. 确保adb命令可用
3. 测试所有功能是否正常
4. 检查文件大小是否合理
