#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
赫拉配置管理器
负责赫拉相关的配置功能
"""

import os
import time
import subprocess
import urllib.request
import sys
import io
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog

def run_adb_command(cmd, **kwargs):
    """运行ADB命令，隐藏控制台窗口"""
    if isinstance(cmd, str):
        # 字符串命令，使用shell=True
        kwargs.setdefault('shell', True)
    else:
        # 列表命令，不使用shell
        kwargs.setdefault('shell', False)
    
    # 添加隐藏控制台窗口的标志
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    
    return subprocess.run(cmd, **kwargs)

# 可选依赖
try:
    import uiautomator2 as u2  # type: ignore
    HAS_UIAUTOMATOR2 = True
except ImportError:
    u2 = None  # type: ignore
    HAS_UIAUTOMATOR2 = False

# 修复控制台中文显示问题（仅在非PyInstaller环境中）
try:
    if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except (AttributeError, TypeError):
    # 在PyInstaller环境中忽略编码设置
    pass

class HeraConfigManager:
    def __init__(self, app_instance):
        """
        初始化赫拉配置管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        self.device = None
        
        # 配置参数
        self.package_to_disable = "com.tcl.logger"
        self.package_name = "com.debug.loggerui"
        self.activity_name = ".MainActivity"
        self.toggle_button_id = "com.debug.loggerui:id/startStopToggleButton"
        self.icon_xpath = '//*[@resource-id="android:id/action_bar"]/android.widget.LinearLayout[2]'
        self.test_package_name = "com.example.test"
        
        # 输出目录将在需要时创建
        self.output_dir = None
        
        # 检查uiautomator2是否可用
        if not HAS_UIAUTOMATOR2:
            print("[WARNING] uiautomator2 not available, some features may not work")
    
    def _ensure_output_directory(self):
        """确保输出目录存在，如果不存在则创建"""
        if self.output_dir is None:
            try:
                today = datetime.now().strftime("%Y%m%d")
                self.output_dir = f"C:\\log\\{today}\\hera"
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                print(f"[WARNING] 创建输出目录失败: {str(e)}")
                self.output_dir = "."
        return self.output_dir
    
    def configure_hera(self):
        """配置赫拉 - 主入口函数"""
        try:
            # 检查设备连接
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 显示配置选项对话框
            config_options = self._show_config_dialog()
            if not config_options:
                return False
            
            # 在后台线程中执行配置流程
            import threading
            thread = threading.Thread(target=self._run_config_process, args=(config_options,), daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"赫拉配置启动失败: {str(e)}"
            self._log_message(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            return False
    
    def _run_config_process(self, config_options):
        """在后台线程中运行配置流程"""
        # 用于记录失败的项目
        failed_items = []
        
        try:
            # 开始配置流程
            self._log_message("开始赫拉配置流程...")
            time.sleep(0.5)  # 给UI时间更新
            
            # 1. 安装APK
            if config_options.get('install_apk', True):
                if not self._install_apk():
                    # APK安装失败，立即终止配置流程
                    self._log_message("❌ 赫拉配置终止：必须安装com.example.test.apk")
                    self.app.root.after(0, lambda: messagebox.showerror("配置终止", 
                        "赫拉配置已终止！\n\n"
                        "必须安装com.example.test.apk才能继续配置。\n\n"
                        "请确保APK文件存在并重新运行配置。"))
                    return
                time.sleep(0.5)
            
            # 2. 初始化uiautomator2 (可选)
            uiautomator_available = self._init_uiautomator()
            if not uiautomator_available:
                self._log_message("⚠️ 跳过需要UI自动化的步骤")
            time.sleep(0.5)
            
            # 3. 设置屏幕常亮
            self._set_screen_timeout(2147483647)
            time.sleep(0.5)
            
            # 4. 禁用TCL用户支持
            if config_options.get('disable_tcl_logger', False):
                self._disable_tcl_logger()
                time.sleep(0.5)
            
            # 5. 启动logger
            self._start_logger()
            time.sleep(0.5)
            
            # 6. 设置手机日志
            self._setup_mobile_log()
            time.sleep(0.5)
            
            # 7. 处理GDPR设置 (需要UI自动化)
            if config_options.get('handle_gdpr', True):
                if uiautomator_available:
                    self._handle_gdpr_settings()
                else:
                    self._log_message("⚠️ 跳过GDPR设置 (需要UI自动化)")
                time.sleep(0.5)
            
            # 8. 检查各种状态
            status_results = self._check_all_status()
            failed_items.extend(status_results)
            time.sleep(0.5)
            
            # 9. 运行bugreport
            if config_options.get('run_bugreport', False):
                if not self._run_bugreport():
                    failed_items.append("bugreport收集")
            
            # 10. 模拟应用崩溃
            if config_options.get('simulate_crash', False):
                if not self._simulate_app_crash():
                    failed_items.append("应用崩溃模拟")
            
            # 根据失败项目决定最终结果
            if failed_items:
                self._log_message("赫拉配置终止！")
                failure_reasons = "、".join(failed_items)
                # 在主线程中显示结果对话框
                self.app.root.after(0, lambda: messagebox.showerror("配置终止", f"赫拉配置已终止！\n\n失败项目:\n{failure_reasons}\n\n请检查上述项目后重试。"))
            else:
                self._log_message("赫拉配置完成！")
                # 在主线程中显示结果对话框
                self.app.root.after(0, lambda: messagebox.showinfo("成功", "赫拉配置完成！"))
                
                # 配置完成后设置屏幕超时为60秒
                self._set_screen_timeout(60000)
                                
                # 显示后续操作提示
                self._show_completion_tips()

            
        except Exception as e:
            error_msg = f"赫拉配置失败: {str(e)}"
            self._log_message(f"❌ {error_msg}")
            # 在主线程中显示错误对话框
            self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def _log_message(self, message):
        """在日志区域显示消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 使用更兼容的状态标识
        if message.startswith("✅"):
            status_icon = "[成功]"
            color_tag = "success"
        elif message.startswith("❌"):
            status_icon = "[失败]"
            color_tag = "error"
        else:
            status_icon = "[信息]"
            color_tag = "info"
        
        # 移除原始图标，使用文字标识
        clean_message = message.replace("✅", "").replace("❌", "").strip()
        log_message = f"[{timestamp}] {status_icon} {clean_message}\n"
        
        # 使用after(0)确保立即在主线程中执行
        self.app.root.after(0, lambda: self._update_log_display(log_message, color_tag))
    
    def _update_log_display(self, message, color_tag="info"):
        """更新日志显示"""
        try:
            self.app.ui.log_text.config(state='normal')
            
            # 插入消息
            start_index = self.app.ui.log_text.index(tk.END + "-1c")
            self.app.ui.log_text.insert(tk.END, message)
            end_index = self.app.ui.log_text.index(tk.END + "-1c")
            
            # 应用颜色标签
            if color_tag == "success":
                self.app.ui.log_text.tag_add("success", start_index, end_index)
                self.app.ui.log_text.tag_config("success", foreground="#00AA00")  # 绿色
            elif color_tag == "error":
                self.app.ui.log_text.tag_add("error", start_index, end_index)
                self.app.ui.log_text.tag_config("error", foreground="#FF4444")  # 红色
            elif color_tag == "info":
                self.app.ui.log_text.tag_add("info", start_index, end_index)
                self.app.ui.log_text.tag_config("info", foreground="#0088FF")  # 蓝色
            
            self.app.ui.log_text.see(tk.END)
            self.app.ui.log_text.config(state='disabled')
            
            # 立即刷新显示
            self.app.ui.log_text.update_idletasks()
            
        except Exception as e:
            print(f"[DEBUG] 更新日志显示失败: {str(e)}")
    
    def _show_config_dialog(self):
        """显示配置选项对话框"""
        # 这里可以创建一个更复杂的配置对话框
        # 现在先返回默认配置
        result = messagebox.askyesno(
            "赫拉配置选项",
            "确定要开始赫拉配置吗？\n\n"
            "配置内容包括:\n"
            "• 安装测试APK\n"
            "• 设置日志大小\n"
            "• 仅开启mobile日志\n"
            "• GDPR检查和设置\n"
            "• 检查系统状态\n\n"
            "是否继续？"
        )
        
        if result:
            return {
                'install_apk': True,
                'disable_tcl_logger': True,
                'handle_gdpr': True,
                'run_bugreport': True,
                'simulate_crash': True
            }
        return None
    
    def _install_apk(self):
        """安装APK文件"""
        try:
            # 首先检查APK是否已经安装
            if self._check_apk_installed():
                self._log_message("✅ 测试APK已安装，跳过安装步骤")
                return True
            
            # 尝试从打包的资源中提取APK文件
            apk_file = self._extract_apk_from_resources()
            
            # 如果资源中没有找到，尝试从文件系统查找
            if not apk_file:
                apk_file = self._find_apk_in_filesystem()
            
            # 如果还是没找到，让用户选择
            if not apk_file:
                apk_file = self._ask_user_to_select_apk()
                if not apk_file:
                    self._log_message("❌ 用户取消APK安装 - 必须安装com.example.test.apk")
                    return False
            
            # 安装APK
            self._log_message(f"正在安装APK: {os.path.basename(apk_file)}")
            
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} install -r \"{apk_file}\""
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self._log_message("✅ APK安装成功")
                return True
            else:
                self._log_message(f"❌ APK安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            self._log_message(f"❌ APK安装异常: {str(e)}")
            return False
    
    def _extract_apk_from_resources(self):
        """从打包的资源中提取APK文件"""
        try:
            import sys
            import tempfile
            
            # 检查是否在PyInstaller打包的环境中
            if hasattr(sys, '_MEIPASS'):
                # 在打包环境中，从临时目录查找APK
                resource_dir = sys._MEIPASS
                apk_path = os.path.join(resource_dir, "Heratest-trigger-com.example.test.apk")
                
                if os.path.exists(apk_path):
                    # 将APK复制到临时目录
                    temp_dir = tempfile.gettempdir()
                    temp_apk = os.path.join(temp_dir, "Heratest-trigger-com.example.test.apk")
                    
                    import shutil
                    shutil.copy2(apk_path, temp_apk)
                    self._log_message("✅ 从打包资源中找到APK文件")
                    return temp_apk
            
            return None
            
        except Exception as e:
            self._log_message(f"⚠️ 从资源提取APK失败: {str(e)}")
            return None
    
    def _find_apk_in_filesystem(self):
        """在文件系统中查找APK文件"""
        try:
            # 首先在同级目录查找APK文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            apk_files = []
            
            # 查找常见的APK文件名
            common_names = [
                "Heratest-trigger-com.example.test.apk",
                "hera-test.apk",
                "test-trigger.apk"
            ]
            
            for name in common_names:
                apk_path = os.path.join(current_dir, name)
                if os.path.exists(apk_path):
                    apk_files.append(apk_path)
            
            if apk_files:
                self._log_message("✅ 在文件系统中找到APK文件")
                return apk_files[0]
            
            return None
            
        except Exception as e:
            self._log_message(f"⚠️ 在文件系统中查找APK失败: {str(e)}")
            return None
    
    def _ask_user_to_select_apk(self):
        """让用户选择APK文件"""
        try:
            apk_file = filedialog.askopenfilename(
                title="选择赫拉测试APK文件 (com.example.test.apk)",
                filetypes=[("APK文件", "*.apk"), ("所有文件", "*.*")],
                parent=self.app.root
            )
            
            if apk_file:
                self._log_message("✅ 用户选择了APK文件")
                return apk_file
            
            return None
            
        except Exception as e:
            self._log_message(f"⚠️ 用户选择APK文件失败: {str(e)}")
            return None
    
    def _check_apk_installed(self):
        """检查APK是否已安装"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell pm list packages {self.test_package_name}"
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and self.test_package_name in result.stdout:
                return True
            else:
                return False
                
        except Exception as e:
            self._log_message(f"❌ 检查APK安装状态失败: {str(e)}")
            return False
    
    def _init_uiautomator(self):
        """初始化uiautomator2"""
        try:
            if not HAS_UIAUTOMATOR2:
                self._log_message("❌ uiautomator2未安装，跳过UI自动化操作")
                self._log_message("💡 提示: 请在虚拟环境中运行 'pip install uiautomator2' 安装模块")
                return False
            
            self._log_message("正在初始化uiautomator2...")
            
            # 检查设备连接
            selected_device = self.app.selected_device.get()
            if not self._check_device_connection():
                self._log_message("❌ 设备连接检查失败")
                return False
            
            # 安装uiautomator APK
            if not self._install_uiautomator_apk():
                self._log_message("❌ uiautomator APK安装失败")
                return False
            
            # 确保屏幕开启并解锁
            self._ensure_screen_on_and_unlocked()
            
            # 连接设备（带重试机制）
            self.device = self._connect_device_with_retry(selected_device)
            if not self.device:
                self._log_message("❌ 设备连接失败")
                return False
            
            # 测试连接
            if not self._test_uiautomator_connection():
                self._log_message("❌ uiautomator连接测试失败")
                return False
            
            self._log_message("✅ uiautomator2初始化成功")
            return True
            
        except Exception as e:
            self._log_message(f"❌ uiautomator2初始化失败: {str(e)}")
            return False
    
    def _check_device_connection(self):
        """检查设备连接状态"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell echo test"
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self._log_message(f"❌ 设备连接检查异常: {str(e)}")
            return False
    
    def _connect_device_with_retry(self, device_id, max_retries=3):
        """带重试机制的设备连接"""
        for attempt in range(max_retries):
            try:
                # self._log_message(f"尝试连接设备 (第{attempt + 1}次)...")
                device = u2.connect(device_id)
                
                # 简单测试连接
                device.info
                return device
                
            except Exception as e:
                self._log_message(f"❌ 连接尝试{attempt + 1}失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待2秒后重试
                else:
                    return None
    
    def _test_uiautomator_connection(self):
        """测试uiautomator连接"""
        try:
            if not self.device:
                return False
            
            # 获取设备信息作为连接测试
            device_info = self.device.info
            if device_info and 'displayWidth' in device_info:
                self._log_message(f"✅ 设备信息获取成功: {device_info['displayWidth']}x{device_info['displayHeight']}")
                return True
            else:
                return False
                
        except Exception as e:
            self._log_message(f"❌ uiautomator连接测试异常: {str(e)}")
            return False
    
    def _install_uiautomator_apk(self):
        """安装uiautomator APK"""
        try:
            # 检查是否已安装
            result = run_adb_command(['adb', 'shell', 'pm', 'list', 'packages', 'com.github.uiautomator'], 
                                   capture_output=True, text=True)
            if 'com.github.uiautomator' in result.stdout:
                self._log_message("✅ uiautomator APK已安装")
                return True
            
            self._log_message("正在安装uiautomator APK...")
            
            # 检查APK文件是否存在
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.join(current_dir, 'app-uiautomator.apk')
            test_path = os.path.join(current_dir, 'app-uiautomator-test.apk')
            
            if os.path.exists(app_path) and os.path.exists(test_path):
                run_adb_command(['adb', 'install', '-r', app_path], check=True)
                run_adb_command(['adb', 'install', '-r', test_path], check=True)
                self._log_message("✅ uiautomator APK安装成功")
                return True
            else:
                self._log_message("❌ uiautomator APK文件不存在")
                return False
                
        except Exception as e:
            self._log_message(f"❌ uiautomator APK安装失败: {str(e)}")
            return False
    
    
    def _ensure_screen_on_and_unlocked(self):
        """确保屏幕开启并解锁"""
        try:
            selected_device = self.app.selected_device.get()
            
            # 检查屏幕状态
            # self._log_message("检查屏幕状态...")
            screen_check_cmd = f"adb -s {selected_device} shell dumpsys display"
            result = run_adb_command(screen_check_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                if "mScreenState=OFF" in result.stdout:
                    # 屏幕关闭，需要点亮
                    self._log_message("屏幕关闭，正在点亮...")
                    wake_cmd = f"adb -s {selected_device} shell input keyevent KEYCODE_WAKEUP"
                    run_adb_command(wake_cmd, capture_output=True, text=True, timeout=15)
                    run_adb_command(['adb', 'shell', 'input', 'keyevent', '82'], check=True)
                    
                    # 等待屏幕亮起
                    time.sleep(2)
            else:
                self._log_message(f"❌ 检查屏幕状态失败: {result.stderr}")
            
            # 独立检查锁屏状态（不依赖于屏幕状态）
            # self._log_message("检查锁屏状态...")
            lock_check_cmd = f"adb -s {selected_device} shell dumpsys deviceidle"
            lock_result = run_adb_command(lock_check_cmd, capture_output=True, text=True, timeout=15)
            
            if lock_result.returncode == 0 and "mScreenLocked=true" in lock_result.stdout:
                self._log_message("屏幕锁定，正在解锁...")
                self._unlock_device()
                time.sleep(1)
                
        except Exception as e:
            self._log_message(f"❌ 屏幕状态处理失败: {str(e)}")
    
    def _check_screen_state(self):
        """检查屏幕状态"""
        try:
            result = run_adb_command(['adb', 'shell', 'dumpsys', 'deviceidle'], 
                                   capture_output=True, text=True)
            output = result.stdout
            
            is_screen_on = "mScreenOn=true" in output
            is_locked = "mScreenLocked=true" in output
            
            return is_screen_on, is_locked
            
        except Exception as e:
            self._log_message(f"❌ 检查屏幕状态失败: {str(e)}")
            return False, False
    
    def _wake_up_device(self):
        """唤醒设备"""
        try:
            run_adb_command(['adb', 'shell', 'input', 'keyevent', '26'], check=True)
            time.sleep(1)
        except Exception as e:
            self._log_message(f"❌ 唤醒设备失败: {str(e)}")
    
    def _unlock_device(self):
        """解锁设备"""
        try:
            if not self.device:
                return
            
            # screen_height = self.device.info['displayHeight']
            # screen_width = self.device.info['displayWidth']
            
            # # 从底部向上滑动解锁
            # self.device.swipe(screen_width // 2, screen_height * 2 // 3, 
            #                 screen_width // 2, screen_height // 3)
            
            run_adb_command(['adb', 'shell', 'input', 'keyevent', '82'], check=True)
            run_adb_command(['adb', 'shell', 'input', 'keyevent', '82'], check=True)
            time.sleep(1)
            
            
        except Exception as e:
            self._log_message(f"❌ 解锁设备失败: {str(e)}")
    
    def _set_screen_timeout(self, timeout):
        """设置屏幕超时"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell settings put system screen_off_timeout {timeout}"
            run_adb_command(cmd, check=True)
            
            if timeout == 2147483647:
                self._log_message("✅ 屏幕超时已设置为永不灭屏")
            elif timeout == 60000:
                self._log_message("✅ 屏幕超时已设置为60秒")
            else:
                self._log_message(f"✅ 屏幕超时已设置为{timeout}毫秒")
        except Exception as e:
            self._log_message(f"❌ 设置屏幕超时失败: {str(e)}")
    
    def _disable_tcl_logger(self):
        """禁用TCL logger"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell pm disable-user {self.package_to_disable}"
            run_adb_command(cmd, check=True)
            self._log_message(f"✅ {self.package_to_disable} 已禁用")
        except Exception as e:
            self._log_message(f"❌ 禁用TCL logger失败: {str(e)}")
    
    def _start_logger(self):
        """启动logger"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell am start -n {self.package_name}/{self.activity_name}"
            run_adb_command(cmd, check=True)
            time.sleep(1)
        except Exception as e:
            self._log_message(f"❌ 启动Logger失败: {str(e)}")
    
    def _setup_mobile_log(self):
        """设置MobileLog"""
        try:
            selected_device = self.app.selected_device.get()
            
            # 设置日志大小
            cmd1 = f'adb -s {selected_device} shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name set_log_size_20000 --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver'
            run_adb_command(cmd1, check=True)
            time.sleep(1)
            
            # 启动MobileLog
            cmd2 = f'adb -s {selected_device} shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name start --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver'
            run_adb_command(cmd2, check=True)
            time.sleep(5)
            
            # 点击MobileLog开关 (需要UI自动化)
            if self.device:
                self._check_and_click_mobile_log_toggle()
            else:
                self._log_message("⚠️ 跳过MobileLog开关点击 (需要UI自动化)")
            
            self._log_message("✅ 日志设置完成")
            
        except Exception as e:
            self._log_message(f"❌ 设置MobileLog失败: {str(e)}")
    
    def _check_and_click_mobile_log_toggle(self):
        """检查并点击MobileLog开关"""
        try:
            if not self.device:
                return
            
            # 确保屏幕开启并解锁
            self._ensure_screen_on_and_unlocked()
            
            toggle_button = self.device(resourceId="com.debug.loggerui:id/mobileLogStartStopToggleButton")
            if toggle_button.exists:
                info = toggle_button.info
                if not info.get('checked', False):
                    toggle_button.click()
                    self._log_message("✅ MobileLog日志开关已点击")
                    time.sleep(1)
                else:
                    self._log_message("✅ MobileLog日志已启用")
            else:
                self._log_message("❌ MobileLog开关未找到")
                
        except Exception as e:
            self._log_message(f"❌ 点击MobileLog开关失败: {str(e)}")
    
    def _handle_gdpr_settings(self):
        """处理GDPR设置"""
        try:
            selected_device = self.app.selected_device.get()
            cmd = f"adb -s {selected_device} shell am start -n com.tct.gdpr/.InSettingActivity"
            run_adb_command(cmd, check=True)
            time.sleep(2)
            
            if self.device:
                self._check_and_click_gdpr_checkbox()
            
            # 返回主屏幕
            self._press_home()
            
        except Exception as e:
            self._log_message(f"❌ 处理GDPR设置失败: {str(e)}")
    
    def _check_and_click_gdpr_checkbox(self):
        """检查并点击GDPR复选框"""
        try:
            if not self.device:
                return
            
            # 确保屏幕开启并解锁
            self._ensure_screen_on_and_unlocked()
            
            checkbox = self.device(resourceId="com.tct.gdpr:id/checkBox")
            checkbox2 = self.device(resourceId="com.tct.gdpr:id/checkBoxDX")
            
            if checkbox.exists():
                info = checkbox.info
                if not info.get('checked', False):
                    checkbox.click()
                    self._log_message("✅ GDPR复选框1已点击")
                    time.sleep(1)
                else:
                    self._log_message("✅ GDPR复选框1已选中")
            
            if checkbox2.exists():
                info = checkbox2.info
                if not info.get('checked', False):
                    checkbox2.click()
                    self._log_message("✅ GDPR复选框2已点击")
                    time.sleep(1)
                else:
                    self._log_message("✅ GDPR复选框2已选中")
            
            if not checkbox.exists() and not checkbox2.exists():
                self._log_message("❌ 未找到GDPR复选框")
                
        except Exception as e:
            self._log_message(f"❌ 处理GDPR复选框失败: {str(e)}")
    
    def _check_all_status(self):
        """检查所有状态"""
        failed_items = []
        
        try:
            # 检查heserver
            if not self._check_heserver_running():
                failed_items.append("heserver运行状态")
            
            # 导出feature信息
            self._dump_feature()
            
            # 检查heraeye feature
            if not self._check_heraeye_feature():
                failed_items.append("Heraeye feature")
            
            # 检查UXP状态
            if not self._check_uxp_enable():
                failed_items.append("UXP启用状态")
            
            # 检查在线支持
            if not self._check_online_support():
                failed_items.append("在线支持服务")
            
            return failed_items
            
        except Exception as e:
            self._log_message(f"❌ 检查状态失败: {str(e)}")
            failed_items.append("状态检查")
            return failed_items
    
    def _check_heserver_running(self):
        """检查heserver是否运行"""
        try:
            result = run_adb_command(['adb', 'shell', 'ps', '-A'], capture_output=True, text=True)
            if 'heserver' in result.stdout:
                self._log_message("✅ heserver正在运行")
                return True
            else:
                self._log_message("❌ heserver未运行")
                return False
        except Exception as e:
            self._log_message(f"❌ 检查heserver失败: {str(e)}")
            return False
    
    def _dump_feature(self):
        """导出feature信息"""
        try:
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'dumpfeature.txt')
            run_adb_command(['adb', 'shell', 'dumpsys', 'feature'], 
                          stdout=open(output_file, 'w'), check=True)
            self._log_message(f"✅ Feature信息已导出到: {output_file}")
        except Exception as e:
            self._log_message(f"❌ 导出Feature信息失败: {str(e)}")
    
    def _check_heraeye_feature(self):
        """检查heraeye feature状态"""
        try:
            result = run_adb_command(['adb', 'shell', 'feature', 'query', 'heraeye'], 
                                   capture_output=True, text=True)
            if '{"name":"enable","value":"true"}' in result.stdout:
                self._log_message("✅ Heraeye feature已启用")
                return True
            else:
                self._log_message("❌ Heraeye feature未启用")
                return False
        except Exception as e:
            self._log_message(f"❌ 检查Heraeye feature失败: {str(e)}")
            return False
    
    def _check_uxp_enable(self):
        """检查UXP启用状态"""
        try:
            result = run_adb_command(['adb', 'shell', 'getprop', 'ro.product.uxp.enable'], 
                                   capture_output=True, text=True)
            if result.stdout.strip().lower() == 'true':
                self._log_message("✅ UXP已启用")
                return True
            else:
                self._log_message("❌ UXP未启用")
                return False
        except Exception as e:
            self._log_message(f"❌ 检查UXP状态失败: {str(e)}")
            return False
    
    def _check_online_support(self):
        """检查在线支持服务状态"""
        try:
            # 导出服务信息
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport1.txt')
            run_adb_command(['adb', 'shell', 'dumpsys', 'activity', 'service', 'Onlinesupport'], 
                          stdout=open(output_file, 'w'), check=True)
            
            # 检查注册状态
            # result = run_adb_command(['adb', 'shell', 'dumpsys', 'activity', 'service', 'Onlinesupport'], 
            #                        capture_output=True, text=True)
            
            # # 检查Device和Register状态
            # device_status = 'Device:true' in result.stdout
            # register_status = 'Register: true' in result.stdout
            
            # if device_status and register_status:
            #     self._log_message("✅ 在线支持已注册 (Device:true, Register:true)")
            #     return True
            # else:
            #     # 详细显示失败原因
            #     if not device_status and not register_status:
            #         self._log_message("❌ 在线支持未注册 (Device:false, Register:false)")
            #     elif not device_status:
            #         self._log_message("❌ 在线支持未注册 (Device:false)")
            #     elif not register_status:
            #         self._log_message("❌ 在线支持未注册 (Register:false)")
            #     return False
                    # 检查注册状态
            result = run_adb_command(['adb', 'shell', 'dumpsys', 'activity', 'service', 'Onlinesupport'], 
                                   capture_output=True, text=True)
            
            # 检查Device和Register状态
            register_status = 'Register: true' in result.stdout
            
            if register_status:
                self._log_message("✅ 在线支持已注册")
                return True
            else:
                # 详细显示失败原因
                if not register_status:
                    self._log_message("❌ 在线支持未注册")
                return False
        except Exception as e:
            self._log_message(f"❌ 检查在线支持失败: {str(e)}")
            return False
    
    def _run_bugreport(self):
        """运行bugreport"""
        try:
            self._log_message("正在收集bugreport...")
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, f'bugreport_{timestamp}.txt')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                result = run_adb_command(['adb', 'bugreport'], 
                                       stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                self._log_message(f"✅ bugreport收集完成，保存到: {output_file}")
                return True
            else:
                self._log_message(f"❌ bugreport收集失败: {result.stderr}")
                return False
        except Exception as e:
            self._log_message(f"❌ 运行bugreport失败: {str(e)}")
            return False
    
    def _simulate_app_crash(self):
        """模拟应用崩溃 - 执行10次，每次间隔305秒"""
        try:
            if not self.device:
                self._log_message("❌ 设备未连接，无法模拟崩溃")
                return False
            
            self._log_message("开始模拟应用崩溃 (10次，每次间隔305秒)...")
            
            success_count = 0
            for i in range(10):
                self._log_message(f"执行第{i+1}次崩溃模拟...")
                
                # 确保屏幕开启并解锁
                self._ensure_screen_on_and_unlocked()
                
                # 启动测试应用
                selected_device = self.app.selected_device.get()
                cmd = f"adb -s {selected_device} shell am start -n com.example.test/.MainActivity"
                run_adb_command(cmd, check=True)
                time.sleep(2)
                
                # 再次确保屏幕状态（点击前检查）
                self._ensure_screen_on_and_unlocked()
                
                # 查找并点击崩溃按钮
                crash_button = self.device(resourceId="com.example.test:id/crash_button")
                if crash_button.exists:
                    crash_button.click()
                    self._log_message(f"✅ 第{i+1}次崩溃按钮已点击")
                    time.sleep(3)
                    
                    # 检查崩溃日志
                    result = run_adb_command(['adb', 'logcat', '-b', 'crash', '-d'], 
                                           capture_output=True, text=True)
                    if "Simulated Crash" in result.stdout:
                        self._log_message(f"✅ 第{i+1}次崩溃日志验证成功")
                        success_count += 1
                    else:
                        self._log_message(f"❌ 第{i+1}次崩溃日志验证失败")
                else:
                    self._log_message(f"❌ 第{i+1}次崩溃按钮未找到")
                
                # 如果不是最后一次，等待305秒
                if i < 9:
                    self._log_message(f"等待305秒后进行下一次崩溃模拟...")
                    time.sleep(305)
            
            self._log_message(f"✅ 崩溃模拟完成，成功次数: {success_count}/10")
            return success_count > 0
            
        except Exception as e:
            self._log_message(f"❌ 模拟应用崩溃失败: {str(e)}")
            return False
    
    def configure_collect_data(self):
        """赫拉测试数据收集"""
        try:
            # 检查设备连接
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 在后台线程中执行数据收集
            import threading
            thread = threading.Thread(target=self._run_ua_data_collection, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"赫拉测试数据收集启动失败: {str(e)}"
            self._log_message(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            return False
    
    def _run_ua_data_collection(self):
        """在后台线程中运行UA数据收集"""
        try:
            # 开始数据收集流程
            self._log_message("开始赫拉测试数据收集...")
            time.sleep(0.5)  # 给UI时间更新
            
            # 1. 导出Onlinesupport信息
            if not self._export_onlinesupport_data():
                self._log_message("❌ 导出Onlinesupport数据失败")
                self.app.root.after(0, lambda: messagebox.showerror("数据收集失败", "导出Onlinesupport数据失败"))
                return
            
            # 2. 分析数据
            analysis_result = self._analyze_onlinesupport_data()
            
            # 3. 显示结果
            self.app.root.after(0, lambda: self._show_ua_analysis_result(analysis_result))
            
        except Exception as e:
            error_msg = f"赫拉测试数据收集失败: {str(e)}"
            self._log_message(f"❌ {error_msg}")
            self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def _export_onlinesupport_data(self):
        """导出Onlinesupport数据"""
        try:
            selected_device = self.app.selected_device.get()
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport2.txt')
            
            self._log_message("正在导出Onlinesupport数据...")
            
            # 执行命令
            cmd = f"adb -s {selected_device} shell dumpsys activity service Onlinesupport"
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # 保存到文件
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                self._log_message(f"✅ Onlinesupport数据已导出到: {output_file}")
                return True
            else:
                self._log_message(f"❌ 导出Onlinesupport数据失败: {result.stderr}")
                return False
                
        except Exception as e:
            self._log_message(f"❌ 导出Onlinesupport数据异常: {str(e)}")
            return False
    
    def _analyze_onlinesupport_data(self):
        """分析Onlinesupport数据"""
        try:
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport2.txt')
            
            if not os.path.exists(output_file):
                return {"status": "error", "message": "数据文件不存在"}
            
            self._log_message("正在分析Onlinesupport数据...")
            
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找LOG部分
            log_section = self._extract_log_section(content)
            
            if not log_section:
                return {"status": "error", "message": "未找到LOG部分"}
            
            # 分析LOG内容
            if "Empty" in log_section:
                return {"status": "fail", "message": "LOG部分为空(Empty)"}
            
            # 检查是否有crash类型的日志
            if "type='crash'" in log_section:
                return {"status": "success", "message": "发现crash类型日志", "has_crash": True}
            else:
                return {"status": "fail", "message": "LOG中有日志但无crash类型", "has_crash": False}
                
        except Exception as e:
            return {"status": "error", "message": f"分析数据异常: {str(e)}"}
    
    def _extract_log_section(self, content):
        """提取LOG部分内容"""
        try:
            lines = content.split('\n')
            log_started = False
            log_lines = []
            
            for line in lines:
                if "LOG:" in line:
                    log_started = True
                    log_lines.append(line)
                    continue
                
                if log_started:
                    # 如果遇到下一个主要部分，停止收集
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t') and ':' in line:
                        break
                    log_lines.append(line)
            
            return '\n'.join(log_lines)
            
        except Exception as e:
            self._log_message(f"❌ 提取LOG部分失败: {str(e)}")
            return None
    
    def _show_ua_analysis_result(self, result):
        """显示UA分析结果"""
        try:
            if result["status"] == "success":
                # 成功情况 - 发现crash日志
                self._log_message("✅ 赫拉测试数据收集完成")
                self._log_message("✅ 发现crash类型日志")
                
                message = ("赫拉测试数据收集完成！\n\n"
                          "✅ 发现crash类型日志\n\n"
                          "请隔天在以下网站查询设备信息：\n"
                          "https://tmna.tclking.com/")
                
                messagebox.showinfo("数据收集成功", message)
                
            elif result["status"] == "fail":
                # 失败情况 - 显示红色高亮信息
                fail_message = f"❌ {result['message']}"
                self._log_message(fail_message)
                
                # 在日志区域显示红色高亮的失败信息
                self._display_fail_message(fail_message)
                
                messagebox.showerror("数据收集失败", f"赫拉测试数据收集失败！\n\n{result['message']}")
                
            else:
                # 错误情况
                error_message = f"❌ {result['message']}"
                self._log_message(error_message)
                messagebox.showerror("数据收集错误", f"赫拉测试数据收集出错！\n\n{result['message']}")
                
        except Exception as e:
            self._log_message(f"❌ 显示分析结果失败: {str(e)}")
    
    def _display_fail_message(self, message):
        """在日志区域显示红色高亮的失败信息"""
        try:
            self.app.ui.log_text.config(state='normal')
            
            # 添加空行分隔
            self.app.ui.log_text.insert(tk.END, "\n")
            
            # 记录插入位置
            start_index = self.app.ui.log_text.index(tk.END + "-1c")
            self.app.ui.log_text.insert(tk.END, message + "\n")
            end_index = self.app.ui.log_text.index(tk.END + "-1c")
            
            # 应用红色字体
            self.app.ui.log_text.tag_add("fail_highlight", start_index, end_index)
            self.app.ui.log_text.tag_config("fail_highlight", foreground="#FF4444")  # 红色
            
            self.app.ui.log_text.see(tk.END)
            self.app.ui.log_text.config(state='disabled')
            
            # 立即刷新显示
            self.app.ui.log_text.update_idletasks()
            
        except Exception as e:
            print(f"[DEBUG] 显示失败信息失败: {str(e)}")
    
    def _press_home(self):
        """按HOME键返回主屏幕"""
        try:
            run_adb_command(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_HOME'], check=True)
            time.sleep(1)
            self._log_message("✅ 已返回主屏幕")
        except Exception as e:
            self._log_message(f"❌ 返回主屏幕失败: {str(e)}")
    
    def _show_completion_tips(self):
        """显示完成后的操作提示"""
        try:
            # 使用after(0)确保在主线程中执行
            self.app.root.after(0, lambda: self._display_completion_tips())
        except Exception as e:
            print(f"[DEBUG] 显示完成提示失败: {str(e)}")
    
    def _display_completion_tips(self):
        """在日志区域显示完成提示"""
        try:
            self.app.ui.log_text.config(state='normal')
            
            # 添加空行分隔
            self.app.ui.log_text.insert(tk.END, "\n")
            
            # 添加提示标题
            title_message = "=" * 60 + "\n"
            self.app.ui.log_text.insert(tk.END, title_message)
            
            # 添加主要提示内容
            tips_message = """Hera测试前置操作完成，

1. 保持SIM卡在手机中，WIFI一直处于连接状态，插上充电器等待超过25H。
2. 25小时后点亮手机屏幕连接电脑，使用该工具"赫拉测试数据收集"按钮。

"""
            
            # 记录插入位置
            start_index = self.app.ui.log_text.index(tk.END + "-1c")
            self.app.ui.log_text.insert(tk.END, tips_message)
            end_index = self.app.ui.log_text.index(tk.END + "-1c")
            
            # 应用黄色字体
            self.app.ui.log_text.tag_add("completion_tips", start_index, end_index)
            self.app.ui.log_text.tag_config("completion_tips", foreground="#FFA500")  # 橙色/黄色
            
            # 添加结束分隔线
            self.app.ui.log_text.insert(tk.END, "=" * 60 + "\n")
            
            self.app.ui.log_text.see(tk.END)
            self.app.ui.log_text.config(state='disabled')
            
            # 立即刷新显示
            self.app.ui.log_text.update_idletasks()
            
        except Exception as e:
            print(f"[DEBUG] 显示完成提示内容失败: {str(e)}")
