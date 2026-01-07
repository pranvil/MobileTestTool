#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口
"""

import os
import subprocess
import sys
import json
import time
import threading
from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                              QSplitter, QTabWidget, QMessageBox, QProgressDialog,
                              QHBoxLayout, QPushButton, QSizePolicy, QApplication)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QMimeData, QTimer, QObject
from PySide6.QtGui import QDrag
from ui.menu_bar import DisplayLinesDialog
from ui.tools_config_dialog import ToolsConfigDialog
from core.debug_logger import logger

from core.update_manager import (
    UpdateManager,
    DownloadResult,
    UpdateError,
)
from core.update_manifest import LatestManifest
from core.version import APP_VERSION

from ui.toolbar import DeviceToolBar
from ui.widgets.log_viewer import LogViewer
from ui.tabs.log_control_tab import LogControlTab
from ui.tabs.log_filter_tab import LogFilterTab
from ui.tabs.network_info_tab import NetworkInfoTab
from ui.tabs.tmo_cc_tab import TMOCCTab
from ui.tabs.tmo_echolocate_tab import TMOEcholocateTab
from ui.tabs.background_data_tab import BackgroundDataTab
from ui.tabs.app_operations_tab import AppOperationsTab
from ui.tabs.other_tab import OtherTab
from ui.tabs.sim_tab import SimTab
from ui.tabs.office_tool_tab import OfficeToolTab
from core.device_manager import PySide6DeviceManager
from core.mtklog_manager import PySide6MTKLogManager
from core.adblog_manager import PySide6ADBLogManager
from core.log_processor import PySide6LogProcessor
from core.network_info_manager import PySide6NetworkInfoManager
from core.screenshot_manager import PySide6ScreenshotManager
from core.video_manager import VideoManager
from core.tcpdump_manager import PySide6TCPDumpManager
from core.log_utilities import PySide6BugreportManager
from core.aee_log_manager import PySide6AEELogManager
from core.google_log_manager import PySide6GoogleLogManager
from core.rrc3gpp_decoder import RRC3GPPDecoder
from core.enable_telephony_manager import PySide6TelephonyManager
from core.tmo_cc_manager import PySide6TMOCCManager
from core.echolocate_manager import PySide6EcholocateManager
from core.device_operations import (
    PySide6BackgroundDataManager,
    PySide6AppOperationsManager,
    PySide6DeviceInfoManager,
    PySide6HeraConfigManager,
    PySide6OtherOperationsManager
)
from core.theme_manager import ThemeManager
from core.custom_button_manager import CustomButtonManager
from core.log_keyword_manager import LogKeywordManager
from core.language_manager import LanguageManager
from core.tab_config_manager import TabConfigManager


CUSTOM_BUTTON_MIME_TYPE = "application/x-custom-button"


class DraggableCustomButton(QPushButton):
    """支持在主界面拖拽排序的自定义按钮"""

    def __init__(self, button_data, container):
        super().__init__(button_data.get('name', ''))
        self.button_data = button_data
        self.container = container
        self._drag_start_pos = None

        tooltip = button_data.get('description') or button_data.get('command', '')
        if tooltip:
            self.setToolTip(tooltip)

        self.setProperty('custom_button', True)
        self.setCursor(Qt.OpenHandCursor)

    def update_display(self, button_data):
        """更新按钮展示信息"""
        self.button_data = button_data
        self.setText(button_data.get('name', ''))
        tooltip = button_data.get('description') or button_data.get('command', '')
        if tooltip:
            self.setToolTip(tooltip)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._drag_start_pos = None

    def contextMenuEvent(self, event):
        """右键：显示自定义按钮菜单（不显示卡片右键菜单）"""
        try:
            from PySide6.QtWidgets import QDialog, QMenu, QMessageBox
            from ui.custom_button_dialog import ButtonEditDialog

            main_window = getattr(self.container, "main_window", None)
            if not main_window or not getattr(main_window, "custom_button_manager", None):
                return

            current_data = dict(self.button_data or {})
            button_id = current_data.get("id")
            if not button_id:
                return

            menu = QMenu(self)
            edit_action = menu.addAction(main_window.tr("编辑"))
            delete_action = menu.addAction(main_window.tr("删除"))
            chosen = menu.exec(event.globalPos())
            if chosen == edit_action:
                dialog = ButtonEditDialog(
                    main_window.custom_button_manager,
                    button_data=current_data,
                    parent=main_window,
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    new_data = dialog.get_button_data()
                    main_window.custom_button_manager.update_button(button_id, new_data)
            elif chosen == delete_action:
                button_name = current_data.get('name', '')
                reply = QMessageBox.question(
                    main_window,
                    main_window.tr("确认删除"),
                    f"{main_window.tr('确定要删除按钮')} '{button_name}' {main_window.tr('吗？')}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if main_window.custom_button_manager.delete_button(button_id):
                        QMessageBox.information(main_window, main_window.tr("成功"), main_window.tr("按钮删除成功！"))
                    else:
                        QMessageBox.warning(main_window, main_window.tr("失败"), main_window.tr("按钮删除失败，请检查日志"))
        except Exception as e:
            try:
                logger.exception(f"{getattr(self.container, 'main_window', None).tr('操作自定义按钮失败:') if getattr(self.container, 'main_window', None) else '操作自定义按钮失败:'} {e}")
            except Exception:
                logger.exception(f"操作自定义按钮失败: {e}")
        finally:
            # 一定要吞掉事件，避免冒泡到 card_frame 触发卡片右键菜单
            try:
                event.accept()
            except Exception:
                pass

    def _start_drag(self):
        button_id = self.button_data.get('id')
        if not button_id:
            return

        button_name = self.button_data.get('name', '')

        drag = QDrag(self)
        mime = QMimeData()
        payload = {
            'button_id': button_id,
            'tab': self.container.tab_name,
            'card': self.container.card_name
        }
        mime.setData(CUSTOM_BUTTON_MIME_TYPE, json.dumps(payload).encode('utf-8'))
        drag.setMimeData(mime)
        
        # 设置拖动预览图像，避免 QPixmap 警告
        # 创建一个按钮的快照作为拖动预览
        try:
            from PySide6.QtGui import QPixmap, QPainter
            pixmap = QPixmap(self.size())
            pixmap.fill(Qt.transparent)
            self.render(pixmap)
            if not pixmap.isNull():
                drag.setPixmap(pixmap)
        except Exception:
            # 如果创建预览失败，使用默认行为（不设置预览）
            pass
        
        drag.exec(Qt.DropAction.MoveAction)


class CustomButtonContainer(QWidget):
    """承载自定义按钮并处理拖拽排序的容器"""

    order_changed = Signal(str, str, list)

    def __init__(self, main_window, tab_name, card_name, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.tab_name = tab_name
        self.card_name = card_name
        self._button_widgets = {}

        self.setAcceptDrops(True)
        self.setProperty('custom_button_container', True)
        # 使用MinimumExpanding，让容器根据内容自动调整宽度
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        # 不添加stretch，让按钮自然排列，避免按钮被压缩
        # self._layout.addStretch()  # 注释掉，让按钮容器根据内容自动调整宽度

    def update_context(self, tab_name, card_name):
        self.tab_name = tab_name
        self.card_name = card_name

    def clear_buttons(self):
        for widget in list(self._button_widgets.values()):
            self._layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._button_widgets.clear()

    def add_custom_button(self, button_data):
        button = DraggableCustomButton(button_data, self)
        button.clicked.connect(lambda checked=False, data=button_data: self.main_window.execute_custom_button_command(data))

        # 直接添加到布局末尾，保持按钮顺序
        self._layout.addWidget(button)
        self._button_widgets[button_data.get('id')] = button
        return button

    def dragEnterEvent(self, event):
        if self._accepts_event(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._accepts_event(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        payload = self._parse_payload(event.mimeData())
        if not payload:
            event.ignore()
            return

        button_id = payload.get('button_id')
        button = self._button_widgets.get(button_id)
        if button is None:
            event.ignore()
            return

        buttons = self._ordered_buttons()
        if len(buttons) <= 1:
            event.ignore()
            return

        source_index = buttons.index(button)
        mouse_pos = event.pos()
        target_index = self._determine_target_index(mouse_pos, buttons)

        # 如果目标位置和源位置相同，或者目标位置紧挨着源位置（不需要移动），则忽略
        if target_index == source_index:
            event.ignore()
            return

        # 移除源按钮
        self._layout.removeWidget(button)

        # 计算正确的插入位置
        # 如果目标索引在源索引之后，需要减1（因为源按钮已被移除）
        if target_index > source_index:
            target_index -= 1

        # 确保目标索引在有效范围内
        target_index = max(0, min(target_index, self._layout.count()))
        
        # 插入到目标位置
        self._layout.insertWidget(target_index, button)
        event.acceptProposedAction()

        # 发送排序变更信号
        ordered_ids = self._current_button_ids()
        logger.debug(f"[拖动排序] Tab '{self.tab_name}', Card '{self.card_name}' 按钮顺序已更新")
        self.order_changed.emit(self.tab_name, self.card_name, ordered_ids)

    def _ordered_buttons(self):
        buttons = []
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, DraggableCustomButton):
                buttons.append(widget)
        return buttons

    def _current_button_ids(self):
        return [btn.button_data.get('id') for btn in self._ordered_buttons() if btn.button_data.get('id')]

    def _determine_target_index(self, pos, buttons):
        """
        根据鼠标位置确定目标插入索引
        
        Args:
            pos: 鼠标位置（QPoint，相对于容器的坐标）
            buttons: 按钮列表
            
        Returns:
            int: 目标索引位置（插入位置，在指定索引的按钮之前）
        """
        if not buttons:
            return 0
        
        # 默认插入到末尾
        target_index = len(buttons)
        
        # 遍历所有按钮，找到鼠标应该在的位置
        # 使用按钮的左边界作为判断标准，更直观
        for index, btn in enumerate(buttons):
            btn_rect = btn.geometry()
            btn_left = btn_rect.left()
            btn_right = btn_rect.right()
            btn_center_x = btn_rect.center().x()
            
            # 如果鼠标在按钮的左侧一半区域内，插入到该按钮之前
            # 这样可以更准确地判断用户想要插入的位置
            if pos.x() < btn_left:
                target_index = index
                break
            # 如果鼠标在按钮上，根据位置判断是插入到之前还是之后
            elif btn_left <= pos.x() <= btn_right:
                if pos.x() < btn_center_x:
                    # 在按钮左侧一半，插入到该按钮之前
                    target_index = index
                else:
                    # 在按钮右侧一半，插入到该按钮之后
                    target_index = index + 1
                break
        
        return target_index

    def _accepts_event(self, mime_data):
        payload = self._parse_payload(mime_data)
        if not payload:
            return False
        return payload.get('tab') == self.tab_name and payload.get('card') == self.card_name

    def _parse_payload(self, mime_data):
        if not mime_data or not mime_data.hasFormat(CUSTOM_BUTTON_MIME_TYPE):
            return None
        try:
            data = bytes(mime_data.data(CUSTOM_BUTTON_MIME_TYPE)).decode('utf-8')
            return json.loads(data)
        except Exception as exc:
            logger.warning(f"解析拖拽数据失败: {exc}")
            return None


class ButtonCommandWorker(QThread):
    """在后台执行自定义按钮命令"""
    
    finished = Signal(bool, str, str)  # success, output, button_name
    log_message = Signal(str, str)  # message, color
    dialog_request = Signal(str, str, str, int, int)  # dialog_type, title, message, buttons, default_button
    dialog_response_received = Signal(int)  # 接收对话框响应
    
    def __init__(self, button_data, device_id, button_manager, lang_manager, main_window):
        super().__init__()
        self.button_data = button_data
        self.device_id = device_id
        self.button_manager = button_manager
        self.lang_manager = lang_manager
        self.main_window = main_window  # 用于在主线程显示对话框
        self._dialog_response_handler = None  # 存储对话框响应处理器
        self._current_dialog_response = None  # 当前对话框响应值
        self._dialog_response_ready = False  # 响应是否就绪
        self._process = None  # 存储进程对象（用于program类型）
        self._stop_event = None  # 停止事件（用于program类型）
    
    def _tr(self, text):
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def _create_dialog_request_handler(self):
        """创建对话框请求处理器，用于在脚本中调用"""
        def dialog_request_handler(dialog_type, title, message, buttons, default_button):
            """在工作线程中调用，通过信号请求主线程显示对话框"""
            # 重置响应状态
            self._current_dialog_response = None
            self._dialog_response_ready = False
            
            # 使用信号发送请求到主线程
            self.dialog_request.emit(dialog_type, title, message, buttons, default_button)
            
            # 等待响应（最多30秒）
            from PySide6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            timer = QTimer()
            timer.timeout.connect(lambda: None)  # 空回调，保持事件循环活跃
            timer.start(10)
            
            # 超时保护
            timeout_timer = QTimer()
            timeout_timer.timeout.connect(loop.quit)
            timeout_timer.setSingleShot(True)
            timeout_timer.start(30000)  # 30秒超时
            
            # 轮询等待响应
            while not self._dialog_response_ready and timeout_timer.isActive():
                loop.processEvents()
                from PySide6.QtCore import QThread
                QThread.msleep(10)
            
            timer.stop()
            timeout_timer.stop()
            
            return self._current_dialog_response if self._dialog_response_ready else default_button
        
        # 连接响应信号
        self.dialog_response_received.connect(self._on_dialog_response_received)
        
        return dialog_request_handler
    
    @Slot(int)
    def _on_dialog_response_received(self, value):
        """接收对话框响应（由信号触发）"""
        self._current_dialog_response = value
        self._dialog_response_ready = True
    
    def run(self):
        """在线程中执行命令"""
        try:
            button_name = self.button_data.get('name', self._tr('自定义按钮'))
            button_type = self.button_data.get('type', 'adb')
            
            # 如果是Python脚本，需要创建对话框请求处理器
            if button_type == 'python':
                # 创建对话框请求处理器
                dialog_handler = self._create_dialog_request_handler()
                
                # 直接调用_execute_python_script，传递对话框处理器
                script_code = self.button_data.get('script', '')
                if script_code:
                    success, output = self.button_manager._execute_python_script(
                        script_code,
                        self.device_id,
                        dialog_handler
                    )
                else:
                    success, output = False, self.lang_manager.tr("Python脚本内容为空")
            
            # 如果是运行程序类型，需要实时读取输出
            elif button_type == 'program':
                success, output = self._run_program_with_output()
            
            else:
                # 其他类型的命令正常执行
                success, output = self.button_manager.execute_button_command(
                    self.button_data,
                    self.device_id
                )
            
            # 发送完成信号
            self.finished.emit(success, output or '', button_name)
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"{self._tr('执行自定义按钮命令失败:')} {e}")
            self.finished.emit(False, error_msg, self.button_data.get('name', self._tr('自定义按钮')))
        finally:
            # 确保进程被清理
            self._cleanup_process()
    
    def _run_program_with_output(self):
        """运行程序并实时读取输出"""
        import threading
        import queue
        import subprocess
        
        process = None
        stdout_thread = None
        stderr_thread = None
        output_queue = None
        stop_event = None
        
        try:
            program_path = self.button_data.get('command', '')
            if not program_path:
                return False, self._tr('程序路径不能为空')
            
            # 启动进程
            process, success, error_msg = self.button_manager._run_program(
                program_path,
                self.device_id
            )
            
            if not success:
                return False, error_msg or self._tr('启动进程失败')
            
            if process is None:
                return False, self._tr('启动进程失败')
            
            # 保存进程引用，用于清理
            self._process = process
            
            # 创建停止事件和输出队列
            stop_event = threading.Event()
            self._stop_event = stop_event
            output_queue = queue.Queue()
            
            # 读取线程函数
            def read_stdout():
                """读取标准输出"""
                try:
                    for line in iter(process.stdout.readline, ''):
                        if stop_event.is_set():
                            break
                        if line:
                            output_queue.put(('stdout', line))
                except Exception as e:
                    if not stop_event.is_set():
                        output_queue.put(('error', f"{self._tr('读取输出错误:')} {str(e)}"))
                finally:
                    output_queue.put(('stdout_done', None))
            
            def read_stderr():
                """读取错误输出"""
                try:
                    for line in iter(process.stderr.readline, ''):
                        if stop_event.is_set():
                            break
                        if line:
                            output_queue.put(('stderr', line))
                except Exception as e:
                    if not stop_event.is_set():
                        output_queue.put(('error', f"{self._tr('读取错误输出错误:')} {str(e)}"))
                finally:
                    output_queue.put(('stderr_done', None))
            
            # 启动读取线程（daemon线程，主程序退出时自动清理）
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            
            # 实时处理输出
            stdout_done = False
            stderr_done = False
            
            while not (stdout_done and stderr_done):
                try:
                    msg_type, line = output_queue.get(timeout=0.1)
                    
                    if msg_type == 'stdout':
                        # 发送标准输出到日志窗口
                        self.log_message.emit(line, None)
                    elif msg_type == 'stderr':
                        # 发送错误输出到日志窗口（红色显示）
                        self.log_message.emit(line, "#FF0000")
                    elif msg_type == 'stdout_done':
                        stdout_done = True
                    elif msg_type == 'stderr_done':
                        stderr_done = True
                    elif msg_type == 'error':
                        self.log_message.emit(f"⚠️ {line}\n", "#FFA500")
                        
                except queue.Empty:
                    # 检查进程是否已结束
                    if process.poll() is not None:
                        # 进程已结束，等待读取线程完成
                        if not stdout_done:
                            stdout_thread.join(timeout=1)
                        if not stderr_done:
                            stderr_thread.join(timeout=1)
                        break
            
            # 等待进程结束
            return_code = process.wait(timeout=300)  # 最多等待5分钟
            
            # 处理剩余的队列消息
            while not output_queue.empty():
                try:
                    msg_type, line = output_queue.get_nowait()
                    if msg_type == 'stdout':
                        self.log_message.emit(line, None)
                    elif msg_type == 'stderr':
                        self.log_message.emit(line, "#FF0000")
                    elif msg_type == 'error':
                        self.log_message.emit(f"⚠️ {line}\n", "#FFA500")
                except queue.Empty:
                    break
            
            # 根据返回码判断成功或失败
            if return_code == 0:
                return True, f"{self._tr('程序执行完成，退出码:')} {return_code}"
            else:
                return False, f"{self._tr('程序执行失败，退出码:')} {return_code}"
                
        except subprocess.TimeoutExpired:
            # 进程超时，强制终止
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                    except:
                        pass
            return False, self._tr('程序执行超时，已强制终止')
            
        except Exception as e:
            error_msg = f"{self._tr('运行程序异常:')} {str(e)}"
            logger.exception(error_msg)
            # 确保进程被终止
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                    except:
                        pass
            return False, error_msg
        
        finally:
            # 设置停止标志
            if stop_event:
                stop_event.set()
            
            # 等待读取线程结束（最多等待1秒）
            if stdout_thread:
                stdout_thread.join(timeout=1)
            if stderr_thread:
                stderr_thread.join(timeout=1)
    
    def _cleanup_process(self):
        """清理进程，确保不产生孤儿进程"""
        if self._process:
            try:
                # 检查进程是否还在运行
                if self._process.poll() is None:
                    # 进程仍在运行，尝试终止
                    try:
                        self._process.terminate()
                        self._process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # 如果terminate失败，强制kill
                        try:
                            self._process.kill()
                            self._process.wait(timeout=1)
                        except:
                            pass
                    except:
                        # terminate失败，尝试kill
                        try:
                            self._process.kill()
                            self._process.wait(timeout=1)
                        except:
                            pass
            except Exception as e:
                logger.exception(f"{self._tr('清理进程失败:')} {e}")
            finally:
                self._process = None
                
        if self._stop_event:
            self._stop_event.set()
            self._stop_event = None


class RootRemountWorker(QThread):
    """在后台执行 adb root & remount"""

    log_message = Signal(str, str)
    finished = Signal(bool, str, bool, str)  # success, message, reboot_required, device

    def __init__(self, device, lang_manager=None):
        super().__init__()
        self.device = device
        self.lang_manager = lang_manager

    def _tr(self, text):
        return self.lang_manager.tr(text) if self.lang_manager else text

    def _run_command(self, args, timeout):
        return subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

    def _forward_output(self, result):
        if result.stdout:
            self.log_message.emit(result.stdout, None)
        if result.stderr:
            self.log_message.emit(result.stderr, None)

    def run(self):
        try:
            # Step 1: adb root
            self.log_message.emit(self._tr("执行 adb root...") + "\n", None)
            root_result = self._run_command(["adb", "-s", self.device, "root"], timeout=10)
            self._forward_output(root_result)

            if root_result.returncode != 0:
                error_msg = root_result.stderr.strip() or self._tr("执行 adb root 失败")
                self.log_message.emit(f"❌ {error_msg}\n", "#FF0000")
                self.finished.emit(False, error_msg, False, self.device)
                return

            # Step 2: adb remount
            self.log_message.emit(self._tr("执行 adb remount...") + "\n", None)
            remount_result = self._run_command(["adb", "-s", self.device, "remount"], timeout=10)
            self._forward_output(remount_result)

            if remount_result.returncode != 0:
                error_msg = remount_result.stderr.strip() or self._tr("执行 adb remount 失败")
                self.log_message.emit(f"❌ {error_msg}\n", "#FF0000")
                self.finished.emit(False, error_msg, False, self.device)
                return

            combined_output = (remount_result.stdout or "") + (remount_result.stderr or "")
            reboot_required = "reboot" in combined_output.lower()

            success_message = self._tr("Root&remount 完成")
            self.log_message.emit(f"✅ {success_message}\n", "#00FF00")
            self.finished.emit(True, success_message, reboot_required, self.device)

        except subprocess.TimeoutExpired as timeout_error:
            stage = self._tr("adb remount" if "remount" in str(timeout_error.cmd or []) else "adb root")
            warning_msg = f"{stage} {self._tr('执行超时')}"
            self.log_message.emit(f"⚠️ {warning_msg}\n", "#FFA500")
            self.finished.emit(False, warning_msg, False, self.device)
        except Exception as e:
            error_msg = f"{self._tr('执行 Root&remount 时发生错误:')} {e}"
            self.log_message.emit(f"❌ {error_msg}\n", "#FF0000")
            self.finished.emit(False, error_msg, False, self.device)


class UpdateWorker(QThread):
    """在后台执行更新检查与下载"""

    status_message = Signal(str)
    progress_changed = Signal(int, int)  # downloaded, total (-1 表示未知)
    update_not_required = Signal(str)
    update_available = Signal(dict)
    download_finished = Signal(LatestManifest, DownloadResult)
    update_failed = Signal(str, dict)  # 修改：添加额外信息字典参数
    # 新增信号：备用下载地址
    alternative_url_info = Signal(str, str, str)  # region, url, message

    def __init__(self, update_manager: UpdateManager, lang_manager=None):
        super().__init__()
        self._manager = update_manager
        self._lang_manager = lang_manager
        self._cancel_requested = False
        self._decision_event = threading.Event()
        self._should_download = False

    def _tr(self, text: str) -> str:
        if self._lang_manager:
            try:
                return self._lang_manager.tr(text)
            except Exception:
                return text
        return text

    def request_cancel(self) -> None:
        """请求取消当前操作"""

        self._cancel_requested = True
        self._decision_event.set()
        try:
            self._manager.cancel_download()
        except Exception:
            pass

    def allow_download(self) -> None:
        logger.debug("UpdateWorker: allow_download called")
        self._should_download = True
        self._decision_event.set()

    def reject_download(self) -> None:
        logger.debug("UpdateWorker: reject_download called")
        self._should_download = False
        self._decision_event.set()

    def run(self) -> None:
        logger.debug("UpdateWorker: run start")
        self._cancel_requested = False
        self._decision_event.clear()
        self._should_download = False

        try:
            self.status_message.emit(self._tr("正在检查更新..."))
            manifest = self._manager.fetch_latest_manifest()
            logger.debug(f"UpdateWorker: manifest fetched -> {manifest.version}")

            if not self._manager.is_update_available(manifest):
                logger.debug("UpdateWorker: no update available")
                self.update_not_required.emit(self._tr("当前已是最新版本"))
                return

            # 检测地区
            detected_region = self._manager._detect_region()
            logger.debug(f"UpdateWorker: detected region = {detected_region}")
            
            # 准备 manifest 数据，包含备用地址信息
            manifest_dict = manifest.to_dict()
            manifest_dict['_detected_region'] = detected_region
            
            # 获取备用下载地址
            if detected_region == "cn":
                # 中国区：获取备用地址（通常是网盘链接）
                alternative_url = self._manager.get_alternative_download_url(manifest, "cn")
                if alternative_url:
                    manifest_dict['_alternative_url'] = alternative_url
                    manifest_dict['_alternative_region'] = "cn"
            else:
                # 非中国区：获取 GitHub 和 Gitee 作为备用
                github_url = self._manager.get_alternative_download_url(manifest, "us") or manifest.download_url
                gitee_url = self._manager.get_alternative_download_url(manifest, "cn")
                manifest_dict['_primary_url'] = github_url
                if gitee_url:
                    manifest_dict['_alternative_url'] = gitee_url
                    manifest_dict['_alternative_region'] = "cn"

            logger.debug("UpdateWorker: update available, wait for decision")
            self.update_available.emit(manifest_dict)
            self._decision_event.wait()
            logger.debug(f"UpdateWorker: decision event set, should_download={self._should_download} cancel={self._cancel_requested}")

            if self._cancel_requested or not self._should_download:
                logger.debug("UpdateWorker: decision -> cancel")
                # 用户取消：传递备用地址信息
                error_info = {
                    'reason': 'user_cancelled',
                    'alternative_url': manifest_dict.get('_alternative_url'),
                    'alternative_region': manifest_dict.get('_alternative_region'),
                    'detected_region': detected_region
                }
                self.update_failed.emit(self._tr("用户取消更新"), error_info)
                return

            # 中国区特殊处理：不自动下载，提示用户手动下载
            if detected_region == "cn" and manifest_dict.get('_alternative_url'):
                error_info = {
                    'reason': 'manual_download_required',
                    'alternative_url': manifest_dict['_alternative_url'],
                    'alternative_region': 'cn',
                    'detected_region': detected_region
                }
                self.update_failed.emit(
                    self._tr("检测到新版本，请前往备用地址手动下载"),
                    error_info
                )
                # 同时发送备用地址信息
                self.alternative_url_info.emit(
                    "cn",
                    manifest_dict['_alternative_url'],
                    self._tr("中国区域用户，请使用以下地址手动下载：")
                )
                return

            self.status_message.emit(self._tr("检测到新版本，开始下载安装包..."))

            def _on_progress(downloaded: int, total: Optional[int]) -> None:
                self.progress_changed.emit(downloaded, total if total is not None else -1)

            result = self._manager.download_release(manifest, progress_callback=_on_progress)

            if self._cancel_requested:
                logger.debug("UpdateWorker: cancel after download started")
                # 下载被取消：传递备用地址信息
                error_info = {
                    'reason': 'download_cancelled',
                    'alternative_url': manifest_dict.get('_alternative_url'),
                    'alternative_region': manifest_dict.get('_alternative_region'),
                    'detected_region': detected_region
                }
                self.update_failed.emit(self._tr("下载已取消"), error_info)
                return

            logger.debug("UpdateWorker: download finished")
            self.download_finished.emit(manifest, result)

        except UpdateError as exc:
            logger.debug(f"UpdateWorker: UpdateError -> {exc}")
            # 下载失败：传递备用地址信息
            error_info = {
                'reason': 'download_failed',
                'alternative_url': manifest_dict.get('_alternative_url') if 'manifest_dict' in locals() else None,
                'alternative_region': manifest_dict.get('_alternative_region') if 'manifest_dict' in locals() else None,
                'detected_region': detected_region if 'detected_region' in locals() else None,
                'error_message': str(exc)
            }
            self.update_failed.emit(str(exc), error_info)
        except Exception as exc:  # pragma: no cover - 防御性捕获
            logger.debug(f"UpdateWorker: Exception -> {exc}")
            error_info = {
                'reason': 'unknown_error',
                'error_message': str(exc)
            }
            self.update_failed.emit(str(exc), error_info)

class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 信号定义
    device_changed = Signal(str)
    append_log = Signal(str, str)  # text, color
    update_status = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.selected_device = ""
        self._root_remount_worker = None
        self._button_command_workers = []  # 存储按钮命令工作线程
        self._update_worker = None
        self._update_progress_dialog = None
        self._update_status_text = ""
        self._update_progress_extra = ""
        self.app_version = APP_VERSION
        self._update_request_origin = "manual"
        self._update_check_interval_seconds = 24 * 60 * 60
        self._auto_update_timer = QTimer(self)
        self._auto_update_timer.setSingleShot(True)
        self._auto_update_timer.timeout.connect(self._on_auto_update_timer)
        self._suppress_progress_cancel = False
        
        # 初始化语言管理器
        self.lang_manager = LanguageManager(self)
        
        # 初始化设备管理器
        self.device_manager = PySide6DeviceManager(self)
        
        # 显示友好的加载界面
        self._show_loading_screen()
        
        # 初始化所有管理器
        self._init_managers()
        
        # 设置UI（但不显示主窗口）
        self.setup_ui()
        
        # 加载主题
        self.theme_manager.load_theme("dark")
        
        # 主题加载后，更新日志查看器的文本颜色
        if hasattr(self, 'log_viewer') and self.log_viewer:
            self.log_viewer._update_text_colors()
        
        # 连接信号槽
        self.setup_connections()
        
        # 根据保存的语言设置刷新UI
        self._refresh_all_ui_texts()
        
        # 设置log_processor的log_viewer引用
        self.log_processor.set_log_viewer(self.log_viewer)
        
        # 加载所有Tab的自定义按钮
        self.load_custom_buttons_for_all_tabs()
        
        # 连接自定义按钮管理器信号
        self.custom_button_manager.buttons_updated.connect(self.on_custom_buttons_updated)
        
        # 隐藏加载界面，显示主界面
        self._hide_loading_screen()
        
        # 异步刷新设备列表，避免阻塞UI显示
        QTimer.singleShot(100, self.device_manager.refresh_devices)

        self._initialize_auto_update_schedule()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def _set_window_icon(self):
        """设置窗口图标"""
        from PySide6.QtGui import QIcon
        import sys
        import os
        
        # 尝试设置窗口图标
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icon.ico')
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            # 验证图标是否有效
            if not icon.isNull() and icon.availableSizes() != []:
                self.setWindowIcon(icon)
                logger.info(f"窗口图标已设置: {icon_path}")
            else:
                logger.warning(f"图标文件无效: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
    
    def _show_loading_screen(self):
        """显示友好的加载界面"""
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QProgressBar
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QFont
        
        # 创建加载窗口
        self.loading_window = QWidget()
        self.loading_window.setWindowTitle(self.lang_manager.tr("手机测试辅助工具"))
        self.loading_window.setFixedSize(400, 200)
        self.loading_window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 设置窗口居中
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.loading_window.width()) // 2
        y = (screen.height() - self.loading_window.height()) // 2
        self.loading_window.move(x, y)
        
        # 设置样式
        self.loading_window.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border-radius: 10px;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self.loading_window)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # 应用标题
        title_label = QLabel(self.lang_manager.tr("手机测试辅助工具"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #4CAF50; margin-bottom: 10px;")
        
        # 加载提示
        loading_label = QLabel(self.lang_manager.tr("正在初始化..."))
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("color: #cccccc; font-size: 14px;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # 版本信息
        version_label = QLabel(f"v{self.app_version}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #888888; font-size: 12px;")
        
        # 添加到布局
        layout.addWidget(title_label)
        layout.addWidget(loading_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(version_label)
        
        # 显示加载窗口
        self.loading_window.show()
        
        # 强制刷新界面
        QApplication.processEvents()
    
    def _hide_loading_screen(self):
        """隐藏加载界面并显示主窗口"""
        if hasattr(self, 'loading_window'):
            self.loading_window.close()
            self.loading_window = None
        
        # 显示主窗口（最大化）
        self.showMaximized()
        
    def _init_managers(self):
        """初始化所有管理器"""
        # 初始化设备工具类
        from core.utilities import DeviceUtilities
        self.device_utilities = DeviceUtilities(self.device_manager, self)
        self.device_utilities.status_message.connect(self._on_device_status_message)
        self.device_utilities.reboot_started.connect(self._on_reboot_started)
        self.device_utilities.reboot_finished.connect(self._on_reboot_finished)
        
        # 初始化MTKLOG管理器
        self.mtklog_manager = PySide6MTKLogManager(self.device_manager, self)
        
        # 初始化ADB Log管理器
        self.adblog_manager = PySide6ADBLogManager(self.device_manager, self)
        
        # 初始化Log过滤管理器
        self.log_processor = PySide6LogProcessor(self.device_manager, self)
        
        # 初始化网络信息管理器
        self.network_info_manager = PySide6NetworkInfoManager(self.device_manager, self)
        
        # 初始化截图管理器
        self.screenshot_manager = PySide6ScreenshotManager(self.device_manager, self)
        
        # 初始化录制管理器
        self.video_manager = VideoManager(self.device_manager, self)
        
        # 初始化3GPP消息解码器
        self.rrc3gpp_decoder = RRC3GPPDecoder(self)
        self.rrc3gpp_decoder.status_message.connect(self._on_3gpp_decoder_status)
        
        # 初始化其他管理器
        self.tcpdump_manager = PySide6TCPDumpManager(self.device_manager, self)
        self.telephony_manager = PySide6TelephonyManager(self.device_manager, self)
        self.google_log_manager = PySide6GoogleLogManager(
            self.device_manager, 
            parent=self,
            adblog_manager=self.adblog_manager, 
            video_manager=self.video_manager
        )
        self.aee_log_manager = PySide6AEELogManager(self.device_manager, self)
        self.bugreport_manager = PySide6BugreportManager(self.device_manager, self)
        
        # 初始化TMO CC管理器
        self.tmo_cc_manager = PySide6TMOCCManager(self.device_manager, self)
        
        # 初始化Echolocate管理器
        self.echolocate_manager = PySide6EcholocateManager(self.device_manager, self)
        
        # 初始化背景数据管理器
        self.background_data_manager = PySide6BackgroundDataManager(self.device_manager, self)
        
        # 初始化APP操作管理器
        self.app_operations_manager = PySide6AppOperationsManager(self.device_manager, self)
        
        # 初始化设备信息管理器
        self.device_info_manager = PySide6DeviceInfoManager(self.device_manager, self)
        
        # 初始化赫拉配置管理器
        self.hera_config_manager = PySide6HeraConfigManager(self.device_manager, self)
        
        # 初始化其他操作管理器
        self.other_operations_manager = PySide6OtherOperationsManager(self.device_manager, self)
        
        # 添加工具配置属性，供其他管理器访问
        self.tool_config = self.other_operations_manager.tool_config
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化自定义按钮管理器
        self.custom_button_manager = CustomButtonManager(self)
        
        # 初始化log关键字管理器
        self.log_keyword_manager = LogKeywordManager(self)
        
        # 初始化Tab配置管理器
        self.tab_config_manager = TabConfigManager(self)
        
        # 重新设置CustomButtonManager的tab_config_manager引用
        self.custom_button_manager.tab_config_manager = self.tab_config_manager
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle(f"{self.lang_manager.tr('手机测试辅助工具')} v{self.app_version}")
        # 注释掉固定大小设置，使用showMaximized()时会自动设置
        # self.setGeometry(100, 100, 900, 600)
        
        # 设置窗口图标（任务栏图标）
        self._set_window_icon()
        
        # 不立即显示主窗口，等初始化完成后再显示
        
        # 创建顶部工具栏
        self.toolbar = DeviceToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 创建分割器（Tab区域 + 日志区域）
        splitter = QSplitter(Qt.Vertical)
        
        # Tab 区域
        self.tab_widget = QTabWidget()
        
        # 设置Tab内容区域最小高度
        self.tab_widget.setMinimumHeight(100)
        
        # 启用Tab拖拽排序
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(self._on_tab_moved)
        
        # 添加各个Tab
        self.setup_tabs()
        
        splitter.addWidget(self.tab_widget)
        
        # 日志显示区域
        self.log_viewer = LogViewer(self)  # 传入parent以便获取主题管理器
        splitter.addWidget(self.log_viewer)
        
        # 设置分割比例（Tab区域:日志区域 = 1:2）
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
    def setup_connections(self):
        """连接信号槽"""
        
        # 连接日志追加信号
        self.append_log.connect(self._append_log_handler)
        
        # 连接设备管理器信号
        self.device_manager.devices_updated.connect(self._on_devices_updated)
        self.device_manager.device_selected.connect(self._on_device_selected)
        self.device_manager.status_message.connect(self._on_device_status_message)
        
        # 连接MTKLOG管理器信号
        self.mtklog_manager.mtklog_started.connect(self._on_mtklog_started)
        self.mtklog_manager.mtklog_stopped.connect(self._on_mtklog_stopped)
        self.mtklog_manager.mtklog_deleted.connect(self._on_mtklog_deleted)
        self.mtklog_manager.mtklog_exported.connect(self._on_mtklog_exported)
        self.mtklog_manager.progress_updated.connect(self._on_mtklog_progress)
        self.mtklog_manager.status_message.connect(self._on_mtklog_status)
        
        # 连接ADB Log管理器信号
        self.adblog_manager.adblog_started.connect(self._on_adblog_started)
        self.adblog_manager.adblog_stopped.connect(self._on_adblog_stopped)
        self.adblog_manager.adblog_exported.connect(self._on_adblog_exported)
        self.adblog_manager.status_message.connect(self._on_adblog_status)
        self.adblog_manager.clear_old_logs_required.connect(self._on_clear_old_logs_required)
        self.adblog_manager.online_mode_started.connect(self._on_online_mode_started)
        self.adblog_manager.online_mode_stopped.connect(self._on_online_mode_stopped)
        self.adblog_manager.usb_disconnected.connect(self._on_usb_disconnected)
        self.adblog_manager.usb_reconnected.connect(self._on_usb_reconnected)
        
        # 连接Log过滤管理器信号
        self.log_processor.filtering_started.connect(self._on_filtering_started)
        self.log_processor.filtering_stopped.connect(self._on_filtering_stopped)
        self.log_processor.log_received.connect(self._on_filter_log_received)
        self.log_processor.status_message.connect(self._on_filter_status)
        
        # 连接网络信息管理器信号
        self.network_info_manager.network_info_updated.connect(self._on_network_info_updated)
        self.network_info_manager.ping_result.connect(self._on_ping_result)
        self.network_info_manager.status_message.connect(self._on_network_status)
        self.network_info_manager.network_info_started.connect(self._on_network_info_started)
        self.network_info_manager.network_info_start_failed.connect(self._on_network_info_start_failed)
        self.network_info_manager.ping_started.connect(self._on_ping_started)
        self.network_info_manager.ping_start_failed.connect(self._on_ping_start_failed)
        
        # 连接工具栏信号
        self.toolbar.device_changed.connect(self._on_device_changed)
        self.toolbar.refresh_clicked.connect(self._on_refresh_devices)
        self.toolbar.screenshot_clicked.connect(self._on_screenshot)
        self.toolbar.record_toggled.connect(self._on_record_toggled)
        self.toolbar.reboot_clicked.connect(self._on_reboot_device)
        self.toolbar.root_remount_clicked.connect(self._on_root_remount)
        self.toolbar.theme_toggled.connect(self._on_theme_toggled)
        self.toolbar.check_update_clicked.connect(self._on_check_update_clicked)
        # 工具栏中的ADB命令输入框已移到日志显示区域下方
        # self.toolbar.adb_command_executed.connect(self._on_adb_command_executed)
        
        # 连接日志查看器的ADB命令信号
        self.log_viewer.adb_command_executed.connect(self._on_adb_command_executed)
        
        # 连接语言管理器信号
        self.lang_manager.language_changed.connect(self._on_language_changed)
        
        # 设置快捷键
        self._setup_shortcuts()
        
        # 连接截图管理器信号
        self.screenshot_manager.screenshot_completed.connect(self._on_screenshot_completed)
        self.screenshot_manager.progress_updated.connect(self._on_screenshot_progress)
        self.screenshot_manager.status_message.connect(self._on_screenshot_status)
        
        # 连接录制管理器信号
        self.video_manager.recording_started.connect(self._on_recording_started)
        self.video_manager.recording_stopped.connect(self._on_recording_stopped)
        self.video_manager.video_saved.connect(self._on_video_saved)
        self.video_manager.status_message.connect(self._on_video_status)
        
        # 连接其他管理器信号
        self.tcpdump_manager.status_message.connect(self._on_tcpdump_status)
        self.telephony_manager.status_message.connect(self._on_telephony_status)
        self.google_log_manager.status_message.connect(self._on_google_log_status)
        self.google_log_manager.google_log_started.connect(self._on_google_log_started)
        self.google_log_manager.google_log_stopped.connect(self._on_google_log_stopped)
        self.aee_log_manager.status_message.connect(self._on_aee_log_status)
        self.bugreport_manager.status_message.connect(self._on_bugreport_status)
        
        # 连接TMO CC管理器信号
        self.tmo_cc_manager.cc_pulled.connect(self._on_cc_pulled)
        self.tmo_cc_manager.cc_pushed.connect(self._on_cc_pushed)
        self.tmo_cc_manager.server_started.connect(self._on_server_started)
        self.tmo_cc_manager.status_message.connect(self._on_tmo_cc_status)
        
        # 连接Echolocate管理器信号
        self.echolocate_manager.echolocate_installed.connect(self._on_echolocate_installed)
        self.echolocate_manager.echolocate_triggered.connect(self._on_echolocate_triggered)
        self.echolocate_manager.file_pulled.connect(self._on_echolocate_file_pulled)
        self.echolocate_manager.file_deleted.connect(self._on_echolocate_file_deleted)
        self.echolocate_manager.status_message.connect(self._on_echolocate_status)
        self.echolocate_manager.log_message.connect(self._on_echolocate_log)
        
        # 连接背景数据管理器信号
        self.background_data_manager.status_message.connect(self._on_background_data_status)
        self.background_data_manager.log_message.connect(self._on_background_data_log)
        
        # 连接APP操作管理器信号
        self.app_operations_manager.status_message.connect(self._on_app_operations_status)
        
        # 连接设备信息管理器信号
        self.device_info_manager.status_message.connect(self._on_device_info_status)
        
        # 连接赫拉配置管理器信号
        self.hera_config_manager.status_message.connect(self._on_hera_config_status)
        
        # 连接其他操作管理器信号
        self.other_operations_manager.status_message.connect(self._on_other_operations_status)
        
        # 连接 SIM Tab 信号
        self.sim_tab.status_message.connect(self._on_sim_status_message)
        
        # 连接 Log控制 Tab 信号
        self.log_control_tab.mtklog_start.connect(self._on_mtklog_start)
        self.log_control_tab.mtklog_stop_export.connect(self._on_mtklog_stop_export)
        self.log_control_tab.mtklog_delete.connect(self._on_mtklog_delete)
        self.log_control_tab.mtklog_set_log_size.connect(self._on_mtklog_set_log_size)
        self.log_control_tab.mtklog_sd_mode.connect(self._on_mtklog_sd_mode)
        self.log_control_tab.mtklog_usb_mode.connect(self._on_mtklog_usb_mode)
        self.log_control_tab.mtklog_install.connect(self._on_mtklog_install)
        self.log_control_tab.adblog_start.connect(self._on_adblog_start)
        self.log_control_tab.adblog_online_start.connect(self._on_adblog_online_start)
        self.log_control_tab.adblog_export.connect(self._on_adblog_export)
        self.log_control_tab.telephony_enable.connect(self._on_telephony_enable)
        self.log_control_tab.google_log_toggle.connect(self._on_google_log_toggle)
        self.log_control_tab.bugreport_generate.connect(self._on_bugreport_generate)
        self.log_control_tab.bugreport_pull.connect(self._on_bugreport_pull)
        self.log_control_tab.bugreport_delete.connect(self._on_bugreport_delete)
        self.log_control_tab.aee_log_start.connect(self._on_aee_log_start)
        self.log_control_tab.tcpdump_show_dialog.connect(self._on_tcpdump_show_dialog)
        
        # 连接 Log过滤 Tab 信号
        self.log_filter_tab.start_filtering.connect(self._on_start_filtering)
        self.log_filter_tab.stop_filtering.connect(self._on_stop_filtering)
        self.log_filter_tab.manage_log_keywords.connect(self._on_manage_log_keywords)
        self.log_filter_tab.clear_logs.connect(self._on_clear_logs)
        self.log_filter_tab.clear_device_logs.connect(self._on_clear_device_logs)
        self.log_filter_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
        self.log_filter_tab.save_logs.connect(self._on_save_logs)
        
        # Log处理器信号连接
        self.log_processor.keyword_loaded.connect(self._on_keyword_loaded)
        self.log_processor.filter_state_changed.connect(self._on_filter_state_changed)
        
        # 连接 网络信息 Tab 信号
        self.network_info_tab.start_network_info.connect(self._on_start_network_info)
        self.network_info_tab.stop_network_info.connect(self._on_stop_network_info)
        self.network_info_tab.start_ping.connect(self._on_start_ping)
        self.network_info_tab.stop_ping.connect(self._on_stop_ping)
        
        # 连接 TMO CC Tab 信号
        self.tmo_cc_tab.push_cc_file.connect(self._on_push_cc_file)
        self.tmo_cc_tab.pull_cc_file.connect(self._on_pull_cc_file)
        self.tmo_cc_tab.simple_filter.connect(self._on_simple_filter)
        self.tmo_cc_tab.complete_filter.connect(self._on_complete_filter)
        self.tmo_cc_tab.prod_server.connect(self._on_prod_server)
        self.tmo_cc_tab.stg_server.connect(self._on_stg_server)
        self.tmo_cc_tab.clear_logs.connect(self._on_clear_logs)
        self.tmo_cc_tab.clear_device_logs.connect(self._on_clear_device_logs)
        
        # 连接 TMO Echolocate Tab 信号
        self.tmo_echolocate_tab.install_echolocate.connect(self._on_install_echolocate)
        self.tmo_echolocate_tab.trigger_echolocate.connect(self._on_trigger_echolocate)
        self.tmo_echolocate_tab.pull_echolocate_file.connect(self._on_pull_echolocate_file)
        self.tmo_echolocate_tab.delete_echolocate_file.connect(self._on_delete_echolocate_file)
        self.tmo_echolocate_tab.get_echolocate_version.connect(self._on_get_echolocate_version)
        self.tmo_echolocate_tab.filter_callid.connect(self._on_filter_callid)
        self.tmo_echolocate_tab.filter_callstate.connect(self._on_filter_callstate)
        self.tmo_echolocate_tab.filter_uicallstate.connect(self._on_filter_uicallstate)
        self.tmo_echolocate_tab.filter_allcallstate.connect(self._on_filter_allcallstate)
        self.tmo_echolocate_tab.filter_ims_signalling.connect(self._on_filter_ims_signalling)
        self.tmo_echolocate_tab.filter_allcallflow.connect(self._on_filter_allcallflow)
        self.tmo_echolocate_tab.filter_voice_intent.connect(self._on_filter_voice_intent)
        
        # 连接 24小时背景数据 Tab 信号
        self.background_data_tab.configure_phone.connect(self._on_configure_phone)
        self.background_data_tab.analyze_logs.connect(self._on_analyze_logs)
        
        # 连接 APP操作 Tab 信号
        try:
            self.app_operations_tab.query_package.connect(self._on_query_package)
            self.app_operations_tab.query_package_name.connect(self._on_query_package_name)
            self.app_operations_tab.query_install_path.connect(self._on_query_install_path)
            self.app_operations_tab.query_find_file.connect(self._on_query_find_file)
            self.app_operations_tab.pull_apk.connect(self._on_pull_apk)
            self.app_operations_tab.push_apk.connect(self._on_push_apk)
            self.app_operations_tab.install_apk.connect(self._on_install_apk)
            self.app_operations_tab.view_processes.connect(self._on_view_processes)
            self.app_operations_tab.dump_app.connect(self._on_dump_app)
            self.app_operations_tab.enable_app.connect(self._on_enable_app)
            self.app_operations_tab.disable_app.connect(self._on_disable_app)
            logger.debug("AppOperationsTab 信号槽连接完成")
        except Exception as e:
            logger.error(f"连接 AppOperationsTab 信号槽失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        
        # 连接 log_control Tab 信号（从其他Tab移过来的log操作按钮）
        self.log_control_tab.merge_mtklog.connect(self._on_merge_mtklog)
        self.log_control_tab.extract_pcap_from_mtklog.connect(self._on_extract_pcap_from_mtklog)
        self.log_control_tab.merge_pcap.connect(self._on_merge_pcap)
        self.log_control_tab.extract_pcap_from_qualcomm_log.connect(self._on_extract_pcap_from_qualcomm_log)
        self.log_control_tab.parse_3gpp_message.connect(self._on_parse_3gpp_message)
        self.log_control_tab.mtk_sip_decode.connect(self._on_mtk_sip_decode)
        
        # 连接办公工具Tab信号
        try:
            if hasattr(self, 'office_tool_tab'):
                self.office_tool_tab.show_jira_tool.connect(self._on_show_jira_tool)
        except Exception as e:
            logger.error(f"连接OfficeToolTab信号槽失败: {e}")
        
        # 连接 其他 Tab 信号
        try:
            self.other_tab.show_device_info_dialog.connect(self._on_show_device_info_dialog)
            self.other_tab.set_screen_timeout.connect(self._on_set_screen_timeout)
            self.other_tab.configure_hera.connect(self._on_configure_hera)
            self.other_tab.configure_collect_data.connect(self._on_configure_collect_data)
            self.other_tab.show_input_text_dialog.connect(self._on_show_input_text_dialog)
            self.other_tab.show_tools_config_dialog.connect(self._on_show_tools_config_dialog)
            self.other_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
            self.other_tab.show_at_tool_dialog.connect(self._on_show_at_tool_dialog)
            self.other_tab.show_config_backup_dialog.connect(self.show_config_backup_dialog)
            self.other_tab.show_unified_manager.connect(self.show_unified_manager_dialog)
            self.other_tab.show_secret_code_dialog.connect(self.show_secret_code_dialog)
            self.other_tab.show_lock_cell_dialog.connect(self.show_lock_cell_dialog)
            self.other_tab.show_qc_nv_dialog.connect(self.show_qc_nv_dialog)
            self.other_tab.show_pr_translation_dialog.connect(self._on_show_pr_translation_dialog)
            # 验证关键信号连接是否成功
            try:
                receivers = QObject.receivers(self.other_tab, self.other_tab.show_pr_translation_dialog)
                if receivers == 0:
                    logger.error("✗ show_pr_translation_dialog 信号连接失败！")
            except Exception as check_error:
                logger.warning(f"无法检查信号 show_pr_translation_dialog 的接收器数量: {check_error}")
            self.other_tab.show_encoding_tool_dialog.connect(self._on_show_encoding_tool_dialog)
            logger.debug("OtherTab 信号槽连接完成")
        except Exception as e:
            logger.error(f"连接 OtherTab 信号槽失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        
        # 连接Tab配置管理器信号
        self.tab_config_manager.tab_config_updated.connect(self._on_tab_config_updated)
        
    def _ensure_app_core_importable(self):
        """
        确保导入到的是主工程的 core 包，而不是 sim_reader/core 或其它子工程中的同名 core。
        这在某些功能（例如 SIM Reader）动态修改 sys.path/sys.modules 后，可能导致概率性导入失败。
        """
        try:
            import sys
            import os
            import importlib

            # 计算项目根目录（开发环境）或 PyInstaller base_path（打包环境）
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                project_root = sys._MEIPASS
            else:
                # ui/main_window.py -> ui -> 项目根目录
                current_file = os.path.abspath(__file__)
                project_root = os.path.dirname(os.path.dirname(current_file))

            normalized_project_root = os.path.normpath(os.path.abspath(project_root))
            expected_core_init = os.path.normpath(os.path.join(project_root, "core", "__init__.py"))
            normalized_sim_reader_root = os.path.normpath(os.path.abspath(os.path.join(project_root, "sim_reader")))

            # 置顶 project_root，避免同名包被更前的路径抢占
            try:
                if project_root in sys.path:
                    sys.path.remove(project_root)
            except ValueError:
                pass
            sys.path.insert(0, project_root)

            def _module_file(mod):
                return getattr(mod, "__file__", None) or ""

            def _looks_like_wrong_core(mod) -> bool:
                mod_file = _module_file(mod)
                if not mod_file:
                    return True
                normalized_mod_file = os.path.normpath(os.path.abspath(mod_file))
                # sim_reader 的 core 一律视为冲突
                if normalized_sim_reader_root in normalized_mod_file:
                    return True
                # core 包不在预期位置，也视为冲突（例如 SIM_APDU_Parser/core）
                if expected_core_init and normalized_mod_file != expected_core_init:
                    return True
                # 文件不存在也视为脏缓存
                if not os.path.exists(mod_file):
                    return True
                # 兜底：确保来自项目根目录
                if normalized_project_root not in normalized_mod_file:
                    return True
                return False

            core_pkg = sys.modules.get("core")
            if core_pkg is not None and _looks_like_wrong_core(core_pkg):
                for name in list(sys.modules.keys()):
                    if name == "core" or name.startswith("core."):
                        sys.modules.pop(name, None)
                importlib.invalidate_caches()
        except Exception as e:
            # 兜底：不影响主流程，只记录 debug
            try:
                logger.debug(f"[MainWindow] ensure_app_core_importable failed: {e}")
            except Exception:
                pass

    def setup_tabs(self):
        """设置Tab页面"""
        logger.info(self.lang_manager.tr("开始初始化所有Tab页面..."))
        
        try:
            # 关键：某些功能可能修改 sys.path / sys.modules 导致同名 core 包污染，先恢复到主工程 core
            self._ensure_app_core_importable()

            # 修复tab_order，确保包含所有默认tab和自定义tab
            # 这样可以避免因为配置不完整导致tab无法显示的问题
            self.tab_config_manager._fix_tab_order()
            
            # 获取Tab配置
            tab_order = self.tab_config_manager.get_tab_order()
            tab_visibility = self.tab_config_manager.get_tab_visibility()
            all_tabs = self.tab_config_manager.get_all_tabs()
            
            
            # 创建tab实例映射
            tab_instances = {}
            
            # 初始化所有默认Tab
            # 注意：不传递 parent 参数，避免与 QTabWidget.addTab() 时的 parent 设置冲突
            # 在创建后手动设置 lang_manager
            
            self.log_control_tab = LogControlTab()
            self.log_control_tab.lang_manager = self.lang_manager
            self.log_control_tab.tab_id = 'log_control'  # 添加tab_id属性
            tab_instances['log_control'] = self.log_control_tab
            
            self.log_filter_tab = LogFilterTab()
            self.log_filter_tab.lang_manager = self.lang_manager
            self.log_filter_tab.tab_id = 'log_filter'  # 添加tab_id属性
            tab_instances['log_filter'] = self.log_filter_tab
            
            self.network_info_tab = NetworkInfoTab()
            self.network_info_tab.lang_manager = self.lang_manager
            self.network_info_tab.tab_id = 'network_info'  # 添加tab_id属性
            tab_instances['network_info'] = self.network_info_tab
            
            self.tmo_cc_tab = TMOCCTab()
            self.tmo_cc_tab.lang_manager = self.lang_manager
            self.tmo_cc_tab.tab_id = 'tmo_cc'  # 添加tab_id属性
            tab_instances['tmo_cc'] = self.tmo_cc_tab
            
            self.tmo_echolocate_tab = TMOEcholocateTab()
            self.tmo_echolocate_tab.lang_manager = self.lang_manager
            self.tmo_echolocate_tab.tab_id = 'tmo_echolocate'  # 添加tab_id属性
            tab_instances['tmo_echolocate'] = self.tmo_echolocate_tab
            
            self.background_data_tab = BackgroundDataTab()
            self.background_data_tab.lang_manager = self.lang_manager
            self.background_data_tab.tab_id = 'background_data'  # 添加tab_id属性
            tab_instances['background_data'] = self.background_data_tab
            
            self.app_operations_tab = AppOperationsTab()
            self.app_operations_tab.lang_manager = self.lang_manager
            self.app_operations_tab.tab_id = 'app_operations'  # 添加tab_id属性
            tab_instances['app_operations'] = self.app_operations_tab
            
            self.office_tool_tab = OfficeToolTab()
            self.office_tool_tab.lang_manager = self.lang_manager
            self.office_tool_tab.tab_id = 'office_tool'  # 添加tab_id属性
            tab_instances['office_tool'] = self.office_tool_tab
            
            self.other_tab = OtherTab()
            self.other_tab.lang_manager = self.lang_manager
            self.other_tab.tab_id = 'other'  # 添加tab_id属性
            tab_instances['other'] = self.other_tab
            
            self.sim_tab = SimTab()
            self.sim_tab.lang_manager = self.lang_manager
            self.sim_tab.tab_id = 'sim'  # 添加tab_id属性
            tab_instances['sim'] = self.sim_tab
            
            # 初始化自定义Tab
            for custom_tab in self.tab_config_manager.custom_tabs:
                tab_id = custom_tab['id']
                tab_name = custom_tab['name']
                
                # 创建自定义Tab实例（这里可以扩展为动态创建）
                custom_tab_instance = self._create_custom_tab_instance(custom_tab)
                if custom_tab_instance:
                    tab_instances[tab_id] = custom_tab_instance
            
            # 按照配置的顺序添加Tab
            for tab_id in tab_order:
                if tab_id in tab_instances and tab_visibility.get(tab_id, True):
                    tab_instance = tab_instances[tab_id]
                    tab_name = self._get_tab_name(tab_id, all_tabs)
                    
                    # 添加Tab到QTabWidget（QTabWidget会自动设置parent并管理布局）
                    self.tab_widget.addTab(tab_instance, tab_name)
            
            logger.info(self.lang_manager.tr("所有Tab页面初始化完成"))
            
            # 为所有预置Tab的card添加右键菜单
            self._setup_preset_tab_card_context_menus()
            
        except Exception as e:
            logger.exception(self.lang_manager.tr("Tab页面初始化失败"))
            raise
    
    def _get_tab_name(self, tab_id, all_tabs):
        """获取Tab名称（已翻译）"""
        # 首先在all_tabs中查找
        for tab in all_tabs:
            if tab['id'] == tab_id:
                # 获取原始名称并翻译
                original_name = tab['name']
                return self.lang_manager.tr(original_name) if self.lang_manager else original_name
        
        # 如果找不到，使用默认映射并翻译
        default_names = {
            'log_control': 'Log控制',
            'log_filter': 'Log过滤',
            'network_info': '网络信息',
            'tmo_cc': 'TMO CC',
            'tmo_echolocate': 'TMO Echolocate',
            'background_data': '24小时背景数据',
            'app_operations': 'APP操作',
            'office_tool': '办公工具',
            'other': '其他',
            'sim': 'SIM'
        }
        
        original_name = default_names.get(tab_id, tab_id)
        # 翻译名称
        return self.lang_manager.tr(original_name) if self.lang_manager else original_name
    
    def _create_custom_tab_instance(self, custom_tab):
        """创建自定义Tab实例"""
        try:
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
            from PySide6.QtCore import Qt
            
            widget = QWidget()
            widget.tab_id = custom_tab['id']  # 设置tab_id属性
            
            # 主布局
            main_layout = QVBoxLayout(widget)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(1)  # 与大部分预置tab一致
            
            # 添加自定义Card
            custom_cards = self.tab_config_manager.get_custom_cards_for_tab(custom_tab['id'])
            for card in custom_cards:
                card_group = self._create_custom_card_group(card, widget)
                if card_group:
                    scroll_layout.addWidget(card_group)
            
            # 如果没有Card，添加提示
            if not custom_cards:
                no_cards_label = QLabel(self.tr("暂无自定义Card，请在Tab管理中创建"))
                no_cards_label.setStyleSheet("color: #666; font-style: italic;")
                scroll_layout.addWidget(no_cards_label)
            
            scroll_layout.addStretch()
            scroll_area.setWidget(scroll_widget)
            main_layout.addWidget(scroll_area)
            
            return widget
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Tab实例失败:')} {e}")
            return None
    
    def _create_custom_card_group(self, card, tab_widget):
        """创建自定义Card组（仅创建结构，按钮由统一方法添加）"""
        try:
            from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QToolTip, QSizePolicy
            from PySide6.QtCore import Qt, QEvent, QObject
            from ui.widgets.shadow_utils import add_card_shadow
            
            # 使用与预置tab一致的现代结构：QLabel + QFrame
            # 容器
            container = QWidget()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)  # 与预置tab一致的间距
            
            # 标题
            title = QLabel(card['name'])
            title.setProperty("class", "section-title")
            # 方案A：标题不占满整行，只占文字宽度，避免“标题行空白处也触发 tooltip”
            title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # 描述不直接占用界面空间：鼠标悬停通过 tooltip 查看完整描述
            # 仅在标题处显示 tooltip（不在 card 其它区域显示，避免干扰）
            card_desc = (card.get('description') or '').strip()
            if card_desc:
                try:
                    # 某些场景下 QLabel 的默认 tooltip 触发不稳定：用事件过滤器强制只在标题悬停时显示
                    class _TitleTooltipFilter(QObject):
                        def __init__(self, text, parent=None):
                            super().__init__(parent)
                            self._text = text

                        def eventFilter(self, obj, event):
                            if event.type() == QEvent.ToolTip:
                                QToolTip.showText(event.globalPos(), self._text, obj)
                                return True
                            return False

                    tooltip_filter = _TitleTooltipFilter(card_desc, title)
                    if not hasattr(self, "_custom_card_title_tooltip_filters"):
                        self._custom_card_title_tooltip_filters = []
                    self._custom_card_title_tooltip_filters.append(tooltip_filter)  # 防止被GC回收
                    title.installEventFilter(tooltip_filter)
                    title.setAttribute(Qt.WA_AlwaysShowToolTips, True)
                except Exception:
                    pass
            # 用一行容器包住标题：左侧标题 + 右侧 stretch
            title_row = QWidget()
            title_row_layout = QHBoxLayout(title_row)
            title_row_layout.setContentsMargins(0, 0, 0, 0)
            title_row_layout.setSpacing(0)
            title_row_layout.addWidget(title, 0, Qt.AlignLeft)
            title_row_layout.addStretch(1)
            v.addWidget(title_row)
            
            # 卡片
            card_frame = QFrame()
            card_frame.setObjectName("card")
            add_card_shadow(card_frame)
            card_frame.setProperty('custom_card', True)  # 标记为自定义Card
            # 直接存储 card_name，避免后续通过布局回溯推断失败导致右键菜单无法弹出
            card_frame.setProperty('card_name', card.get('name', ''))
            
            # 统一使用水平布局（与预置tab一致），描述通过标题 tooltip 展示，避免占用卡片空间
            card_layout = QHBoxLayout(card_frame)
            card_layout.setContentsMargins(10, 1, 10, 1)
            card_layout.setSpacing(8)
            card_layout.addStretch()  # 添加stretch，按钮会插入到stretch之前
            
            v.addWidget(card_frame)
            
            # 为自定义card的QFrame添加右键菜单
            card_frame.setContextMenuPolicy(Qt.CustomContextMenu)
            card_frame.customContextMenuRequested.connect(
                lambda pos: self._show_card_context_menu(pos, card_frame, tab_widget)
            )
            
            return container
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Card组失败:')} {e}")
            return None
    
    def _get_tab_name_by_id(self, tab_id):
        """根据Tab ID获取Tab名称"""
        all_tabs = self.tab_config_manager.get_all_tabs()
        for tab in all_tabs:
            if tab['id'] == tab_id:
                return tab['name']
        return tab_id
    
    def _find_custom_card_by_name(self, card_name):
        """根据Card名称查找自定义Card"""
        try:
            for card in self.tab_config_manager.custom_cards:
                if card['name'] == card_name:
                    return card
            return None
        except Exception as e:
            logger.exception(f"{self.tr('查找自定义Card失败:')} {e}")
            return None
    
    def _find_custom_card_id_by_name_and_tab(self, card_name, tab_id):
        """根据Card名称和Tab ID查找自定义Card的ID"""
        try:
            for card in self.tab_config_manager.custom_cards:
                if card['name'] == card_name and card.get('tab_id') == tab_id:
                    return card.get('id')
            return None
        except Exception as e:
            logger.exception(f"{self.tr('查找自定义Card ID失败:')} {e}")
            return None
    
    def _get_card_name_from_frame_simple(self, card_frame, tab_widget):
        """简单方法：从card frame获取card名称（用于初始化时存储）"""
        try:
            from PySide6.QtWidgets import QLabel
            
            # 获取card frame的父widget（通常是container）
            parent_widget = card_frame.parent()
            if not parent_widget:
                return None
            
            parent_layout = parent_widget.layout()
            if not parent_layout:
                return None
            
            # 遍历parent_layout，找到card_frame的位置
            frame_index = -1
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget == card_frame:
                        frame_index = i
                        break
                    elif widget:
                        # 检查widget是否包含card_frame
                        widget_layout = widget.layout()
                        if widget_layout:
                            for j in range(widget_layout.count()):
                                layout_item = widget_layout.itemAt(j)
                                if layout_item:
                                    child_widget = layout_item.widget()
                                    if child_widget == card_frame:
                                        frame_index = i
                                        break
                            if frame_index >= 0:
                                break
            
            # 如果找到了frame的位置，查找它前面最近的section-title label
            if frame_index >= 0:
                # 从frame_index-1开始向前查找
                for i in range(frame_index - 1, -1, -1):
                    item = parent_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget:
                            # 情况1：标题本身就是一个 QLabel（常见：QLabel + card QFrame 的结构）
                            if isinstance(widget, QLabel):
                                label_class = widget.property("class")
                                if label_class == "section-title":
                                    return widget.text()

                            # 情况2：标题在某个容器 widget 的 layout 中
                            widget_layout = widget.layout()
                            if widget_layout:
                                # 遍历widget_layout查找label
                                for j in range(widget_layout.count()):
                                    layout_item = widget_layout.itemAt(j)
                                    if layout_item:
                                        child_widget = layout_item.widget()
                                        if isinstance(child_widget, QLabel):
                                            label_class = child_widget.property("class")
                                            if label_class == "section-title":
                                                return child_widget.text()
            
            return None
        except Exception as e:
            logger.exception(f"{self.tr('获取Card名称失败:')} {e}")
            return None
    
    def _get_card_name_from_frame(self, card_frame, tab_widget=None):
        """从card frame获取card名称"""
        try:
            # 首先尝试从frame的属性中获取（如果已设置）
            card_name = card_frame.property('card_name')
            if card_name:
                return card_name
            
            # 如果没有存储，使用查找方法
            from PySide6.QtWidgets import QLabel
            
            # 如果没有传入tab_widget，尝试查找
            if not tab_widget:
                tab_widget = self._find_tab_widget_for_frame(card_frame)
            
            # 获取当前tab的可用card列表用于验证
            tab_name = None
            available_cards = []
            if tab_widget:
                tab_info = self._get_tab_info_from_widget(tab_widget)
                if tab_info:
                    tab_name = tab_info['name']
                    available_cards = self.custom_button_manager.get_available_cards(tab_name)
            
            # 使用简单方法查找card名称
            card_name = self._get_card_name_from_frame_simple(card_frame, tab_widget)
            if card_name:
                # 验证card_name是否在当前tab的可用card列表中
                if not available_cards or card_name in available_cards:
                    # 存储到frame属性中，下次直接使用
                    card_frame.setProperty('card_name', card_name)
                    return card_name
                else:
                    logger.debug(f"{self.tr('Card名称验证失败')}: {card_name} 不在 {available_cards} 中, tab_name={tab_name}")
            
            return None
        except Exception as e:
            logger.exception(f"{self.tr('获取Card名称失败:')} {e}")
            return None
    
    def _find_tab_widget_for_frame(self, card_frame):
        """查找card_frame所在的tab_widget"""
        try:
            widget = card_frame
            # 向上遍历parent，找到tab_widget（有tab_id属性的widget）
            while widget:
                if hasattr(widget, 'tab_id'):
                    return widget
                widget = widget.parent()
            return None
        except Exception as e:
            logger.exception(f"{self.tr('查找Tab Widget失败:')} {e}")
            return None
    
    def _get_tab_info_from_widget(self, tab_widget):
        """从tab widget获取tab信息（id、名称、是否自定义）"""
        try:
            # 从tab widget的tab_id属性获取tab id
            tab_id = None
            if hasattr(tab_widget, 'tab_id'):
                tab_id = tab_widget.tab_id
            
            if not tab_id:
                return None
            
            # 查询tab_config_manager获取tab信息
            all_tabs = self.tab_config_manager.get_all_tabs()
            for tab in all_tabs:
                if tab['id'] == tab_id:
                    tab_name = tab.get('name', '')
                    is_custom = tab.get('custom', False)
                    return {
                        'id': tab_id,
                        'name': tab_name,
                        'is_custom': is_custom
                    }
            
            return None
        except Exception as e:
            logger.exception(f"{self.tr('获取Tab信息失败:')} {e}")
            return None
    
    def _show_card_context_menu(self, position, card_frame, tab_widget):
        """显示card的右键菜单"""
        try:
            from PySide6.QtWidgets import QMenu, QPushButton
            from PySide6.QtGui import QAction

            # 只在 card 的“空白处”显示卡片菜单：
            # - 右键点在任意 QPushButton（含预置/自定义）上：不弹卡片菜单
            # - 右键点在其它子控件（如 QLabel 等）上：也不弹（避免误触）
            # - 右键点在按钮容器(CustomButtonContainer)的空白区域：允许弹出（视为 card 空白）
            clicked = card_frame.childAt(position)
            if clicked is not None:
                w = clicked
                while w is not None and w != card_frame:
                    if isinstance(w, QPushButton):
                        return
                    if w.property("custom_button_container"):
                        break
                    w = w.parent()
                else:
                    # 点在非空白子控件上
                    return
            
            # 获取tab信息（先获取，用于验证card名称）
            tab_info = self._get_tab_info_from_widget(tab_widget)
            if not tab_info:
                logger.debug(f"{self.tr('无法获取Tab信息')}")
                return
            
            tab_id = tab_info['id']
            tab_name = tab_info['name']
            is_custom_tab = tab_info['is_custom']
            
            # 获取card名称（传入tab_widget用于验证）
            card_name = self._get_card_name_from_frame(card_frame, tab_widget)
            if not card_name:
                logger.debug(f"{self.tr('无法获取Card名称')}, tab_id={tab_id}, tab_name={tab_name}")
                return
            
            logger.debug(f"{self.tr('右键菜单')}: tab_id={tab_id}, tab_name={tab_name}, card_name={card_name}")
            
            # 创建右键菜单
            menu = QMenu(self)
            
            # 添加Button选项（所有tab都支持）
            add_button_action = QAction(self.tr("添加Button"), self)
            add_button_action.triggered.connect(
                lambda: self._add_button_from_card_context(tab_id, tab_name, card_name)
            )
            menu.addAction(add_button_action)
            
            # 添加Card选项（只有自定义tab支持）
            if is_custom_tab:
                menu.addSeparator()
                add_card_action = QAction(self.tr("添加Card"), self)
                add_card_action.triggered.connect(
                    lambda: self._add_card_from_context(tab_id)
                )
                menu.addAction(add_card_action)
                
                # 检查是否为自定义Card，如果是则添加编辑和删除选项
                card_id = self._find_custom_card_id_by_name_and_tab(card_name, tab_id)
                if card_id:
                    menu.addSeparator()
                    edit_card_action = QAction(self.tr("编辑Card"), self)
                    edit_card_action.triggered.connect(
                        lambda: self._edit_card_from_context(card_id)
                    )
                    menu.addAction(edit_card_action)
                    
                    delete_card_action = QAction(self.tr("删除Card"), self)
                    delete_card_action.triggered.connect(
                        lambda: self._delete_card_from_context(card_id, card_name)
                    )
                    menu.addAction(delete_card_action)
            
            # 显示菜单
            menu.exec(card_frame.mapToGlobal(position))
            
        except Exception as e:
            logger.exception(f"{self.tr('显示Card右键菜单失败:')} {e}")
    
    def _add_button_from_card_context(self, tab_id, tab_name, card_name):
        """从右键菜单添加button"""
        try:
            from ui.custom_button_dialog import ButtonEditDialog
            from PySide6.QtWidgets import QDialog, QMessageBox
            
            # 打开按钮对话框，预设tab和card
            dialog = ButtonEditDialog(
                self.custom_button_manager,
                preset_tab_name=tab_name,
                preset_card_name=card_name,
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 获取按钮数据并添加到管理器
                button_data = dialog.get_button_data()
                if self.custom_button_manager.add_button(button_data):
                    # 刷新按钮显示
                    self.custom_button_manager.buttons_updated.emit()
                    QMessageBox.information(self, self.tr("成功"), self.tr("按钮添加成功！"))
                else:
                    QMessageBox.warning(self, self.tr("失败"), self.tr("按钮添加失败，请检查日志"))
        except Exception as e:
            logger.exception(f"{self.tr('从右键菜单添加Button失败:')} {e}")
    
    def _add_card_from_context(self, tab_id):
        """从右键菜单添加card"""
        try:
            from ui.tab_manager_dialog import CustomCardDialog
            from PySide6.QtWidgets import QDialog
            
            # 打开Card对话框，预设tab
            dialog = CustomCardDialog(
                self.tab_config_manager,
                preset_tab_id=tab_id,
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 刷新tab显示
                self.tab_config_manager.tab_config_updated.emit()
        except Exception as e:
            logger.exception(f"{self.tr('从右键菜单添加Card失败:')} {e}")
    
    def _edit_card_from_context(self, card_id):
        """从右键菜单编辑card"""
        try:
            from ui.tab_manager_dialog import CustomCardDialog
            from PySide6.QtWidgets import QDialog, QMessageBox
            
            # 打开Card对话框，编辑现有card
            dialog = CustomCardDialog(
                self.tab_config_manager,
                card_id=card_id,
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 刷新tab显示
                self.tab_config_manager.tab_config_updated.emit()
                QMessageBox.information(self, self.tr("成功"), self.tr("Card已更新"))
        except Exception as e:
            logger.exception(f"{self.tr('从右键菜单编辑Card失败:')} {e}")
    
    def _delete_card_from_context(self, card_id, card_name):
        """从右键菜单删除card"""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            reply = QMessageBox.question(
                self,
                self.tr("确认删除"),
                f"{self.tr('确定要删除Card')} '{card_name}' {self.tr('吗？')}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.tab_config_manager.delete_custom_card(card_id):
                    # 刷新tab显示
                    self.tab_config_manager.tab_config_updated.emit()
                    QMessageBox.information(self, self.tr("成功"), self.tr("Card已删除"))
                else:
                    QMessageBox.warning(self, self.tr("失败"), self.tr("Card删除失败，请检查日志"))
        except Exception as e:
            logger.exception(f"{self.tr('从右键菜单删除Card失败:')} {e}")
    
    def _setup_preset_tab_card_context_menus(self):
        """为所有预置Tab的card统一添加右键菜单"""
        try:
            from PySide6.QtWidgets import QFrame
            from PySide6.QtCore import Qt
            
            # 获取所有tab widget
            for i in range(self.tab_widget.count()):
                tab_widget = self.tab_widget.widget(i)
                if not tab_widget:
                    continue
                
                # 获取tab_id
                tab_id = None
                if hasattr(tab_widget, 'tab_id'):
                    tab_id = tab_widget.tab_id
                
                if not tab_id:
                    continue
                
                # 检查是否为预置tab（不是自定义tab）
                all_tabs = self.tab_config_manager.get_all_tabs()
                is_custom = False
                for tab in all_tabs:
                    if tab['id'] == tab_id:
                        is_custom = tab.get('custom', False)
                        break
                
                # 只为预置tab添加右键菜单（自定义tab的card在_create_custom_card_group中已处理）
                if not is_custom:
                    # 查找所有card frame
                    frames = tab_widget.findChildren(QFrame)
                    for frame in frames:
                        if frame.objectName() == "card":
                            # 获取card名称并存储在frame的属性中
                            card_name = self._get_card_name_from_frame_simple(frame, tab_widget)
                            if card_name:
                                frame.setProperty('card_name', card_name)
                            
                            # 检查是否已经有右键菜单（避免重复设置）
                            if frame.contextMenuPolicy() != Qt.CustomContextMenu:
                                frame.setContextMenuPolicy(Qt.CustomContextMenu)
                                frame.customContextMenuRequested.connect(
                                    lambda pos, f=frame, tw=tab_widget: self._show_card_context_menu(pos, f, tw)
                                )
        except Exception as e:
            logger.exception(f"{self.tr('为预置Tab添加右键菜单失败:')} {e}")
    
        
    def _append_log_handler(self, text, color=None):
        """日志追加处理"""
        self.log_viewer.append_log(text, color)
        
    def _on_device_changed(self, device):
        """设备改变处理"""
        self.selected_device = device
        self.device_manager.set_selected_device(device)
        self.append_log.emit(f"{self.lang_manager.tr('切换到设备:')} {device}\n", None)
        
    def _on_refresh_devices(self):
        """刷新设备列表"""
        self.append_log.emit(self.lang_manager.tr("刷新设备列表...") + "\n", None)
        self.device_manager.refresh_devices()
        
    def _on_devices_updated(self, devices):
        """设备列表更新"""
        self.toolbar.set_device_list(devices)
        
    def _on_device_selected(self, device):
        """设备选择"""
        self.selected_device = device
        
    def _on_device_status_message(self, message):
        """设备状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_sim_status_message(self, message):
        """SIM Tab状态消息"""
        self.append_log.emit(f"[SIM] {message}\n", None)
        
    def _on_screenshot(self):
        """截图处理"""
        self.screenshot_manager.take_screenshot()
        
    def _on_record_toggled(self, is_recording):
        """录制切换处理"""
        # 如果按钮被选中，说明用户想开始录制
        if is_recording:
            self.video_manager.start_recording()
        else:
            # 如果按钮被取消选中，说明用户想停止录制
            self.video_manager.stop_recording()
    
    def _on_reboot_device(self):
        """重启设备处理（异步）"""
        self.device_utilities.reboot_device(self)
    
    def _on_reboot_started(self, device):
        """重启开始回调"""
        self.append_log.emit(f"{self.lang_manager.tr('正在重启设备')} {device}...\n", "#FFA500")
        self.statusBar().showMessage(f"{self.lang_manager.tr('正在重启设备')} {device}...")
    
    def _on_reboot_finished(self, success, message):
        """重启完成回调"""
        if success:
            self.append_log.emit(f"✅ {message}\n", "#00FF00")
            self.statusBar().showMessage(self.lang_manager.tr("设备重启命令已执行"))
        else:
            self.append_log.emit(f"❌ {message}\n", "#FF0000")
            self.statusBar().showMessage(self.lang_manager.tr("设备重启失败"))
    
    def _handle_root_remount_log(self, text, color):
        """转发后台Root&remount日志到主界面"""
        self.append_log.emit(text, color)
    
    def _on_root_remount(self):
        """Root&remount处理（异步执行）"""
        device = self.device_manager.selected_device
        if not device:
            self.append_log.emit(self.lang_manager.tr("未选择设备") + "\n", "#FFA500")
            return

        if self._root_remount_worker and self._root_remount_worker.isRunning():
            self.append_log.emit(f"⚠️ {self.lang_manager.tr('Root&remount 正在执行，请稍候...')}\n", "#FFA500")
            return

        self.statusBar().showMessage(self.lang_manager.tr("正在执行 Root&remount..."))

        self._root_remount_worker = RootRemountWorker(device, self.lang_manager)
        self._root_remount_worker.log_message.connect(self._handle_root_remount_log)
        self._root_remount_worker.finished.connect(self._on_root_remount_finished)
        self._root_remount_worker.start()

    def _on_root_remount_finished(self, success, message, reboot_required, device):
        """Root&remount完成回调"""
        if self._root_remount_worker:
            self._root_remount_worker.deleteLater()
            self._root_remount_worker = None

        if success:
            self.statusBar().showMessage(self.lang_manager.tr("Root&remount 执行完成"))
        else:
            self.statusBar().showMessage(message)

        if not success:
            return

        if reboot_required:
            reply = QMessageBox.question(
                self,
                self.lang_manager.tr('需要重启设备'),
                '检测到需要重启设备才能使设置生效。\n\n是否立即重启设备？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.append_log.emit(f"{self.lang_manager.tr('执行 adb reboot...')}\n", None)
                # 直接异步重启，跳过重复确认
                self.device_utilities.reboot_device(self, confirm=False)
            else:
                self.append_log.emit(f"{self.lang_manager.tr('用户取消重启')}\n", None)

    def _on_check_update_clicked(self):
        """触发手动检查更新"""

        self._start_manual_update(source="manual")

    def _start_manual_update(self, source: str = "manual"):
        """启动手动检查更新流程"""

        if self._update_worker and self._update_worker.isRunning():
            if source == "manual":
                QMessageBox.information(self, self.tr("在线更新"), self.tr("更新正在进行，请稍候..."))
            return

        feed_url = (self.tool_config.get("update_feed_url") or "").strip()
        if not feed_url:
            if source == "manual":
                QMessageBox.warning(
                    self,
                    self.tr("在线更新"),
                    self.tr('未配置版本描述 URL，请先在"工具配置"中设置。'),
                )
            else:
                logger.info("跳过自动检查更新：未配置版本描述 URL")
            return

        self._update_request_origin = source

        try:
            update_manager = UpdateManager(
                current_version=self.app_version,
                tool_config=self.tool_config,
                logger=logger.info,
            )
        except Exception as exc:
            logger.exception("初始化更新模块失败: %s", exc)
            if source == "manual":
                QMessageBox.critical(
                    self,
                    self.tr("在线更新"),
                    f"{self.tr('初始化更新模块失败:')} {exc}",
                )
            return

        if source == "manual":
            self._update_status_text = self.tr("正在检查更新...")
            self._update_progress_extra = ""
            self._show_update_progress_dialog(self._update_status_text)
        else:
            self._update_status_text = ""
            self._update_progress_extra = ""

        if source == "auto":
            self._schedule_next_auto_check(self._update_check_interval_seconds)

        self.toolbar.set_update_enabled(False)

        self._update_worker = UpdateWorker(update_manager, self.lang_manager)
        self._update_worker.status_message.connect(self._on_update_status_message)
        self._update_worker.progress_changed.connect(self._on_update_progress_changed)
        self._update_worker.update_not_required.connect(self._on_update_not_required)
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.download_finished.connect(self._on_update_download_finished)
        self._update_worker.update_failed.connect(self._on_update_failed)
        self._update_worker.alternative_url_info.connect(self._on_alternative_url_info)
        self._update_worker.finished.connect(self._cleanup_update_worker)
        self._update_worker.start()

        if source == "manual":
            self.append_log.emit(f"[更新] {self.tr('开始检查软件更新...')}\n", None)
        elif source == "auto":
            logger.info("开始自动检查更新")

    def _show_update_progress_dialog(self, message: str) -> None:
        """显示更新进度对话框"""

        if self._update_progress_dialog:
            try:
                self._update_progress_dialog.close()
            except Exception:
                pass
            self._update_progress_dialog.deleteLater()

        dialog = QProgressDialog(message, self.tr("取消"), 0, 0, self)
        dialog.setWindowTitle(self.tr("在线更新"))
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setAutoReset(False)
        dialog.setAutoClose(False)
        dialog.setMinimumDuration(0)
        dialog.setMinimumWidth(420)
        dialog.canceled.connect(self._on_update_cancel_requested)
        dialog.show()
        self._update_progress_dialog = dialog

    def _refresh_update_progress_label(self) -> None:
        if not self._update_progress_dialog:
            return

        parts = []
        if self._update_status_text:
            parts.append(self._update_status_text)
        if self._update_progress_extra:
            parts.append(self._update_progress_extra)
        label_text = "\n".join(parts) if parts else ""
        if label_text:
            self._update_progress_dialog.setLabelText(label_text)

    def _on_update_status_message(self, message: str) -> None:
        self._update_status_text = message
        self._refresh_update_progress_label()
        self.append_log.emit(f"[更新] {message}\n", None)

    def _on_update_progress_changed(self, downloaded: int, total: int) -> None:
        if not self._update_progress_dialog:
            return

        if total <= 0:
            self._update_progress_dialog.setRange(0, 0)
            self._update_progress_extra = self.tr("正在下载安装包...")
        else:
            if self._update_progress_dialog.maximum() != total:
                self._update_progress_dialog.setRange(0, total)
            safe_downloaded = max(0, min(downloaded, total))
            self._update_progress_dialog.setValue(safe_downloaded)
            mb_downloaded = safe_downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._update_progress_extra = (
                f"{self.tr('下载进度')}: {mb_downloaded:.1f}/{mb_total:.1f} MB"
            )

        self._refresh_update_progress_label()

    def _on_update_not_required(self, message: str) -> None:
        self._close_update_progress_dialog()
        self._record_update_check_timestamp()
        if self._update_request_origin == "manual":
            QMessageBox.information(self, self.tr("在线更新"), message)
        else:
            logger.info(f"自动检查更新结果: {message}")
        self.append_log.emit(f"[更新] {message}\n", "#4CAF50")

    def _on_update_download_finished(self, manifest: LatestManifest, result: DownloadResult) -> None:
        self._close_update_progress_dialog()

        success_message = f"{self.tr('更新包下载完成')} - {manifest.version}"
        detail_lines = [
            f"{self.tr('保存路径')}: {result.file_path}",
            f"SHA-256: {result.sha256}",
        ]
        self.append_log.emit(f"[更新] ✅ {success_message}\n", "#00FF00")

        # 检查是否启用自动更新
        auto_update = bool(self.tool_config.get("update_auto_update", True))
        
        if auto_update:
            # 尝试启动自动更新器
            if self._try_launch_updater(result.file_path, manifest.version):
                # 更新器已启动，主程序退出
                self.append_log.emit(f"[更新] {self.tr('正在启动更新器，程序将自动退出...')}\n", "#FFA500")
                # 直接退出，不显示消息框
                QTimer.singleShot(100, self._exit_for_update)
                return
        
        # 回退到手动更新流程
        instruction_text = self.tr("请解压更新包并覆盖原有程序文件，以完成更新。")
        auto_launch = bool(self.tool_config.get("update_auto_launch_installer", True))
        if auto_launch:
            launched = self._try_launch_installer(result.file_path)
            info_lines = [success_message] + detail_lines
            if launched:
                info_lines.append(self.tr("已尝试打开更新包，请按照提示完成解压并覆盖。"))
            else:
                info_lines.append(instruction_text)
            QMessageBox.information(
                self,
                self.tr("在线更新"),
                "\n".join(info_lines),
            )
        else:
            reply = QMessageBox.question(
                self,
                self.tr("在线更新"),
                "\n".join([success_message] + detail_lines + [instruction_text, self.tr("是否打开下载位置？")]),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._reveal_in_file_manager(result.file_path)

    def _on_update_failed(self, message: str, error_info: dict = None) -> None:
        """处理更新失败，显示备用下载地址"""
        logger.debug(f"MainWindow: update failed -> {message}")
        self._close_update_progress_dialog()
        
        # 解析错误信息
        if error_info is None:
            error_info = {}
        
        reason = error_info.get('reason', 'unknown')
        alternative_url = error_info.get('alternative_url')
        alternative_region = error_info.get('alternative_region')
        detected_region = error_info.get('detected_region', '')
        
        # 日志消息
        log_color = "#FFA500" if reason in ['user_cancelled', 'download_cancelled'] else "#FF0000"
        
        if reason == "user_cancelled":
            logger.info("用户取消更新流程")
            self.append_log.emit(f"[更新] {message}\n", log_color)
            if alternative_url:
                log_msg = f"[更新] 备用下载地址（{alternative_region or '中国区'}）：{alternative_url}\n"
                self.append_log.emit(log_msg, "#FFA500")
        elif alternative_url:
            # 下载失败或取消，显示备用地址
            self.append_log.emit(f"[更新] ❌ {message}\n", log_color)
            log_msg = f"[更新] 备用下载地址（{alternative_region or '中国区'}）：{alternative_url}\n"
            self.append_log.emit(log_msg, "#FFA500")
            
            if self._update_request_origin == "manual":
                # 手动更新：显示详细消息框
                details = [message]
                details.append("")
                details.append(self.tr("请使用以下备用地址手动下载："))
                details.append(alternative_url)
                details.append("")
                details.append(self.tr("下载完成后，解压并覆盖原文件即可完成更新。"))
                
                QMessageBox.warning(
                    self,
                    self.tr("在线更新"),
                    "\n".join(details),
                )
            else:
                # 自动更新：只记录日志
                logger.error(f"自动检查更新失败: {message}")
        else:
            # 没有备用地址，按原逻辑处理
            logger.error(f"在线更新失败: {message}")
            self.append_log.emit(f"[更新] ❌ {message}\n", "#FF0000")
            if self._update_request_origin == "manual":
                QMessageBox.critical(self, self.tr("在线更新"), message)
            else:
                logger.error(f"自动检查更新失败: {message}")

    def _on_update_cancel_requested(self) -> None:
        if self._suppress_progress_cancel:
            return
        if self._update_worker and self._update_worker.isRunning():
            self._update_worker.request_cancel()
            if self._update_progress_dialog:
                try:
                    self._update_progress_dialog.setCancelButtonText(self.tr("已取消"))
                except Exception:
                    pass
                self._update_progress_dialog.setEnabled(False)
                self._update_progress_dialog.setLabelText(self.tr("正在取消下载，请稍候..."))

    def _close_update_progress_dialog(self) -> None:
        if not self._update_progress_dialog:
            return

        dialog = self._update_progress_dialog
        self._update_progress_dialog = None
        try:
            self._suppress_progress_cancel = True
            dialog.close()
        except Exception:
            pass
        finally:
            self._suppress_progress_cancel = False
        dialog.deleteLater()

    def _cleanup_update_worker(self) -> None:
        if self._update_worker:
            self._update_worker.deleteLater()
            self._update_worker = None

        self.toolbar.set_update_enabled(True)
        self._update_status_text = ""
        self._update_progress_extra = ""

    def _try_launch_installer(self, file_path: str) -> bool:
        if not file_path:
            return False

        if not os.path.exists(file_path):
            QMessageBox.warning(self, self.tr("在线更新"), self.tr("安装包文件不存在。"))
            return False

        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            return True
        except Exception as exc:
            logger.exception("启动安装包失败: %s", exc)
            return False

    def _reveal_in_file_manager(self, file_path: str) -> None:
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(self, self.tr("在线更新"), self.tr("安装包文件不存在。"))
            return

        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", f"/select,{file_path}"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", file_path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(file_path)])
        except Exception as exc:
            logger.exception("打开文件位置失败: %s", exc)
            QMessageBox.warning(self, self.tr("在线更新"), self.tr("无法打开文件所在位置，请手动查找。"))
    
    def _get_install_dir(self) -> str:
        """获取程序安装目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的exe运行目录
            return os.path.dirname(os.path.abspath(sys.executable))
        else:
            # 开发环境：使用项目根目录
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _get_updater_path(self) -> Optional[str]:
        """获取更新器可执行文件路径"""
        install_dir = self._get_install_dir()
        
        # 生产环境：查找 updater.exe
        if getattr(sys, 'frozen', False):
            # 优先在 _internal 目录中查找（更隐蔽）
            internal_dir = os.path.join(install_dir, "_internal")
            updater_exe = os.path.join(internal_dir, "updater.exe")
            if os.path.exists(updater_exe):
                return updater_exe
            
            # 回退到主目录查找（兼容旧版本）
            updater_exe = os.path.join(install_dir, "updater.exe")
            if os.path.exists(updater_exe):
                return updater_exe
        else:
            # 开发环境：使用 Python 运行 updater.py
            updater_py = os.path.join(install_dir, "core", "updater.py")
            if os.path.exists(updater_py):
                return sys.executable, updater_py
        
        return None
    
    def _try_launch_updater(self, zip_path: str, version: str) -> bool:
        """尝试启动更新器
        
        策略：先将 updater.exe 复制到临时目录，然后从临时目录运行
        这样可以避免 updater.exe 锁定 _internal 目录中的 DLL 文件
        """
        try:
            updater_path = self._get_updater_path()
            if not updater_path:
                logger.warning("更新器未找到，无法执行自动更新")
                return False
            
            install_dir = self._get_install_dir()
            main_exe = os.path.join(install_dir, "MobileTestTool.exe")
            
            # 构建更新器命令
            if isinstance(updater_path, tuple):
                # 开发环境：Python脚本
                python_exe, updater_script = updater_path
                cmd = [
                    python_exe,
                    updater_script,
                    zip_path,
                    install_dir,
                    "--main-exe", main_exe if os.path.exists(main_exe) else "main.py",
                    "--process-name", "MobileTestTool.exe",
                    "--wait-timeout", "30",
                ]
                # 开发环境直接运行，不需要复制
                logger.info(f"启动更新器: {' '.join(cmd)}")
                subprocess.Popen(cmd)
                logger.info("更新器已启动")
                return True
            else:
                # 生产环境：可执行文件
                # 先复制到临时目录，避免锁定 _internal 目录中的 DLL
                import tempfile
                import shutil
                
                temp_dir = tempfile.gettempdir()
                temp_updater = os.path.join(temp_dir, f"MobileTestTool_updater_{int(time.time())}.exe")
                
                try:
                    # 复制更新器到临时目录
                    logger.info(f"复制更新器到临时目录: {temp_updater}")
                    shutil.copy2(updater_path, temp_updater)
                    
                    # 从临时目录运行更新器
                    cmd = [
                        temp_updater,
                        zip_path,
                        install_dir,
                        "--main-exe", main_exe,
                        "--process-name", "MobileTestTool.exe",
                        "--wait-timeout", "30",
                    ]
                    
                    logger.info(f"启动更新器: {' '.join(cmd)}")
                    
                    # 启动更新器（不等待它完成）
                    # 注意：更新器需要显示控制台窗口，所以不使用 CREATE_NO_WINDOW
                    subprocess.Popen(
                        cmd,
                        creationflags=0,  # 显示控制台窗口
                        # 不重定向输出，让更新器直接显示在控制台
                    )
                    
                    logger.info("更新器已启动（从临时目录运行）")
                    
                    # 注意：临时文件会在更新器完成后自行清理，或者由系统清理
                    # 更新器可以在完成后删除自己的临时副本
                    return True
                    
                except Exception as copy_error:
                    logger.error(f"复制更新器到临时目录失败: {copy_error}")
                    # 如果复制失败，尝试直接运行（可能仍会锁定文件，但至少可以尝试）
                    logger.warning("尝试直接运行更新器（可能锁定 _internal 文件）")
                    cmd = [
                        updater_path,
                        zip_path,
                        install_dir,
                        "--main-exe", main_exe,
                        "--process-name", "MobileTestTool.exe",
                        "--wait-timeout", "30",
                    ]
                    subprocess.Popen(cmd, creationflags=0)
                    logger.info("更新器已启动（直接运行）")
                    return True
            
        except Exception as exc:
            logger.exception("启动更新器失败: %s", exc)
            return False
    
    def _exit_for_update(self) -> None:
        """为更新而退出程序"""
        logger.info("程序即将退出以进行更新")
        QApplication.instance().quit()
    
    def _on_theme_toggled(self):
        """主题切换处理"""
        self.theme_manager.toggle_theme()
        current_theme = self.theme_manager.get_current_theme()
        self.toolbar.update_theme_button(current_theme)
        
        # 更新日志查看器的文本颜色
        if hasattr(self, 'log_viewer') and self.log_viewer:
            self.log_viewer._update_text_colors()
        
        self.append_log.emit(f"{self.tr('已切换到')}{current_theme}{self.tr('主题')}\n", None)
    
    def _on_language_changed(self, new_lang):
        """语言切换处理"""
        self.append_log.emit(f"{self.tr('语言已切换到:')}{self.tr('英文') if new_lang == 'en' else self.tr('中文')}\n", None)
        # 刷新所有UI文本
        self._refresh_all_ui_texts()
    
    def _refresh_all_ui_texts(self):
        """刷新所有UI文本"""
        try:
            # 刷新窗口标题
            self.setWindowTitle(f"{self.lang_manager.tr('手机测试辅助工具')} v{self.app_version}")
            
            # 刷新所有Tab标题和内容
            if hasattr(self, 'tab_widget'):
                # 根据Tab的实际内容来设置标题，而不是硬编码
                for i in range(self.tab_widget.count()):
                    tab_widget = self.tab_widget.widget(i)
                    
                    # 根据Tab实例类型设置正确的标题
                    if hasattr(tab_widget, 'tab_id'):
                        tab_id = tab_widget.tab_id
                        # 使用Tab配置管理器获取正确的标题
                        all_tabs = self.tab_config_manager.get_all_tabs()
                        correct_title = self._get_tab_name(tab_id, all_tabs)
                        self.tab_widget.setTabText(i, correct_title)
                    
                    # 更新Tab内容
                    if hasattr(tab_widget, 'refresh_texts'):
                        tab_widget.refresh_texts(self.lang_manager)
            
            # 刷新工具栏文本
            if hasattr(self, 'toolbar'):
                self.toolbar.refresh_texts(self.lang_manager)
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('刷新UI文本失败:')} {e}")
    
    def _on_adb_command_executed(self, command):
        """执行ADB命令"""
        import subprocess
        
        # 黑名单：不支持的持续输出命令
        BLOCKED_COMMANDS = {
            'logcat': '请使用"Log过滤"功能',
            'tcpdump': '请使用"Log控制"标签页的tcpdump功能',
            'ping': '请使用"Network信息"标签页的ping功能',
            'top': '此命令会持续输出，不支持',
            'getevent': '此命令会持续输出，不支持',
            'monkey': '此命令会持续输出，不支持'
        }
        
        # 检查是否包含黑名单命令
        import shlex

        try:
            tokens = shlex.split(command, posix=False)
        except ValueError:
            tokens = []

        blocked_hint = None

        if tokens:
            tokens_lower = [token.lower() for token in tokens]

            def _requires_value(original_token, lower_token):
                if original_token.startswith('--'):
                    return lower_token != '--help'
                if lower_token in {'-s', '-p', '-h', '-l'}:
                    # -h 无需参数，-H 需要参数
                    if lower_token == '-h' and original_token == '-h':
                        return False
                    return True
                return False

            # 首个命令（非 adb）直接判断
            first_token = tokens_lower[0]
            if first_token in BLOCKED_COMMANDS:
                blocked_hint = BLOCKED_COMMANDS[first_token]
            elif first_token == 'adb':
                # 解析 adb 子命令
                idx = 1
                expect_value = False

                while idx < len(tokens_lower):
                    tok_lower = tokens_lower[idx]
                    tok_original = tokens[idx]

                    if expect_value:
                        expect_value = False
                        idx += 1
                        continue

                    if _requires_value(tok_original, tok_lower):
                        expect_value = True
                        idx += 1
                        continue

                    if tok_original.startswith('-'):
                        idx += 1
                        continue

                    break

                if idx < len(tokens_lower):
                    subcmd_lower = tokens_lower[idx]

                    if subcmd_lower == 'shell':
                        idx += 1
                        expect_value = False
                        shell_start_idx = idx  # 记录shell后的起始位置
                        found_shell_command = False  # 标记是否找到实际命令

                        while idx < len(tokens_lower):
                            shell_tok_lower = tokens_lower[idx]
                            shell_tok_original = tokens[idx]

                            if expect_value:
                                expect_value = False
                                idx += 1
                                continue

                            if _requires_value(shell_tok_original, shell_tok_lower):
                                expect_value = True
                                idx += 1
                                continue

                            if shell_tok_original.startswith('-'):
                                idx += 1
                                continue

                            # 找到了实际命令（非参数）
                            found_shell_command = True
                            primary_cmd = shell_tok_lower.split()[0]

                            if primary_cmd in BLOCKED_COMMANDS:
                                blocked_hint = BLOCKED_COMMANDS[primary_cmd]
                            break
                        
                        # 检查 adb shell 后面是否有实际命令
                        if not found_shell_command:
                            # adb shell 后面没有任何命令
                            blocked_hint = self.tr('adb shell 后面必须跟命令，不允许单独使用')
                    else:
                        primary_cmd = subcmd_lower.split()[0]
                        if primary_cmd in BLOCKED_COMMANDS:
                            blocked_hint = BLOCKED_COMMANDS[primary_cmd]

        if blocked_hint:
            self.append_log.emit(f"{self.tr('⚠️ 不支持命令: ')}{command}\n", "#FFA500")
            self.append_log.emit(f"{self.tr('💡 提示: ')}{blocked_hint}\n", "#17a2b8")
            return
        
        # 显示命令
        self.append_log.emit(f"{self.tr('执行命令: ')}{command}\n", None)
        
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 透传输出内容（使用紫色显示返回值）
            if result.stdout:
                self.append_log.emit(result.stdout, "#9D4EDD")
            
            if result.stderr:
                self.append_log.emit(result.stderr, "#9D4EDD")
                
        except subprocess.TimeoutExpired:
            self.append_log.emit(f"⚠️ {self.lang_manager.tr('命令执行超时（30秒）')}\n", "#FFA500")
            self.append_log.emit(f"💡 {self.lang_manager.tr('如需长时间运行的命令，请使用对应的专门功能')}\n", "#17a2b8")
        except Exception as e:
            self.append_log.emit(f"{self.tr('执行失败: ')}{str(e)}\n", None)
            
    # Log控制 Tab 信号处理
    def _on_mtklog_start(self):
        """MTKLOG 开启"""
        self.append_log.emit(self.lang_manager.tr("开启 MTKLOG...") + "\n", None)
        self.mtklog_manager.start_mtklog()
        
    def _on_mtklog_stop_export(self):
        """MTKLOG 停止并导出"""
        self.append_log.emit(self.lang_manager.tr("停止并导出 MTKLOG...") + "\n", None)
        self.mtklog_manager.stop_and_export_mtklog()
        
    def _on_mtklog_delete(self):
        """MTKLOG 删除"""
        self.append_log.emit(self.lang_manager.tr("删除 MTKLOG...") + "\n", None)
        self.mtklog_manager.delete_mtklog()
    
    def _on_mtklog_set_log_size(self):
        """设置 MTKLOG 大小"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG 大小...") + "\n", None)
        self.mtklog_manager.set_log_size()
        
    def _on_mtklog_sd_mode(self):
        """MTKLOG SD模式"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG SD模式...") + "\n", None)
        self.mtklog_manager.set_sd_mode()
        
    def _on_mtklog_usb_mode(self):
        """MTKLOG USB模式"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG USB模式...") + "\n", None)
        self.mtklog_manager.set_usb_mode()
        
    def _on_mtklog_install(self):
        """安装 MTKLOGGER"""
        self.append_log.emit(self.lang_manager.tr("安装 MTKLOGGER...") + "\n", None)
        self.mtklog_manager.install_mtklogger()
        
    # MTKLOG管理器信号处理
    def _on_mtklog_started(self):
        """MTKLOG启动完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG启动成功") + "\n", None)
        
    def _on_mtklog_stopped(self):
        """MTKLOG停止完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG已停止") + "\n", None)
        
    def _on_mtklog_deleted(self):
        """MTKLOG删除完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG已删除") + "\n", None)
        
    def _on_mtklog_exported(self, export_path):
        """MTKLOG导出完成"""
        self.append_log.emit(f"{self.tr('MTKLOG已导出到: ')}{export_path}\n", None)
        
    def _on_mtklog_progress(self, progress, status):
        """MTKLOG进度更新"""
        self.append_log.emit(f"- {status}\n", None)
        
    def _on_mtklog_status(self, message):
        """MTKLOG状态消息"""
        self.append_log.emit(f"{message}\n", None)
        
    def _on_adblog_start(self):
        """离线ADB Log 开启"""
        print(f"{self.tr('离线ADB Log按钮被点击，当前is_running状态: ')}{self.adblog_manager.is_running}")
        
        # 检查ADB Log是否正在运行
        if self.adblog_manager.is_running:
            print("ADB Log正在运行，无法启动离线模式")
            self.append_log.emit(self.lang_manager.tr("ADB Log已经在运行中，请先停止当前任务\n"), None)
            return
        
        # 获取log名称
        from PySide6.QtWidgets import QInputDialog
        log_name, ok = QInputDialog.getText(
            self,
            self.lang_manager.tr('输入log名称'),
            self.lang_manager.tr('请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线')
        )
        
        if not ok or not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        # 启动离线ADB Log
        self.append_log.emit(f"{self.lang_manager.tr('开启离线ADB Log...')}\n", None)
        self.adblog_manager.start_adblog("offline", log_name)
    
    def _on_adblog_online_start(self):
        """连线ADB Log 开启/停止"""
        print(f"{self.tr('连线ADB Log按钮被点击，当前is_running状态: ')}{self.adblog_manager.is_running}")
        
        # 检查ADB Log是否正在运行
        if self.adblog_manager.is_running:
            print("ADB Log正在运行，执行停止操作")
            # 停止连线logcat进程
            self.adblog_manager.stop_online_adblog()
            return
        
        # 获取log名称
        from PySide6.QtWidgets import QInputDialog
        log_name, ok = QInputDialog.getText(
            self,
            self.lang_manager.tr('输入log名称'),
            self.lang_manager.tr('请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线')
        )
        
        if not ok or not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        # 启动连线ADB Log
        self.append_log.emit(f"{self.lang_manager.tr('开启连线ADB Log...')}\n", None)
        self.adblog_manager.start_adblog("online", log_name)
        
    def _on_adblog_export(self):
        """ADB Log 导出（只处理离线模式）"""
        self.append_log.emit(self.lang_manager.tr("导出 ADB Log...") + "\n", None)
        self.adblog_manager.export_offline_adblog()
        
    # ADB Log管理器信号处理
    def _on_adblog_started(self):
        """ADB Log启动完成"""
        self.append_log.emit(self.lang_manager.tr("ADB Log已启动") + "\n", None)
        
    def _on_adblog_stopped(self):
        """ADB Log停止完成"""
        self.append_log.emit(self.lang_manager.tr("ADB Log已停止") + "\n", None)
        
    def _on_adblog_exported(self, export_path):
        """ADB Log导出完成"""
        self.append_log.emit(f"{self.lang_manager.tr('ADB Log已导出到:')} {export_path}\n", None)
        
    def _on_adblog_status(self, message):
        """ADB Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_clear_old_logs_required(self, device, file_count, txt_files):
        """需要清除旧log文件的提示"""
        from PySide6.QtWidgets import QMessageBox
        
        # 显示文件名列表（最多显示5个）
        file_list = [os.path.basename(f.strip()) for f in txt_files if f.strip()][:5]
        file_display = '\n'.join(file_list)
        if file_count > 5:
            file_display += '\n...'
        
        reply = QMessageBox.question(
            self,
            self.lang_manager.tr('发现旧log文件'),
            f'在设备 {device} 的 /data/local/tmp 目录中发现 {file_count} 个txt文件:\n\n'
            f'{file_display}\n\n'
            '是否清除这些旧log文件？\n\n'
            '选择"是"：清除所有旧文件，然后输入新文件名\n'
            '选择"否"：保留旧文件，然后输入新文件名',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        # 通知管理器用户的选择
        clear_old = (reply == QMessageBox.StandardButton.Yes)
        self.adblog_manager.handle_clear_old_logs_decision(clear_old)
    
    def _on_online_mode_started(self):
        """连线模式已启动"""
        self.log_control_tab.set_online_mode_started()
    
    def _on_online_mode_stopped(self):
        """连线模式已停止"""
        self.log_control_tab.set_online_mode_stopped()
    
    def _on_usb_disconnected(self, device):
        """USB断开"""
        self.append_log.emit(f"{self.tr('USB断开 - ')}{device}\n", None)
    
    def _on_usb_reconnected(self, device):
        """USB重连"""
        self.append_log.emit(f"{self.tr('USB已重连 - ')}{device}\n", None)
        
    def _on_telephony_enable(self):
        """启用 Telephony"""
        self.telephony_manager.enable_telephony()
        
    def _on_google_log_toggle(self):
        """切换 Google 日志"""
        self.google_log_manager.toggle_google_log()
    
    def _on_google_log_started(self):
        """Google日志已启动，更新按钮状态"""
        self.log_control_tab.google_log_btn.setText(self.lang_manager.tr("停止 Google 日志"))
        self.log_control_tab.google_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
    
    def _on_google_log_stopped(self):
        """Google日志已停止，恢复按钮状态"""
        self.log_control_tab.google_log_btn.setText(self.lang_manager.tr("Google 日志"))
        self.log_control_tab.google_log_btn.setStyleSheet("")
        
    def _on_bugreport_generate(self):
        """生成 Bugreport"""
        self.bugreport_manager.generate_bugreport()
        
    def _on_bugreport_pull(self):
        """Pull Bugreport"""
        self.bugreport_manager.pull_bugreport()
        
    def _on_bugreport_delete(self):
        """删除 Bugreport"""
        self.bugreport_manager.delete_bugreport()
        
    def _on_aee_log_start(self):
        """AEE Log"""
        self.aee_log_manager.start_aee_log()
        
    def _on_tcpdump_show_dialog(self):
        """显示 TCPDUMP 对话框"""
        self.tcpdump_manager.show_tcpdump_dialog()
        
    # Log过滤 Tab 信号处理
    def _on_start_filtering(self):
        """开始过滤"""
        keyword = self.log_filter_tab.get_keyword()
        use_regex = self.log_filter_tab.is_use_regex()
        case_sensitive = self.log_filter_tab.is_case_sensitive()
        color_highlight = self.log_filter_tab.is_color_highlight()
        
        self.append_log.emit(f"{self.tr('开始过滤 - 关键字: ')}{keyword}\n", None)
        self.append_log.emit(f"  {self.tr('正则表达式: ')}{use_regex}, {self.tr('区分大小写: ')}{case_sensitive}, {self.tr('彩色高亮: ')}{color_highlight}\n", None)
        
        # 调用Log过滤管理器
        self.log_processor.start_filtering(keyword, use_regex, case_sensitive, color_highlight)
        
    def _on_stop_filtering(self):
        """停止过滤"""
        self.append_log.emit(self.lang_manager.tr("停止过滤...") + "\n", None)
        self.log_processor.stop_filtering()
        
    def _on_manage_log_keywords(self):
        """打开log关键字管理对话框"""
        try:
            from ui.log_keyword_dialog import LogKeywordDialog
            
            dialog = LogKeywordDialog(self.log_keyword_manager, parent=self)
            dialog.exec()
            
            # 如果用户选择了关键字并点击了"加载到过滤"按钮
            selected_keyword = dialog.get_selected_keyword()
            if selected_keyword:
                self.log_filter_tab.set_keyword(selected_keyword)
                self.append_log.emit(f"✅ {self.tr('已加载关键字: ')}{selected_keyword}\n", "#00FF00")
                
                # 自动开始过滤
                self._on_start_filtering()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('打开log关键字管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开log关键字管理失败')}：{str(e)}")
    
    def _on_keyword_loaded(self, keyword):
        """关键字已加载，更新输入框"""
        self.log_filter_tab.set_keyword(keyword)
    
    def _on_filter_state_changed(self, is_running, current_keyword):
        """过滤状态改变，更新TMO CC Tab的按钮状态"""
        self.tmo_cc_tab.update_filter_buttons(is_running, current_keyword)
        
    def _on_clear_logs(self):
        """清空日志"""
        self.log_viewer.clear_logs()
        self.append_log.emit(self.lang_manager.tr("日志已清空") + "\n", None)
        
    def _on_clear_device_logs(self):
        """清除设备日志缓存"""
        self.append_log.emit(self.lang_manager.tr("清除设备日志缓存...") + "\n", None)
        if hasattr(self, 'log_processor') and self.log_processor:
            self.log_processor.clear_device_logs()
        else:
            self.statusBar().showMessage(self.lang_manager.tr("日志处理器未初始化"))
        
    def _on_show_display_lines_dialog(self):
        """显示设置行数对话框"""
        self.append_log.emit(f"{self.lang_manager.tr('显示设置行数对话框...')}\n", None)
        
    def _on_save_logs(self):
        """保存日志"""
        if hasattr(self, 'log_processor') and self.log_processor:
            self.log_processor.save_logs()
        else:
            self.statusBar().showMessage(self.lang_manager.tr("日志处理器未初始化"))
        
    # Log过滤管理器信号处理
    def _on_filtering_started(self):
        """日志过滤启动完成"""
        # 更新UI状态为过滤中
        self.log_filter_tab.set_filtering_state(True)
        
    def _on_filtering_stopped(self):
        """日志过滤停止完成"""
        # 更新UI状态为停止过滤
        self.log_filter_tab.set_filtering_state(False)
        
    def _on_filter_log_received(self, log_line):
        """Log过滤接收日志"""
        self.append_log.emit(log_line, None)
        
    def _on_filter_status(self, message):
        """Log过滤状态消息"""
        self.append_log.emit(f"{message}\n", None)
        
    # 网络信息 Tab 信号处理
    def _on_start_network_info(self):
        """开始获取网络信息"""
        self.append_log.emit(self.lang_manager.tr("开始获取网络信息...") + "\n", None)
        self.network_info_manager.start_network_info()
        
    def _on_stop_network_info(self):
        """停止获取网络信息"""
        self.append_log.emit(self.lang_manager.tr("停止获取网络信息...") + "\n", None)
        self.network_info_manager.stop_network_info()
        
    def _on_start_ping(self, ping_target="www.google.com"):
        """开始 Ping"""
        self.append_log.emit(self.lang_manager.tr("开始 Ping 测试...") + "\n", None)
        self.network_info_manager.start_ping(ping_target)
        
    def _on_stop_ping(self):
        """停止 Ping"""
        self.append_log.emit(self.lang_manager.tr("停止 Ping 测试...") + "\n", None)
        self.network_info_manager.stop_ping()
        
    # 网络信息管理器信号处理
    def _on_network_info_updated(self, network_info):
        """网络信息更新"""
        # 更新网络信息Tab的表格
        if hasattr(self, 'network_info_tab'):
            # network_info应该是一个列表
            if isinstance(network_info, list):
                self.network_info_tab.update_network_table(network_info)
            else:
                # 兼容旧格式
                self.network_info_tab.update_network_table([network_info])
        
    def _on_ping_result(self, result):
        """Ping结果"""
        # 打印到日志（除了 ping_stopped 消息）
        if result != "ping_stopped":
            self.append_log.emit(f"{result}\n", None)
        
        # 更新网络信息Tab的状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.update_ping_status(result)
        
    def _on_network_status(self, message):
        """网络信息状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_network_info_started(self):
        """网络信息获取启动成功"""
        # 更新Tab按钮状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.set_network_state(True)
    
    def _on_network_info_start_failed(self):
        """网络信息获取启动失败"""
        # 不改变Tab按钮状态，保持原样
        pass
    
    def _on_ping_started(self):
        """Ping启动成功"""
        # 更新Tab按钮状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.set_ping_state(True)
    
    def _on_ping_start_failed(self):
        """Ping启动失败"""
        # 不改变Tab按钮状态，保持原样
        pass
        
    # TMO CC Tab 信号处理
    def _on_push_cc_file(self):
        """推CC文件"""
        self.tmo_cc_manager.push_cc_file()
        
    def _on_pull_cc_file(self):
        """拉CC文件"""
        self.tmo_cc_manager.pull_cc_file()
        
    def _on_simple_filter(self):
        """简单过滤"""
        self.log_processor.simple_filter()
        
    def _on_complete_filter(self):
        """完全过滤"""
        self.log_processor.complete_filter()
        
    def _on_prod_server(self):
        """PROD服务器"""
        self.tmo_cc_manager.start_prod_server()
        
    def _on_stg_server(self):
        """STG服务器"""
        self.tmo_cc_manager.start_stg_server()
        
    # TMO Echolocate Tab 信号处理
    def _on_install_echolocate(self):
        """安装Echolocate"""
        self.echolocate_manager.install_echolocate()
        
    def _on_trigger_echolocate(self):
        """Trigger Echolocate"""
        self.echolocate_manager.trigger_echolocate()
        
    def _on_pull_echolocate_file(self):
        """Pull Echolocate文件"""
        self.echolocate_manager.pull_echolocate_file()
        
    def _on_delete_echolocate_file(self):
        """删除Echolocate文件"""
        self.echolocate_manager.delete_echolocate_file()
        
    def _on_get_echolocate_version(self):
        """获取Echolocate版本号"""
        self.echolocate_manager.get_echolocate_version()
        
    def _on_echolocate_log(self, message, color):
        """Echolocate日志消息（带颜色）"""
        # 检查是否包含版本号信息，如果是则只让版本号部分显示为绿色
        if "Echolocate版本号:" in message or "Echolocate版本信息:" in message:
            # 提取版本号部分并设置为绿色
            import re
            # 匹配版本号模式 (更宽泛的版本号格式)
            version_pattern = r'([0-9]+\.[0-9A-Za-z._-]+)'
            if re.search(version_pattern, message):
                # 分割消息，分别处理版本号部分和其他部分
                parts = re.split(version_pattern, message)
                for i, part in enumerate(parts):
                    if re.match(version_pattern, part):
                        # 版本号部分使用绿色
                        self.append_log.emit(part, "green")
                    else:
                        # 其他部分使用默认颜色，最后添加换行符
                        if i == len(parts) - 1:  # 最后一部分
                            self.append_log.emit(f"{part}\n", None)
                        else:
                            self.append_log.emit(part, None)
            else:
                # 如果没有匹配到版本号模式，使用原来的颜色
                self.append_log.emit(f"{message}\n", color)
        else:
            # 其他消息使用原来的颜色
            self.append_log.emit(f"{message}\n", color)
        
    def _on_filter_callid(self):
        """过滤CallID"""
        self.echolocate_manager.filter_callid()
        
    def _on_filter_callstate(self):
        """过滤CallState"""
        self.echolocate_manager.filter_callstate()
        
    def _on_filter_uicallstate(self):
        """过滤UICallState"""
        self.echolocate_manager.filter_uicallstate()
        
    def _on_filter_allcallstate(self):
        """过滤AllCallState"""
        self.echolocate_manager.filter_allcallstate()
        
    def _on_filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        self.echolocate_manager.filter_ims_signalling()
        
    def _on_filter_allcallflow(self):
        """过滤AllCallFlow"""
        self.echolocate_manager.filter_allcallflow()
        
    def _on_filter_voice_intent(self):
        """过滤voice_intent测试"""
        self.echolocate_manager.filter_voice_intent()
        
    # 24小时背景数据 Tab 信号处理
    def _on_configure_phone(self):
        """配置手机"""
        self.background_data_manager.configure_phone()
        
    def _on_analyze_logs(self):
        """分析日志"""
        self.background_data_manager.analyze_logs()
        
    # APP操作 Tab 信号处理
    def _on_query_package(self):
        """查询package"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 查询package")
        logger.debug(f"函数: _on_query_package")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.query_package()")
            self.app_operations_manager.query_package()
            logger.debug("查询package成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"查询package失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"查询package失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_query_package_name(self):
        """查询包名"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 查询包名")
        logger.debug(f"函数: _on_query_package_name")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.query_package_name()")
            self.app_operations_manager.query_package_name()
            logger.debug("查询包名成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"查询包名失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"查询包名失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_query_install_path(self):
        """查询安装路径"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 查询安装路径")
        logger.debug(f"函数: _on_query_install_path")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.query_install_path()")
            self.app_operations_manager.query_install_path()
            logger.debug("查询安装路径成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"查询安装路径失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"查询安装路径失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_query_find_file(self):
        """查找文件"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 查找文件")
        logger.debug(f"函数: _on_query_find_file")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.query_find_file()")
            self.app_operations_manager.query_find_file()
            logger.debug("查找文件成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"查找文件失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"查找文件失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_pull_apk(self):
        """pull apk"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: pull apk")
        logger.debug(f"函数: _on_pull_apk")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.pull_apk()")
            self.app_operations_manager.pull_apk()
            logger.debug("pull apk成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"pull apk失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"pull apk失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_push_apk(self):
        """push apk"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: push apk")
        logger.debug(f"函数: _on_push_apk")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.push_apk()")
            self.app_operations_manager.push_apk()
            logger.debug("push apk成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"push apk失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"push apk失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_install_apk(self):
        """安装APK"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 安装APK")
        logger.debug(f"函数: _on_install_apk")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.install_apk()")
            self.app_operations_manager.install_apk()
            logger.debug("安装APK成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"安装APK失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"安装APK失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_view_processes(self):
        """查看进程"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 查看进程")
        logger.debug(f"函数: _on_view_processes")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.view_processes()")
            self.app_operations_manager.view_processes()
            logger.debug("查看进程成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"查看进程失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"查看进程失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_dump_app(self):
        """dump app"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: dump app")
        logger.debug(f"函数: _on_dump_app")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.dump_app()")
            self.app_operations_manager.dump_app()
            logger.debug("dump app成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"dump app失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"dump app失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_enable_app(self):
        """启用app"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 启用app")
        logger.debug(f"函数: _on_enable_app")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.enable_app()")
            self.app_operations_manager.enable_app()
            logger.debug("启用app成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"启用app失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"启用app失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_disable_app(self):
        """禁用app"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 禁用app")
        logger.debug(f"函数: _on_disable_app")
        logger.debug(f"APP操作管理器对象: {self.app_operations_manager}")
        try:
            if not hasattr(self, 'app_operations_manager') or self.app_operations_manager is None:
                logger.error("app_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("APP操作管理器未初始化"))
                return
            logger.debug("调用 app_operations_manager.disable_app()")
            self.app_operations_manager.disable_app()
            logger.debug("禁用app成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"禁用app失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"禁用app失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    # 其他 Tab 信号处理
    def _on_show_device_info_dialog(self):
        """显示手机信息对话框"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示手机信息对话框")
        logger.debug(f"函数: _on_show_device_info_dialog")
        logger.debug(f"设备管理器对象: {self.device_info_manager}")
        try:
            if not hasattr(self, 'device_info_manager') or self.device_info_manager is None:
                logger.error("device_info_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("设备信息管理器未初始化"))
                return
            logger.debug("调用 device_info_manager.show_device_info()")
            self.device_info_manager.show_device_info()
            logger.debug("设备信息对话框显示成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"显示手机信息对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"显示手机信息对话框失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_set_screen_timeout(self):
        """设置灭屏时间"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 设置灭屏时间")
        logger.debug(f"函数: _on_set_screen_timeout")
        logger.debug(f"设备管理器对象: {self.device_info_manager}")
        try:
            if not hasattr(self, 'device_info_manager') or self.device_info_manager is None:
                logger.error("device_info_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("设备信息管理器未初始化"))
                return
            logger.debug("调用 device_info_manager.set_screen_timeout()")
            self.device_info_manager.set_screen_timeout()
            logger.debug("设置灭屏时间成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"设置灭屏时间失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"设置灭屏时间失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_merge_mtklog(self):
        """合并MTKlog"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 合并MTKlog")
        logger.debug(f"函数: _on_merge_mtklog")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.merge_mtklog()")
            self.other_operations_manager.merge_mtklog()
            logger.debug("合并MTKlog成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"合并MTKlog失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"合并MTKlog失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_extract_pcap_from_mtklog(self):
        """MTKlog提取pcap"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: MTKlog提取pcap")
        logger.debug(f"函数: _on_extract_pcap_from_mtklog")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.extract_pcap_from_mtklog()")
            self.other_operations_manager.extract_pcap_from_mtklog()
            logger.debug("MTKlog提取pcap成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"MTKlog提取pcap失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"MTKlog提取pcap失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_merge_pcap(self):
        """合并PCAP"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 合并PCAP")
        logger.debug(f"函数: _on_merge_pcap")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.merge_pcap()")
            self.other_operations_manager.merge_pcap()
            logger.debug("合并PCAP成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"合并PCAP失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"合并PCAP失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_extract_pcap_from_qualcomm_log(self):
        """高通log提取pcap"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 高通log提取pcap")
        logger.debug(f"函数: _on_extract_pcap_from_qualcomm_log")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.extract_pcap_from_qualcomm_log()")
            self.other_operations_manager.extract_pcap_from_qualcomm_log()
            logger.debug("高通log提取pcap成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"高通log提取pcap失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"高通log提取pcap失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_mtk_sip_decode(self):
        """MTK SIP DECODE"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: MTK SIP DECODE")
        logger.debug(f"函数: _on_mtk_sip_decode")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.mtk_sip_decode()")
            self.other_operations_manager.mtk_sip_decode()
            logger.debug("MTK SIP DECODE成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"MTK SIP DECODE失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"MTK SIP DECODE失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_parse_3gpp_message(self):
        """3GPP消息解码"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 3GPP消息解码")
        logger.debug(f"函数: _on_parse_3gpp_message")
        try:
            logger.debug("开始导入模块: ui.rrc3gpp_decoder_dialog")
            from ui.rrc3gpp_decoder_dialog import RRC3GPPDecoderDialog
            logger.debug("模块导入成功: RRC3GPPDecoderDialog")
            from PySide6.QtWidgets import QDialog, QMessageBox
            logger.debug("模块导入成功: QDialog, QMessageBox")
            
            logger.debug("创建 RRC3GPPDecoderDialog 实例")
            dialog = RRC3GPPDecoderDialog(self, decoder=self.rrc3gpp_decoder)
            logger.debug("显示对话框")
            dialog.exec()
            logger.debug("对话框已关闭")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"3GPP消息解码失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"3GPP消息解码失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_3gpp_decoder_status(self, message):
        """3GPP消息解码状态消息"""
        self.update_status.emit(message)
        
    def _on_configure_hera(self):
        """赫拉配置"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 赫拉配置")
        logger.debug(f"函数: _on_configure_hera")
        logger.debug(f"赫拉配置管理器对象: {self.hera_config_manager}")
        try:
            if not hasattr(self, 'hera_config_manager') or self.hera_config_manager is None:
                logger.error("hera_config_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("赫拉配置管理器未初始化"))
                return
            logger.debug("调用 hera_config_manager.configure_hera()")
            self.hera_config_manager.configure_hera()
            logger.debug("赫拉配置成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"赫拉配置失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"赫拉配置失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_configure_collect_data(self):
        """赫拉测试数据收集"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 赫拉测试数据收集")
        logger.debug(f"函数: _on_configure_collect_data")
        logger.debug(f"赫拉配置管理器对象: {self.hera_config_manager}")
        try:
            if not hasattr(self, 'hera_config_manager') or self.hera_config_manager is None:
                logger.error("hera_config_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("赫拉配置管理器未初始化"))
                return
            logger.debug("调用 hera_config_manager.configure_collect_data()")
            self.hera_config_manager.configure_collect_data()
            logger.debug("赫拉测试数据收集成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"赫拉测试数据收集失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"赫拉测试数据收集失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
        
    def _on_show_input_text_dialog(self):
        """显示输入文本对话框"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示输入文本对话框")
        logger.debug(f"函数: _on_show_input_text_dialog")
        logger.debug(f"其他操作管理器对象: {self.other_operations_manager}")
        try:
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("错误"), self.tr("其他操作管理器未初始化"))
                return
            logger.debug("调用 other_operations_manager.show_input_text_dialog()")
            self.other_operations_manager.show_input_text_dialog()
            logger.debug("显示输入文本对话框成功")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"模块导入失败: {str(e)}"))
        except Exception as e:
            logger.error(f"显示输入文本对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"显示输入文本对话框失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_show_pr_translation_dialog(self):
        """显示PR翻译对话框"""
        logger.debug("=" * 60)
        logger.debug("【重要】_on_show_pr_translation_dialog 函数被调用！")
        logger.debug("按钮点击: 显示PR翻译对话框")
        logger.debug(f"函数: _on_show_pr_translation_dialog")
        try:
            logger.debug("开始导入模块: ui.pr_translation_dialog")
            from ui.pr_translation_dialog import PRTranslationDialog
            logger.debug("模块导入成功: PRTranslationDialog")
            logger.debug("创建 PRTranslationDialog 实例")
            dialog = PRTranslationDialog(parent=self)
            logger.debug("显示对话框")
            dialog.exec()
            logger.debug("PR翻译对话框已关闭")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"显示PR翻译对话框失败: {str(e)}"))
        except Exception as e:
            logger.error(f"显示PR翻译对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"显示PR翻译对话框失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    # 菜单栏信号处理
    def _on_show_display_lines_dialog(self):
        """显示设置显示行数对话框"""
        dialog = DisplayLinesDialog(current_lines=self.log_processor.adaptive_params['max_display_lines'], parent=self)
        if dialog.exec() == DisplayLinesDialog.DialogCode.Accepted:
            new_lines = dialog.result_lines
            self.log_processor.adaptive_params['max_display_lines'] = new_lines
            self.log_processor.adaptive_params['trim_threshold'] = int(new_lines * 0.05)
            self.statusBar().showMessage(f"{self.lang_manager.tr('最大显示行数已设置为')}: {new_lines} {self.lang_manager.tr('行')}")
            QMessageBox.information(self, self.lang_manager.tr("成功"), 
                f"{self.lang_manager.tr('设置已应用')}!\n{self.lang_manager.tr('最大显示行数')}: {new_lines}\ntrim_threshold: {self.log_processor.adaptive_params['trim_threshold']}")
    
    def _on_show_tools_config_dialog(self):
        """显示工具配置对话框"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示工具配置对话框")
        logger.debug(f"函数: _on_show_tools_config_dialog")
        try:
            logger.debug("检查 other_operations_manager 对象")
            if not hasattr(self, 'other_operations_manager') or self.other_operations_manager is None:
                logger.error("other_operations_manager 未初始化或为None")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.lang_manager.tr("错误"), self.lang_manager.tr("其他操作管理器未初始化"))
                return
            logger.debug(f"other_operations_manager.tool_config: {self.other_operations_manager.tool_config}")
            logger.debug("开始导入模块: ui.tools_config_dialog")
            from ui.tools_config_dialog import ToolsConfigDialog
            logger.debug("模块导入成功: ToolsConfigDialog")
            logger.debug("创建 ToolsConfigDialog 实例")
            dialog = ToolsConfigDialog(self.other_operations_manager.tool_config, parent=self)
            logger.debug("显示对话框")
            dialog.exec()
            logger.debug("工具配置对话框已关闭")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开工具配置对话框失败')}：{str(e)}")
        except Exception as e:
            logger.error(f"打开工具配置对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开工具配置对话框失败')}：{str(e)}")
        finally:
            logger.debug("=" * 60)
    
    def _on_show_jira_tool(self):
        """显示JIRA工具窗口"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示JIRA工具窗口")
        logger.debug(f"函数: _on_show_jira_tool")
        try:
            from core.jira_tool_launcher import launch_jira_tool
            launch_jira_tool(self)
            logger.debug("JIRA工具窗口启动成功")
        except Exception as e:
            logger.exception(f"启动JIRA工具失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), self.lang_manager.tr(f"启动JIRA工具失败: {str(e)}"))
        finally:
            logger.debug("=" * 60)
    
    def _on_show_at_tool_dialog(self):
        """显示AT工具对话框"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示AT工具对话框")
        logger.debug(f"函数: _on_show_at_tool_dialog")
        try:
            logger.debug("开始导入模块: ui.at_tool_dialog")
            from ui.at_tool_dialog import ATCommandDialog
            logger.debug("模块导入成功: ATCommandDialog")
            logger.debug("创建 ATCommandDialog 实例")
            dialog = ATCommandDialog(parent=self)
            logger.debug("显示对话框")
            dialog.exec()
            logger.debug("AT工具对话框已关闭")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开AT工具对话框失败')}：{str(e)}")
        except Exception as e:
            logger.error(f"打开AT工具对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开AT工具对话框失败')}：{str(e)}")
        finally:
            logger.debug("=" * 60)
    
    def _on_show_encoding_tool_dialog(self):
        """显示转码工具对话框"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 显示转码工具对话框")
        logger.debug(f"函数: _on_show_encoding_tool_dialog")
        try:
            logger.debug("开始导入模块: ui.encoding_tool_dialog")
            from ui.encoding_tool_dialog import EncodingToolDialog
            logger.debug("模块导入成功: EncodingToolDialog")
            logger.debug("创建 EncodingToolDialog 实例")
            dialog = EncodingToolDialog(parent=self)
            logger.debug("显示对话框")
            dialog.exec()
            logger.debug("转码工具对话框已关闭")
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开转码工具对话框失败')}：{str(e)}")
        except Exception as e:
            logger.error(f"打开转码工具对话框失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开转码工具对话框失败')}：{str(e)}")
        finally:
            logger.debug("=" * 60)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        from PySide6.QtGui import QKeySequence, QShortcut
        
        # Ctrl+F - 搜索
        shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_search.activated.connect(lambda: self.log_viewer.search_edit.setFocus())
        
        # F3 - 查找下一个
        shortcut_next = QShortcut(QKeySequence("F3"), self)
        shortcut_next.activated.connect(self.log_viewer.find_next)
        
        # Shift+F3 - 查找上一个
        shortcut_prev = QShortcut(QKeySequence("Shift+F3"), self)
        shortcut_prev.activated.connect(self.log_viewer.find_previous)
        
        # Ctrl+G - 查找下一个（备用）
        shortcut_next_alt = QShortcut(QKeySequence("Ctrl+G"), self)
        shortcut_next_alt.activated.connect(self.log_viewer.find_next)
    
    # 截图管理器信号处理
    def _on_screenshot_completed(self, message):
        """截图完成"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_screenshot_progress(self, progress, status):
        """截图进度更新"""
        self.append_log.emit(f"[{progress}%] {status}\n", None)
    
    def _on_screenshot_status(self, message):
        """截图状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 录制管理器信号处理
    def _on_recording_started(self):
        """录制开始"""
        # 更新按钮状态
        record_btn = self.toolbar.record_btn
        record_btn.blockSignals(True)
        record_btn.setText(self.lang_manager.tr("停止录制"))
        record_btn.setChecked(True)
        record_btn.blockSignals(False)
        self.append_log.emit(self.lang_manager.tr("视频录制已开始") + "\n", None)
    
    def _on_recording_stopped(self):
        """录制停止"""
        # 更新按钮状态
        record_btn = self.toolbar.record_btn
        record_btn.blockSignals(True)
        record_btn.setText(self.lang_manager.tr("开始录制"))
        record_btn.setChecked(False)
        record_btn.blockSignals(False)
        self.append_log.emit(self.lang_manager.tr("视频录制已停止") + "\n", None)
    
    def _on_video_saved(self, folder, count):
        """视频保存完成（仅在直接点击停止录制按钮时调用）"""
        if count > 0:
            self.append_log.emit(f"{self.tr('视频已保存到: ')}{folder} ({count}{self.tr('个文件)')}\n", None)
    
    def _on_video_status(self, message):
        """录制状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 其他管理器信号处理
    def _on_tcpdump_status(self, message):
        """TCPDUMP状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_telephony_status(self, message):
        """Telephony状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_google_log_status(self, message):
        """Google Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_aee_log_status(self, message):
        """AEE Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_bugreport_status(self, message):
        """Bugreport状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # TMO CC管理器信号处理
    def _on_cc_pulled(self, folder):
        """CC文件拉取完成"""
        self.append_log.emit(f"{self.tr('CC文件已拉取到: ')}{folder}\n", None)
    
    def _on_cc_pushed(self, success_count, total_count):
        """CC文件推送完成"""
        self.append_log.emit(f"{self.tr('CC文件推送完成: ')}{success_count}/{total_count} {self.tr('个文件成功')}\n", None)
    
    def _on_server_started(self, server_type):
        """服务器启动完成"""
        self.append_log.emit(f"{server_type}{self.tr('服务器活动已启动')}\n", None)
    
    def _on_tmo_cc_status(self, message):
        """TMO CC状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # Echolocate管理器信号处理
    def _on_echolocate_installed(self):
        """Echolocate安装完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate安装完成并已启动") + "\n", None)
    
    def _on_echolocate_triggered(self):
        """Echolocate触发完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate应用已启动") + "\n", None)
    
    def _on_echolocate_file_pulled(self, folder):
        """Echolocate文件拉取完成"""
        self.append_log.emit(f"{self.tr('Echolocate文件已拉取到: ')}{folder}\n", None)
    
    def _on_echolocate_file_deleted(self):
        """Echolocate文件删除完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate文件已删除") + "\n", None)
    
    def _on_echolocate_status(self, message):
        """Echolocate状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 背景数据管理器信号处理
    def _on_background_data_status(self, message):
        """背景数据状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_background_data_log(self, message, color):
        """背景数据日志消息（带颜色）"""
        self.append_log.emit(f"{message}\n", color)
    
    # APP操作管理器信号处理
    def _on_app_operations_status(self, message):
        """APP操作状态消息"""
        # 检查是否包含包名信息，如果是则使用绿色
        if "Current foreground app package:" in message or "当前前台应用包名:" in message:
            # 提取包名部分并设置为绿色
            import re
            # 匹配包名模式 (com.xxx.xxx 格式)
            package_pattern = r'(com\.[a-zA-Z0-9_.]+)'
            if re.search(package_pattern, message):
                # 分割消息，分别处理包名部分和其他部分
                parts = re.split(package_pattern, message)
                for i, part in enumerate(parts):
                    if re.match(package_pattern, part):
                        # 包名部分使用绿色
                        self.append_log.emit(part, "green")
                    else:
                        # 其他部分使用默认颜色，最后添加换行符
                        if i == len(parts) - 1:  # 最后一部分
                            self.append_log.emit(f"{part}\n", None)
                        else:
                            self.append_log.emit(part, None)
            else:
                self.append_log.emit(f"{message}\n", None)
        else:
            self.append_log.emit(f"{message}\n", None)
    
    # 设备信息管理器信号处理
    def _on_device_info_status(self, message):
        """设备信息状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 赫拉配置管理器信号处理
    def _on_hera_config_status(self, message):
        """赫拉配置状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 其他操作管理器信号处理
    def _on_other_operations_status(self, message):
        """其他操作状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 自定义按钮相关方法
    def load_custom_buttons_for_all_tabs(self):
        """为所有Tab加载自定义按钮"""
        try:
            logger.info(self.lang_manager.tr("开始为所有Tab加载自定义按钮..."))
            
            # 获取所有Tab对应的实例
            tabs = {
                'Log控制': self.log_control_tab,
                'Log过滤': self.log_filter_tab,
                '网络信息': self.network_info_tab,
                'TMO CC': self.tmo_cc_tab,
                'TMO Echolocate': self.tmo_echolocate_tab,
                '24小时背景数据': self.background_data_tab,
                'APP操作': self.app_operations_tab,
                '其他': self.other_tab
            }
            
            logger.debug(f"{self.lang_manager.tr('处理预制Tab:')} {list(tabs.keys())}")
            
            for tab_name, tab_instance in tabs.items():
                self.load_custom_buttons_for_tab(tab_name, tab_instance)
            
            # 处理自定义Tab
            logger.debug(f"{self.lang_manager.tr('处理自定义Tab...')}")
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if hasattr(widget, 'tab_id'):
                    tab_id = widget.tab_id
                    logger.debug(f"{self.lang_manager.tr('检查Tab:')} {tab_id}")
                    
                    # 检查是否是自定义Tab
                    for custom_tab in self.tab_config_manager.custom_tabs:
                        if custom_tab['id'] == tab_id:
                            logger.debug(f"{self.lang_manager.tr('找到自定义Tab:')} {custom_tab['name']}")
                            self.load_custom_buttons_for_custom_tab(custom_tab, widget)
                            break
            
            logger.info(self.lang_manager.tr("所有Tab的自定义按钮加载完成"))
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('加载自定义按钮失败:')} {e}")
    
    def load_custom_buttons_for_custom_tab(self, custom_tab, tab_widget):
        """为自定义Tab加载自定义按钮"""
        try:
            # 获取该自定义Tab的所有自定义Card
            custom_cards = self.tab_config_manager.get_custom_cards_for_tab(custom_tab['id'])
            
            for card in custom_cards:
                # 获取该Card的自定义按钮
                tab_name = custom_tab['name']
                buttons = self.custom_button_manager.get_buttons_by_location(tab_name, card['name'])
                if buttons:
                    logger.debug(f"[自定义Tab] Tab '{tab_name}', Card '{card['name']}' 有 {len(buttons)} 个按钮")
                
                if buttons:
                    # 查找对应的Card GroupBox并添加按钮
                    self._add_buttons_to_custom_card(tab_widget, tab_name, card['name'], buttons)
                else:
                    # 清除按钮时，重置card宽度
                    self._clear_button_container(tab_widget, tab_name, card['name'])
                    self._reset_custom_card_width(tab_widget, card['name'])
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('为自定义Tab加载按钮失败:')} {e}")
    
    def _add_buttons_to_custom_card(self, tab_widget, tab_name, card_name, buttons):
        """向自定义Card添加按钮"""
        try:
            from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
            
            # 现在自定义Card使用QFrame+QLabel结构，与预置tab一致
            # 查找对应的Frame（标记为custom_card）
            frames = tab_widget.findChildren(QFrame)
            
            for frame in frames:
                # 仅处理自定义Card的Frame
                if frame.property('custom_card') and frame.objectName() == "card":
                    # 检查Frame上方是否有对应的标题Label
                    parent_widget = frame.parent()
                    if parent_widget:
                        labels = parent_widget.findChildren(QLabel)
                        for label in labels:
                            label_text = label.text()
                            label_class = label.property("class")
                            
                            if label_text == card_name and label_class == "section-title":
                                button_layouts = frame.findChildren(QHBoxLayout)
                                
                                if button_layouts:
                                    button_layout = button_layouts[0]
                                    container = self._get_or_create_button_container(tab_widget, button_layout, tab_name, card_name)
                                    container.clear_buttons()
                                    for btn_data in buttons:
                                        container.add_custom_button(btn_data)
                                    
                                    # 动态调整自定义card的宽度
                                    self._adjust_custom_card_width(frame, container)
                                else:
                                    logger.warning(f"{self.lang_manager.tr('未找到按钮布局')}")
                                return
                
                elif frame.property('custom_card'):
                    logger.debug(f"{self.lang_manager.tr('跳过，不是card对象名的Frame')}")
            
            logger.warning(f"{self.lang_manager.tr('未找到自定义Card')} '{card_name}'")
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向自定义Card添加按钮失败:')} {e}")
    
    def _adjust_custom_card_width(self, card_frame, button_container):
        """根据按钮情况动态调整自定义card的宽度"""
        try:
            from PySide6.QtCore import QTimer
            
            # 使用QTimer延迟计算，确保按钮已经完成布局
            def calculate_and_set_width():
                try:
                    # 计算所有按钮的总宽度
                    total_button_width = 0
                    button_count = 0
                    
                    # 从布局中获取按钮（即使按钮不可见，因为按钮可能在不激活的tab中）
                    buttons_from_layout = []
                    for i in range(button_container._layout.count()):
                        item = button_container._layout.itemAt(i)
                        if item and item.widget():
                            widget = item.widget()
                            if isinstance(widget, DraggableCustomButton):
                                buttons_from_layout.append(widget)
                    
                    # 如果布局中没有按钮，尝试从_button_widgets获取
                    if not buttons_from_layout:
                        buttons_from_layout = list(button_container._button_widgets.values())
                    
                    for button_widget in buttons_from_layout:
                        # 先确保按钮已经完成布局
                        button_widget.adjustSize()
                        button_widget.updateGeometry()
                        
                        # 获取按钮文本用于估算宽度
                        button_text = button_widget.text()
                        
                        # 获取按钮的实际宽度（优先使用实际宽度）
                        button_width = button_widget.width()
                        size_hint_width = button_widget.sizeHint().width()
                        min_hint_width = button_widget.minimumSizeHint().width()
                        is_visible = button_widget.isVisible()
                        
                        # 如果按钮不可见或实际宽度无效，使用文本长度估算
                        if not is_visible or button_width <= 0 or button_width < 50:
                            # 先尝试使用sizeHint
                            if size_hint_width > 0 and size_hint_width >= 50:
                                button_width = size_hint_width
                            elif min_hint_width > 0 and min_hint_width >= 50:
                                button_width = min_hint_width
                            else:
                                # 根据文本长度估算宽度（中文字符按2倍宽度计算）
                                chinese_chars = sum(1 for c in button_text if '\u4e00' <= c <= '\u9fff')
                                english_chars = len(button_text) - chinese_chars
                                estimated_width = chinese_chars * 18 + english_chars * 9 + 24
                                button_width = max(estimated_width, 80)
                        elif button_width < 50:
                            # 如果实际宽度太小，也使用估算
                            chinese_chars = sum(1 for c in button_text if '\u4e00' <= c <= '\u9fff')
                            english_chars = len(button_text) - chinese_chars
                            estimated_width = chinese_chars * 18 + english_chars * 9 + 24
                            button_width = max(estimated_width, button_width)
                        
                        total_button_width += button_width
                        button_count += 1
                    
                    if button_count == 0:
                        # 没有按钮时，使用默认最小宽度
                        min_width = 200
                    else:
                        # 计算总宽度：按钮宽度 + 按钮间距 + card的padding和margin
                        button_spacing = button_container._layout.spacing()
                        spacing_width = button_spacing * max(0, button_count - 1)
                        
                        # card的padding: 左右各10px
                        card_padding = 20
                        
                        # card的margin: 左右各6px
                        card_margin = 12
                        
                        # 计算最小宽度，增加10%的余量以确保按钮不会重叠
                        safety_margin = int(total_button_width * 0.1)
                        min_width = total_button_width + spacing_width + card_padding + card_margin + safety_margin
                        min_width = max(min_width, 200)
                    
                    # 设置sizePolicy为Preferred，不拉伸
                    from PySide6.QtWidgets import QSizePolicy
                    size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    size_policy.setHorizontalStretch(0)
                    card_frame.setSizePolicy(size_policy)
                    
                    # 设置最小宽度和最大宽度
                    card_frame.setMinimumWidth(min_width)
                    card_frame.setMaximumWidth(min_width * 2)
                    
                    # 设置固定宽度，避免被父布局拉伸
                    card_frame.setFixedWidth(min_width)
                    
                    # 更新布局
                    card_frame.updateGeometry()
                    if card_frame.parent() and hasattr(card_frame.parent(), 'layout'):
                        parent_layout = card_frame.parent().layout()
                        if parent_layout:
                            parent_layout.invalidate()
                            parent_layout.update()
                    
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('计算Card宽度失败:')} {e}")
            
            # 延迟执行，确保按钮布局完成
            # 使用重试机制，确保按钮已经添加到布局中
            container_ref = [button_container]  # 使用列表来避免nonlocal问题
            
            retry_count = [5]  # 最多重试5次
            def retry_calculate(delay=200):
                """重试计算宽度，直到找到按钮或达到最大重试次数"""
                def attempt():
                    current_container = container_ref[0]
                    
                    # 检查按钮是否已经添加到布局中
                    buttons_from_layout = []
                    for i in range(current_container._layout.count()):
                        item = current_container._layout.itemAt(i)
                        if item and item.widget():
                            widget = item.widget()
                            if isinstance(widget, DraggableCustomButton):
                                buttons_from_layout.append(widget)
                    
                    # 如果布局中没有按钮，尝试从_button_widgets获取
                    if not buttons_from_layout:
                        buttons_from_layout = list(current_container._button_widgets.values())
                    
                    if len(buttons_from_layout) > 0:
                        # 找到按钮了，执行计算
                        calculate_and_set_width()
                    else:
                        # 还没找到按钮，继续重试
                        retry_count[0] -= 1
                        if retry_count[0] > 0:
                            QTimer.singleShot(delay, attempt)
                        else:
                            # 达到最大重试次数，尝试从card_frame重新查找container
                            found_container = None
                            for child in card_frame.findChildren(CustomButtonContainer):
                                if child.tab_name == container_ref[0].tab_name and child.card_name == container_ref[0].card_name:
                                    found_container = child
                                    break
                            
                            if found_container and len(found_container._button_widgets) > 0:
                                # 更新container引用并重新计算
                                container_ref[0] = found_container
                                calculate_and_set_width()
                            else:
                                # 即使没找到按钮，也尝试计算（会使用默认宽度）
                                calculate_and_set_width()
                
                # 第一次延迟执行
                QTimer.singleShot(delay, attempt)
            
            retry_calculate(delay=200)
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('调整Card宽度失败:')} {e}")
    
    def _reset_custom_card_width(self, tab_widget, card_name):
        """重置自定义card的宽度（当按钮被清除时）"""
        try:
            from PySide6.QtWidgets import QFrame, QLabel
            
            # 查找对应的card frame
            frames = tab_widget.findChildren(QFrame)
            for frame in frames:
                if frame.property('custom_card') and frame.objectName() == "card":
                    # 检查Frame上方是否有对应的标题Label
                    parent_widget = frame.parent()
                    if parent_widget:
                        labels = parent_widget.findChildren(QLabel)
                        for label in labels:
                            label_text = label.text()
                            label_class = label.property("class")
                            
                            if label_text == card_name and label_class == "section-title":
                                # 重置为默认最小宽度
                                frame.setMinimumWidth(200)
                                logger.debug(f"{self.lang_manager.tr('重置Card宽度:')} '{card_name}'")
                                return
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('重置Card宽度失败:')} {e}")
    
    def load_custom_buttons_for_tab(self, tab_name, tab_instance):
        """为指定Tab加载自定义按钮"""
        try:
            # 检查Tab实例是否有custom_buttons_container属性（用于存储自定义按钮）
            if not hasattr(tab_instance, 'custom_buttons_containers'):
                tab_instance.custom_buttons_containers = {}
            
            # 获取该Tab的所有卡片（GroupBox或Frame）
            # 遍历Tab中的所有子部件，找到卡片
            self._add_custom_buttons_to_tab(tab_name, tab_instance)
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('为Tab')} '{tab_name}' {self.lang_manager.tr('加载自定义按钮失败:')} {e}")
    
    def _add_custom_buttons_to_tab(self, tab_name, tab_instance):
        """为Tab添加自定义按钮"""
        # 获取Tab下所有可用的卡片名称
        cards = self.custom_button_manager.get_available_cards(tab_name)
        
        for card_name in cards:
            # 获取该位置的自定义按钮
            buttons = self.custom_button_manager.get_buttons_by_location(tab_name, card_name)
            
            if buttons:
                # 尝试找到对应的卡片容器并添加按钮
                self._inject_custom_buttons_to_card(tab_instance, tab_name, card_name, buttons)
            else:
                self._clear_button_container(tab_instance, tab_name, card_name)
    
    def _inject_custom_buttons_to_card(self, tab_instance, tab_name, card_name, buttons):
        """向指定卡片注入自定义按钮（仅处理预制Card）"""
        try:
            from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel
            
            logger.debug(f"{self.lang_manager.tr('尝试向预制卡片')} '{card_name}' {self.lang_manager.tr('注入')} {len(buttons)} {self.lang_manager.tr('个按钮')}")
            
            # 检查是否是自定义Card，如果是则跳过（自定义Card由_create_custom_card_group处理）
            custom_card = self._find_custom_card_by_name(card_name)
            if custom_card:
                logger.debug(f"{self.lang_manager.tr('跳过自定义Card')} '{card_name}' {self.lang_manager.tr('，由统一方法处理')}")
                return
            
            # 搜索Tab中的所有Frame/卡片（仅处理预制Card）
            frames = tab_instance.findChildren(QFrame)
            logger.debug(f"{self.lang_manager.tr('找到')} {len(frames)} {self.lang_manager.tr('个Frame')}")
            
            found_card = False
            for frame in frames:
                # 仅处理我们定义的卡片Frame
                if frame.objectName() != "card":
                    continue
                # 检查Frame上方是否有对应的标题Label
                parent_widget = frame.parent()
                if parent_widget:
                    labels = parent_widget.findChildren(QLabel)
                    
                    for label in labels:
                        label_text = label.text()
                        label_class = label.property("class")
                        
                        if label_text == card_name and label_class == "section-title":
                            logger.debug(f"{self.lang_manager.tr('找到匹配的预制卡片:')} '{card_name}'")
                            found_card = True
                            
                            # 找到了对应的卡片
                            layout = frame.layout()
                            if not layout:
                                logger.debug(f"{self.lang_manager.tr('Frame没有直接布局，尝试查找子部件布局')} ...")
                                # 回退：在该Frame下寻找首个带布局的子部件
                                for child in frame.findChildren(QWidget):
                                    if child.layout():
                                        layout = child.layout()
                                        logger.debug(f"{self.lang_manager.tr('使用子部件布局作为按钮布局')} -> {type(layout).__name__}")
                                        break
                            if layout:
                                # 使用统一的按钮添加逻辑
                                self._populate_button_layout(tab_instance, tab_name, card_name, layout, buttons)
                                break
                            else:
                                logger.warning(f"{self.lang_manager.tr('未能获取到卡片布局')} '{card_name}'")
                    
                    if found_card:
                        break
                                    
            if not found_card:
                logger.warning(f"{self.lang_manager.tr('未找到预制卡片')} '{card_name}'")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向预制卡片')} '{card_name}' {self.lang_manager.tr('注入自定义按钮失败:')} {e}")
    
    def _populate_button_layout(self, tab_instance, tab_name, card_name, layout, buttons):
        """在指定布局中填充自定义按钮容器"""
        try:
            from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget
            
            button_layout = None
            
            if isinstance(layout, QHBoxLayout):
                button_layout = layout
                logger.debug(f"{self.lang_manager.tr('直接使用QHBoxLayout作为按钮布局')}")
            elif isinstance(layout, QVBoxLayout):
                for i in range(layout.count() - 1, -1, -1):
                    item = layout.itemAt(i)
                    if item:
                        if item.layout() and isinstance(item.layout(), QHBoxLayout):
                            button_layout = item.layout()
                            logger.debug(f"{self.lang_manager.tr('在QVBoxLayout中找到子QHBoxLayout作为按钮布局')}")
                            break
                        if item.widget() and item.widget().layout() and isinstance(item.widget().layout(), QHBoxLayout):
                            button_layout = item.widget().layout()
                            logger.debug(f"{self.lang_manager.tr('在QVBoxLayout的子Widget中找到QHBoxLayout作为按钮布局')}")
                            break
                        if item.layout() and isinstance(item.layout(), QVBoxLayout):
                            nested = item.layout()
                            for j in range(nested.count() - 1, -1, -1):
                                sub = nested.itemAt(j)
                                if sub and sub.layout() and isinstance(sub.layout(), QHBoxLayout):
                                    button_layout = sub.layout()
                                    logger.debug(f"{self.lang_manager.tr('在嵌套QVBoxLayout中找到子QHBoxLayout作为按钮布局')}")
                                    break
                            if button_layout:
                                break
            elif isinstance(layout, QGridLayout):
                for i in range(layout.count() - 1, -1, -1):
                    item = layout.itemAt(i)
                    if item:
                        if item.layout() and isinstance(item.layout(), QHBoxLayout):
                            button_layout = item.layout()
                            logger.debug(f"{self.lang_manager.tr('在QGridLayout中找到子QHBoxLayout作为按钮布局')}")
                            break
                        if item.widget() and isinstance(item.widget(), QWidget) and item.widget().layout():
                            sub_layout = item.widget().layout()
                            if isinstance(sub_layout, QHBoxLayout):
                                button_layout = sub_layout
                                logger.debug(f"{self.lang_manager.tr('在QGridLayout的子Widget中找到QHBoxLayout作为按钮布局')}")
                                break
            
            if button_layout:
                container = self._get_or_create_button_container(tab_instance, button_layout, tab_name, card_name)
                if container is None:
                    return
                container.clear_buttons()
                for btn_data in buttons:
                    container.add_custom_button(btn_data)
                logger.debug(f"[按钮加载] 已加载 {len(buttons)} 个按钮到 '{card_name}'")
            else:
                logger.warning(f"{self.lang_manager.tr('未找到合适的按钮布局')}")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向布局添加按钮失败:')} {e}")
    
    def _get_or_create_button_container(self, tab_instance, base_layout, tab_name, card_name):
        """获取或创建用于承载自定义按钮的容器"""
        try:
            if not hasattr(tab_instance, 'custom_buttons_containers'):
                tab_instance.custom_buttons_containers = {}

            key = (tab_name, card_name)
            container = tab_instance.custom_buttons_containers.get(key)

            if container is None or container.parent() is None:
                self._remove_legacy_custom_buttons(base_layout)
                container = CustomButtonContainer(self, tab_name, card_name)
                container.order_changed.connect(self._on_custom_button_order_changed)
                tab_instance.custom_buttons_containers[key] = container

                insert_pos = base_layout.count()
                if insert_pos > 0 and base_layout.itemAt(insert_pos - 1).spacerItem():
                    insert_pos -= 1
                base_layout.insertWidget(insert_pos, container)
            else:
                container.update_context(tab_name, card_name)

            return container

        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('创建按钮容器失败:')} {e}")
            return None

    def _remove_legacy_custom_buttons(self, layout):
        """移除旧版本遗留的自定义按钮控件"""
        try:
            for index in range(layout.count() - 1, -1, -1):
                item = layout.itemAt(index)
                widget = item.widget() if item else None
                if widget and isinstance(widget, QPushButton) and widget.property('custom_button'):
                    layout.takeAt(index)
                    widget.setParent(None)
                    widget.deleteLater()
        except Exception as e:
            logger.warning(f"{self.lang_manager.tr('清理旧自定义按钮失败:')} {e}")

    def _clear_button_container(self, tab_instance, tab_name, card_name):
        """清空指定容器中的自定义按钮"""
        try:
            if hasattr(tab_instance, 'custom_buttons_containers'):
                container = tab_instance.custom_buttons_containers.get((tab_name, card_name))
                if container:
                    container.clear_buttons()
        except Exception as e:
            logger.warning(f"{self.lang_manager.tr('清空按钮容器失败:')} {e}")

    def _on_custom_button_order_changed(self, tab_name, card_name, ordered_ids):
        """处理主界面拖拽排序后的保存逻辑"""
        try:
            if not ordered_ids:
                return

            if not self.custom_button_manager.reorder_buttons_in_location(tab_name, card_name, ordered_ids):
                logger.warning(self.lang_manager.tr("保存自定义按钮排序失败"))
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('处理按钮排序更新失败:')} {e}")

    def execute_custom_button_command(self, button_data):
        """执行自定义按钮命令（异步执行）"""
        logger.debug("=" * 60)
        logger.debug("按钮点击: 执行自定义按钮命令")
        logger.debug(f"函数: execute_custom_button_command")
        try:
            name = button_data.get('name', self.lang_manager.tr('自定义按钮'))
            button_type = button_data.get('type', 'unknown')
            logger.debug(f"按钮名称: {name}")
            logger.debug(f"按钮类型: {button_type}")
            logger.debug(f"按钮数据: {button_data}")
            
            self.append_log.emit(f"🔧 {self.tr('执行自定义按钮: ')}{name}\n", "#17a2b8")
            
            logger.debug("检查必要对象")
            if not hasattr(self, 'device_manager') or self.device_manager is None:
                logger.error("device_manager 未初始化或为None")
                raise RuntimeError("设备管理器未初始化")
            if not hasattr(self, 'custom_button_manager') or self.custom_button_manager is None:
                logger.error("custom_button_manager 未初始化或为None")
                raise RuntimeError("自定义按钮管理器未初始化")
            
            logger.debug("开始导入模块: ui.main_window.ButtonCommandWorker")
            from ui.main_window import ButtonCommandWorker
            logger.debug("模块导入成功: ButtonCommandWorker")
            
            logger.debug("创建 ButtonCommandWorker 实例")
            worker = ButtonCommandWorker(
                button_data,
                self.device_manager.selected_device,
                self.custom_button_manager,
                self.lang_manager,
                self  # 传递主窗口引用
            )
            logger.debug("ButtonCommandWorker 实例创建成功")
            
            # 保存工作线程引用（避免被垃圾回收）
            self._button_command_workers.append(worker)
            logger.debug(f"工作线程已添加到列表，当前线程数: {len(self._button_command_workers)}")
            
            logger.debug("连接工作线程信号")
            # 连接信号
            worker.finished.connect(lambda success, output, btn_name, w=worker: self._on_button_command_finished(success, output, btn_name, w))
            logger.debug("信号连接成功: finished")
            
            # 连接日志消息信号（用于实时显示程序输出）
            worker.log_message.connect(lambda msg, color: self.append_log.emit(msg, color))
            logger.debug("信号连接成功: log_message")
            
            # 连接对话框请求信号（用于脚本中的UI调用）
            worker.dialog_request.connect(
                lambda dialog_type, title, message, buttons, default_button, w=worker: 
                self._handle_script_dialog_request(dialog_type, title, message, buttons, default_button, w)
            )
            logger.debug("信号连接成功: dialog_request")
            
            logger.debug("启动工作线程")
            # 启动线程
            worker.start()
            logger.debug("工作线程启动成功")
            
        except ImportError as e:
            logger.error(f"模块导入失败:\n  错误类型: ImportError\n  错误信息: {str(e)}")
            logger.exception("模块导入异常详情")
            self.append_log.emit(f"❌ {self.tr('启动执行失败: ')}{str(e)}\n", "#dc3545")
        except Exception as e:
            logger.error(f"启动自定义按钮命令执行失败:\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
            self.append_log.emit(f"❌ {self.tr('启动执行失败: ')}{str(e)}\n", "#dc3545")
        finally:
            logger.debug("=" * 60)
    
    def _handle_script_dialog_request(self, dialog_type, title, message, buttons, default_button, worker):
        """处理脚本中发起的对话框请求（在主线程中执行）"""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            # 将int类型的buttons和default_button转换为QMessageBox.StandardButtons类型
            buttons_enum = QMessageBox.StandardButtons(buttons) if isinstance(buttons, int) else buttons
            default_button_enum = QMessageBox.StandardButton(default_button) if isinstance(default_button, int) else default_button
            
            # 根据对话框类型显示相应的对话框
            if dialog_type == "question":
                reply = QMessageBox.question(
                    self,
                    title,
                    message,
                    buttons_enum,
                    default_button_enum
                )
            elif dialog_type == "information":
                reply = QMessageBox.information(
                    self,
                    title,
                    message,
                    buttons_enum,
                    default_button_enum
                )
            elif dialog_type == "warning":
                reply = QMessageBox.warning(
                    self,
                    title,
                    message,
                    buttons_enum,
                    default_button_enum
                )
            elif dialog_type == "critical":
                reply = QMessageBox.critical(
                    self,
                    title,
                    message,
                    buttons_enum,
                    default_button_enum
                )
            elif dialog_type == "about":
                QMessageBox.about(self, title, message)
                reply = QMessageBox.StandardButton.Ok
            else:
                # 默认使用question
                reply = QMessageBox.question(
                    self,
                    title,
                    message,
                    buttons_enum,
                    default_button_enum
                )
            
            # 通过信号发送响应回工作线程
            worker.dialog_response_received.emit(int(reply))
            
        except Exception as e:
            logger.exception(f"处理脚本对话框请求失败: {e}")
            # 如果出错，发送默认响应
            default_value = int(default_button) if isinstance(default_button, int) else default_button
            worker.dialog_response_received.emit(default_value)
    
    def _on_button_command_finished(self, success, output, button_name, worker):
        """处理按钮命令执行完成"""
        try:
            if success:
                self.append_log.emit(f"✅ {self.tr('执行成功')}\n", "#28a745")
                if output:
                    self.append_log.emit(f"{output}\n", "#9370DB")
            else:
                self.append_log.emit(f"❌ {self.tr('执行失败: ')}{output}\n", "#dc3545")
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('处理按钮命令完成信号失败:')} {e}")
        finally:
            # 清理工作线程引用
            if worker in self._button_command_workers:
                self._button_command_workers.remove(worker)
            # 安全地删除工作线程对象（在事件循环中）
            worker.deleteLater()
    
    def on_custom_buttons_updated(self):
        """自定义按钮配置更新时的处理"""
        try:
            logger.info(self.lang_manager.tr("检测到自定义按钮配置更新，重新加载..."))
            current_index = self.tab_widget.currentIndex()
            current_widget = self.tab_widget.currentWidget() if current_index >= 0 else None
            current_tab_id = getattr(current_widget, 'tab_id', None) if current_widget else None
            
            # 清除所有Tab中的自定义按钮
            self._clear_all_custom_buttons()
            
            # 重新加载预制Tab的自定义按钮
            self.load_custom_buttons_for_all_tabs()
            
            # 重新加载自定义Tab（重新创建Tab实例以包含新的按钮）
            self._refresh_custom_tabs()
            
            # 为新创建的自定义Tab加载按钮
            self.load_custom_buttons_for_all_tabs()

            self._restore_tab_selection(current_tab_id, current_index)
            
            self.append_log.emit(self.lang_manager.tr("自定义按钮已更新") + "\n", "#00FF00")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('更新自定义按钮失败:')} {e}")
    
    def _refresh_custom_tabs(self):
        """刷新自定义Tab（重新创建以包含新的按钮）"""
        try:
            logger.info(self.lang_manager.tr("刷新自定义Tab..."))
            
            # 获取当前Tab顺序和可见性
            tab_order = self.tab_config_manager.get_tab_order()
            tab_visibility = self.tab_config_manager.get_tab_visibility()
            
            # 找到所有自定义Tab的索引
            custom_tab_indices = []
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if hasattr(widget, 'tab_id'):
                    tab_id = widget.tab_id
                    # 检查是否是自定义Tab
                    for custom_tab in self.tab_config_manager.custom_tabs:
                        if custom_tab['id'] == tab_id:
                            custom_tab_indices.append(i)
                            break
            
            # 从后往前删除自定义Tab（避免索引变化）
            for i in reversed(custom_tab_indices):
                self.tab_widget.removeTab(i)
            
            # 重新创建自定义Tab
            for custom_tab in self.tab_config_manager.custom_tabs:
                tab_id = custom_tab['id']
                if tab_visibility.get(tab_id, True):
                    # 重新创建自定义Tab实例
                    custom_tab_instance = self._create_custom_tab_instance(custom_tab)
                    if custom_tab_instance:
                        # 找到正确的插入位置
                        insert_index = self._find_tab_insert_position(tab_id, tab_order)
                        tab_name = self._get_tab_name(tab_id, self.tab_config_manager.get_all_tabs())
                        self.tab_widget.insertTab(insert_index, custom_tab_instance, tab_name)
                        logger.debug(f"{self.lang_manager.tr('重新创建自定义Tab:')} {tab_name}")
            
            logger.info(self.lang_manager.tr("自定义Tab刷新完成"))
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('刷新自定义Tab失败:')} {e}")
    
    def _find_tab_insert_position(self, tab_id, tab_order):
        """找到Tab的插入位置"""
        try:
            # 找到tab_id在tab_order中的位置
            if tab_id in tab_order:
                target_index = tab_order.index(tab_id)
                
                # 计算当前Tab中应该插入的位置
                current_index = 0
                for i, ordered_tab_id in enumerate(tab_order):
                    if ordered_tab_id == tab_id:
                        return current_index
                    
                    # 检查这个Tab是否在当前Tab中可见
                    for j in range(self.tab_widget.count()):
                        widget = self.tab_widget.widget(j)
                        if hasattr(widget, 'tab_id') and widget.tab_id == ordered_tab_id:
                            current_index += 1
                            break
                
                return current_index
            
            return self.tab_widget.count()  # 如果找不到，插入到最后
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('查找Tab插入位置失败:')} {e}")
            return self.tab_widget.count()
    
    def _clear_all_custom_buttons(self):
        """清除所有自定义按钮"""
        try:
            tabs = [
                self.log_control_tab,
                self.log_filter_tab,
                self.network_info_tab,
                self.tmo_cc_tab,
                self.tmo_echolocate_tab,
                self.background_data_tab,
                self.app_operations_tab,
                self.other_tab
            ]
            
            for tab in tabs:
                if hasattr(tab, 'custom_buttons_containers'):
                    for container in tab.custom_buttons_containers.values():
                        container.clear_buttons()

                # 找到所有标记为自定义按钮的QPushButton并删除
                custom_buttons = tab.findChildren(QPushButton)
                for btn in custom_buttons:
                    if btn.property('custom_button'):
                        btn.setParent(None)
                        btn.deleteLater()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('清除自定义按钮失败:')} {e}")

    def _restore_tab_selection(self, target_tab_id, fallback_index=None):
        """根据tab_id恢复当前选中Tab"""
        try:
            if target_tab_id:
                for i in range(self.tab_widget.count()):
                    widget = self.tab_widget.widget(i)
                    if getattr(widget, 'tab_id', None) == target_tab_id:
                        self.tab_widget.setCurrentIndex(i)
                        return
            if fallback_index is not None and 0 <= fallback_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(fallback_index)
        except Exception as e:
            logger.warning(f"[MainWindow] restore tab selection failed: {e}")
    
    def show_config_backup_dialog(self):
        """显示配置备份对话框"""
        try:
            from ui.config_backup_dialog import ConfigBackupDialog
            
            dialog = ConfigBackupDialog(parent=self)
            dialog.exec()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示配置备份对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开配置备份失败')}：{str(e)}")
    
    def show_unified_manager_dialog(self):
        """显示自定义界面管理对话框"""
        try:
            from ui.unified_manager_dialog import UnifiedManagerDialog
            
            dialog = UnifiedManagerDialog(self.tab_config_manager, self.custom_button_manager, parent=self)
            dialog.exec()
            
            # 对话框关闭后，重新加载Tab以应用可能的更改
            self.reload_tabs()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示自定义界面管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开自定义界面管理失败')}：{str(e)}")
    
    def show_secret_code_dialog(self):
        """显示暗码管理对话框"""
        try:
            from ui.secret_code_dialog import SecretCodeDialog
            
            dialog = SecretCodeDialog(parent=self)
            dialog.exec()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示暗码管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开暗码管理失败')}：{str(e)}")
    
    def show_lock_cell_dialog(self):
        """显示高通lock cell对话框"""
        try:
            from ui.cell_lock_dialog import LockCellDialog
            
            dialog = LockCellDialog(parent=self)
            dialog.exec()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示高通lock cell对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开高通lock cell失败')}：{str(e)}")
    
    def show_qc_nv_dialog(self):
        """显示高通NV对话框"""
        try:
            from ui.qc_nv_dialog import QCNVDialog
            
            dialog = QCNVDialog(parent=self)
            dialog.exec()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示高通NV对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开高通NV失败')}：{str(e)}")
    
    def _on_tab_moved(self, from_index, to_index):
        """Tab拖拽移动处理"""
        try:
            # 使用防抖机制，避免频繁保存
            if hasattr(self, '_tab_move_timer'):
                self._tab_move_timer.stop()
            else:
                from PySide6.QtCore import QTimer
                self._tab_move_timer = QTimer()
                self._tab_move_timer.setSingleShot(True)
                self._tab_move_timer.timeout.connect(self._save_tab_order)
            
            # 延迟500ms保存，避免拖拽过程中频繁保存
            self._tab_move_timer.start(500)
            
        except Exception as e:
            logger.exception(f"{self.tr('Tab拖拽处理失败:')} {e}")
    
    def _save_tab_order(self):
        """保存Tab顺序（防抖处理）"""
        try:
            # 获取新的Tab顺序
            new_order = []
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                tab_id = self._get_tab_id_by_widget(widget)
                if tab_id:
                    new_order.append(tab_id)
                    logger.debug(f"保存Tab顺序: 位置{i} -> Tab ID: {tab_id}, Widget: {type(widget).__name__}")
                else:
                    logger.warning(f"无法获取Tab ID: 位置{i}, Widget: {type(widget).__name__}")
            
            # 保存新的顺序
            self.tab_config_manager.set_tab_order(new_order)
            logger.debug(f"{self.tr('Tab顺序已更新:')} {new_order}")
            
        except Exception as e:
            logger.exception(f"{self.tr('保存Tab顺序失败:')} {e}")
    
    def _get_tab_id_by_widget(self, widget):
        """根据widget获取tab_id"""
        # 直接从widget的tab_id属性获取ID
        if hasattr(widget, 'tab_id'):
            tab_id = widget.tab_id
            logger.debug(f"从tab_id属性获取ID: {tab_id}, Widget: {type(widget).__name__}")
            return tab_id
        
        # 如果widget没有tab_id属性，使用旧的映射方法作为后备
        widget_to_id = {
            self.log_control_tab: 'log_control',
            self.log_filter_tab: 'log_filter',
            self.network_info_tab: 'network_info',
            self.tmo_cc_tab: 'tmo_cc',
            self.tmo_echolocate_tab: 'tmo_echolocate',
            self.background_data_tab: 'background_data',
            self.app_operations_tab: 'app_operations',
            self.other_tab: 'other'
        }
        
        # 检查是否是默认tab
        if widget in widget_to_id:
            tab_id = widget_to_id[widget]
            logger.debug(f"从widget_to_id映射获取ID: {tab_id}, Widget: {type(widget).__name__}")
            return tab_id
        
        # 检查是否是自定义tab
        for custom_tab in self.tab_config_manager.custom_tabs:
            # 这里需要根据实际的自定义tab实例来判断
            # 目前简化处理
            pass
        
        logger.warning(f"无法获取Tab ID: Widget: {type(widget).__name__}")
        return None
    
    def _on_tab_config_updated(self):
        """Tab配置更新处理"""
        try:
            logger.info(self.tr("检测到Tab配置更新，重新加载Tab..."))
            self.reload_tabs()
        except Exception as e:
            logger.exception(f"{self.tr('Tab配置更新处理失败:')} {e}")
    
    def reload_tabs(self):
        """重新加载Tab"""
        try:
            # 关键：重新加载Tab时先恢复主工程 core 包，避免概率性导入失败
            self._ensure_app_core_importable()

            # 保存当前选中的tab
            current_index = self.tab_widget.currentIndex()
            current_widget = self.tab_widget.currentWidget() if current_index >= 0 else None
            current_tab_id = getattr(current_widget, 'tab_id', None) if current_widget else None
            
            # 清除所有tab
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0)
            
            # 重新设置tab
            self.setup_tabs()
            
            # 重新连接Tab信号槽
            self._reconnect_tab_signals()
            
            # 重新加载所有Tab的自定义按钮
            self.load_custom_buttons_for_all_tabs()
            
            # 尝试恢复之前选中的tab
            self._restore_tab_selection(current_tab_id, current_index)
            
            logger.info(self.tr("Tab重新加载完成"))
            
        except Exception as e:
            logger.exception(f"{self.tr('Tab重新加载失败:')} {e}")
    
    def _reconnect_tab_signals(self):
        """重新连接Tab信号槽"""
        try:
            # 连接 Log控制 Tab 信号
            if hasattr(self, 'log_control_tab'):
                self.log_control_tab.mtklog_start.connect(self._on_mtklog_start)
                self.log_control_tab.mtklog_stop_export.connect(self._on_mtklog_stop_export)
                self.log_control_tab.mtklog_delete.connect(self._on_mtklog_delete)
                self.log_control_tab.mtklog_set_log_size.connect(self._on_mtklog_set_log_size)
                self.log_control_tab.mtklog_sd_mode.connect(self._on_mtklog_sd_mode)
                self.log_control_tab.mtklog_usb_mode.connect(self._on_mtklog_usb_mode)
                self.log_control_tab.mtklog_install.connect(self._on_mtklog_install)
                self.log_control_tab.adblog_start.connect(self._on_adblog_start)
                self.log_control_tab.adblog_online_start.connect(self._on_adblog_online_start)
                self.log_control_tab.adblog_export.connect(self._on_adblog_export)
                self.log_control_tab.telephony_enable.connect(self._on_telephony_enable)
                self.log_control_tab.google_log_toggle.connect(self._on_google_log_toggle)
                self.log_control_tab.bugreport_generate.connect(self._on_bugreport_generate)
                self.log_control_tab.bugreport_pull.connect(self._on_bugreport_pull)
                self.log_control_tab.bugreport_delete.connect(self._on_bugreport_delete)
                self.log_control_tab.aee_log_start.connect(self._on_aee_log_start)
                self.log_control_tab.tcpdump_show_dialog.connect(self._on_tcpdump_show_dialog)
            
            # 连接 Log过滤 Tab 信号
            if hasattr(self, 'log_filter_tab'):
                self.log_filter_tab.start_filtering.connect(self._on_start_filtering)
                self.log_filter_tab.stop_filtering.connect(self._on_stop_filtering)
                self.log_filter_tab.manage_log_keywords.connect(self._on_manage_log_keywords)
                self.log_filter_tab.clear_logs.connect(self._on_clear_logs)
                self.log_filter_tab.clear_device_logs.connect(self._on_clear_device_logs)
                self.log_filter_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
                self.log_filter_tab.save_logs.connect(self._on_save_logs)
            
            # 连接 网络信息 Tab 信号
            if hasattr(self, 'network_info_tab'):
                self.network_info_tab.start_network_info.connect(self._on_start_network_info)
                self.network_info_tab.stop_network_info.connect(self._on_stop_network_info)
                self.network_info_tab.start_ping.connect(self._on_start_ping)
                self.network_info_tab.stop_ping.connect(self._on_stop_ping)

            # 连接 办公工具 Tab 信号（reload_tabs 后需要重连）
            if hasattr(self, 'office_tool_tab'):
                try:
                    self.office_tool_tab.show_jira_tool.connect(self._on_show_jira_tool)
                except Exception as e:
                    logger.error(f"重新连接OfficeToolTab信号槽失败: {e}")
            
            # 连接 TMO CC Tab 信号
            if hasattr(self, 'tmo_cc_tab'):
                self.tmo_cc_tab.push_cc_file.connect(self._on_push_cc_file)
                self.tmo_cc_tab.pull_cc_file.connect(self._on_pull_cc_file)
                self.tmo_cc_tab.simple_filter.connect(self._on_simple_filter)
                self.tmo_cc_tab.complete_filter.connect(self._on_complete_filter)
                self.tmo_cc_tab.prod_server.connect(self._on_prod_server)
                self.tmo_cc_tab.stg_server.connect(self._on_stg_server)
                self.tmo_cc_tab.clear_logs.connect(self._on_clear_logs)
                self.tmo_cc_tab.clear_device_logs.connect(self._on_clear_device_logs)
            
            # 连接 TMO Echolocate Tab 信号
            if hasattr(self, 'tmo_echolocate_tab'):
                self.tmo_echolocate_tab.install_echolocate.connect(self._on_install_echolocate)
                self.tmo_echolocate_tab.trigger_echolocate.connect(self._on_trigger_echolocate)
                self.tmo_echolocate_tab.pull_echolocate_file.connect(self._on_pull_echolocate_file)
                self.tmo_echolocate_tab.delete_echolocate_file.connect(self._on_delete_echolocate_file)
                self.tmo_echolocate_tab.get_echolocate_version.connect(self._on_get_echolocate_version)
                self.tmo_echolocate_tab.filter_callid.connect(self._on_filter_callid)
                self.tmo_echolocate_tab.filter_callstate.connect(self._on_filter_callstate)
                self.tmo_echolocate_tab.filter_uicallstate.connect(self._on_filter_uicallstate)
                self.tmo_echolocate_tab.filter_allcallstate.connect(self._on_filter_allcallstate)
                self.tmo_echolocate_tab.filter_ims_signalling.connect(self._on_filter_ims_signalling)
                self.tmo_echolocate_tab.filter_allcallflow.connect(self._on_filter_allcallflow)
                self.tmo_echolocate_tab.filter_voice_intent.connect(self._on_filter_voice_intent)
            
            # 连接 24小时背景数据 Tab 信号
            if hasattr(self, 'background_data_tab'):
                self.background_data_tab.configure_phone.connect(self._on_configure_phone)
                self.background_data_tab.analyze_logs.connect(self._on_analyze_logs)
            
            # 连接 APP操作 Tab 信号
            if hasattr(self, 'app_operations_tab'):
                self.app_operations_tab.query_package.connect(self._on_query_package)
                self.app_operations_tab.query_package_name.connect(self._on_query_package_name)
                self.app_operations_tab.query_install_path.connect(self._on_query_install_path)
                self.app_operations_tab.query_find_file.connect(self._on_query_find_file)
                self.app_operations_tab.pull_apk.connect(self._on_pull_apk)
                self.app_operations_tab.push_apk.connect(self._on_push_apk)
                self.app_operations_tab.install_apk.connect(self._on_install_apk)
                self.app_operations_tab.view_processes.connect(self._on_view_processes)
                self.app_operations_tab.dump_app.connect(self._on_dump_app)
                self.app_operations_tab.enable_app.connect(self._on_enable_app)
                self.app_operations_tab.disable_app.connect(self._on_disable_app)
            
            # 连接 其他 Tab 信号
            if hasattr(self, 'log_control_tab'):
                self.log_control_tab.merge_mtklog.connect(self._on_merge_mtklog)
                self.log_control_tab.extract_pcap_from_mtklog.connect(self._on_extract_pcap_from_mtklog)
                self.log_control_tab.merge_pcap.connect(self._on_merge_pcap)
                self.log_control_tab.extract_pcap_from_qualcomm_log.connect(self._on_extract_pcap_from_qualcomm_log)
                self.log_control_tab.parse_3gpp_message.connect(self._on_parse_3gpp_message)
                self.log_control_tab.mtk_sip_decode.connect(self._on_mtk_sip_decode)
            
            if hasattr(self, 'other_tab'):
                self.other_tab.show_device_info_dialog.connect(self._on_show_device_info_dialog)
                self.other_tab.set_screen_timeout.connect(self._on_set_screen_timeout)
                self.other_tab.configure_hera.connect(self._on_configure_hera)
                self.other_tab.configure_collect_data.connect(self._on_configure_collect_data)
                self.other_tab.show_input_text_dialog.connect(self._on_show_input_text_dialog)
                self.other_tab.show_tools_config_dialog.connect(self._on_show_tools_config_dialog)
                self.other_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
                self.other_tab.show_at_tool_dialog.connect(self._on_show_at_tool_dialog)
                self.other_tab.show_encoding_tool_dialog.connect(self._on_show_encoding_tool_dialog)
                self.other_tab.show_config_backup_dialog.connect(self.show_config_backup_dialog)
                self.other_tab.show_unified_manager.connect(self.show_unified_manager_dialog)
                self.other_tab.show_secret_code_dialog.connect(self.show_secret_code_dialog)
                self.other_tab.show_lock_cell_dialog.connect(self.show_lock_cell_dialog)
                self.other_tab.show_qc_nv_dialog.connect(self.show_qc_nv_dialog)
            
            # 连接 SIM Tab 信号
            if hasattr(self, 'sim_tab'):
                self.sim_tab.status_message.connect(self._on_sim_status_message)
            
            logger.debug(self.tr("Tab信号槽重新连接完成"))
            
        except Exception as e:
            logger.exception(f"{self.tr('重新连接Tab信号槽失败:')} {e}")
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # ESC键退出全屏模式
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止网络信息获取（cleanup 会处理）
            if hasattr(self, 'network_info_manager') and self.network_info_manager:
                try:
                    if hasattr(self.network_info_manager, 'cleanup'):
                        self.network_info_manager.cleanup()
                    elif self.network_info_manager.is_running:
                        self.network_info_manager.stop_network_info()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理网络信息管理器失败:')} {e}")
            
            # 停止MTKLOG
            if hasattr(self, 'mtklog_manager') and self.mtklog_manager.is_running:
                self.mtklog_manager.stop_mtklog()
            
            # 停止ADB Log
            if hasattr(self, 'adblog_manager') and self.adblog_manager.is_running:
                self.adblog_manager.stop_adblog()
            
            # 停止录制（cleanup 会处理）
            if hasattr(self, 'video_manager') and self.video_manager:
                try:
                    if hasattr(self.video_manager, 'cleanup'):
                        self.video_manager.cleanup()
                    elif self.video_manager.is_recording:
                        self.video_manager.stop_recording()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理视频管理器失败:')} {e}")
            
            # 清理所有自定义按钮工作线程中的进程（防止孤儿进程）
            if hasattr(self, '_button_command_workers'):
                for worker in self._button_command_workers[:]:  # 创建副本，避免修改时出错
                    try:
                        if hasattr(worker, '_cleanup_process'):
                            worker._cleanup_process()
                        # 等待线程结束（最多等待2秒）
                        if worker.isRunning():
                            worker.wait(2000)
                            if worker.isRunning():
                                worker.terminate()
                                worker.wait(1000)
                    except Exception as e:
                        logger.exception(f"{self.lang_manager.tr('清理工作线程失败:')} {e}")
            
            # 清理GUI进程（防止孤儿进程）
            if hasattr(self, 'custom_button_manager') and self.custom_button_manager:
                try:
                    if hasattr(self.custom_button_manager, 'cleanup'):
                        self.custom_button_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理自定义按钮管理器失败:')} {e}")
            
            # 清理赫拉配置管理器的工作线程
            if hasattr(self, 'hera_config_manager') and self.hera_config_manager:
                try:
                    self.hera_config_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理赫拉配置管理器失败:')} {e}")
            
            # 清理MTKLOG管理器的工作线程
            if hasattr(self, 'mtklog_manager') and self.mtklog_manager:
                try:
                    if hasattr(self.mtklog_manager, 'cleanup'):
                        self.mtklog_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理MTKLOG管理器失败:')} {e}")
            
            # 清理ADB Log管理器的工作线程
            if hasattr(self, 'adblog_manager') and self.adblog_manager:
                try:
                    if hasattr(self.adblog_manager, 'cleanup'):
                        self.adblog_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理ADB Log管理器失败:')} {e}")
            
            # 清理设备信息管理器的工作线程
            if hasattr(self, 'device_info_manager') and self.device_info_manager:
                try:
                    if hasattr(self.device_info_manager, 'cleanup'):
                        self.device_info_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理设备信息管理器失败:')} {e}")
            
            # 清理其他操作管理器的工作线程
            if hasattr(self, 'other_operations_manager') and self.other_operations_manager:
                try:
                    if hasattr(self.other_operations_manager, 'cleanup'):
                        self.other_operations_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理其他操作管理器失败:')} {e}")
            
            # 清理Google日志管理器的工作线程
            if hasattr(self, 'google_log_manager') and self.google_log_manager:
                try:
                    if hasattr(self.google_log_manager, 'cleanup'):
                        self.google_log_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理Google日志管理器失败:')} {e}")
            
            # 清理截图管理器的工作线程
            if hasattr(self, 'screenshot_manager') and self.screenshot_manager:
                try:
                    if hasattr(self.screenshot_manager, 'cleanup'):
                        self.screenshot_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理截图管理器失败:')} {e}")
            
            # 清理Telephony管理器的工作线程
            if hasattr(self, 'telephony_manager') and self.telephony_manager:
                try:
                    if hasattr(self.telephony_manager, 'cleanup'):
                        self.telephony_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理Telephony管理器失败:')} {e}")
            
            # 清理Echolocate管理器的工作线程
            if hasattr(self, 'echolocate_manager') and self.echolocate_manager:
                try:
                    if hasattr(self.echolocate_manager, 'cleanup'):
                        self.echolocate_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理Echolocate管理器失败:')} {e}")
            
            # 清理日志处理器的工作线程
            if hasattr(self, 'log_processor') and self.log_processor:
                try:
                    if hasattr(self.log_processor, 'cleanup'):
                        self.log_processor.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理日志处理器失败:')} {e}")
            
            # 清理网络信息管理器（确保清理ping和网络信息线程）
            if hasattr(self, 'network_info_manager') and self.network_info_manager:
                try:
                    if hasattr(self.network_info_manager, 'cleanup'):
                        self.network_info_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理网络信息管理器失败:')} {e}")
            
            # 清理视频管理器（确保清理录制进程）
            if hasattr(self, 'video_manager') and self.video_manager:
                try:
                    if hasattr(self.video_manager, 'cleanup'):
                        self.video_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理视频管理器失败:')} {e}")
            
            # 清理AEE日志管理器的工作线程
            if hasattr(self, 'aee_log_manager') and self.aee_log_manager:
                try:
                    if hasattr(self.aee_log_manager, 'cleanup'):
                        self.aee_log_manager.cleanup()
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理AEE日志管理器失败:')} {e}")
            
            # 清理Root&Remount工作线程
            if hasattr(self, '_root_remount_worker') and self._root_remount_worker:
                try:
                    if self._root_remount_worker.isRunning():
                        self._root_remount_worker.wait(3000)
                        if self._root_remount_worker.isRunning():
                            self._root_remount_worker.terminate()
                            self._root_remount_worker.wait(1000)
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理Root&Remount工作线程失败:')} {e}")
                finally:
                    self._root_remount_worker = None
            
            # 清理更新工作线程
            if hasattr(self, '_update_worker') and self._update_worker:
                try:
                    if self._update_worker.isRunning():
                        self._update_worker.request_cancel()
                        self._update_worker.wait(3000)
                        if self._update_worker.isRunning():
                            self._update_worker.terminate()
                            self._update_worker.wait(1000)
                except Exception as e:
                    logger.exception(f"{self.lang_manager.tr('清理更新工作线程失败:')} {e}")
                finally:
                    self._update_worker = None
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            print(f"{self.lang_manager.tr('Close event error:')} {e}")
            event.accept()

    def _schedule_next_auto_check(self, delay_seconds: float) -> None:
        if not hasattr(self, "_auto_update_timer") or self._auto_update_timer is None:
            return
        delay_seconds = max(0.0, float(delay_seconds))
        self._auto_update_timer.start(int(delay_seconds * 1000))

    def _initialize_auto_update_schedule(self) -> None:
        feed_url = (self.tool_config.get("update_feed_url") or "").strip()
        if not feed_url:
            return

        interval = self._update_check_interval_seconds
        last_checked = float(self.tool_config.get("update_last_checked_at") or 0)
        now = time.time()
        elapsed = now - last_checked

        if elapsed >= interval:
            QTimer.singleShot(2000, lambda: self._start_manual_update(source="auto"))
            self._schedule_next_auto_check(interval)
        else:
            self._schedule_next_auto_check(interval - elapsed)

    def _on_auto_update_timer(self) -> None:
        self._start_manual_update(source="auto")

    def _record_update_check_timestamp(self) -> None:
        timestamp = time.time()
        self.tool_config["update_last_checked_at"] = float(timestamp)
        try:
            self.other_operations_manager.tool_config["update_last_checked_at"] = float(timestamp)
            self.other_operations_manager._save_tool_config()
        except Exception as exc:
            logger.warning(f"保存自动更新检查时间失败: {exc}")
        self._schedule_next_auto_check(self._update_check_interval_seconds)

    def _on_update_available(self, manifest_data: dict) -> None:
        logger.debug(f"MainWindow: update available signal, worker={self._update_worker}")
        self._close_update_progress_dialog()
        version = manifest_data.get("version", "?")
        notes = manifest_data.get("release_notes") or ""
        file_size = manifest_data.get("file_size")
        detected_region = manifest_data.get("_detected_region", "")
        alternative_url = manifest_data.get("_alternative_url")

        details = [self.tr("检测到新版本: {version}").format(version=version)]
        if file_size:
            try:
                mb = float(file_size) / (1024 * 1024)
                details.append(self.tr("文件大小: {size:.1f} MB").format(size=mb))
            except Exception:
                pass
        if notes:
            details.append(self.tr("更新说明:"))
            details.append(notes)
        
        # 中国区：显示备用下载地址，提示手动下载
        if detected_region == "cn" and alternative_url:
            details.append("")  # 空行
            details.append(self.tr("⚠️ 中国区域用户，请使用以下地址手动下载："))
            details.append(alternative_url)
            details.append("")
            details.append(self.tr("下载完成后，解压并覆盖原文件即可完成更新。"))
            
            # 在日志区域显示
            log_msg = f"[更新] 检测到新版本 {version}\n"
            log_msg += f"[更新] 备用下载地址（中国区）：{alternative_url}\n"
            self.append_log.emit(log_msg, "#FFA500")
            
            QMessageBox.information(
                self,
                self.tr("在线更新"),
                "\n\n".join(details),
            )
            self._record_update_check_timestamp()
            if self._update_worker:
                self._update_worker.reject_download()
            return
        
        # 非中国区：正常流程
        details.append(self.tr("是否立即下载？"))
        
        # 如果有备用地址，在日志区域显示
        if alternative_url:
            log_msg = f"[更新] 检测到新版本 {version}\n"
            log_msg += f"[更新] 备用下载地址（如主地址失败可使用）：{alternative_url}\n"
            self.append_log.emit(log_msg, None)

        reply = QMessageBox.question(
            self,
            self.tr("在线更新"),
            "\n\n".join(details),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        self._record_update_check_timestamp()

        if reply == QMessageBox.StandardButton.Yes:
            logger.debug("MainWindow: user chose YES")
            self._update_status_text = self.tr("正在下载安装包...")
            self._update_progress_extra = ""
            self._show_update_progress_dialog(self._update_status_text)
            if self._update_worker:
                self._update_worker.allow_download()
            self.append_log.emit(f"[更新] {self.tr('确认下载版本')}: {version}\n", None)
        else:
            logger.debug("MainWindow: user chose NO")
            self.append_log.emit(f"[更新] {self.tr('用户已取消更新')}\n", "#FFA500")
            if self._update_worker:
                self._update_worker.reject_download()
            else:
                logger.debug("MainWindow: no worker instance when rejecting download")

    def _on_alternative_url_info(self, region: str, url: str, message: str) -> None:
        """处理备用下载地址信息"""
        log_msg = f"[更新] {message}\n"
        log_msg += f"[更新] 下载地址：{url}\n"
        self.append_log.emit(log_msg, "#FFA500")


