---
name: 修复概率性模块导入错误（含PyInstaller支持）
overview: 修复由 sim_reader_dialog 模块清理导致的概率性 ModuleNotFoundError 问题，通过上下文管理器确保状态可恢复，同时传递 parent 参数和添加导入保护机制（支持 PyInstaller 打包环境）来彻底解决
todos:
  - id: create-context-manager
    content: 创建 SimReaderContext 上下文管理器，用于安全地临时修改 sys.path 和 sys.modules
    status: completed
  - id: refactor-sim-reader-dialog
    content: 重构 sim_reader_dialog.py 使用上下文管理器，确保在关闭时完全恢复状态
    status: completed
  - id: fix-main-window-tabs
    content: 在 ui/main_window.py 的 setup_tabs() 方法中，为所有 Tab 创建时传递 self 作为 parent 参数（TMOCCTab, TMOEcholocateTab, BackgroundDataTab, AppOperationsTab, OtherTab）
    status: pending
  - id: fix-log-control-tab-pyinstaller
    content: 在 ui/tabs/log_control_tab.py 的延迟导入逻辑中补充 PyInstaller 环境支持
    status: pending
  - id: fix-log-filter-tab
    content: 在 ui/tabs/log_filter_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
  - id: fix-tmo-cc-tab
    content: 在 ui/tabs/tmo_cc_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
  - id: fix-tmo-echolocate-tab
    content: 在 ui/tabs/tmo_echolocate_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
  - id: fix-background-data-tab
    content: 在 ui/tabs/background_data_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
  - id: fix-app-operations-tab
    content: 在 ui/tabs/app_operations_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
  - id: fix-other-tab
    content: 在 ui/tabs/other_tab.py 的延迟导入逻辑中添加导入保护机制（支持PyInstaller）
    status: pending
---

# 修复概率性模块导入错误的根本原因（含PyInstaller支持）

## 问题分析

### 根本原因确认

根据日志分析，这是一个**确定性的根本原因**，问题链条如下：

1. **触发点**：`ui/sim_reader_dialog.py` 在初始化时会：

   - 修改 `sys.path`（移除项目根目录，添加 sim_reader 路径）
   - **删除 `sys.modules` 中所有 `core.*` 子模块缓存**（包括 `core.language_manager`）
   - 这些操作在 `__init__` 方法中执行，但在关闭时可能没有完全恢复

2. **问题场景**（根据日志确认）：

   - 用户打开 SIM Reader 对话框后，`core.language_manager` 被从 `sys.modules` 中删除
   - 长时间运行后，关闭 UnifiedManagerDialog 触发 Tab 重新加载
   - 如果 Tab 创建时**没有传递 `parent` 参数**，会触发延迟导入 `core.language_manager`
   - 此时如果 `sys.path` 中项目根目录（或 PyInstaller 的 `sys._MEIPASS`）不在正确位置，就会导致 `ModuleNotFoundError`

3. **PyInstaller 环境特殊性**：

   - 在打包环境中，模块路径在 `sys._MEIPASS` 中
   - 如果 `sys._MEIPASS` 不在 `sys.path` 中，无法找到 `core` 模块
   - 需要同时支持开发环境和打包环境

### 其他模块也会遇到

**所有使用延迟导入 `core.language_manager` 且没有传递 `parent` 的 Tab 都会遇到这个问题**：

从代码检查发现，以下 Tab 在 `ui/main_window.py` 中创建时**没有传递 `parent` 参数**：

- `TMOCCTab()` (line 1468)
- `TMOEcholocateTab()` (line 1472)  
- `BackgroundDataTab()` (line 1476)
- `AppOperationsTab()` (line 1480)
- `OtherTab()` (line 1484)

## 修复方案

采用**三层防护**策略，确保在开发环境和 PyInstaller 打包环境中都能正常工作：

### 1. 核心修复：使用上下文管理器（最根本的解决方案）

**核心原则**：允许临时 import sim_reader，但必须在退出时恢复 sys.path 和 sys.modules，绝不能全局清除 core.*。

创建 `ui/sim_reader_context.py` 上下文管理器：

- 在进入时：保存项目根目录的 core.* 模块，临时移除它们，修改 sys.path
- 在退出时：恢复 sys.path 和 sys.modules，确保状态完全恢复

重构 `ui/sim_reader_dialog.py`：

- 在 `__init__` 中进入上下文管理器
- 在 `closeEvent` 中退出上下文管理器，恢复状态
- 确保即使出错也能正确恢复

### 2. 主要修复：传递 parent 参数（最直接有效）

在 `ui/main_window.py` 的 `setup_tabs()` 方法中，为所有 Tab 创建时传递 `self` 作为 `parent` 参数，避免触发延迟导入。

### 3. 次要修复：添加导入保护机制（防御性编程，支持PyInstaller）

在所有 Tab 类的延迟导入逻辑中添加保护机制，确保：

- **开发环境**：项目根目录在 `sys.path` 中
- **PyInstaller 环境**：`sys._MEIPASS` 在 `sys.path` 中

修改模式：

```python
else:
    # 如果没有父窗口或语言管理器，使用单例
    import sys
    import os
    try:
        from core.language_manager import LanguageManager
        self.lang_manager = LanguageManager.get_instance()
    except ModuleNotFoundError:
        # 如果导入失败，确保正确的路径在 sys.path 中
        # 支持 PyInstaller 打包环境
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境：使用 sys._MEIPASS
            base_path = sys._MEIPASS
            if base_path not in sys.path:
                sys.path.insert(0, base_path)
        else:
            # 开发环境：使用 __file__ 计算项目根目录
            current_file = os.path.abspath(__file__)
            # ui/tabs/xxx_tab.py -> ui/tabs -> ui -> 项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
        # 重试导入
        from core.language_manager import LanguageManager
        self.lang_manager = LanguageManager.get_instance()
```

## 实施优先级

1. **最高优先级**：修复方案1（上下文管理器）- 从根本上解决问题，确保状态可恢复
2. **高优先级**：修复方案2（传递 parent 参数）- 最直接有效
3. **高优先级**：修复方案3（添加导入保护，支持PyInstaller）- 确保打包EXE后能正常工作

## 影响范围

- **新增文件**：
  - `ui/sim_reader_context.py` (上下文管理器)

- **修复的文件**：
  - `ui/sim_reader_dialog.py` (重构使用上下文管理器)
  - `ui/main_window.py` (1处修改)
  - `ui/tabs/log_control_tab.py` (已修复，需补充PyInstaller支持)
  - `ui/tabs/log_filter_tab.py` (1处修改)
  - `ui/tabs/tmo_cc_tab.py` (1处修改)
  - `ui/tabs/tmo_echolocate_tab.py` (1处修改)
  - `ui/tabs/background_data_tab.py` (1处修改)
  - `ui/tabs/app_operations_tab.py` (1处修改)
  - `ui/tabs/other_tab.py` (1处修改)

- **测试建议**：
  - 在开发环境测试：打开 SIM Reader 对话框后，通过统一管理器对话框修改 Tab 显示设置，触发 Tab 重新加载
  - 在打包EXE环境测试：打包后运行，重复上述操作，验证所有 Tab 都能正常加载，不再出现 `ModuleNotFoundError`