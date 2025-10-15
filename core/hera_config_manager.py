#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5赫拉配置管理器
独立实现，不依赖Tkinter
"""

import os
import time
import subprocess
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox

# 可选依赖
try:
    import uiautomator2 as u2
    HAS_UIAUTOMATOR2 = True
except ImportError:
    u2 = None
    HAS_UIAUTOMATOR2 = False


def run_adb_command(cmd, **kwargs):
    """运行ADB命令，隐藏控制台窗口"""
    if isinstance(cmd, str):
        kwargs.setdefault('shell', True)
    else:
        kwargs.setdefault('shell', False)
    
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    
    # 设置默认编码以避免 UnicodeDecodeError
    kwargs.setdefault('encoding', 'utf-8')
    kwargs.setdefault('errors', 'replace')
    
    return subprocess.run(cmd, **kwargs)


class HeraConfigWorker(QThread):
    """赫拉配置工作线程"""
    
    progress = pyqtSignal(str)  # 进度信息
    finished = pyqtSignal(bool, str)  # 完成信号
    
    def __init__(self, device, config_options, parent=None):
        super().__init__(parent)
        self.device = device
        self.config_options = config_options
        self.failed_items = []
        self.output_dir = None
        self.d = None  # uiautomator2设备对象
        self.test_package_name = "com.example.test"
        
    def run(self):
        """执行配置流程"""
        try:
            self.progress.emit("开始赫拉配置流程...")
            time.sleep(0.5)
            
            # 1. 安装APK
            if self.config_options.get('install_apk', True):
                if not self._install_apk():
                    self.progress.emit("❌ 赫拉配置终止：必须安装com.example.test.apk")
                    self.finished.emit(False, "必须安装com.example.test.apk才能继续配置")
                    return
                time.sleep(0.5)
            
            # 2. 初始化uiautomator2
            uiautomator_available = self._init_uiautomator()
            if not uiautomator_available:
                self.progress.emit("⚠️ 跳过需要UI自动化的步骤")
            time.sleep(0.5)
            
            # 3. 设置屏幕常亮
            self._set_screen_timeout(2147483647)
            time.sleep(0.5)
            
            # 4. 禁用TCL用户支持
            if self.config_options.get('disable_tcl_logger', False):
                self._disable_tcl_logger()
                time.sleep(0.5)
            
            # 5. 启动logger
            self._start_logger()
            time.sleep(0.5)
            
            # 6. 设置手机日志
            self._setup_mobile_log()
            time.sleep(0.5)
            
            # 7. 处理GDPR设置
            if self.config_options.get('handle_gdpr', True):
                if uiautomator_available:
                    self._handle_gdpr_settings()
                else:
                    self.progress.emit("⚠️ 跳过GDPR设置 (需要UI自动化)")
                time.sleep(0.5)
            
            # 8. 检查各种状态
            status_results = self._check_all_status()
            self.failed_items.extend(status_results)
            time.sleep(0.5)
            
            # 9. 运行bugreport
            if self.config_options.get('run_bugreport', False):
                if not self._run_bugreport():
                    self.failed_items.append("bugreport收集")
            
            # 10. 模拟应用崩溃
            if self.config_options.get('simulate_crash', False):
                if not self._simulate_app_crash():
                    self.failed_items.append("应用崩溃模拟")
            
            # 根据失败项目决定最终结果
            if self.failed_items:
                self.progress.emit("赫拉配置终止！")
                failure_reasons = "、".join(self.failed_items)
                self.finished.emit(False, f"失败项目:\n{failure_reasons}")
            else:
                self.progress.emit("赫拉配置完成！")
                self._set_screen_timeout(60000)
                self._show_completion_tips()
                self.finished.emit(True, "赫拉配置完成！")
                
        except Exception as e:
            self.progress.emit(f"❌ 赫拉配置失败: {str(e)}")
            self.finished.emit(False, f"配置失败: {str(e)}")
    
    def _ensure_output_directory(self):
        """确保输出目录存在"""
        if self.output_dir is None:
            try:
                today = datetime.now().strftime("%Y%m%d")
                self.output_dir = f"C:\\log\\{today}\\hera"
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                self.progress.emit(f"⚠️ 创建输出目录失败: {str(e)}")
                self.output_dir = "."
        return self.output_dir
    
    def _install_apk(self):
        """安装测试APK"""
        try:
            # 检查APK是否已安装
            if self._check_apk_installed():
                self.progress.emit("✅ 测试APK已安装，跳过安装步骤")
                return True
            
            # 查找APK文件
            apk_file = self._find_apk_file()
            if not apk_file:
                self.progress.emit("❌ 找不到APK文件")
                return False
            
            self.progress.emit(f"正在安装APK: {os.path.basename(apk_file)}")
            result = run_adb_command(["adb", "-s", self.device, "install", "-r", apk_file], 
                                   capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.progress.emit("✅ APK安装成功")
                return True
            else:
                self.progress.emit(f"❌ APK安装失败: {result.stderr}")
                return False
        except Exception as e:
            self.progress.emit(f"❌ APK安装异常: {str(e)}")
            return False
    
    def _check_apk_installed(self):
        """检查APK是否已安装"""
        try:
            result = run_adb_command(["adb", "-s", self.device, "shell", "pm", "list", "packages", self.test_package_name], 
                                   capture_output=True, text=True, timeout=10)
            return self.test_package_name in result.stdout
        except Exception as e:
            self.progress.emit(f"❌ 检查APK安装状态失败: {str(e)}")
            return False
    
    def _find_apk_file(self):
        """查找APK文件"""
        try:
            # 在同级目录查找
            current_dir = os.path.dirname(os.path.abspath(__file__))
            apk_path = os.path.join(current_dir, "..", "resources", "apk", "Heratest-trigger-com.example.test.apk")
            apk_path = os.path.abspath(apk_path)
            
            if os.path.exists(apk_path):
                return apk_path
            
            # 尝试其他常见名称
            for name in ["hera-test.apk", "test-trigger.apk"]:
                test_path = os.path.join(os.path.dirname(current_dir), "resources", "apk", name)
                if os.path.exists(test_path):
                    return test_path
            
            return None
        except Exception as e:
            self.progress.emit(f"⚠️ 查找APK文件失败: {str(e)}")
            return None
    
    def _init_uiautomator(self):
        """初始化uiautomator2"""
        try:
            if not HAS_UIAUTOMATOR2:
                self.progress.emit("❌ uiautomator2未安装，跳过UI自动化操作")
                return False
            
            self.progress.emit("正在初始化uiautomator2...")
            
            # 安装uiautomator APK
            if not self._install_uiautomator_apk():
                self.progress.emit("❌ uiautomator APK安装失败")
                return False
            
            # 确保屏幕开启并解锁
            self._ensure_screen_on_and_unlocked()
            
            # 连接设备
            self.d = self._connect_device_with_retry(self.device)
            if not self.d:
                self.progress.emit("❌ 设备连接失败")
                return False
            
            # 测试连接
            if not self._test_uiautomator_connection():
                self.progress.emit("❌ uiautomator连接测试失败")
                return False
            
            self.progress.emit("✅ uiautomator2初始化成功")
            return True
        except Exception as e:
            self.progress.emit(f"❌ uiautomator2初始化失败: {str(e)}")
            return False
    
    def _install_uiautomator_apk(self):
        """安装uiautomator APK"""
        try:
            # 检查是否已安装
            result = run_adb_command(['adb', 'shell', 'pm', 'list', 'packages', 'com.github.uiautomator'], 
                                   capture_output=True, text=True)
            if 'com.github.uiautomator' in result.stdout:
                self.progress.emit("✅ uiautomator APK已安装")
                return True
            
            self.progress.emit("正在安装uiautomator APK...")
            
            # 查找APK文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.join(current_dir, "..", "resources", "apk", 'app-uiautomator.apk')
            test_path = os.path.join(current_dir, "..", "resources", "apk", 'app-uiautomator-test.apk')
            
            if os.path.exists(app_path) and os.path.exists(test_path):
                run_adb_command(['adb', 'install', '-r', app_path], check=True)
                run_adb_command(['adb', 'install', '-r', test_path], check=True)
                self.progress.emit("✅ uiautomator APK安装成功")
                return True
            else:
                self.progress.emit("❌ uiautomator APK文件不存在")
                return False
        except Exception as e:
            self.progress.emit(f"❌ uiautomator APK安装失败: {str(e)}")
            return False
    
    def _ensure_screen_on_and_unlocked(self):
        """确保屏幕开启并解锁"""
        try:
            # 检查屏幕状态
            screen_check_cmd = f"adb -s {self.device} shell dumpsys display"
            result = run_adb_command(screen_check_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                if "mScreenState=OFF" in result.stdout:
                    # 屏幕关闭，点亮
                    self.progress.emit("屏幕关闭，正在点亮...")
                    wake_cmd = f"adb -s {self.device} shell input keyevent KEYCODE_WAKEUP"
                    run_adb_command(wake_cmd, capture_output=True, text=True, timeout=15)
                    time.sleep(2)
            
            # 检查锁屏状态
            lock_check_cmd = f"adb -s {self.device} shell dumpsys deviceidle"
            lock_result = run_adb_command(lock_check_cmd, capture_output=True, text=True, timeout=15)
            
            if lock_result.returncode == 0 and "mScreenLocked=true" in lock_result.stdout:
                self.progress.emit("屏幕锁定，正在解锁...")
                self._unlock_device()
                time.sleep(1)
        except Exception as e:
            self.progress.emit(f"❌ 屏幕状态处理失败: {str(e)}")
    
    def _unlock_device(self):
        """解锁设备"""
        try:
            run_adb_command(['adb', 'shell', 'input', 'keyevent', '82'], check=True)
            run_adb_command(['adb', 'shell', 'input', 'keyevent', '82'], check=True)
            time.sleep(1)
        except Exception as e:
            self.progress.emit(f"❌ 解锁设备失败: {str(e)}")
    
    def _connect_device_with_retry(self, device_id, max_retries=3):
        """带重试机制的设备连接"""
        for attempt in range(max_retries):
            try:
                device = u2.connect(device_id)
                device.info
                return device
            except Exception as e:
                self.progress.emit(f"❌ 连接尝试{attempt + 1}失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return None
    
    def _test_uiautomator_connection(self):
        """测试uiautomator连接"""
        try:
            if not self.d:
                return False
            
            device_info = self.d.info
            if device_info and 'displayWidth' in device_info:
                self.progress.emit(f"✅ 设备信息获取成功: {device_info['displayWidth']}x{device_info['displayHeight']}")
                return True
            return False
        except Exception as e:
            self.progress.emit(f"❌ uiautomator连接测试异常: {str(e)}")
            return False
    
    def _set_screen_timeout(self, timeout):
        """设置屏幕超时"""
        try:
            run_adb_command(["adb", "-s", self.device, "shell", "settings", "put", "system", "screen_off_timeout", str(timeout)])
            if timeout == 2147483647:
                self.progress.emit("✅ 屏幕超时已设置为永不灭屏")
            elif timeout == 60000:
                self.progress.emit("✅ 屏幕超时已设置为60秒")
            else:
                self.progress.emit(f"✅ 屏幕超时已设置为{timeout}毫秒")
        except Exception as e:
            self.progress.emit(f"❌ 设置屏幕超时失败: {str(e)}")
    
    def _disable_tcl_logger(self):
        """禁用TCL logger"""
        try:
            run_adb_command(["adb", "-s", self.device, "shell", "pm", "disable-user", "com.tcl.logger"], check=True)
            self.progress.emit("✅ com.tcl.logger 已禁用")
        except Exception as e:
            self.progress.emit(f"❌ 禁用TCL logger失败: {str(e)}")
    
    def _start_logger(self):
        """启动logger"""
        try:
            run_adb_command(["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"], check=True)
            time.sleep(1)
        except Exception as e:
            self.progress.emit(f"❌ 启动Logger失败: {str(e)}")
    
    def _setup_mobile_log(self):
        """设置MobileLog"""
        try:
            # 设置日志大小
            cmd1 = f'adb -s {self.device} shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name set_log_size_20000 --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver'
            run_adb_command(cmd1, check=True)
            time.sleep(1)
            
            # 启动MobileLog
            cmd2 = f'adb -s {self.device} shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name start --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver'
            run_adb_command(cmd2, check=True)
            time.sleep(5)
            
            # 点击MobileLog开关
            if self.d:
                self._check_and_click_mobile_log_toggle()
            else:
                self.progress.emit("⚠️ 跳过MobileLog开关点击 (需要UI自动化)")
            
            self.progress.emit("✅ 日志设置完成")
        except Exception as e:
            self.progress.emit(f"❌ 设置MobileLog失败: {str(e)}")
    
    def _check_and_click_mobile_log_toggle(self):
        """检查并点击MobileLog开关"""
        try:
            if not self.d:
                return
            
            self._ensure_screen_on_and_unlocked()
            
            toggle_button = self.d(resourceId="com.debug.loggerui:id/mobileLogStartStopToggleButton")
            if toggle_button.exists:
                info = toggle_button.info
                if not info.get('checked', False):
                    toggle_button.click()
                    self.progress.emit("✅ MobileLog日志开关已点击")
                    time.sleep(1)
                else:
                    self.progress.emit("✅ MobileLog日志已启用")
            else:
                self.progress.emit("❌ MobileLog开关未找到")
        except Exception as e:
            self.progress.emit(f"❌ 点击MobileLog开关失败: {str(e)}")
    
    def _handle_gdpr_settings(self):
        """处理GDPR设置"""
        try:
            run_adb_command(["adb", "-s", self.device, "shell", "am", "start", "-n", "com.tct.gdpr/.InSettingActivity"], check=True)
            time.sleep(2)
            
            if self.d:
                self._check_and_click_gdpr_checkbox()
            
            # 返回主屏幕
            self._press_home()
        except Exception as e:
            self.progress.emit(f"❌ 处理GDPR设置失败: {str(e)}")
    
    def _check_and_click_gdpr_checkbox(self):
        """检查并点击GDPR复选框"""
        try:
            if not self.d:
                return
            
            self._ensure_screen_on_and_unlocked()
            
            checkbox = self.d(resourceId="com.tct.gdpr:id/checkBox")
            checkbox2 = self.d(resourceId="com.tct.gdpr:id/checkBoxDX")
            
            if checkbox.exists():
                info = checkbox.info
                if not info.get('checked', False):
                    checkbox.click()
                    self.progress.emit("✅ GDPR复选框1已点击")
                    time.sleep(1)
                else:
                    self.progress.emit("✅ GDPR复选框1已选中")
            
            if checkbox2.exists():
                info = checkbox2.info
                if not info.get('checked', False):
                    checkbox2.click()
                    self.progress.emit("✅ GDPR复选框2已点击")
                    time.sleep(1)
                else:
                    self.progress.emit("✅ GDPR复选框2已选中")
            
            if not checkbox.exists() and not checkbox2.exists():
                self.progress.emit("❌ 未找到GDPR复选框")
        except Exception as e:
            self.progress.emit(f"❌ 处理GDPR复选框失败: {str(e)}")
    
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
            self.progress.emit(f"❌ 检查状态失败: {str(e)}")
            failed_items.append("状态检查")
            return failed_items
    
    def _check_heserver_running(self):
        """检查heserver是否运行"""
        try:
            result = run_adb_command(['adb', 'shell', 'ps', '-A'], capture_output=True, text=True)
            if 'heserver' in result.stdout:
                self.progress.emit("✅ heserver正在运行")
                return True
            else:
                self.progress.emit("❌ heserver未运行")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 检查heserver失败: {str(e)}")
            return False
    
    def _dump_feature(self):
        """导出feature信息"""
        try:
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'dumpfeature.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                run_adb_command(['adb', 'shell', 'dumpsys', 'feature'], stdout=f, check=True)
            self.progress.emit(f"✅ Feature信息已导出到: {output_file}")
        except Exception as e:
            self.progress.emit(f"❌ 导出Feature信息失败: {str(e)}")
    
    def _check_heraeye_feature(self):
        """检查heraeye feature状态"""
        try:
            result = run_adb_command(['adb', 'shell', 'feature', 'query', 'heraeye'], 
                                   capture_output=True, text=True)
            if '{"name":"enable","value":"true"}' in result.stdout:
                self.progress.emit("✅ Heraeye feature已启用")
                return True
            else:
                self.progress.emit("❌ Heraeye feature未启用")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 检查Heraeye feature失败: {str(e)}")
            return False
    
    def _check_uxp_enable(self):
        """检查UXP启用状态"""
        try:
            result = run_adb_command(['adb', 'shell', 'getprop', 'ro.product.uxp.enable'], 
                                   capture_output=True, text=True)
            if result.stdout.strip().lower() == 'true':
                self.progress.emit("✅ UXP已启用")
                return True
            else:
                self.progress.emit("❌ UXP未启用")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 检查UXP状态失败: {str(e)}")
            return False
    
    def _check_online_support(self):
        """检查在线支持服务状态"""
        try:
            # 导出服务信息
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport1.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                run_adb_command(['adb', 'shell', 'dumpsys', 'activity', 'service', 'Onlinesupport'], stdout=f, check=True)
            
            # 检查注册状态
            result = run_adb_command(['adb', 'shell', 'dumpsys', 'activity', 'service', 'Onlinesupport'], 
                                   capture_output=True, text=True)
            
            register_status = 'Register: true' in result.stdout
            
            if register_status:
                self.progress.emit("✅ 在线支持已注册")
                return True
            else:
                self.progress.emit("❌ 在线支持未注册")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 检查在线支持失败: {str(e)}")
            return False
    
    def _run_bugreport(self):
        """运行bugreport"""
        try:
            self.progress.emit("正在收集bugreport...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, f'bugreport_{timestamp}.txt')
            
            cmd = f"adb -s {self.device} bugreport \"{output_file}\""
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.progress.emit(f"✅ bugreport收集完成，保存到: {output_file}")
                return True
            else:
                self.progress.emit(f"❌ bugreport收集失败: {result.stderr}")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 运行bugreport失败: {str(e)}")
            return False
    
    def _simulate_app_crash(self):
        """模拟应用崩溃"""
        try:
            if not self.d:
                self.progress.emit("❌ 设备未连接，无法模拟崩溃")
                return False
            
            self.progress.emit("开始模拟应用崩溃 (10次，每次间隔305秒)...")
            
            success_count = 0
            for i in range(10):
                self.progress.emit(f"执行第{i+1}次崩溃模拟...")
                
                self._ensure_screen_on_and_unlocked()
                
                # 启动测试应用
                run_adb_command(["adb", "-s", self.device, "shell", "am", "start", "-n", "com.example.test/.MainActivity"], check=True)
                time.sleep(2)
                
                self._ensure_screen_on_and_unlocked()
                
                # 查找并点击崩溃按钮
                crash_button = self.d(resourceId="com.example.test:id/crash_button")
                if crash_button.exists:
                    crash_button.click()
                    self.progress.emit(f"✅ 第{i+1}次崩溃按钮已点击")
                    time.sleep(3)
                    
                    # 检查崩溃日志
                    result = run_adb_command(['adb', 'logcat', '-b', 'crash', '-d'], 
                                           capture_output=True, text=True)
                    if "Simulated Crash" in result.stdout:
                        self.progress.emit(f"✅ 第{i+1}次崩溃日志验证成功")
                        success_count += 1
                    else:
                        self.progress.emit(f"❌ 第{i+1}次崩溃日志验证失败")
                else:
                    self.progress.emit(f"❌ 第{i+1}次崩溃按钮未找到")
                
                # 如果不是最后一次，等待305秒
                if i < 9:
                    self.progress.emit(f"等待305秒后进行下一次崩溃模拟...")
                    time.sleep(305)
            
            self.progress.emit(f"✅ 崩溃模拟完成，成功次数: {success_count}/10")
            return success_count > 0
        except Exception as e:
            self.progress.emit(f"❌ 模拟应用崩溃失败: {str(e)}")
            return False
    
    def _press_home(self):
        """按HOME键返回主屏幕"""
        try:
            run_adb_command(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_HOME'], check=True)
            time.sleep(1)
            self.progress.emit("✅ 已返回主屏幕")
        except Exception as e:
            self.progress.emit(f"❌ 返回主屏幕失败: {str(e)}")
    
    def _show_completion_tips(self):
        """显示完成后的操作提示"""
        tips = """Hera测试前置操作完成，

1. 保持SIM卡在手机中，WIFI一直处于连接状态，插上充电器等待超过25H。
2. 25小时后点亮手机屏幕连接电脑，使用该工具"赫拉测试数据收集"按钮。
"""
        self.progress.emit("=" * 60)
        self.progress.emit(tips)
        self.progress.emit("=" * 60)


class HeraDataCollectionWorker(QThread):
    """赫拉测试数据收集工作线程"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.output_dir = None
        
    def run(self):
        """执行数据收集流程"""
        try:
            self.progress.emit("开始赫拉测试数据收集...")
            time.sleep(0.5)
            
            # 导出Onlinesupport数据
            if not self._export_onlinesupport_data():
                self.progress.emit("❌ 导出Onlinesupport数据失败")
                self.finished.emit(False, "导出Onlinesupport数据失败")
                return
            
            # 分析数据
            analysis_result = self._analyze_onlinesupport_data()
            
            # 显示结果
            if analysis_result["status"] == "success":
                self.progress.emit("✅ 赫拉测试数据收集完成")
                self.progress.emit("✅ 发现crash类型日志")
                message = ("赫拉测试数据收集完成！\n\n"
                          "✅ 发现crash类型日志\n\n"
                          "请隔天在以下网站查询设备信息：\n"
                          "https://tmna.tclking.com/")
                self.finished.emit(True, message)
            else:
                self.progress.emit(f"❌ {analysis_result['message']}")
                self.finished.emit(False, f"赫拉测试数据收集失败！\n\n{analysis_result['message']}")
                
        except Exception as e:
            self.progress.emit(f"❌ 赫拉测试数据收集失败: {str(e)}")
            self.finished.emit(False, f"数据收集失败: {str(e)}")
    
    def _ensure_output_directory(self):
        """确保输出目录存在"""
        if self.output_dir is None:
            try:
                today = datetime.now().strftime("%Y%m%d")
                self.output_dir = f"C:\\log\\{today}\\hera"
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                self.output_dir = "."
        return self.output_dir
    
    def _export_onlinesupport_data(self):
        """导出Onlinesupport数据"""
        try:
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport2.txt')
            
            self.progress.emit("正在导出Onlinesupport数据...")
            
            cmd = f"adb -s {self.device} shell dumpsys activity service Onlinesupport"
            result = run_adb_command(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                self.progress.emit(f"✅ Onlinesupport数据已导出到: {output_file}")
                return True
            else:
                self.progress.emit(f"❌ 导出Onlinesupport数据失败: {result.stderr}")
                return False
        except Exception as e:
            self.progress.emit(f"❌ 导出Onlinesupport数据异常: {str(e)}")
            return False
    
    def _analyze_onlinesupport_data(self):
        """分析Onlinesupport数据"""
        try:
            output_dir = self._ensure_output_directory()
            output_file = os.path.join(output_dir, 'onlinesupport2.txt')
            
            if not os.path.exists(output_file):
                return {"status": "error", "message": "数据文件不存在"}
            
            self.progress.emit("正在分析Onlinesupport数据...")
            
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找LOG部分
            log_section = self._extract_log_section(content)
            
            if not log_section:
                return {"status": "error", "message": "未找到LOG部分"}
            
            # 分析LOG内容
            if "Empty" in log_section:
                return {"status": "fail", "message": "onlinesupport LOG部分为空(Empty)"}
            
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
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t') and ':' in line:
                        break
                    log_lines.append(line)
            
            return '\n'.join(log_lines)
        except Exception as e:
            self.progress.emit(f"❌ 提取LOG部分失败: {str(e)}")
            return None


class PyQtHeraConfigManager(QObject):
    """PyQt5赫拉配置管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.worker = None
        
    def configure_hera(self):
        """赫拉配置"""
        try:
            # 验证设备选择
            device = self.device_manager.validate_device_selection()
            if not device:
                self.status_message.emit("赫拉配置失败: 请先选择设备")
                return
            
            # 显示配置选项
            reply = QMessageBox.question(
                None,
                "赫拉配置选项",
                "确定要开始赫拉配置吗？\n\n"
                "配置内容包括:\n"
                "• 安装测试APK\n"
                "• 设置日志大小\n"
                "• 仅开启mobile日志\n"
                "• GDPR检查和设置\n"
                "• 检查系统状态\n\n"
                "是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 配置选项
            config_options = {
                'install_apk': True,
                'disable_tcl_logger': True,
                'handle_gdpr': True,
                'run_bugreport': True,
                'simulate_crash': True
            }
            
            # 启动配置线程
            self.worker = HeraConfigWorker(device, config_options)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.start()
            
        except Exception as e:
            self.status_message.emit(f"赫拉配置失败: {str(e)}")
    
    def configure_collect_data(self):
        """赫拉测试数据收集"""
        try:
            # 验证设备选择
            device = self.device_manager.validate_device_selection()
            if not device:
                self.status_message.emit("赫拉测试数据收集失败: 请先选择设备")
                return
            
            # 显示配置选项
            reply = QMessageBox.question(
                None,
                "赫拉测试数据收集",
                "确定要开始赫拉测试数据收集吗？\n\n"
                "此功能将收集测试数据。\n\n"
                "是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 启动数据收集线程
            self.worker = HeraDataCollectionWorker(device)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.start()
            
        except Exception as e:
            self.status_message.emit(f"赫拉测试数据收集失败: {str(e)}")
    
    def _on_progress(self, message):
        """进度更新"""
        self.status_message.emit(message)
    
    def _on_finished(self, success, message):
        """配置完成"""
        # 只记录日志，不显示弹框
        if success:
            self.status_message.emit(f"[赫拉配置] 成功: {message}")
        else:
            self.status_message.emit(f"[赫拉配置] 失败: {message}")
