# MTKlogger exe环境兼容性修复说明

## 问题描述

1. **PyInstaller兼容性问题**：在打包成exe后出现以下错误：
   ```
   AttributeError: 'NoneType' object has no attribute 'buffer'
   ```

2. **MTKlogger停止问题**：在exe环境下无法正常停止MTKlogger，但在Python运行时没问题

## 解决方案

### 1. 修复了main.py中的PyInstaller兼容性问题

**问题原因：**
- 在PyInstaller打包环境中，`sys.stdout.buffer`和`sys.stderr.buffer`可能为`None`
- 直接访问这些属性会导致`AttributeError`

**修复方法：**
- 添加了PyInstaller环境检测函数
- 只在非PyInstaller环境中重新配置标准输出流
- 添加了异常处理，确保程序不会因为输出流配置失败而崩溃

### 2. 修复了exe环境下的MTKlogger兼容性问题

**问题分析：**
- 在exe环境下，UIAutomator2可能无法正常工作
- UI状态检查失败导致MTKlogger无法停止

**解决方案：**
- 添加了PyInstaller环境检测
- 在exe环境下优先尝试使用UIAutomator2
- 如果UIAutomator2失败，使用简化的停止逻辑
- 直接执行ADB停止命令并等待固定时间

### 3. 优化了TMO CC和Echolocate模块的exe兼容性

**TMO CC模块：**
- 使用原生`uiautomator`命令进行UI自动化
- 添加了详细的debug日志输出
- 在exe环境下能正常工作

**Echolocate模块：**
- 添加了exe环境检测支持
- 确保在exe环境下能正常导入和使用

**Hera模块：**
- 使用UIAutomator2进行UI自动化操作
- 添加了详细的debug日志输出
- 在exe环境下设置特殊的环境变量
- 支持APK文件的自动安装和配置

### 4. 修复了UIAutomator2在exe环境下的资源文件问题

**问题分析：**
- 错误：`Resource assets/u2.jar not found in uiautomator2 package.`
- 原因：PyInstaller没有自动包含uiautomator2的资源文件

**解决方案：**
- 创建了专门的hook文件`hook-uiautomator2.py`
- 在spec文件中添加了uiautomator2的assets目录
- 确保`u2.jar`等关键资源文件被正确打包
- 动态检测可用的uiautomator2子模块，避免打包警告
- 只包含确实存在的依赖模块（requests、urllib3、websocket、lxml）

### 5. 修复了exe环境下翻译文件失效的问题

**问题分析：**
- 翻译文件`translations.json`和配置文件`config/language.conf`没有被打包到exe中
- 语言管理器使用相对路径加载文件，在exe环境中路径不正确

**解决方案：**
- 在spec文件中添加了翻译文件和配置文件到打包配置
- 修改了语言管理器，支持exe环境下的文件路径获取
- 在exe环境下，配置文件保存到用户目录而不是程序目录

### 3. 优化了打包配置

#### 标准版本 (build.bat)
- 使用 `MobileTestTool.spec`
- 禁用控制台窗口（`console=False`）
- 适合日常使用和分发

## 使用方法

### 1. 打包程序

```bash
# 标准版本（推荐）
build.bat
```

### 2. 运行程序

1. 运行生成的exe文件
2. 连接手机设备
3. 尝试停止MTKlogger操作
4. 程序会自动检测运行环境并选择合适的处理方式

### 3. 环境兼容性说明

**Python环境（开发/调试）：**
- 使用完整的UIAutomator2 UI检查逻辑
- 实时验证MTKlogger按钮状态
- 提供详细的debug日志输出

**exe环境（生产/分发）：**
- 使用简化的停止逻辑
- 假设MTKlogger正在运行，直接执行停止命令
- 跳过UI状态验证，避免UIAutomator2兼容性问题
- 等待固定时间后继续执行

## 注意事项

1. **环境检测**：程序会自动检测是否在exe环境中运行
2. **兼容性**：exe环境下使用简化的停止逻辑，确保稳定性
3. **无控制台**：标准版本不显示控制台窗口，适合用户使用
4. **ADB依赖**：确保ADB工具可用且设备连接正常

## 故障排除

如果仍然遇到问题：

1. **检查ADB连接**：
   - 确保手机USB调试已启用
   - 检查ADB设备列表：`adb devices`
   - 确保设备显示为"device"状态

2. **检查MTKlogger应用**：
   - 确保MTKlogger应用已正确安装
   - 尝试手动启动MTKlogger应用
   - 检查应用权限设置

3. **重启设备**：
   - 重启手机
   - 重新连接USB
   - 重新运行程序

## 技术细节

### 环境检测逻辑
```python
def is_pyinstaller():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
```

### exe环境处理
- 跳过UIAutomator2 UI检查
- 假设logger正在运行
- 直接执行ADB停止命令
- 等待5秒后继续

### Python环境处理
- 使用UIAutomator2检查UI状态
- 实时验证按钮状态
- 提供详细的debug日志

## 版本信息

- 修复日期：2025-10-20
- 修复内容：PyInstaller兼容性 + exe环境MTKlogger兼容性
- 测试环境：Windows 10/11 + Python 3.12 + PyQt5
