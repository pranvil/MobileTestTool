#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIM卡读写工具对话框
将 sim_reader 的 SimEditorUI 封装为对话框，集成到主应用中
"""

import sys
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal

# 注意：sim_reader 的导入路径将在对话框初始化时动态添加
# 这样可以避免与当前的 ui 模块冲突
def _ensure_sim_reader_in_path():
    """确保 sim_reader 在 Python 路径中"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # ui目录
    project_root = os.path.dirname(current_dir)  # 项目根目录
    sim_reader_path = os.path.join(project_root, "sim_reader")
    
    if sim_reader_path not in sys.path:
        sys.path.insert(0, sim_reader_path)
    
    return sim_reader_path


class SimReaderDialog(QDialog):
    """SIM卡读写工具对话框 - 单例模式"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls, parent=None):
        """获取对话框实例（单例模式）"""
        if cls._instance is None or not cls._instance.isVisible():
            # 如果实例不存在或已被关闭，创建新实例
            if cls._instance is not None:
                # 清理旧实例
                try:
                    cls._instance.close()
                    cls._instance.deleteLater()
                except:
                    pass
            cls._instance = cls(parent)
        elif parent and cls._instance.parent() != parent:
            # 如果提供了新的parent，更新parent
            cls._instance.setParent(parent)
            cls._instance.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        return cls._instance
    
    def __init__(self, parent=None):
        """初始化对话框"""
        super().__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("SIM卡读写工具")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # 设置窗口标志，允许最小化和最大化
        self.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        # 初始化布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 尝试导入并创建 SimEditorUI
        try:
            import logging
            import traceback
            
            # 确保 sim_reader 在路径中（这样 sim_reader 内的相对导入才能工作）
            sim_reader_path = _ensure_sim_reader_in_path()
            project_root = os.path.dirname(sim_reader_path)
            
            logging.debug(f"[SimReaderDialog] sim_reader_path: {sim_reader_path}")
            logging.debug(f"[SimReaderDialog] project_root: {project_root}")
            logging.debug(f"[SimReaderDialog] 原始 sys.path (前5个): {sys.path[:5]}")
            
            # 保存原始的 sys.path 用于恢复
            original_sys_path = sys.path.copy()
            
            # 关键：需要清理所有可能包含项目根目录的路径
            # 包括项目根目录本身，以及任何指向项目根目录的路径
            paths_to_remove = []
            normalized_sim_reader_path = os.path.normpath(os.path.abspath(sim_reader_path))
            normalized_project_root = os.path.normpath(os.path.abspath(project_root))
            
            for path in sys.path:
                # 标准化路径以便比较
                try:
                    normalized_path = os.path.normpath(os.path.abspath(path))
                    # 如果路径是项目根目录，需要移除
                    if normalized_path == normalized_project_root:
                        paths_to_remove.append(path)
                    # 还要检查相对路径（如 'core\\..'）解析后是否指向项目根目录
                    elif normalized_path.startswith(normalized_project_root + os.sep):
                        # 但保留 sim_reader_path 和其子目录
                        if not normalized_path.startswith(normalized_sim_reader_path + os.sep) and normalized_path != normalized_sim_reader_path:
                            paths_to_remove.append(path)
                except (OSError, ValueError):
                    # 如果路径无效，跳过
                    pass
            
            logging.debug(f"[SimReaderDialog] 准备移除的路径: {paths_to_remove}")
            
            # 移除冲突的路径
            for path in paths_to_remove:
                if path in sys.path:
                    sys.path.remove(path)
                    logging.debug(f"[SimReaderDialog] 已移除路径: {path}")
            
            # 验证：确保项目根目录不在 sys.path 中
            normalized_paths_in_sys_path = [os.path.normpath(os.path.abspath(p)) for p in sys.path if os.path.exists(p)]
            if normalized_project_root in normalized_paths_in_sys_path:
                logging.warning(f"[SimReaderDialog] 警告：项目根目录仍在 sys.path 中！")
                logging.warning(f"[SimReaderDialog] 项目根目录: {normalized_project_root}")
                logging.warning(f"[SimReaderDialog] sys.path 中的路径: {normalized_paths_in_sys_path[:5]}")
            
            # 注意：sim_reader 内的文件使用相对导入（from core.xxx, from tree_manager）
            # 这要求 sim_reader 目录本身在 sys.path 的开头
            # 临时将 sim_reader 路径移到最前面，确保优先搜索
            if sim_reader_path in sys.path:
                sys.path.remove(sim_reader_path)
            sys.path.insert(0, sim_reader_path)
            logging.debug(f"[SimReaderDialog] 清理后的 sys.path (前5个): {sys.path[:5]}")
            
            # 关键：在执行 ui.py 之前，先手动导入所有依赖模块
            # 这样 ui.py 执行时就能找到这些模块了
            import importlib
            
            # 关键步骤：在清理 sys.path 之后，清除 sys.modules 中的模块缓存
            # 保存当前已存在的同名模块（如果有）
            saved_modules = {}
            
            # 先清除所有可能冲突的模块（包括 core 及其子模块）
            modules_to_check = ['core', 'tree_manager', 'parser_dispatcher']
            for mod_name in modules_to_check:
                if mod_name in sys.modules:
                    mod = sys.modules[mod_name]
                    # 检查模块路径，如果是项目根目录的模块，需要移除
                    if hasattr(mod, '__file__') and mod.__file__:
                        mod_file = os.path.normpath(os.path.abspath(mod.__file__))
                        # 如果模块文件来自项目根目录（但不是 sim_reader），保存并移除
                        if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                            saved_modules[mod_name] = mod
                            del sys.modules[mod_name]
                            logging.debug(f"[SimReaderDialog] 移除项目根目录的模块缓存: {mod_name} ({mod_file})")
            
            # 清除所有 core 的子模块缓存（无论来源）
            modules_to_remove = [mod for mod in list(sys.modules.keys()) if mod.startswith('core.')]
            for mod in modules_to_remove:
                mod_obj = sys.modules[mod]
                if hasattr(mod_obj, '__file__') and mod_obj.__file__:
                    mod_file = os.path.normpath(os.path.abspath(mod_obj.__file__))
                    # 如果是项目根目录的 core 子模块，保存并移除
                    if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                        saved_modules[mod] = mod_obj
                        del sys.modules[mod]
                        logging.debug(f"[SimReaderDialog] 移除项目根目录的 core 子模块缓存: {mod} ({mod_file})")
            
            try:
                # 手动导入 core 模块（这会让 core.serial_comm 等在 sys.modules 中可用）
                # 注意：由于项目根目录已从 sys.path 中移除，导入 'core' 会找到 sim_reader/core
                try:
                    logging.debug(f"[SimReaderDialog] 开始导入 core 模块...")
                    logging.debug(f"[SimReaderDialog] 当前 sys.path (完整): {sys.path}")
                    # 先导入 core 包（这会找到 sim_reader/core/__init__.py）
                    # 使用 reload=False 确保从文件系统重新加载
                    core_module = importlib.import_module('core')
                    logging.debug(f"[SimReaderDialog] core 模块已导入: {core_module.__file__}")
                    
                    # 验证导入的是正确的 core（应该来自 sim_reader）
                    if not hasattr(core_module, '__file__'):
                        raise ImportError(f"导入的 core 模块没有 __file__ 属性")
                    
                    core_file = os.path.normpath(os.path.abspath(core_module.__file__))
                    sim_reader_core_init = os.path.normpath(os.path.join(sim_reader_path, 'core', '__init__.py'))
                    
                    logging.debug(f"[SimReaderDialog] core 模块路径: {core_file}")
                    logging.debug(f"[SimReaderDialog] 期望的 sim_reader core 路径: {sim_reader_core_init}")
                    
                    if core_file != sim_reader_core_init:
                        raise ImportError(f"导入的 core 模块路径不正确:\n实际: {core_file}\n期望: {sim_reader_core_init}\n当前 sys.path: {sys.path[:5]}")
                    
                    logging.debug(f"[SimReaderDialog] core 模块验证通过，开始导入子模块...")
                    # 然后导入 core 的子模块
                    importlib.import_module('core.serial_comm')
                    logging.debug(f"[SimReaderDialog] core.serial_comm 已导入")
                    importlib.import_module('core.data_handler')
                    logging.debug(f"[SimReaderDialog] core.data_handler 已导入")
                    importlib.import_module('core.sim_service')
                    logging.debug(f"[SimReaderDialog] core.sim_service 已导入")
                    importlib.import_module('core.utils')
                    logging.debug(f"[SimReaderDialog] core.utils 已导入")
                except Exception as e:
                    error_detail = traceback.format_exc()
                    logging.error(f"[SimReaderDialog] 导入 core 模块失败: {e}\n{error_detail}")
                    raise ImportError(f"无法导入 core 模块: {e}\n详细错误:\n{error_detail}\n当前 sys.path: {sys.path[:5]}")
                
                # 导入其他依赖模块
                try:
                    importlib.import_module('tree_manager')
                    importlib.import_module('parser_dispatcher')
                except Exception as e:
                    raise ImportError(f"无法导入依赖模块: {e}")
                
                # 初始化 sim_reader 的日志系统（确保日志功能正常）
                try:
                    from core.utils import setup_logging
                    setup_logging()
                    logging.debug(f"[SimReaderDialog] sim_reader 日志系统已初始化")
                except Exception as e:
                    logging.warning(f"[SimReaderDialog] 初始化 sim_reader 日志系统失败: {e}（继续执行）")
                
                # 现在使用 importlib.util 加载 ui.py
                import importlib.util
                ui_file_path = os.path.join(sim_reader_path, "ui.py")
                spec = importlib.util.spec_from_file_location(
                    "sim_reader_ui_module",  # 使用不同的模块名避免冲突
                    ui_file_path
                )
                
                if spec is None or spec.loader is None:
                    raise ImportError(f"无法加载 sim_reader/ui.py 文件: {ui_file_path}")
                
                # 创建一个新的模块并执行
                sim_reader_ui = importlib.util.module_from_spec(spec)
                
                # 设置模块属性
                sim_reader_ui.__file__ = ui_file_path
                sim_reader_ui.__name__ = "sim_reader_ui_module"
                
                # 执行模块（此时 core, tree_manager 等已经在 sys.modules 中）
                spec.loader.exec_module(sim_reader_ui)
                
                SimEditorUI = sim_reader_ui.SimEditorUI
                
                # 保存状态，等对话框关闭时再恢复被覆盖的模块
                self._saved_modules = saved_modules
                self._sim_reader_path = sim_reader_path
                self._original_sys_path = original_sys_path
                self._paths_to_remove = paths_to_remove
                
            except Exception as e:
                import logging
                logging.error(f"[SimReaderDialog] 导入过程中出错: {e}")
                # 如果出错，清理可能被修改的模块
                for mod_name, mod in saved_modules.items():
                    sys.modules[mod_name] = mod
                    logging.debug(f"[SimReaderDialog] 恢复模块: {mod_name}")
                # 恢复 sys.path
                sys.path = original_sys_path.copy()
                logging.debug(f"[SimReaderDialog] 已恢复原始 sys.path")
                # 重新抛出异常，让外层处理
                raise
            
            # 创建 SimEditorUI 实例（作为隐藏的主窗口）
            self.sim_editor = SimEditorUI()
            self.sim_editor.hide()  # 隐藏原始的 QMainWindow
            
            # 将 SimEditorUI 的 centralWidget 提取出来，嵌入到对话框
            central_widget = self.sim_editor.centralWidget()
            if central_widget:
                # 将 centralWidget 的父对象设置为对话框
                # 这样 centralWidget 会成为对话框的子widget
                central_widget.setParent(self)
                
                # 将 centralWidget 添加到对话框布局
                layout.addWidget(central_widget)
                
                # 移除 SimEditorUI 的 centralWidget 引用（但不删除widget）
                # 这样可以避免 SimEditorUI 删除时同时删除 centralWidget
                self.sim_editor.takeCentralWidget()
            
            # 设置对话框的窗口标题（使用 SimEditorUI 的标题）
            self.setWindowTitle(self.sim_editor.windowTitle())
            
        except ImportError as e:
            # 如果导入失败，显示错误信息
            error_label = QMessageBox(
                QMessageBox.Critical,
                "导入错误",
                f"无法导入 sim_reader 模块：\n{str(e)}\n\n请确保 sim_reader 目录存在且包含所有必需的文件。",
                QMessageBox.Ok,
                self
            )
            layout.addWidget(error_label)
            QMessageBox.critical(
                self,
                "导入错误",
                f"无法导入 sim_reader 模块：\n{str(e)}\n\n请确保 sim_reader 目录存在且包含所有必需的文件。"
            )
            
        except Exception as e:
            # 其他错误
            QMessageBox.critical(
                self,
                "初始化错误",
                f"初始化 SIM 卡读写工具失败：\n{str(e)}\n\n详细信息请查看日志。"
            )
    
    def _on_close_event(self, event):
        """处理关闭事件"""
        try:
            # 如果有 sim_editor，尝试清理资源
            if hasattr(self, 'sim_editor') and self.sim_editor:
                # 停止定时器
                if hasattr(self.sim_editor, 'port_timer'):
                    self.sim_editor.port_timer.stop()
                
                # 关闭串口连接
                if hasattr(self.sim_editor, 'comm') and self.sim_editor.comm:
                    try:
                        if hasattr(self.sim_editor.comm, 'ser') and self.sim_editor.comm.ser:
                            if self.sim_editor.comm.ser.is_open:
                                self.sim_editor.comm.ser.close()
                    except:
                        pass
                
                # 关闭线程池
                if hasattr(self.sim_editor, 'executor'):
                    try:
                        self.sim_editor.executor.shutdown(wait=False)
                    except:
                        pass
            
            # 恢复被覆盖的模块（如果有）
            if hasattr(self, '_saved_modules'):
                import sys
                for mod_name, mod in self._saved_modules.items():
                    sys.modules[mod_name] = mod
            
            # 恢复 sys.path
            if hasattr(self, '_original_sys_path'):
                try:
                    import logging
                    logging.debug(f"[SimReaderDialog] 关闭时恢复 sys.path")
                    sys.path = self._original_sys_path.copy()
                except:
                    pass
            
            # 重置单例实例
            SimReaderDialog._instance = None
            
        except Exception as e:
            # 忽略清理时的错误
            pass
        
        # 调用父类的关闭事件
        event.accept()
    
    def closeEvent(self, event):
        """重写的关闭事件处理"""
        self._on_close_event(event)


def show_sim_reader_dialog(parent=None):
    """显示SIM卡读写工具对话框的便捷函数"""
    dialog = SimReaderDialog.get_instance(parent)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog

