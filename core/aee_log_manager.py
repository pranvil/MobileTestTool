#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 AEE日志管理器
适配原Tkinter版本的AEE日志管理功能
"""

import subprocess
import os
import datetime
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QFileDialog


class AEELogWorker(QThread):
    """AEE日志等待和拉取工作线程"""
    
    finished = pyqtSignal(bool, str)
    
    def __init__(self, device, lang_manager=None, storage_path_func=None):
        super().__init__()
        self.device = device
        self.lang_manager = lang_manager
        self.storage_path_func = storage_path_func  # 存储路径获取函数
        
    def run(self):
        """等待5分钟并拉取日志文件"""
        try:
            # 等待5分钟
            print(f"{self.lang_manager.tr('开始等待5分钟，设备:')} {self.device}")
            
            # 每分钟检查一次设备连接状态
            for minute in range(5):
                if not self._check_device_connection(self.device):
                    print(f"{self.lang_manager.tr('设备')} {self.device} {self.lang_manager.tr('连接断开，提前结束等待')}")
                    break
                
                remaining_minutes = 5 - minute - 1
                if remaining_minutes > 0:
                    print(f"{self.lang_manager.tr('等待中... 剩余')} {remaining_minutes} {self.lang_manager.tr('分钟')}")
                    time.sleep(60)  # 等待1分钟
                else:
                    print(self.lang_manager.tr("等待完成"))
            
            # 拉取日志文件
            self._pull_aee_logs_direct(self.device)
            
        except Exception as e:
            print(f"{self.lang_manager.tr('等待和拉取日志时发生错误:')} {e}")
            self.finished.emit(False, f"{self.lang_manager.tr('等待和拉取日志时发生错误:')} {e}")
    
    def _check_device_connection(self, device):
        """检查设备连接状态"""
        try:
            cmd = ["adb", "devices"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                return device in result.stdout and '\tdevice' in result.stdout
            else:
                return False
                
        except Exception:
            return False
    
    def _pull_aee_logs_direct(self, device):
        """直接拉取AEE日志文件"""
        try:
            # 1. 创建日志目录
            if self.storage_path_func:
                log_dir = self.storage_path_func()
            else:
                current_date = datetime.datetime.now().strftime("%Y%m%d")
                log_dir = f"c:\\log\\{current_date}"
            aee_log_dir = os.path.join(log_dir, "aeelog")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            if not os.path.exists(aee_log_dir):
                os.makedirs(aee_log_dir)
            
            # 2. 检查远程日志目录是否存在
            check_cmd = ["adb", "-s", device, "shell", "ls", "/storage/emulated/0/.usersupport/log/zip"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = f"{self.lang_manager.tr('远程日志目录不存在或无法访问:')} {result.stderr.strip()}"
                print(error_msg)
                self.finished.emit(False, error_msg)
                return
            
            # 3. 拉取日志文件
            pull_cmd = ["adb", "-s", device, "pull", "/storage/emulated/0/.usersupport/log/zip", aee_log_dir]
            result = subprocess.run(pull_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = f"{self.lang_manager.tr('拉取AEE日志失败:')} {result.stderr.strip()}"
                print(error_msg)
                self.finished.emit(False, error_msg)
                return
            
            # 4. 完成
            self.finished.emit(True, aee_log_dir)
            
        except Exception as e:
            error_msg = f"{self.lang_manager.tr('拉取AEE日志时发生错误:')} {e}"
            print(error_msg)
            self.finished.emit(False, error_msg)


class PyQtAEELogManager(QObject):
    """PyQt5 AEE日志管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.is_running = False
        self.waiting_thread = None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def get_storage_path(self):
        """获取存储路径，优先使用用户配置的路径"""
        # 从父窗口获取工具配置
        if hasattr(self.parent(), 'tool_config') and self.parent().tool_config:
            storage_path = self.parent().tool_config.get("storage_path", "")
            if storage_path:
                return storage_path
        
        # 使用默认路径
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        return f"c:\\log\\{current_date}"
        
    def start_aee_log(self):
        """开始AEE日志收集"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 1. 检查com.tcl.logger是否已安装
            self.status_message.emit(self.lang_manager.tr("检查com.tcl.logger是否已安装..."))
            
            if not self._check_tcl_logger_installed(device):
                # 如果未安装，开始安装流程
                self._handle_installation(device)
                return
            
            # 2. 执行AEE日志打包命令
            self.status_message.emit(self.lang_manager.tr("执行AEE日志打包命令..."))
            
            pack_cmd = ["adb", "-s", device, "shell", "am", "startservice", 
                       "-n", "com.tcl.logger/com.tcl.logger.service.ClearLogService", 
                       "-a", "com.tcl.logger.packlog"]
            
            result = subprocess.run(pack_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('执行AEE日志打包命令失败:')} {result.stderr.strip()}")
            
            # 3. 显示提示并开始等待
            self.status_message.emit(self.lang_manager.tr("AEE日志打包命令已执行"))
            
            QMessageBox.information(None, self.lang_manager.tr("提示"), "log打包中，保持手机连接5分钟")
            
            # 更新状态
            self.is_running = True
            self.status_message.emit(self.tr("AEE log打包中 - ") + device)
            
            # 在后台线程中等待并拉取日志
            self.waiting_thread = AEELogWorker(device, self.lang_manager, self.get_storage_path)
            self.waiting_thread.finished.connect(self._on_waiting_finished)
            self.waiting_thread.start()
            
        except Exception as e:
            error_msg = f"{self.lang_manager.tr('启动AEE log时发生错误:')} {e}"
            print(error_msg)
            QMessageBox.critical(None, self.lang_manager.tr("错误"), error_msg)
            self.status_message.emit(self.lang_manager.tr("启动AEE log失败"))
    
    def _handle_installation(self, device):
        """处理com.tcl.logger安装流程"""
        try:
            # 循环询问用户是否安装，直到安装成功或用户取消
            while True:
                reply = QMessageBox.question(
                    None,
                    self.lang_manager.tr("安装提示"),
                    self.lang_manager.tr("com.tcl.logger未安装，是否选择APK文件进行安装？\n\n") +
                    self.lang_manager.tr("点击 '是' 选择APK文件进行安装\n点击 '否' 取消操作"),
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 选择APK文件
                    apk_file, _ = QFileDialog.getOpenFileName(
                        None,
                        self.lang_manager.tr("选择com.tcl.logger APK文件"),
                        "",
                        self.lang_manager.tr("APK文件 (*.apk);;所有文件 (*.*)")
                    )
                    
                    if not apk_file:
                        self.status_message.emit(self.lang_manager.tr("用户取消安装"))
                        return
                    
                    # 安装APK
                    if self._install_tcl_logger(device, apk_file):
                        # 安装完成后再次检查包是否存在
                        if self._check_tcl_logger_installed(device):
                            # 安装成功，重新启动AEE log流程
                            self.start_aee_log()
                            return
                        else:
                            # 安装后仍然没有找到包，继续询问
                            continue
                    else:
                        # 安装失败，继续询问
                        continue
                else:
                    self.status_message.emit(self.lang_manager.tr("用户取消AEE log操作"))
                    return
                    
        except Exception as e:
            error_msg = f"{self.lang_manager.tr('处理安装流程时发生错误:')} {e}"
            print(error_msg)
            QMessageBox.critical(None, self.lang_manager.tr("错误"), error_msg)
    
    def _check_tcl_logger_installed(self, device):
        """检查com.tcl.logger是否已安装"""
        try:
            cmd = ["adb", "-s", device, "shell", "pm", "list", "packages", "-e"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                return "com.tcl.logger" in result.stdout
            else:
                print(f"{self.lang_manager.tr('检查包列表失败:')} {result.stderr.strip()}")
                return False
                
        except Exception as e:
            print(f"{self.lang_manager.tr('检查com.tcl.logger安装状态时发生错误:')} {e}")
            return False
    
    def _install_tcl_logger(self, device, apk_file):
        """安装com.tcl.logger APK"""
        try:
            # 直接执行安装命令
            install_cmd = ["adb", "-s", device, "install", "--bypass-low-target-sdk-block", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("安装失败")
                QMessageBox.critical(None, self.lang_manager.tr("安装失败"), f"APK安装失败:\n{error_msg}")
                return False
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                QMessageBox.critical(None, self.lang_manager.tr("安装失败"), f"安装可能失败:\n{result.stdout.strip()}")
                return False
            
            # 等待安装完成
            time.sleep(2)
            
            # 验证安装
            if self._check_tcl_logger_installed(device):
                QMessageBox.information(None, self.lang_manager.tr("安装成功"), 
                    f"{self.lang_manager.tr('com.tcl.logger安装成功!')}\n\n"
                    f"{self.lang_manager.tr('设备:')} {device}\n"
                    f"APK文件: {apk_file}")
                self.status_message.emit(self.tr("com.tcl.logger安装成功 - ") + device)
                return True
            else:
                QMessageBox.critical(None, self.lang_manager.tr("验证失败"), "未找到usersupport应用，请确认安装了正确的apk")
                return False
            
        except Exception as e:
            error_msg = f"{self.lang_manager.tr('安装com.tcl.logger时发生错误:')} {e}"
            print(error_msg)
            QMessageBox.critical(None, self.lang_manager.tr("安装错误"), error_msg)
            return False
    
    def _on_waiting_finished(self, success, message):
        """等待和拉取完成"""
        self.is_running = False
        
        if success:
            # 显示成功消息
            QMessageBox.information(None, self.lang_manager.tr("完成"), 
                f"{self.lang_manager.tr('AEE日志导出完成！')}\n\n"
                f"{self.lang_manager.tr('导出目录:')} {message}\n"
                f"文件夹已自动打开。")
            
            # 打开日志文件夹
            os.startfile(message)
            
            # 更新状态
            self.status_message.emit(self.tr("AEE日志已导出"))
        else:
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"AEE日志导出失败:\n{message}")
            self.status_message.emit("❌ " + self.tr("AEE日志导出失败: ") + str(message))

