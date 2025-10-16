#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24小时背景数据配置管理器 - PyQt5版本
负责配置手机和导出log相关功能
"""

import subprocess
import os
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import (QMessageBox, QInputDialog, QDialog, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QHBoxLayout)


class ExportLogsWorker(QThread):
    """导出日志工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, str)  # message, color
    export_completed = pyqtSignal(bool, int, int, str)  # success, success_count, total_count, log_dir
    
    def __init__(self, device, log_dir, pull_commands):
        super().__init__()
        self.device = device
        self.log_dir = log_dir
        self.pull_commands = pull_commands
        self.stop_flag = False
        
    def run(self):
        """执行导出操作"""
        try:
            success_count = 0
            total_commands = len(self.pull_commands)
            
            self.progress_updated.emit("[导出日志] 开始导出日志...", "blue")
            
            for i, (source_path, folder_name) in enumerate(self.pull_commands):
                if self.stop_flag:
                    self.progress_updated.emit("[导出日志] 用户取消操作", "orange")
                    self.export_completed.emit(False, success_count, total_commands, self.log_dir)
                    return
                
                # 更新进度
                progress_text = f"[导出日志] 正在导出: {folder_name} ({i+1}/{total_commands})"
                self.progress_updated.emit(progress_text, "blue")
                
                if self._execute_adb_pull(source_path, folder_name):
                    success_count += 1
                    self.progress_updated.emit(f"[导出日志] ✓ 成功导出: {folder_name}", "green")
                else:
                    self.progress_updated.emit(f"[导出日志] ✗ 导出失败或目录不存在: {folder_name}", "orange")
            
            # 发送完成信号
            self.export_completed.emit(True, success_count, total_commands, self.log_dir)
            
        except Exception as e:
            self.progress_updated.emit(f"[导出日志] 错误: {str(e)}", "red")
            self.export_completed.emit(False, 0, len(self.pull_commands), self.log_dir)
    
    def _execute_adb_pull(self, source_path, folder_name):
        """执行adb pull命令"""
        try:
            # 创建目标文件夹路径
            target_path = os.path.join(self.log_dir, folder_name)
            
            # 执行adb pull命令
            cmd = f"adb -s {self.device} pull \"{source_path}\" \"{target_path}\""
            print(f"[DEBUG] 执行命令: {cmd}")
            
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                print(f"[DEBUG] adb pull 成功: {source_path} -> {target_path}")
                return True
            else:
                # 检查是否是目录不存在的错误
                error_msg = result.stderr.strip()
                if "does not exist" in error_msg or "No such file or directory" in error_msg:
                    print(f"[DEBUG] 源目录不存在: {source_path}")
                else:
                    print(f"[DEBUG] adb pull 失败: {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] adb pull 超时: {source_path}")
            return False
        except Exception as e:
            print(f"[DEBUG] adb pull 执行异常: {str(e)}")
            return False
    
    def stop(self):
        """停止操作"""
        self.stop_flag = True


class BackgroundConfigManager(QObject):
    """24小时背景数据配置管理器"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # text, color
    
    def __init__(self, device_manager, parent=None):
        """
        初始化背景数据配置管理器
        
        Args:
            device_manager: 设备管理器实例
            parent: 父对象
        """
        super().__init__(parent)
        self.device_manager = device_manager
        self.parent_widget = parent
        self.export_worker = None  # 导出工作线程
        
    def configure_phone(self):
        """配置手机进行24小时背景数据收集"""
        try:
            # 获取选中的设备
            device = self.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 执行配置步骤
            success_count = 0
            total_steps = 3
            
            # 步骤1: adb root
            self.status_message.emit("[配置手机] 正在执行 adb root...")
            if self._execute_adb_root(device):
                success_count += 1
                self.log_message.emit("[配置手机] adb root 执行成功", "green")
            else:
                QMessageBox.critical(
                    self.parent_widget,
                    "配置失败", 
                    "adb root 执行失败！\n请检查设备是否已连接并支持root权限。"
                )
                return False
            
            # 步骤2: 检查初始SELinux状态
            initial_status = self._get_selinux_status(device)
            self.log_message.emit(f"[配置手机] 初始SELinux状态: {initial_status}", "blue")
            
            # 步骤3: adb shell setenforce 0
            self.status_message.emit("[配置手机] 正在执行 setenforce 0...")
            if self._execute_setenforce(device):
                success_count += 1
                self.log_message.emit("[配置手机] setenforce 0 执行成功", "green")
            else:
                QMessageBox.critical(
                    self.parent_widget,
                    "配置失败", 
                    "setenforce 0 执行失败！\n无法设置SELinux为Permissive模式。"
                )
                return False
            
            # 步骤4: 验证SELinux状态
            final_status = self._get_selinux_status(device)
            self.log_message.emit(f"[配置手机] 最终SELinux状态: {final_status}", "blue")
            
            if final_status == "Permissive":
                success_count += 1
                QMessageBox.information(
                    self.parent_widget,
                    "配置成功", 
                    f"手机配置完成！\n\n"
                    f"执行结果:\n"
                    f"• adb root: ✓ 成功\n"
                    f"• setenforce 0: ✓ 成功\n"
                    f"• SELinux状态: {initial_status} → {final_status} ✓\n\n"
                    f"设备已准备就绪，可以进行24小时背景数据收集。"
                )
                self.status_message.emit("[配置手机] 手机配置完成")
                return True
            else:
                QMessageBox.critical(
                    self.parent_widget,
                    "配置失败", 
                    f"SELinux状态设置失败！\n\n"
                    f"当前状态: {final_status}\n"
                    f"期望状态: Permissive\n\n"
                    f"请检查设备是否支持SELinux设置。"
                )
                return False
                
        except Exception as e:
            QMessageBox.critical(
                self.parent_widget,
                "配置错误", 
                f"配置过程中发生错误:\n{str(e)}"
            )
            self.log_message.emit(f"[配置手机] 配置错误: {str(e)}", "red")
            return False
    
    def export_background_logs(self):
        """导出24小时背景数据日志（多线程版本）"""
        try:
            # 检查是否有正在运行的导出任务
            if self.export_worker and self.export_worker.isRunning():
                QMessageBox.warning(
                    self.parent_widget,
                    "正在导出", 
                    "已有导出任务正在进行中，请稍候..."
                )
                return False
            
            # 获取选中的设备
            device = self.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 获取当前日期并创建目录
            current_date = datetime.now().strftime("%Y%m%d")
            log_base_dir = f"C:\\log\\{current_date}"
            
            # 创建日志目录
            if not os.path.exists(log_base_dir):
                os.makedirs(log_base_dir)
                self.log_message.emit(f"[导出日志] 创建日志目录: {log_base_dir}", "blue")
            
            # 获取用户输入的日志名称
            log_name = self._get_log_name()
            if not log_name:
                return False
            
            # 创建完整的日志目录路径
            log_dir = os.path.join(log_base_dir, log_name)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                self.log_message.emit(f"[导出日志] 创建日志子目录: {log_dir}", "blue")
            
            # 定义要导出的目录列表
            pull_commands = [
                ("/sdcard/TCTReport", "TCTReport"),
                ("/sdcard/mtklog", "mtklog"),
                ("/sdcard/debuglogger", "debuglogger"),
                ("/data/debuglogger", "debuglogger"),
                ("/storage/emulated/0/debuglogger", "storage_debuglogger"),
                ("/data/user_de/0/com.android.shell/files/bugreports", "bugreports")
            ]
            
            # 创建并启动工作线程
            self.export_worker = ExportLogsWorker(device, log_dir, pull_commands)
            
            # 连接信号
            self.export_worker.progress_updated.connect(self._on_export_progress)
            self.export_worker.export_completed.connect(self._on_export_completed)
            
            # 启动线程
            self.export_worker.start()
            
            self.log_message.emit("[导出日志] 开始后台导出，主界面保持响应...", "blue")
            
            return True
                
        except Exception as e:
            QMessageBox.critical(
                self.parent_widget,
                "导出错误", 
                f"导出过程中发生错误:\n{str(e)}"
            )
            self.log_message.emit(f"[导出日志] 导出错误: {str(e)}", "red")
            return False
    
    def _on_export_progress(self, message, color):
        """导出进度更新"""
        self.log_message.emit(message, color)
    
    def _on_export_completed(self, success, success_count, total_count, log_dir):
        """导出完成"""
        if success:
            if success_count > 0:
                # 自动打开文件夹
                self._open_folder(log_dir)
                
                self.log_message.emit(
                    f"[导出日志] ✓ 导出完成！成功: {success_count}/{total_count} 个目录", 
                    "green"
                )
                
 
            else:
                self.log_message.emit("[导出日志] ✗ 所有日志导出都失败", "red")
                
                QMessageBox.critical(
                    self.parent_widget,
                    "导出失败", 
                    f"所有日志导出都失败了！\n\n"
                    f"可能的原因:\n"
                    f"• 设备未连接\n"
                    f"• 源目录不存在\n"
                    f"• 权限不足\n\n"
                    f"请检查设备连接状态和权限设置。"
                )
        else:
            self.log_message.emit("[导出日志] ✗ 导出过程中断或失败", "red")
        
        # 清理工作线程
        self.export_worker = None
    
    def _execute_adb_root(self, device):
        """执行adb root命令"""
        try:
            cmd = f"adb -s {device} root"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                print(f"[DEBUG] adb root 成功: {result.stdout.strip()}")
                return True
            else:
                print(f"[DEBUG] adb root 失败: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"[DEBUG] adb root 执行异常: {str(e)}")
            return False
    
    def _execute_setenforce(self, device):
        """执行setenforce 0命令"""
        try:
            cmd = f"adb -s {device} shell setenforce 0"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                print(f"[DEBUG] setenforce 0 成功: {result.stdout.strip()}")
                return True
            else:
                print(f"[DEBUG] setenforce 0 失败: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"[DEBUG] setenforce 0 执行异常: {str(e)}")
            return False
    
    def _get_selinux_status(self, device):
        """获取SELinux状态"""
        try:
            cmd = f"adb -s {device} shell getenforce"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                status = result.stdout.strip()
                print(f"[DEBUG] SELinux状态: {status}")
                return status
            else:
                print(f"[DEBUG] 获取SELinux状态失败: {result.stderr.strip()}")
                return "Unknown"
        except Exception as e:
            print(f"[DEBUG] 获取SELinux状态异常: {str(e)}")
            return "Unknown"
    
    def _get_log_name(self):
        """获取用户输入的日志名称"""
        try:
            # 创建自定义输入对话框
            dialog = LogNameInputDialog(self.parent_widget)
            if dialog.exec_() == QDialog.Accepted:
                log_name = dialog.get_log_name()
                if log_name:
                    self.log_message.emit(f"[导出日志] 日志名称: {log_name}", "blue")
                    return log_name
            return None
            
        except Exception as e:
            print(f"[DEBUG] 获取日志名称异常: {str(e)}")
            return None
    
    def _open_folder(self, folder_path):
        """打开文件夹"""
        try:
            import platform
            
            system = platform.system()
            if system == "Windows":
                # Windows系统使用explorer
                result = subprocess.run(
                    ["explorer", folder_path], 
                    capture_output=True, 
                    text=True
                )
                print(f"[INFO] 尝试打开文件夹: {folder_path}")
                print(f"[DEBUG] explorer命令执行完成，返回码: {result.returncode}")
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path], check=True)
                print(f"[INFO] 成功打开文件夹: {folder_path}")
            elif system == "Linux":
                subprocess.run(["xdg-open", folder_path], check=True)
                print(f"[INFO] 成功打开文件夹: {folder_path}")
            else:
                print(f"[WARNING] 不支持的操作系统: {system}")
                QMessageBox.information(
                    self.parent_widget,
                    "文件夹位置", 
                    f"不支持的操作系统，请手动打开:\n{folder_path}"
                )
                return
                
        except Exception as e:
            print(f"[DEBUG] 打开文件夹失败: {str(e)}")
            # 如果自动打开失败，至少告诉用户文件夹位置
            QMessageBox.information(
                self.parent_widget,
                "文件夹位置", 
                f"无法自动打开文件夹，请手动打开:\n{folder_path}"
            )
            return
        
        # 如果没有异常，说明命令执行了
        if system == "Windows":
            print(f"[INFO] 文件夹应该已经打开: {folder_path}")
        else:
            print(f"[INFO] 成功打开文件夹: {folder_path}")


class LogNameInputDialog(QDialog):
    """日志名称输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("输入日志名称")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("请输入日志名称:")
        title_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 输入框
        self.log_name_input = QLineEdit()
        self.log_name_input.setPlaceholderText("例如: test_001")
        layout.addWidget(self.log_name_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        confirm_btn = QPushButton("确认")
        confirm_btn.setMinimumWidth(80)
        confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addWidget(confirm_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 绑定回车键
        self.log_name_input.returnPressed.connect(self.on_confirm)
        
        # 焦点到输入框
        self.log_name_input.setFocus()
    
    def on_confirm(self):
        """确认按钮点击"""
        log_name = self.log_name_input.text().strip()
        if log_name:
            self.accept()
        else:
            QMessageBox.warning(self, "输入错误", "请输入有效的日志名称！")
    
    def get_log_name(self):
        """获取日志名称"""
        return self.log_name_input.text().strip()


# 导出
__all__ = ['BackgroundConfigManager']

