#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 TCPDUMP管理器
适配原Tkinter版本的TCPDUMP管理功能
"""

import subprocess
import os
import time
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QScrollBar, QWidget


class TCPDumpDialog(QDialog):
    """TCPDUMP抓包对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(self.lang_manager.tr("Android TCPDUMP 抓包工具") if self.lang_manager else "Android TCPDUMP 抓包工具")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        # 状态变量
        self.is_running = False
        self.device_type = "android"
        
        self.init_ui()
    
    def get_storage_path(self):
        """获取存储路径，优先使用用户配置的路径"""
        # 从父窗口获取工具配置
        if hasattr(self.parent(), 'tool_config') and self.parent().tool_config:
            storage_path = self.parent().tool_config.get("storage_path", "")
            if storage_path:
                return storage_path
        
        # 使用默认路径
        current_date = datetime.now().strftime("%Y%m%d")
        return f"c:\\log\\{current_date}"
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel(self.lang_manager.tr("Android TCPDUMP 抓包工具"))
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 状态显示区域
        status_label = QLabel(self.lang_manager.tr("状态信息:"))
        layout.addWidget(status_label)
        
        # 创建状态文本显示区域
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QTextEdit().font())  # 使用等宽字体
        self.status_text.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt;")
        
        # 配置文本颜色标签
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #a9b7c6;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        
        status_layout.addWidget(self.status_text)
        layout.addWidget(status_widget)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_stop_btn = QPushButton(self.lang_manager.tr("开始"))
        self.start_stop_btn.clicked.connect(self.toggle_capture)
        button_layout.addWidget(self.start_stop_btn)
        
        clear_btn = QPushButton(self.lang_manager.tr("清空日志"))
        clear_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_btn)
        
        close_btn = QPushButton(self.lang_manager.tr("关闭"))
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def log_message(self, message, level="info"):
        """添加日志消息到状态显示区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据消息类型添加颜色标记
        if "✅" in message or self.lang_manager.tr("成功") in message:
            color = "#28a745"  # 绿色
        elif "❌" in message or self.lang_manager.tr("失败") in message or self.lang_manager.tr("错误") in message:
            color = "#dc3545"  # 红色
        elif "⚠️" in message or self.lang_manager.tr("警告") in message:
            color = "#ffc107"  # 黄色
        else:
            color = "#17a2b8"  # 蓝色
        
        # 插入消息
        self.status_text.append(f'<span style="color: {color}">[{timestamp}] {message}</span>')
        
        # 滚动到底部
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清空日志显示"""
        self.status_text.clear()
    
    def run_adb_command(self, command, timeout=10):
        """运行ADB命令并返回结果"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", self.lang_manager.tr("命令执行超时")
        except Exception as e:
            return False, "", str(e)
    
    def check_root_permission(self):
        """检查Root权限"""
        self.log_message(self.lang_manager.tr("正在检查Root权限..."))
        success, stdout, stderr = self.run_adb_command("adb root")
        
        if not success:
            self.log_message(f"{self.lang_manager.tr('ADB命令执行失败:')} {stderr}")
            return False
        
        # adb root的错误信息通常在stdout中，需要同时检查stdout和stderr
        error_message = "adbd cannot run as root in production builds"
        if error_message in stdout or error_message in stderr:
            return False
        else:
            # 只要不是production builds错误，都认为有root权限
            self.log_message(self.lang_manager.tr("✅ Root权限检查通过"))
            return True
    
    def check_tcpdump_support(self):
        """检查TCPDUMP支持"""
        self.log_message(self.lang_manager.tr("正在检查TCPDUMP支持..."))
        success, stdout, stderr = self.run_adb_command("adb shell tcpdump --version")
        
        if not success or "inaccessible or not found" in stderr:
            self.log_message(self.lang_manager.tr("❌ 设备不支持TCPDUMP命令"))
            return False
        else:
            self.log_message(self.lang_manager.tr("✅ TCPDUMP支持检查通过"))
            return True
    
    def check_initial_status(self):
        """初始化状态检查"""
        self.log_message(self.lang_manager.tr("开始初始化检查..."))
        
        # 检查ADB连接
        success, stdout, stderr = self.run_adb_command("adb devices")
        if not success:
            self.log_message(self.lang_manager.tr("❌ ADB连接失败，请确保设备已连接并开启USB调试"))
            return
        
        if "device" not in stdout:
            self.log_message(self.lang_manager.tr("❌ 未检测到连接的设备"))
            return
        
        self.log_message(self.lang_manager.tr("✅ 设备连接正常"))
        
        # 检查Root权限
        if not self.check_root_permission():
            self.log_message(self.lang_manager.tr("❌ 设备不支持Root权限"))
            return
        
        # 检查TCPDUMP支持
        if not self.check_tcpdump_support():
            self.log_message(self.lang_manager.tr("❌ 设备不支持TCPDUMP"))
            return
        
        self.log_message(self.lang_manager.tr("✅ 所有检查通过，可以开始抓包"))
    
    def get_log_path(self):
        """根据设备类型获取日志路径"""
        if self.device_type == "kaios":
            return "/data/media/music/netlog.pcap"
        else:
            return "/data/tmp/netlog.pcap"
    
    def get_log_directory(self):
        """根据设备类型获取日志目录"""
        if self.device_type == "kaios":
            return "/data/media/music"
        else:
            return "/data/tmp"
    
    def check_path_and_start(self):
        """检查路径并启动抓包"""
        log_dir = self.get_log_directory()
        log_path = self.get_log_path()
        
        self.log_message(f"{self.lang_manager.tr('检查设备路径:')} {log_dir}")
        
        # 检查路径是否存在
        success, stdout, stderr = self.run_adb_command(f"adb shell ls -d '{log_dir}'")
        
        if not success or "No such file or directory" in stderr:
            self.log_message(f"❌ {self.lang_manager.tr('路径不存在:')} {log_dir}")
            self.log_message(self.lang_manager.tr("正在尝试创建目录..."))
            
            # 尝试创建目录
            success2, stdout2, stderr2 = self.run_adb_command(f"adb shell mkdir -p '{log_dir}'")
            
            if success2:
                self.log_message(f"✅ {self.lang_manager.tr('目录创建成功:')} {log_dir}")
            else:
                self.log_message(f"❌ {self.lang_manager.tr('目录创建失败:')} {stderr2}")
                self.log_message(self.lang_manager.tr("程序停止：无法创建必要的目录"))
                return
        else:
            self.log_message(f"✅ {self.lang_manager.tr('路径存在:')} {log_dir}")
        
        # 在新线程中启动抓包，避免UI阻塞
        threading.Thread(target=self.start_capture, daemon=True).start()
    
    def start_capture(self):
        """开始抓包"""
        log_path = self.get_log_path()
        self.log_message(f"{self.lang_manager.tr('开始抓包，日志保存到:')} {log_path}")
        
        # 构建tcpdump命令
        tcpdump_cmd = f'adb shell "nohup tcpdump -i any -s 0 -w {log_path} >/dev/null 2>&1 &"'
        
        success, stdout, stderr = self.run_adb_command(tcpdump_cmd)
        
        if success:
            self.is_running = True
            self.start_stop_btn.setText(self.lang_manager.tr("停止"))
            self.log_message(self.lang_manager.tr("TCPDUMP进程启动成功"))
            
            # 等待进程启动
            self.log_message(self.lang_manager.tr("等待TCPDUMP进程启动..."))
            time.sleep(1)
            
            # 验证进程是否真的在运行（重试检查）
            self.verify_tcpdump_process()
        else:
            self.log_message(f"❌ {self.lang_manager.tr('TCPDUMP启动失败:')} {stderr}")
    
    def stop_capture(self):
        """停止抓包并拉取日志"""
        self.log_message(self.lang_manager.tr("正在停止抓包..."))
        
        # 停止tcpdump进程
        success, stdout, stderr = self.run_adb_command("adb shell pkill tcpdump")
        if success:
            self.log_message(self.lang_manager.tr("TCPDUMP进程已停止"))
        else:
            self.log_message(f"⚠️ {self.lang_manager.tr('停止进程时出现警告:')} {stderr}")
        
        # 等待进程完全停止
        time.sleep(2)
        
        # 拉取日志文件
        self.pull_log_file()
        
        # 更新UI状态
        self.is_running = False
        self.start_stop_btn.setText(self.lang_manager.tr("开始"))
    
    def pull_log_file(self):
        """拉取日志文件到本地"""
        log_path = self.get_log_path()
        self.log_message(f"{self.lang_manager.tr('正在拉取日志文件:')} {log_path}")
        
        # 创建本地日志目录 - 使用统一的路径格式
        date_str = datetime.now().strftime("%Y%m%d")
        base_log_dir = self.get_storage_path()
        local_log_dir = os.path.join(base_log_dir, "tcpdump")
        
        try:
            os.makedirs(local_log_dir, exist_ok=True)
            self.log_message(f"✅ {self.lang_manager.tr('创建日志目录:')} {local_log_dir}")
        except Exception as e:
            self.log_message(f"⚠️ {self.lang_manager.tr('无法创建日志目录，将保存到当前目录:')} {e}")
            local_log_dir = "."
        
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_type = self.device_type
        local_file = os.path.join(local_log_dir, f"netlog_{device_type}_{timestamp}.pcap")
        
        # 拉取文件
        pull_cmd = f'adb pull "{log_path}" "{local_file}"'
        success, stdout, stderr = self.run_adb_command(pull_cmd, timeout=30)
        
        if success and os.path.exists(local_file):
            file_size = os.path.getsize(local_file)
            self.log_message(f"✅ {self.lang_manager.tr('日志文件拉取成功')}")
            self.log_message(f"📁 {self.lang_manager.tr('文件路径:')} {os.path.abspath(local_file)}")
            self.log_message(f"📊 {self.lang_manager.tr('文件大小:')} {file_size} {self.lang_manager.tr('字节')}")
            
            # 打开文件夹
            try:
                os.startfile(os.path.dirname(os.path.abspath(local_file)))
                self.log_message(self.lang_manager.tr("已打开日志文件夹"))
            except Exception as e:
                self.log_message(f"⚠️ {self.lang_manager.tr('无法自动打开文件夹:')} {e}")
        else:
            self.log_message(f"❌ {self.lang_manager.tr('日志文件拉取失败:')} {stderr}")
            self.log_message(self.lang_manager.tr("请检查设备存储空间和文件权限"))
    
    def check_system_requirements(self):
        """检查系统要求"""
        self.log_message(self.lang_manager.tr("检查系统要求..."))
        
        # 检查ADB连接
        success, stdout, stderr = self.run_adb_command("adb devices")
        if not success:
            self.log_message(self.lang_manager.tr("ADB连接失败，请确保设备已连接并开启USB调试"))
            return False
        
        if "device" not in stdout:
            self.log_message(self.lang_manager.tr("未检测到连接的设备"))
            return False
        
        # 检查Root权限
        if not self.check_root_permission():
            self.log_message(self.lang_manager.tr("设备不支持Root权限，程序终止"))
            return False
        
        # 检查TCPDUMP支持
        if not self.check_tcpdump_support():
            self.log_message(self.lang_manager.tr("设备不支持TCPDUMP，程序终止"))
            return False
        
        return True
    
    def verify_tcpdump_process(self):
        """验证TCPDUMP进程是否正在运行"""
        max_retries = 2
        for attempt in range(max_retries):
            # 使用 ps -A 命令检查所有进程，使用grep在shell内部过滤
            command = 'adb shell "ps -A | grep tcpdump"'
            success, stdout, stderr = self.run_adb_command(command)
            
            if success and stdout.strip() and "tcpdump" in stdout:
                # 提取进程信息
                lines = stdout.strip().split('\n')
                for line in lines:
                    if "tcpdump" in line and "grep" not in line:
                        self.log_message(self.lang_manager.tr("确认TCPDUMP进程正在运行"))
                        return True
            
            # 如果未找到，等待后重试
            if attempt < max_retries - 1:
                self.log_message(self.lang_manager.tr("等待进程启动..."))
                time.sleep(1)
            else:
                # 检查日志文件是否存在
                log_path = self.get_log_path()
                success2, stdout2, stderr2 = self.run_adb_command(f"adb shell ls -la '{log_path}'")
                if success2 and log_path.split('/')[-1] in stdout2:
                    self.log_message(self.lang_manager.tr("日志文件存在，TCPDUMP可能正在后台运行"))
                    return True
                else:
                    self.log_message(self.lang_manager.tr("TCPDUMP进程不存在，程序终止"))
                    self.log_message(self.lang_manager.tr("请检查设备权限和TCPDUMP安装状态"))
                    # 恢复按钮状态
                    self.is_running = False
                    self.start_stop_btn.setText(self.lang_manager.tr("开始"))
                    return False
        return False
    
    def show_device_selection_dialog(self):
        """显示设备类型选择对话框"""
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        
        device_dialog = QDialog(self)
        device_dialog.setWindowTitle(self.lang_manager.tr("选择设备类型"))
        device_dialog.setFixedSize(300, 200)
        device_dialog.setModal(True)
        
        layout = QVBoxLayout(device_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel(self.lang_manager.tr("请选择设备类型"))
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 设备类型选择
        device_type_group = QButtonGroup(device_dialog)
        android_rb = QRadioButton("Android")
        android_rb.setChecked(True)
        device_type_group.addButton(android_rb, 0)
        layout.addWidget(android_rb)
        
        kaios_rb = QRadioButton("KaiOS")
        device_type_group.addButton(kaios_rb, 1)
        layout.addWidget(kaios_rb)
        
        # 按钮框架
        button_layout = QHBoxLayout()
        
        def on_ok():
            if android_rb.isChecked():
                self.device_type = "android"
            else:
                self.device_type = "kaios"
            device_dialog.accept()
            # 检查路径并启动抓包
            self.check_path_and_start()
        
        def on_cancel():
            device_dialog.reject()
        
        ok_btn = QPushButton(self.lang_manager.tr("确定"))
        ok_btn.clicked.connect(on_ok)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton(self.lang_manager.tr("取消"))
        cancel_btn.clicked.connect(on_cancel)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        if device_dialog.exec() == QDialog.DialogCode.Accepted:
            pass
    
    def toggle_capture(self):
        """切换抓包状态"""
        if self.is_running:
            self.stop_capture()
        else:
            # 先检查系统要求
            if not self.check_system_requirements():
                self.log_message(self.lang_manager.tr("❌ 系统检查失败，无法开始抓包"))
                return
            
            # 显示设备选择对话框
            self.show_device_selection_dialog()
    
    def closeEvent(self, event):
        """关闭对话框事件"""
        if self.is_running:
            reply = QMessageBox.question(
                self,
                self.lang_manager.tr("确认关闭"),
                self.lang_manager.tr("TCPDUMP正在运行中，关闭对话框将停止抓包。是否继续？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_capture()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class PySide6TCPDumpManager(QObject):
    """PySide6 TCPDUMP管理器"""
    
    status_message = Signal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.dialog = None
        
    def show_tcpdump_dialog(self):
        """显示TCPDUMP抓包对话框"""
        try:
            # 检查设备连接
            device = self.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 创建并显示对话框
            self.dialog = TCPDumpDialog(parent=self.parent())
            self.dialog.check_initial_status()
            self.dialog.exec()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"打开TCPDUMP工具失败: {str(e)}")
            return False

