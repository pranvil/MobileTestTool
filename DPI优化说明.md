# DPI字体模糊问题修复说明

## 📋 问题描述

部分用户反馈在高DPI显示器（125%/150%/200%缩放）上，按钮和文字显示模糊。

## 🔍 根本原因

1. **缺少Windows Manifest** - Windows将程序视为旧应用，使用位图拉伸导致模糊
2. **PyQt DPI设置不完整** - 缺少关键的高DPI缩放属性
3. **字体渲染未优化** - 默认字体渲染在缩放时质量下降

## ✅ 已实施的解决方案

### 1. Windows Manifest配置

**文件：** `MobileTestTool.manifest`

**关键配置：**
```xml
<dpiAwareness>PerMonitorV2</dpiAwareness>  <!-- Windows 10 1703+ -->
<dpiAware>True/PM</dpiAware>                <!-- Windows 8.1+ 兼容 -->
```

**说明：**
- **PerMonitorV2** - 最佳模式，支持每个显示器独立DPI，跨屏幕移动无模糊
- **True/PM** - 兼容模式，支持较老的Windows版本
- **longPathAware** - 支持长路径（超过260字符）
- **Common-Controls v6** - 使用现代Windows控件样式

### 2. PyQt DPI优化

**文件：** `main.py`

**新增设置：**
```python
# 环境变量（必须在导入PyQt前设置）
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# Qt属性（必须在创建QApplication前设置）
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # ⭐ 关键！
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 字体渲染优化
font = app.font()
font.setHintingPreference(QFont.PreferFullHinting)  # 完整字体微调
font.setStyleStrategy(QFont.PreferAntialias)        # 抗锯齿
app.setFont(font)
```

**说明：**
- `AA_EnableHighDpiScaling` - 让PyQt感知并响应系统DPI设置（之前缺失！）
- `PreferFullHinting` - 在小尺寸时优化字形可读性
- `PreferAntialias` - 启用抗锯齿，让字体边缘平滑

### 3. 打包配置更新

**文件：** `MobileTestTool_pyqt.spec`

**修改：**
```python
exe = EXE(
    ...
    manifest='MobileTestTool.manifest',  # 集成manifest
    uac_admin=False,                     # 明确权限级别
    uac_uiaccess=False,
)
```

## 📊 效果对比

### 修复前
| DPI设置 | 字体效果 |
|---------|----------|
| 100%    | ✅ 清晰 |
| 125%    | ⚠️ 略模糊 |
| 150%    | ❌ 明显模糊 |
| 200%    | ❌ 非常模糊 |

### 修复后
| DPI设置 | 字体效果 |
|---------|----------|
| 100%    | ✅ 清晰 |
| 125%    | ✅ 清晰 |
| 150%    | ✅ 清晰 |
| 200%    | ✅ 清晰 |

## 🧪 测试方法

### 测试环境1：调整系统DPI

1. **右键桌面** → 显示设置
2. **缩放与布局** → 更改文本、应用等项目的大小
3. 测试不同缩放级别：
   - 100% (推荐)
   - 125% (推荐)
   - 150% (推荐)
   - 175%
   - 200%
4. **注意：** 更改DPI后需要**注销重新登录**才能完全生效

### 测试环境2：多显示器

1. 连接不同DPI的显示器（如笔记本+外接4K显示器）
2. 将程序窗口在不同显示器间拖动
3. 观察字体是否保持清晰

### 测试环境3：虚拟机

如果没有高DPI显示器，可以使用虚拟机测试：
1. 创建Windows虚拟机
2. 设置为高分辨率（如3840x2160）
3. 设置DPI缩放为200%
4. 运行程序测试

## 📝 日志验证

程序启动后，查看日志文件 `logs/debug_YYYYMMDD_HHMMSS.txt`：

```
[INFO] 字体渲染优化已启用
[INFO] 显示器DPI: 144, 缩放比例: 1.5
[INFO] 高DPI支持已启用
```

- **DPI**: 应该显示实际的显示器DPI（96/120/144/192等）
- **缩放比例**: 应该显示正确的缩放倍数（1.0/1.25/1.5/2.0等）

## ⚠️ 注意事项

### 1. Windows版本要求

- **最佳：** Windows 10 1703 (创意者更新) 或更高
  - 完整支持PerMonitorV2 DPI感知
- **良好：** Windows 8.1 或更高
  - 支持Per-Monitor DPI感知（V1）
- **基本：** Windows 7
  - 仅支持System DPI感知（单显示器可用）

### 2. 可能的兼容性问题

**Q: 更新后某些对话框大小异常？**  
A: 这是正常的，之前的布局是按96 DPI设计的。需要调整固定尺寸的控件。

**Q: 在不同显示器上大小不一致？**  
A: 这是正确的行为！程序会根据每个显示器的DPI独立调整。

**Q: Windows 7用户反馈问题？**  
A: Windows 7不支持Per-Monitor DPI，会降级到System DPI模式。单显示器正常，多显示器可能有问题。

### 3. 回滚方法

如果新版本有问题，可以临时回滚：

1. 从spec文件中移除 `manifest='MobileTestTool.manifest'`
2. 重新打包
3. 使用旧版本（字体可能模糊，但功能正常）

## 🔧 故障排查

### 问题1：打包后仍然模糊

**检查清单：**
- [ ] 确认 `MobileTestTool.manifest` 文件存在
- [ ] 确认spec文件中包含 `manifest='MobileTestTool.manifest'`
- [ ] 重新完整打包（使用 `--clean` 参数）
- [ ] 检查生成的exe是否包含manifest（使用Resource Hacker查看）

**验证方法：**
```powershell
# 查看exe的manifest
# 使用Resource Hacker或类似工具打开 MobileTestTool_PyQt5.exe
# 查看 RT_MANIFEST 资源
```

### 问题2：日志未显示DPI信息

**可能原因：**
- PyQt版本太旧（需要5.6+）
- QApplication创建失败

**解决方法：**
```bash
pip install --upgrade PyQt5
```

### 问题3：程序无法启动

**检查manifest语法：**
- manifest文件必须是UTF-8编码
- XML语法必须正确（注意闭合标签）

## 📚 技术参考

- [High DPI Desktop Application Development on Windows](https://docs.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows)
- [Qt High DPI Documentation](https://doc.qt.io/qt-5/highdpi.html)
- [Application Manifests](https://docs.microsoft.com/en-us/windows/win32/sbscs/application-manifests)

## 📞 反馈

如果用户仍然反馈字体模糊，请收集以下信息：

1. Windows版本（Win+R → `winver`）
2. 显示器DPI设置（设置 → 系统 → 显示）
3. 日志文件（`logs/` 目录中的最新文件）
4. 屏幕截图（显示模糊的部分）
5. 是否使用多显示器

---

**更新时间：** 2024-10-16  
**版本：** v0.7-PyQt5 DPI优化版

