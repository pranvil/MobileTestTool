#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 Echolocate管理器
适配原Tkinter版本的Echolocate功能 - 完整功能版本
"""

import subprocess
import os
import glob
import datetime
import time
import sys
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (QMessageBox, QFileDialog, QInputDialog, QDialog, 
                              QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                              QPushButton, QListWidget, QProgressBar, QTextEdit,
                              QApplication)

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class ProgressDialog(QDialog):
    """进度对话框，支持用户确认"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(title)
        self.setFixedSize(500, 200)
        self.setModal(True)
        self._user_confirmed = False
        self.setup_ui()
        
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 状态标签
        self.status_label = QLabel("正在处理...")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 确认按钮（初始隐藏）
        self.confirm_button = QPushButton(self.tr("测试已完成，确认"))
        self.confirm_button.clicked.connect(self._on_confirm)
        self.confirm_button.setVisible(False)
        button_layout.addWidget(self.confirm_button)
        
        # 取消按钮
        self.cancel_button = QPushButton(self.tr("取消"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def set_status(self, text):
        """设置状态文本"""
        self.status_label.setText(text)
    
    def set_progress(self, value):
        """设置进度值"""
        self.progress_bar.setValue(value)
    
    def show_confirm_button(self, test_case_id):
        """显示确认按钮"""
        self.confirm_button.setVisible(True)
        self.status_label.setText(self.tr("测试用例 ") + str(test_case_id) + self.tr(" - 请在完成测试后点击确认按钮"))
    
    def _on_confirm(self):
        """确认按钮点击"""
        self._user_confirmed = True
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText(self.tr("已确认，正在处理..."))


class VoiceIntentWorker(QThread):
    """Voice Intent测试后台线程"""
    
    progress_updated = Signal(int, str)  # progress, status
    show_confirm = Signal(str)  # test_case_id
    finished = Signal(dict)  # result
    
    def __init__(self, device, test_case_id, progress_dialog):
        super().__init__()
        self.device = device
        self.test_case_id = test_case_id
        self.progress_dialog = progress_dialog
    
    def run(self):
        """执行测试"""
        try:
            # 清理旧文件
            self.progress_updated.emit(10, self.lang_manager.tr("清理旧文件..."))
            cmd = f"adb -s {self.device} shell rm /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/*"
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30,
                         creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 等待用户执行测试
            self.progress_updated.emit(20, self.lang_manager.tr("请手动执行测试..."))
            now = datetime.datetime.now()
            filename = now.strftime("%Y%m%d_%H%M%S")
            
            # 显示确认按钮
            self.show_confirm.emit(self.test_case_id)
            
            # 等待用户确认
            max_wait_time = 3600  # 最多等待1小时
            wait_start_time = time.time()
            
            while time.time() - wait_start_time < max_wait_time:
                if self.progress_dialog._user_confirmed:
                    break
                time.sleep(1)
            
            if not self.progress_dialog._user_confirmed:
                self.finished.emit({
                    'success': False,
                    'error': self.tr('等待用户确认超时，请重新开始测试。')
                })
                return
            
            # 检查测试结果
            self.progress_updated.emit(50, self.lang_manager.tr("检查测试结果..."))
            list_cmd = f"adb -s {self.device} shell ls -l /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/"
            list_result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=30,
                                       creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if list_result.returncode != 0:
                self.finished.emit({
                    'success': False,
                    'error': f"{self.tr('无法访问目录，错误:')} {list_result.stderr}"
                })
                return
            
            # 检查是否包含log_voice_intents文件
            file_found = False
            possible_names = ['log_voice_intents', 'voice_intents', 'voice_intent']
            
            for name in possible_names:
                if name in list_result.stdout:
                    file_found = True
                    break
            
            if not file_found:
                self.finished.emit({
                    'success': False,
                    'error': f"{self.tr('未找到voice_intents相关文件。目录内容:')}\n{list_result.stdout}\n\n{self.tr('请确认测试已完成并生成了正确的日志文件。')}"
                })
                return
            
            # 拉取日志文件
            self.progress_updated.emit(60, self.lang_manager.tr("拉取日志文件..."))
            date_str = now.strftime("%Y%m%d")
            target_folder = f"{self.progress_dialog.parent().get_storage_path()}\\{self.test_case_id}_{filename}"
            os.makedirs(target_folder, exist_ok=True)
            
            # 拉取echolocate文件
            pull_cmd1 = f"adb -s {self.device} pull /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug \"{target_folder}\""
            subprocess.run(pull_cmd1, shell=True, capture_output=True, text=True, timeout=120,
                         creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 拉取debuglogger文件
            self.progress_updated.emit(80, self.lang_manager.tr("拉取debuglogger文件..."))
            pull_cmd2 = f"adb -s {self.device} pull /data/debuglogger \"{target_folder}\""
            subprocess.run(pull_cmd2, shell=True, capture_output=True, text=True, timeout=120,
                         creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 完成
            self.progress_updated.emit(100, self.lang_manager.tr("测试完成!"))
            
            # 打开文件夹
            try:
                os.startfile(target_folder)
            except Exception as e:
                print(f"[DEBUG] {self.tr('打开文件夹失败:')} {str(e)}")
            
            self.finished.emit({
                'success': True,
                'test_folder': target_folder
            })
            
        except subprocess.TimeoutExpired:
            self.finished.emit({
                'success': False,
                'error': self.tr('操作超时，请检查设备连接')
            })
        except Exception as e:
            self.finished.emit({
                'success': False,
                'error': f"{self.tr('执行voice_intent测试失败:')} {str(e)}"
            })


class PySide6EcholocateManager(QObject):
    """PySide6 Echolocate管理器 - 完整功能版本"""
    
    # 信号定义
    echolocate_installed = Signal()
    echolocate_triggered = Signal()
    file_pulled = Signal(str)  # folder
    file_deleted = Signal()
    status_message = Signal(str)
    log_message = Signal(str, str)  # text, color
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.is_installed = False
        self.is_running = False
    
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
        
    def install_echolocate(self):
        """安装Echolocate"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 在当前文件夹查找APK文件（1tkinter_backup/Echolocate/）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            echolocate_dir = os.path.join(project_root, "1tkinter_backup", "Echolocate")
            
            apk_files = []
            if os.path.exists(echolocate_dir):
                apk_files = glob.glob(os.path.join(echolocate_dir, "*.apk"))
            
            if apk_files:
                # 找到APK文件，安装所有APK
                QMessageBox.information(None, self.tr("安装"), self.tr("找到 ") + str(len(apk_files)) + self.tr(" 个APK文件，开始安装..."))
                self.status_message.emit(self.tr("找到 ") + str(len(apk_files)) + self.tr(" 个APK文件，开始安装..."))
                
                for apk_file in apk_files:
                    try:
                        # 执行adb install命令
                        result = subprocess.run(
                            ["adb", "-s", device, "install", "-r", apk_file],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        
                        if result.returncode == 0:
                            print(f"[DEBUG] {self.tr('APK安装成功:')} {os.path.basename(apk_file)}")
                        else:
                            print(f"[DEBUG] {self.tr('APK安装失败:')} {os.path.basename(apk_file)}, {self.tr('错误:')} {result.stderr}")
                            QMessageBox.critical(None, self.tr("错误"), f"APK安装失败: {os.path.basename(apk_file)}\n{result.stderr}")
                            return
                            
                    except subprocess.TimeoutExpired:
                        QMessageBox.critical(None, self.tr("错误"), f"APK安装超时: {os.path.basename(apk_file)}")
                        return
                    except Exception as e:
                        QMessageBox.critical(None, self.tr("错误"), f"APK安装异常: {os.path.basename(apk_file)}\n{str(e)}")
                        return
            else:
                # 没有找到APK文件，让用户选择
                apk_file, _ = QFileDialog.getOpenFileName(
                    None,
                    self.tr("选择Echolocate APK文件"),
                    "",
                    self.tr("APK文件 (*.apk);;所有文件 (*.*)")
                )
                
                if not apk_file:
                    return
                
                try:
                    # 执行adb install命令
                    result = subprocess.run(
                        ["adb", "-s", device, "install", "-r", apk_file],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    if result.returncode != 0:
                        QMessageBox.critical(None, self.tr("错误"), f"APK安装失败\n{result.stderr}")
                        return
                        
                except subprocess.TimeoutExpired:
                    QMessageBox.critical(None, self.tr("错误"), "APK安装超时")
                    return
                except Exception as e:
                    QMessageBox.critical(None, self.tr("错误"), f"APK安装异常\n{str(e)}")
                    return
            
            # 安装完成后启动应用
            try:
                result = subprocess.run(
                    ["adb", "-s", device, "shell", "am", "start", "-n", "com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    self.is_installed = True
                    self.echolocate_installed.emit()
                    self.status_message.emit(self.tr("Echolocate安装完成并已启动"))
                    QMessageBox.information(None, self.tr("成功"), self.tr("Echolocate安装完成并已启动"))
                else:
                    # APK安装成功但启动失败，显示警告
                    self.is_installed = True
                    self.echolocate_installed.emit()
                    self.status_message.emit(self.tr("APK安装成功但启动失败"))
                    QMessageBox.warning(None, self.tr("警告"), "APK安装成功但启动失败，请手动启动应用")
                    
            except Exception as e:
                # APK安装成功但启动异常，显示警告
                self.is_installed = True
                self.echolocate_installed.emit()
                self.status_message.emit("⚠️ " + self.tr("APK安装成功但启动失败: ") + str(e))
                QMessageBox.warning(None, self.tr("警告"), self.tr("APK安装成功但启动失败: ") + str(e))
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("安装Echolocate失败: ") + str(e))
            QMessageBox.critical(None, self.tr("错误"), self.tr("安装Echolocate失败: ") + str(e))
    
    def trigger_echolocate(self):
        """触发Echolocate"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "am", "start", "-n", "com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.is_running = True
            self.echolocate_triggered.emit()
            self.status_message.emit(self.tr("Echolocate应用已启动"))
            
        except Exception as e:
            self.status_message.emit(f"{self.tr('启动Echolocate失败:')} {str(e)}")
    
    def pull_echolocate_file(self):
        """Pull Echolocate文件（带重命名对话框）"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 显示重命名对话框
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"diag_debug_{timestamp}"
            
            dialog = QDialog()
            dialog.setWindowTitle(self.tr("重命名文件"))
            dialog.setFixedSize(400, 180)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 标题
            title_label = QLabel(self.tr("重命名Echolocate文件"))
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            layout.addWidget(title_label)
            
            # 文件名输入
            name_label = QLabel(self.tr("文件夹名称:"))
            layout.addWidget(name_label)
            
            name_input = QLineEdit()
            name_input.setText(default_name)
            name_input.selectAll()
            layout.addWidget(name_input)
            
            # 按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton(self.tr("取消"))
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            confirm_btn = QPushButton(self.tr("确定"))
            confirm_btn.clicked.connect(dialog.accept)
            confirm_btn.setDefault(True)
            button_layout.addWidget(confirm_btn)
            
            layout.addLayout(button_layout)
            
            # 显示对话框
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            folder_name = name_input.text().strip()
            if not folder_name:
                QMessageBox.warning(None, self.tr("输入错误"), self.tr("请输入文件夹名称"))
                return
            
            # 创建目标文件夹
            self.status_message.emit(self.tr("开始拉取Echolocate文件..."))
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            target_dir = f"{self.get_storage_path()}\\{folder_name}"
            os.makedirs(target_dir, exist_ok=True)
            
            # 拉取文件
            pull_cmd = ["adb", "-s", device, "pull", "/sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug", target_dir]
            result = subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.file_pulled.emit(target_dir)
                self.status_message.emit(self.tr("Echolocate文件已拉取到: ") + target_dir)
                QMessageBox.information(None, self.tr("成功"), self.tr("Echolocate文件拉取完成\n保存位置: ") + target_dir)
                # 直接打开文件夹
                try:
                    os.startfile(target_dir)
                except Exception as e:
                    self.status_message.emit("❌ " + self.tr("打开文件夹失败: ") + str(e))
            else:
                self.status_message.emit("❌ " + self.tr("拉取Echolocate文件失败: ") + result.stderr.strip())
                QMessageBox.critical(None, self.tr("错误"), self.tr("拉取文件失败\n") + result.stderr)
                
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("拉取Echolocate文件失败: ") + str(e))
            QMessageBox.critical(None, self.tr("错误"), self.tr("拉取Echolocate文件失败: ") + str(e))
    
    def delete_echolocate_file(self):
        """删除Echolocate文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "rm", "-rf", "/sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/*"],
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.file_deleted.emit()
            self.status_message.emit(self.tr("Echolocate文件已删除"))
            QMessageBox.information(None, self.tr("成功"), self.tr("Echolocate文件删除完成"))
            
        except Exception as e:
            self.status_message.emit(f"{self.tr('删除Echolocate文件失败:')} {str(e)}")
            QMessageBox.critical(None, self.tr("错误"), f"{self.tr('删除文件失败')}\n{str(e)}")
    
    def get_filter_keywords(self, filter_type):
        """
        获取指定类型的过滤关键字
        
        Args:
            filter_type: 过滤类型
        
        Returns:
            str or list: 对应的过滤关键字
        """
        keywords_map = {
            'CallID': ['CallID'],
            'CallState': ['CallState'],
            'UICallState': ['UICallState'],
            'AllCallState': ['UICallState', 'CallState'],
            'IMSSignallingMessageLine1': ['IMSSignallingMessageLine1'],
            'AllCallFlow': ['UICallState', 'CallState', 'IMSSignallingMessageLine1'],
            'voice_intent': []  # 特殊处理
        }
        
        return keywords_map.get(filter_type, [])
    
    def process_file_filter(self, keywords, filter_name, special_logic=None, source_file=None):
        """
        处理文件过滤的通用方法
        
        Args:
            keywords: 过滤关键字列表
            filter_name: 过滤名称，用于生成输出文件名
            special_logic: 特殊逻辑函数，用于处理特殊的过滤规则
            source_file: 源文件路径，如果为None则弹出文件选择对话框
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 如果没有提供源文件路径，则让用户选择文件
            if source_file is None:
                source_file, _ = QFileDialog.getOpenFileName(
                    None,
                    f"{self.tr('选择要过滤的文件 -')} {filter_name}",
                    "",
                    self.tr("文本文件 (*.txt);;所有文件 (*.*)")
                )
                
                if not source_file:
                    return False
            
            # 获取文件目录和文件名
            file_dir = os.path.dirname(source_file)
            
            # 生成输出文件名
            output_file = os.path.join(file_dir, f"{filter_name}.txt")
            
            # 打开源文件和目标文件
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as source_f:
                lines = source_f.readlines()
            
            # 查找包含关键字的行
            result_lines = []
            for line_number, line in enumerate(lines, 1):
                # 将行按空格分割成单词
                words = line.strip().split()
                
                # 检查是否匹配
                matched = False
                if special_logic:
                    # 使用特殊逻辑
                    matched = special_logic(words)
                else:
                    # 标准逻辑：检查关键字是否在单词列表中
                    matched = any(keyword in words for keyword in keywords)
                
                if matched:
                    # 移除(java.lang.String)
                    cleaned_line = line.replace('(java.lang.String)', '').strip()
                    result_lines.append(f"Line {line_number}: {cleaned_line}\n")
            
            # 将结果写入新文件
            with open(output_file, 'w', encoding='utf-8') as target_f:
                target_f.writelines(result_lines)
            
            # 打开生成的文件
            try:
                os.startfile(output_file)
            except Exception as e:
                print(f"[DEBUG] {self.tr('打开文件失败:')} {str(e)}")
            
            self.status_message.emit("✅ " + self.tr("过滤完成！找到 ") + str(len(result_lines)) + self.tr(" 行匹配内容"))
            
            return True
            
        except UnicodeDecodeError:
            QMessageBox.critical(None, self.tr("错误"), "文件编码错误，请确保文件是UTF-8编码")
            return False
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"处理文件过滤失败: {str(e)}")
            return False
    
    def filter_callid(self):
        """过滤CallID"""
        keywords = self.get_filter_keywords('CallID')
        return self.process_file_filter(keywords, 'CallID')
    
    def filter_callstate(self):
        """过滤CallState"""
        keywords = self.get_filter_keywords('CallState')
        return self.process_file_filter(keywords, 'CallState')
    
    def filter_uicallstate(self):
        """过滤UICallState"""
        keywords = self.get_filter_keywords('UICallState')
        return self.process_file_filter(keywords, 'UICallState')
    
    def filter_allcallstate(self):
        """过滤AllCallState"""
        keywords = self.get_filter_keywords('AllCallState')
        return self.process_file_filter(keywords, 'AllCallState')
    
    def filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        keywords = self.get_filter_keywords('IMSSignallingMessageLine1')
        return self.process_file_filter(keywords, 'IMSSignallingMessageLine1')
    
    def filter_allcallflow(self):
        """过滤AllCallFlow - 查找UICallState、CallState或IMSSignallingMessageLine1"""
        # 先让用户选择源文件
        source_file, _ = QFileDialog.getOpenFileName(
            None,
            self.tr("选择要过滤的文件 - AllCallFlow"),
            "",
            self.tr("文本文件 (*.txt);;所有文件 (*.*)")
        )
        
        if not source_file:
            return False
        
        # 先执行主要的AllCallFlow过滤
        keywords = self.get_filter_keywords('AllCallFlow')
        result = self.process_file_filter(keywords, 'AllCallFlow', source_file=source_file)
        
        # 额外调用其他过滤函数，传递相同的源文件路径
        try:
            self.process_file_filter(self.get_filter_keywords('IMSSignallingMessageLine1'), 
                                    'IMSSignallingMessageLine1', source_file=source_file)
            self.process_file_filter(self.get_filter_keywords('UICallState'), 
                                    'UICallState', source_file=source_file)
            self.process_file_filter(self.get_filter_keywords('CallState'), 
                                    'CallState', source_file=source_file)
            self.process_file_filter(self.get_filter_keywords('CallID'), 
                                    'CallID', source_file=source_file)
        except Exception as e:
            print(f"[DEBUG] {self.tr('额外过滤函数调用失败:')} {str(e)}")
        
        return result
    
    def filter_voice_intent(self):
        """过滤voice_intent测试功能"""
        try:
            # 创建选择对话框
            dialog = QDialog()
            dialog.setWindowTitle(self.tr("Voice Intent测试选项"))
            dialog.setFixedSize(400, 200)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 标题
            title_label = QLabel(self.tr("选择Voice Intent测试模式"))
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            layout.addWidget(title_label)
            
            # 按钮布局
            button_layout = QHBoxLayout()
            
            start_btn = QPushButton(self.tr("开始测试"))
            start_btn.clicked.connect(lambda: self._start_voice_intent_test(dialog))
            button_layout.addWidget(start_btn)
            
            extract_btn = QPushButton(self.tr("提取指定intent"))
            extract_btn.clicked.connect(lambda: self._extract_voice_intent(dialog))
            button_layout.addWidget(extract_btn)
            
            layout.addWidget(QLabel(""))  # 间隔
            layout.addLayout(button_layout)
            
            # 取消按钮
            cancel_btn = QPushButton(self.tr("取消"))
            cancel_btn.clicked.connect(dialog.reject)
            layout.addWidget(cancel_btn)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"创建voice_intent测试对话框失败: {str(e)}")
    
    def _start_voice_intent_test(self, dialog):
        """开始voice_intent测试"""
        try:
            dialog.accept()  # 关闭选择对话框
            
            # 获取选中的设备
            device = self.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 获取测试用例ID
            test_case_id, ok = QInputDialog.getText(
                None,
                self.tr("输入测试用例ID"),
                self.tr("请输入测试用例ID:")
            )
            
            if not ok or not test_case_id:
                return False
            
            # 创建进度对话框
            progress_dialog = ProgressDialog(self.tr("Voice Intent测试"))
            
            # 创建后台线程
            self.worker = VoiceIntentWorker(device, test_case_id, progress_dialog)
            
            # 连接信号
            self.worker.progress_updated.connect(lambda p, s: self._update_progress(progress_dialog, p, s))
            self.worker.show_confirm.connect(lambda tid: progress_dialog.show_confirm_button(tid))
            self.worker.finished.connect(lambda r: self._on_test_finished(progress_dialog, r))
            
            # 启动线程
            self.worker.start()
            
            # 显示进度对话框
            progress_dialog.exec()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"开始voice_intent测试失败: {str(e)}")
            return False
    
    def cleanup(self):
        """清理工作线程，在窗口关闭时调用"""
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            try:
                self.worker.wait(3000)
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait(1000)
            except Exception:
                pass
            finally:
                self.worker = None
    
    def _update_progress(self, dialog, progress, status):
        """更新进度"""
        dialog.set_progress(progress)
        dialog.set_status(status)
    
    def _on_test_finished(self, dialog, result):
        """测试完成回调"""
        dialog.accept()  # 关闭进度对话框
        
        if result and result.get('success', False):
            test_folder = result.get('test_folder', '')
            QMessageBox.information(None, self.tr("测试完成"), 
                f"{self.tr('Voice Intent测试完成！')}\n\n"
                f"{self.tr('测试文件夹:')} {test_folder}\n"
                f"文件已自动打开。")
        else:
            error_msg = result.get('error', self.tr('未知错误')) if result else self.tr('测试失败')
            QMessageBox.critical(None, self.tr("测试失败"), f"Voice Intent测试失败: {error_msg}")
    
    def _extract_voice_intent(self, dialog):
        """提取指定voice_intent"""
        try:
            dialog.accept()  # 关闭选择对话框
            
            # 让用户选择txt文件
            source_file, _ = QFileDialog.getOpenFileName(
                None,
                self.tr("选择要提取intent的文件"),
                "",
                self.tr("文本文件 (*.txt);;所有文件 (*.*)")
            )
            
            if not source_file:
                return False
            
            # Intent类型列表
            intent_types = [
                "diagandroid.phone.detailedCallState",
                "diagandroid.phone.UICallState", 
                "diagandroid.phone.imsSignallingMessage",
                "diagandroid.phone.AppTriggeredCall",
                "diagandroid.phone.CallSetting message",
                "diagandroid.phone.emergencyCallTimerState",
                "diagandroid.phone.carrierConfig",
                "diagandroid.phone.RTPDLStat",
                "diagandroid.phone.VoiceRadioBearerHandoverState"
            ]
            
            # 创建intent选择对话框
            intent_dialog = QDialog()
            intent_dialog.setWindowTitle(self.tr("选择Intent类型"))
            intent_dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout(intent_dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 标题
            title_label = QLabel(self.tr("选择要提取的Intent类型"))
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            layout.addWidget(title_label)
            
            # 列表框
            listbox = QListWidget()
            for i, intent_type in enumerate(intent_types):
                listbox.addItem(f"{i+1}. {intent_type}")
            layout.addWidget(listbox)
            
            # 按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton(self.tr("取消"))
            cancel_btn.clicked.connect(intent_dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            extract_btn = QPushButton(self.tr("提取"))
            extract_btn.clicked.connect(intent_dialog.accept)
            extract_btn.setDefault(True)
            button_layout.addWidget(extract_btn)
            
            layout.addLayout(button_layout)
            
            # 显示对话框
            if intent_dialog.exec() != QDialog.DialogCode.Accepted:
                return False
            
            # 获取选中的intent
            selected_items = listbox.selectedItems()
            if not selected_items:
                QMessageBox.warning(None, self.tr("选择错误"), "请选择一个Intent类型")
                return False
            
            selected_index = listbox.row(selected_items[0])
            selected_intent = intent_types[selected_index]
            
            # 执行提取
            self._execute_intent_extraction(source_file, selected_intent)
            
            return True
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"提取voice_intent失败: {str(e)}")
            return False
    
    def _execute_intent_extraction(self, source_file, intent_type):
        """执行intent提取"""
        try:
            # 获取文件目录
            file_dir = os.path.dirname(source_file)
            
            # 生成输出文件名
            output_file = os.path.join(file_dir, f"{intent_type.replace('.', '_').replace(' ', '_')}.txt")
            
            # 读取源文件
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 提取指定intent的内容
            result_lines = []
            found = False
            start_token = f"Action: {intent_type}"
            end_token = "--INTENT--"
            
            for line in lines:
                line = line.strip()
                
                if found:
                    result_lines.append(line + '\n')
                    if line == end_token:
                        found = False
                        result_lines.append('\n')
                
                if line == start_token:
                    found = True
                    result_lines.append(line + '\n')
            
            # 写入结果文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.writelines(result_lines)
            
            # 打开结果文件
            try:
                os.startfile(output_file)
            except Exception as e:
                print(f"[DEBUG] {self.tr('打开文件失败:')} {str(e)}")
            
            QMessageBox.information(None, self.tr("提取完成"), 
                f"{self.tr('Intent提取完成！')}\n\n"
                f"{self.tr('找到')} {len(result_lines)} {self.tr('行匹配内容')}\n"
                f"{self.tr('文件已保存:')} {output_file}\n"
                f"文件已自动打开。")
            
            return True
            
        except UnicodeDecodeError:
            QMessageBox.critical(None, self.tr("错误"), "文件编码错误，请确保文件是UTF-8编码")
            return False
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"执行intent提取失败: {str(e)}")
            return False
    
    def check_installation_status(self):
        """检查Echolocate安装状态"""
        try:
            device = self.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 检查应用是否已安装
            result = subprocess.run(
                ["adb", "-s", device, "shell", "pm", "list", "packages", "com.tmobile.echolocate"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.is_installed = "com.tmobile.echolocate" in result.stdout
            return self.is_installed
            
        except Exception as e:
            print(f"[DEBUG] {self.tr('检查安装状态失败:')} {str(e)}")
            return False
    
    def get_echolocate_version(self):
        """获取Echolocate版本号"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 执行命令获取版本号
            cmd = ["adb", "-s", device, "shell", "dumpsys", "package", "com.tmobile.echolocate"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 查找versionName行
                lines = result.stdout.split('\n')
                version_line = None
                for line in lines:
                    if 'versionName' in line:
                        version_line = line.strip()
                        break
                
                if version_line:
                    # 提取版本号
                    if 'versionName=' in version_line:
                        version = version_line.split('versionName=')[1]
                        # QMessageBox.information(None, "Echolocate版本", f"Echolocate版本号:\n{version}")
                        version_msg = f"📱 {self.tr('Echolocate版本号')}: {version}"
                        if hasattr(self, 'log_message'):
                            self.log_message.emit(version_msg, "green")
                        else:
                            self.status_message.emit(version_msg)
                    else:
                        # QMessageBox.information(None, "Echolocate版本", f"版本信息:\n{version_line}")
                        version_msg = f"📱 {self.tr('Echolocate版本信息')}: {version_line}"
                        if hasattr(self, 'log_message'):
                            self.log_message.emit(version_msg, "green")
                        else:
                            self.status_message.emit(version_msg)
                else:
                    # QMessageBox.warning(None, "版本信息", "未找到版本信息，可能应用未安装")
                    self.status_message.emit(self.tr("未找到Echolocate版本信息"))
            else:
                # QMessageBox.critical(None, "错误", f"获取版本信息失败:\n{result.stderr}")
                self.status_message.emit("❌ " + self.tr("获取Echolocate版本失败: ") + result.stderr)
                
        except subprocess.TimeoutExpired:
            # QMessageBox.critical(None, "错误", "获取版本信息超时")
            self.status_message.emit(self.tr("获取Echolocate版本超时"))
        except Exception as e:
            # QMessageBox.critical(None, "错误", f"获取版本信息失败: {str(e)}")
            self.status_message.emit("❌ " + self.tr("获取Echolocate版本失败: ") + str(e))
    
    def get_status_info(self):
        """获取Echolocate状态信息"""
        device = self.device_manager.validate_device_selection()
        return {
            'installed': self.is_installed,
            'running': self.is_running,
            'device': device if device else self.tr("未选择")
        }
