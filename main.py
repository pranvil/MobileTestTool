#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机测试辅助工具 - PyQt5 版本
主程序入口
"""

import sys
import os

# 在打包环境中，提前导入必要的模块以确保PyInstaller包含它们
try:
    import serial
    import serial.tools.list_ports
    from concurrent.futures import ThreadPoolExecutor  # sim_reader需要
except ImportError:
    pass  # 如果未安装相关模块，继续运行（某些功能可能不可用）

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# 设置控制台编码（解决Windows下中文乱码问题）
if sys.platform == 'win32':
    import io
    
    # 设置控制台代码页为UTF-8
    try:
        os.system('chcp 65001 >nul 2>&1')
    except:
        pass
    
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 重新配置标准输出流（兼容PyInstaller打包）
    if not is_pyinstaller():
        # 只在非PyInstaller环境中重新配置输出流
        try:
            if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, OSError):
            pass

# 必须在导入PyQt5之前设置高DPI支持
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# 导入日志系统（尽早初始化）
from core.debug_logger import logger, setup_exception_hook

# 设置全局异常捕获
setup_exception_hook()

# 重定向所有控制台输出到日志文件，避免乱码
def redirect_stdout_to_log():
    """将标准输出重定向到日志文件"""
    try:
        # 创建一个自定义的输出类
        class LogRedirector:
            def __init__(self, log_file_path):
                self.log_file_path = log_file_path
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
            
            def write(self, text):
                # 将输出写入日志文件而不是控制台
                try:
                    if self.log_file_path and text.strip():
                        with open(self.log_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[CONSOLE] {text}")
                except:
                    pass  # 静默处理写入错误
            
            def flush(self):
                pass  # 不需要刷新
            
            def __getattr__(self, name):
                return getattr(self.original_stdout, name)
        
        # 重定向标准输出和错误输出
        if logger.get_log_file_path():
            redirector = LogRedirector(logger.get_log_file_path())
            sys.stdout = redirector
            sys.stderr = redirector
            logger.info("控制台输出已重定向到日志文件")
    except Exception as e:
        # 静默处理重定向错误
        pass

# 执行输出重定向
redirect_stdout_to_log()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from ui.main_window import MainWindow


def _set_application_icon(app):
    """设置应用程序图标"""
    try:
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"应用程序图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
    except Exception as e:
        logger.warning(f"设置图标失败: {str(e)}")


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("程序启动")
        logger.info("=" * 60)
        
        # 检测CLI参数（在创建QApplication之前）
        # 如果检测到 -w、-p、--help 或 -h 参数，执行CLI模式
        if len(sys.argv) > 1:
            cli_args = sys.argv[1:]
            # 检查是否是帮助请求
            is_help_request = any(arg in ['--help', '-h'] for arg in cli_args)
            # 检查是否有实际的CLI参数
            has_cli_args = any(arg in ['-w', '-p'] for arg in cli_args)
            
            if has_cli_args or is_help_request:
                if is_help_request:
                    logger.info("检测到帮助请求，显示CLI帮助信息")
                else:
                    logger.info("检测到CLI参数，进入CLI模式")
                
                try:
                    # 处理 sim_reader 模块导入的路径问题
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    sim_reader_path = os.path.join(project_root, "sim_reader")
                    
                    # 保存原始路径和模块状态
                    original_sys_path = sys.path.copy()
                    normalized_project_root = os.path.normpath(os.path.abspath(project_root))
                    normalized_sim_reader_path = os.path.normpath(os.path.abspath(sim_reader_path))
                    
                    # 关键：需要项目根目录在 sys.path 中才能导入 sim_reader 包
                    # 但需要确保 sim_reader 目录在项目根目录之前，这样 core 会优先从 sim_reader 导入
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    # 将 sim_reader 目录也添加到路径最前面（用于相对导入）
                    if sim_reader_path in sys.path:
                        sys.path.remove(sim_reader_path)
                    sys.path.insert(0, sim_reader_path)
                    
                    # 清除可能冲突的模块缓存（只清除项目根目录的 core，保留 sim_reader 的）
                    saved_modules = {}
                    for mod_name in ['core', 'tree_manager', 'parser_dispatcher']:
                        if mod_name in sys.modules:
                            mod = sys.modules[mod_name]
                            if hasattr(mod, '__file__') and mod.__file__:
                                mod_file = os.path.normpath(os.path.abspath(mod.__file__))
                                # 如果模块来自项目根目录（但不是 sim_reader），保存并移除
                                if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                                    saved_modules[mod_name] = mod
                                    del sys.modules[mod_name]
                    
                    # 清除 core 的子模块缓存（只清除项目根目录的）
                    modules_to_remove = [mod for mod in list(sys.modules.keys()) if mod.startswith('core.')]
                    for mod in modules_to_remove:
                        mod_obj = sys.modules[mod]
                        if hasattr(mod_obj, '__file__') and mod_obj.__file__:
                            mod_file = os.path.normpath(os.path.abspath(mod_obj.__file__))
                            if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                                saved_modules[mod] = mod_obj
                                del sys.modules[mod]
                    
                    try:
                        # 导入并执行CLI功能
                        # argparse 会自动处理 --help 和 -h，打印帮助信息后会抛出 SystemExit(0)
                        # 使用 importlib 动态导入，确保从正确的路径导入
                        import importlib
                        sim_reader_cli = importlib.import_module('sim_reader.cli')
                        cli_main = sim_reader_cli.main
                        
                        try:
                            cli_main()
                            # 如果执行到这里（非帮助请求），说明CLI执行完成
                            if not is_help_request:
                                logger.info("CLI模式执行完成")
                            # CLI模式执行完成后直接退出，不启动GUI
                            sys.exit(0)
                        except SystemExit as e:
                            # argparse 在处理 --help 时会抛出 SystemExit(0)，这是正常的
                            # 直接传播这个异常即可
                            raise
                    finally:
                        # 恢复模块和路径
                        for mod_name, mod in saved_modules.items():
                            sys.modules[mod_name] = mod
                        sys.path = original_sys_path.copy()
                        
                except Exception as e:
                    logger.exception("CLI模式执行失败")
                    # 尝试显示错误消息框（如果有GUI环境）
                    try:
                        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
                        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
                        app = QApplication(sys.argv)
                        from PyQt5.QtWidgets import QMessageBox
                        QMessageBox.critical(None, "CLI执行失败", f"CLI模式执行失败：\n{str(e)}\n\n详细信息请查看日志文件。")
                    except:
                        pass
                    sys.exit(1)
        
        # 在创建QApplication之前启用高DPI缩放（Qt 5.6+）
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # 创建应用程序
        logger.info("创建QApplication实例...")
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        app.setApplicationName("手机测试辅助工具")
        app.setApplicationVersion("0.7-PyQt5")
        app.setOrganizationName("MobileTestTool")
        
        # 设置应用程序图标
        _set_application_icon(app)
        
        logger.info("应用程序属性设置完成")
        
        # 设置字体渲染质量和大小
        font = app.font()
        font.setHintingPreference(QFont.PreferFullHinting)
        font.setStyleStrategy(QFont.PreferAntialias)
        
        # 智能字体大小补偿 - 解决DPI感知后字体变小的问题
        screen = app.primaryScreen()
        current_dpi = screen.logicalDotsPerInch()
        dpi_scale = current_dpi / 96.0
        
        # 根据DPI缩放智能调整字体大小
        if dpi_scale <= 1.0:
            # 标准DPI (96) 或更小
            font.setPointSize(9)
            logger.info(f"标准DPI ({current_dpi}), 字体大小: 9pt")
        elif dpi_scale <= 1.25:
            # 125% DPI (120)
            font.setPointSize(10)
            logger.info(f"125% DPI ({current_dpi}), 字体大小: 10pt")
        elif dpi_scale <= 1.5:
            # 150% DPI (144)
            font.setPointSize(11)
            logger.info(f"150% DPI ({current_dpi}), 字体大小: 11pt")
        elif dpi_scale <= 2.0:
            # 200% DPI (192)
            font.setPointSize(12)
            logger.info(f"200% DPI ({current_dpi}), 字体大小: 12pt")
        else:
            # 更高DPI
            font.setPointSize(13)
            logger.info(f"超高DPI ({current_dpi}), 字体大小: 13pt")
        
        app.setFont(font)
        logger.info("字体渲染优化已启用")
        
        # 记录DPI信息
        dpi = screen.logicalDotsPerInch()
        scale_factor = screen.devicePixelRatio()
        logger.info(f"显示器DPI: {dpi}, 缩放比例: {scale_factor}")
        logger.info("高DPI支持已启用")
        
        # 创建主窗口
        logger.info("开始创建主窗口...")
        window = MainWindow()
        logger.info("主窗口创建成功")
        
        logger.info("显示主窗口...")
        window.show()
        logger.info("主窗口已显示")
        
        logger.info("进入事件循环...")
        logger.info(f"日志文件位置: {logger.get_log_file_path()}")
        logger.separator()
        
        # 运行应用程序
        exit_code = app.exec_()
        
        logger.info("=" * 60)
        logger.info(f"程序正常退出，退出码: {exit_code}")
        logger.info("=" * 60)
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception("程序启动失败")
        
        # 尝试显示错误对话框
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("启动失败")
            msg.setText(f"程序启动失败: {str(e)}")
            msg.setInformativeText(f"详细信息请查看日志文件：\n{logger.get_log_file_path()}")
            msg.exec_()
        except:
            # 静默处理启动失败错误，避免控制台乱码
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()

