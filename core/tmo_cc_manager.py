#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 TMO CC管理器
适配原Tkinter版本的TMO CC功能
"""

import subprocess
import os
import shutil
import datetime
import time
import re
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog, QVBoxLayout, QLabel, QPushButton


class PyQtTMOCCManager(QObject):
    """PyQt5 TMO CC管理器"""
    
    # 信号定义
    cc_pulled = pyqtSignal(str)  # folder
    cc_pushed = pyqtSignal(int, int)  # success_count, total_count
    server_started = pyqtSignal(str)  # server_type
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
    
    def _ask_file_exists(self, deviceinfo_path):
        """询问用户如何处理已存在的文件"""
        dialog = QDialog()
        dialog.setWindowTitle("文件已存在")
        dialog.setModal(True)
        dialog.resize(500, 300)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("目标文件已存在")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)
        
        path_label = QLabel(deviceinfo_path)
        path_label.setStyleSheet("color: blue;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        info_label = QLabel("请选择如何处理现有文件：")
        layout.addWidget(info_label)
        
        result_choice = {"choice": None}
        
        def on_overwrite():
            result_choice["choice"] = "overwrite"
            dialog.accept()
        
        def on_backup():
            result_choice["choice"] = "backup"
            dialog.accept()
        
        def on_cancel():
            result_choice["choice"] = "cancel"
            dialog.accept()
        
        btn_overwrite = QPushButton("覆盖现有文件")
        btn_overwrite.clicked.connect(on_overwrite)
        layout.addWidget(btn_overwrite)
        
        btn_backup = QPushButton("重命名备份并继续")
        btn_backup.clicked.connect(on_backup)
        layout.addWidget(btn_backup)
        
        btn_cancel = QPushButton("取消操作")
        btn_cancel.clicked.connect(on_cancel)
        layout.addWidget(btn_cancel)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
        return result_choice["choice"]
    
    def pull_cc_file(self):
        """拉CC文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            self.status_message.emit("开始拉取CC文件...")
            
            # 创建保存目录
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            target_dir = f"C:\\log\\{date_str}\\ccfile"
            os.makedirs(target_dir, exist_ok=True)
            deviceinfo_path = os.path.join(target_dir, "deviceInfo")
            
            # 检查文件是否已存在
            if os.path.exists(deviceinfo_path):
                choice = self._ask_file_exists(deviceinfo_path)
                if choice == "overwrite":
                    try:
                        if os.path.isdir(deviceinfo_path):
                            shutil.rmtree(deviceinfo_path)
                        else:
                            os.remove(deviceinfo_path)
                    except Exception as e:
                        QMessageBox.critical(None, "错误", f"删除现有文件/目录失败: {str(e)}")
                        return
                elif choice == "backup":
                    try:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_path = f"{deviceinfo_path}_backup_{timestamp}"
                        
                        if os.path.exists(backup_path):
                            counter = 1
                            while os.path.exists(f"{backup_path}_{counter}"):
                                counter += 1
                            backup_path = f"{backup_path}_{counter}"
                        
                        if os.path.isdir(deviceinfo_path):
                            shutil.move(deviceinfo_path, backup_path)
                        else:
                            os.rename(deviceinfo_path, backup_path)
                    except Exception as e:
                        QMessageBox.critical(None, "错误", f"重命名现有文件/目录失败: {str(e)}")
                        return
                else:  # cancel
                    self.status_message.emit("用户取消操作")
                    return
            
            # 拉取CC文件
            self.status_message.emit("正在拉取 /data/deviceInfo...")
            pull_cmd = ["adb", "-s", device, "pull", "/data/deviceInfo", target_dir]
            result = subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 检查Permission denied错误
            if result.returncode != 0 and "Permission denied" in result.stderr:
                self.status_message.emit("检测到权限问题，检查 root 权限...")
                
                # 执行 adb root
                cmd = ["adb", "-s", device, "root"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                output = result.stdout + result.stderr
                if "adbd cannot run as root in production builds" in output:
                    QMessageBox.critical(None, "错误", "设备没有root权限，操作无法执行")
                    return
                
                # 重新执行 adb pull
                self.status_message.emit("Root权限检查通过，重新拉取文件...")
                result = subprocess.run(
                    pull_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            
            if result.returncode == 0:
                # 验证文件是否真的被拉取
                if os.path.exists(deviceinfo_path):
                    self.cc_pulled.emit(target_dir)
                    self.status_message.emit(f"CC文件已拉取到: {target_dir}")
                    # 直接打开文件夹
                    try:
                        os.startfile(target_dir)
                    except Exception as e:
                        self.status_message.emit(f"打开文件夹失败: {str(e)}")
                else:
                    QMessageBox.critical(None, "错误", "文件拉取后验证失败，文件不存在")
            else:
                QMessageBox.critical(None, "错误", f"拉取CC文件失败: {result.stderr.strip()}")
                
        except Exception as e:
            QMessageBox.critical(None, "错误", f"拉取CC文件失败: {str(e)}")
    
    def push_cc_file(self):
        """推CC文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 检查root权限
        try:
            self.status_message.emit("检查设备root权限...")
            result = subprocess.run(
                ["adb", "-s", device, "root"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            output = result.stdout + result.stderr
            if "adbd cannot run as root in production builds" in output:
                QMessageBox.critical(None, "错误", "设备没有root权限，操作无法执行")
                self.status_message.emit("设备没有root权限")
                return
                
        except Exception as e:
            QMessageBox.critical(None, "错误", f"权限检查失败: {str(e)}")
            return
        
        # 选择文件
        file_paths, _ = QFileDialog.getOpenFileNames(
            None,
            "选择要推送的CC文件",
            "",
            "所有文件 (*.*);;文本文件 (*.txt);;配置文件 (*.conf);;设备信息文件 (deviceInfo*)"
        )
        
        if not file_paths:
            return
        
        try:
            self.status_message.emit(f"开始推送 {len(file_paths)} 个文件...")
            
            total_files = len(file_paths)
            success_count = 0
            failed_files = []
            
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                
                push_cmd = ["adb", "-s", device, "push", file_path, f"/data/deviceInfo/{file_name}"]
                result = subprocess.run(
                    push_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    success_count += 1
                else:
                    failed_files.append(f"{file_name}: {result.stderr.strip()}")
            
            self.cc_pushed.emit(success_count, total_files)
            
            # 处理推送结果
            if success_count == total_files:
                self.status_message.emit(f"CC文件推送完成 - 成功推送 {success_count} 个文件")
                # 推送成功后启动Entitlement界面
                self._start_entitlement_activity_after_push(device)
            elif success_count > 0:
                self.status_message.emit(f"CC文件部分推送完成 - 成功 {success_count}/{total_files}")
                # 部分成功也启动Entitlement界面
                self._start_entitlement_activity_after_push(device)
            else:
                failed_info = "\n".join(failed_files)
                QMessageBox.critical(
                    None,
                    "推送失败",
                    f"所有文件推送失败!\n\n设备: {device}\n失败文件:\n{failed_info}"
                )
            
        except Exception as e:
            QMessageBox.critical(None, "错误", f"推送CC文件失败: {str(e)}")
    
    def _start_entitlement_activity_after_push(self, device):
        """推送成功后启动Entitlement活动并点击NO CARD按钮"""
        try:
            self.status_message.emit("推送成功后启动Entitlement活动...")
            
            # 确保屏幕亮屏且解锁
            if not self.device_manager.ensure_screen_unlocked(device):
                return
            
            # 启动Entitlement活动
            cmd = ["adb", "-s", device, "shell", "am", "start", "com.tct.entitlement/.EditEntitlementEndpointActivity"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 等待界面加载
                time.sleep(3)
                
                # 使用uiautomator点击NO CARD按钮
                self._click_no_card_button_with_uiautomator(device)
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.status_message.emit(f"Entitlement活动启动失败: {error_msg}")
                
        except Exception as e:
            self.status_message.emit(f"启动Entitlement活动失败: {str(e)}")
    
    def _click_no_card_button_with_uiautomator(self, device):
        """使用uiautomator点击NO CARD按钮"""
        try:
            # 使用uiautomator命令查找并点击NO CARD按钮
            cmd = ["adb", "-s", device, "shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 获取UI dump内容
                cmd_get_dump = ["adb", "-s", device, "shell", "cat", "/sdcard/ui_dump.xml"]
                dump_result = subprocess.run(
                    cmd_get_dump,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if dump_result.returncode == 0:
                    ui_content = dump_result.stdout
                    
                    # 查找NO CARD按钮的坐标
                    pattern = r'text="NO CARD"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                    match = re.search(pattern, ui_content)
                    
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        # 点击按钮
                        click_cmd = ["adb", "-s", device, "shell", "input", "tap", str(center_x), str(center_y)]
                        click_result = subprocess.run(
                            click_cmd,
                            capture_output=True,
                            text=True,
                            timeout=10,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        
                        if click_result.returncode == 0:
                            self.status_message.emit("NO CARD按钮点击成功")
                        else:
                            QMessageBox.warning(
                                None,
                                "点击失败",
                                f"NO CARD按钮点击失败!\n\n设备: {device}\n坐标: ({center_x}, {center_y})\n\n请手动点击NO CARD按钮"
                            )
                    else:
                        # 尝试其他可能的文本
                        alt_patterns = [
                            r'text="No Card"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                            r'text="no card"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                        ]
                        
                        found_button = False
                        for alt_pattern in alt_patterns:
                            match = re.search(alt_pattern, ui_content)
                            if match:
                                x1, y1, x2, y2 = map(int, match.groups())
                                center_x = (x1 + x2) // 2
                                center_y = (y1 + y2) // 2
                                
                                click_cmd = ["adb", "-s", device, "shell", "input", "tap", str(center_x), str(center_y)]
                                click_result = subprocess.run(
                                    click_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                                )
                                
                                if click_result.returncode == 0:
                                    found_button = True
                                    self.status_message.emit("NO CARD按钮点击成功")
                                    break
                        
                        if not found_button:
                            QMessageBox.warning(
                                None,
                                "未找到按钮",
                                f"未找到NO CARD按钮!\n\n设备: {device}\n界面可能未完全加载或按钮文本不匹配\n\n请手动点击NO CARD按钮"
                            )
                            
        except Exception as e:
            self.status_message.emit(f"点击NO CARD按钮失败: {str(e)}")
    
    def start_prod_server(self):
        """启动PROD服务器"""
        self._start_entitlement_activity("PROD")
    
    def start_stg_server(self):
        """启动STG服务器"""
        self._start_entitlement_activity("STG")
    
    def _start_entitlement_activity(self, server_type):
        """启动Entitlement活动并设置服务器URL"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            self.status_message.emit(f"启动{server_type}服务器...")
            
            # 确保屏幕亮屏且解锁
            if not self.device_manager.ensure_screen_unlocked(device):
                return
            
            # 启动Entitlement活动
            cmd = ["adb", "-s", device, "shell", "am", "start", "com.tct.entitlement/.EditEntitlementEndpointActivity"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                QMessageBox.critical(None, "错误", f"启动{server_type}服务器活动失败: {error_msg}")
                return
            
            # 等待界面加载
            self.status_message.emit("等待界面加载...")
            if not self._wait_for_entitlement_loaded(device, timeout=8):
                QMessageBox.critical(None, "错误", "等待界面加载超时")
                return
            
            # 设置URL
            self.status_message.emit("设置服务器URL...")
            self._set_entitlement_urls(device, server_type)
            
            self.server_started.emit(server_type)
            self.status_message.emit(f"{server_type}服务器活动已启动并设置完成")
                
        except Exception as e:
            QMessageBox.critical(None, "错误", f"启动{server_type}服务器失败: {str(e)}")
    
    def _adb(self, args, device, timeout=15):
        """执行adb命令的辅助方法"""
        return subprocess.run(
            ["adb", "-s", device] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
    
    def _dump_ui_and_get(self, device):
        """生成并读取UI dump"""
        r = self._adb(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"], device, 10)
        if r.returncode != 0:
            return None
        r2 = self._adb(["shell", "cat", "/sdcard/ui_dump.xml"], device, 10)
        return r2.stdout if r2.returncode == 0 else None
    
    def _wait_for_entitlement_loaded(self, device, timeout=8):
        """等待页面出现两个EditText（最多timeout秒）"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            xml = self._dump_ui_and_get(device)
            if not xml:
                time.sleep(0.6)
                continue
            # 粗匹配两个EditText（class=EditText）
            if xml.count('class="android.widget.EditText"') >= 2:
                return True
            time.sleep(0.6)
        return False
    
    def _bounds_center(self, bounds_str):
        """计算bounds的中心点坐标"""
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", bounds_str))
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    def _tap(self, device, x, y):
        """点击指定坐标"""
        result = self._adb(["shell", "input", "tap", str(x), str(y)], device, 5)
        return result
    
    def _long_press(self, device, x, y, dur_ms=800):
        """长按指定坐标"""
        result = self._adb(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(dur_ms)], device, 5)
        return result
    
    def _select_all_then_replace(self, device, replacement_text):
        """长按后自动全选，直接输入文本替换"""
        result = self._adb(["shell", "input", "text", replacement_text], device, 5)
        return result.returncode == 0
    
    def _replace_edittext_by_bounds(self, device, bounds, replacement_text):
        """对给定EditText的bounds执行长按→自动全选→替换"""
        cx, cy = self._bounds_center(bounds)
        
        # 聚焦
        self._tap(device, cx, cy)
        time.sleep(0.15)
        
        # 长按自动全选
        self._long_press(device, cx, cy, 700)
        time.sleep(1.0)
        
        # 直接输入文本替换
        ok = self._select_all_then_replace(device, replacement_text)
        return ok
    
    def _set_entitlement_urls(self, device, server_type):
        """设置两个EditText的URL。根据server_type设置不同的URL。"""
        xml = self._dump_ui_and_get(device)
        if not xml:
            return
        
        # 抓两个EditText的bounds
        edit_bounds = re.findall(r'class="android\.widget\.EditText"[^>]*bounds="(\[[^"]+\])"', xml)
        
        if len(edit_bounds) < 2:
            return
        
        # 根据服务器类型设置URL
        if server_type == "PROD":
            url = "https://eas3.msg.t-mobile.com/generic_devices"
        elif server_type == "STG":
            url = "https://easstg1.msg.t-mobile.com/generic_devices"
        else:
            return
        
        # 依次设置两个EditText
        for i, b in enumerate(edit_bounds[:2], start=1):
            self._replace_edittext_by_bounds(device, b, url)
            time.sleep(0.5)
        
        # 设置完成后点击OK按钮
        self._click_ok_button(device)
    
    def _click_ok_button(self, device):
        """点击OK按钮"""
        try:
            # 获取UI dump
            xml = self._dump_ui_and_get(device)
            if not xml:
                return False
            
            # 查找OK按钮
            ok_patterns = [
                r'text="OK".*?bounds="(\[[^"]+\])"',
                r'text="确定".*?bounds="(\[[^"]+\])"',
                r'text="Done".*?bounds="(\[[^"]+\])"',
                r'text="完成".*?bounds="(\[[^"]+\])"',
                r'content-desc="OK".*?bounds="(\[[^"]+\])"',
                r'content-desc="确定".*?bounds="(\[[^"]+\])"',
                r'content-desc="Done".*?bounds="(\[[^"]+\])"'
            ]
            
            ok_bounds = None
            for pattern in ok_patterns:
                match = re.search(pattern, xml)
                if match:
                    ok_bounds = match.group(1)
                    break
            
            if ok_bounds:
                cx, cy = self._bounds_center(ok_bounds)
                self._tap(device, cx, cy)
                return True
            else:
                return False
                
        except Exception as e:
            return False

