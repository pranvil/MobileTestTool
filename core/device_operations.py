#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 剩余管理器集合
包含背景数据、APP操作、设备信息、赫拉配置、其他操作等管理器
"""

import subprocess
import os
import datetime
import json
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QDialog

from core.update_manager import DEFAULT_UPDATE_FEED_URL


class PySide6BackgroundDataManager(QObject):
    """背景数据管理器 - 使用完整实现"""
    
    status_message = Signal(str)
    log_message = Signal(str, str)  # text, color
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def configure_phone(self):
        """配置手机 - 设置SELinux为Permissive模式"""
        try:
            device = self.device_manager.validate_device_selection()
            if not device:
                return
            
            self.status_message.emit(self.tr("正在配置手机..."))
            
            # 步骤1: 执行adb root
            self.status_message.emit(self.tr("步骤1: 执行adb root..."))
            try:
                result = subprocess.run(
                    ["adb", "-s", device, "root"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    success_msg = f"✅ {self.tr('adb root 执行成功')}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(success_msg, "green")
                    else:
                        self.status_message.emit(success_msg)
                else:
                    error_msg = f"❌ {self.tr('adb root 执行失败')}: {result.stderr}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(error_msg, "red")
                    else:
                        self.status_message.emit(error_msg)
                    return
                    
            except Exception as e:
                error_msg = f"❌ {self.tr('adb root 执行异常')}: {str(e)}"
                if hasattr(self, 'log_message'):
                    self.log_message.emit(error_msg, "red")
                else:
                    self.status_message.emit(error_msg)
                return
            
            # 等待一下确保root权限生效
            import time
            time.sleep(2)
            
            # 步骤2: 设置SELinux为Permissive
            self.status_message.emit(self.tr("步骤2: 设置SELinux为Permissive模式..."))
            try:
                result = subprocess.run(
                    ["adb", "-s", device, "shell", "setenforce", "0"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    success_msg = f"✅ {self.tr('setenforce 0 执行成功')}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(success_msg, "green")
                    else:
                        self.status_message.emit(success_msg)
                else:
                    error_msg = f"❌ {self.tr('setenforce 0 执行失败')}: {result.stderr}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(error_msg, "red")
                    else:
                        self.status_message.emit(error_msg)
                    return
                    
            except Exception as e:
                error_msg = f"❌ {self.tr('setenforce 0 执行异常')}: {str(e)}"
                if hasattr(self, 'log_message'):
                    self.log_message.emit(error_msg, "red")
                else:
                    self.status_message.emit(error_msg)
                return
            
            # 步骤3: 验证SELinux状态
            self.status_message.emit(self.tr("步骤3: 验证SELinux状态..."))
            try:
                result = subprocess.run(
                    ["adb", "-s", device, "shell", "getenforce"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    selinux_status = result.stdout.strip()
                    status_msg = f"📊 {self.tr('当前SELinux状态')}: {selinux_status}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(status_msg, "blue")
                    else:
                        self.status_message.emit(status_msg)
                    
                    if selinux_status == "Permissive":
                        success_msg = f"✅ {self.tr('手机配置成功！')}\n📊 {self.tr('SELinux状态')}: {selinux_status}\n🔧 {self.tr('已设置为Permissive模式')}"
                        if hasattr(self, 'log_message'):
                            self.log_message.emit(success_msg, "green")
                        else:
                            self.status_message.emit(success_msg)
                    else:
                        warning_msg = f"⚠️ {self.tr('SELinux状态未正确设置')}\n📊 {self.tr('当前状态')}: {selinux_status}\n❌ {self.tr('期望状态: Permissive')}"
                        if hasattr(self, 'log_message'):
                            self.log_message.emit(warning_msg, "orange")
                        else:
                            self.status_message.emit(warning_msg)
                else:
                    error_msg = f"❌ {self.tr('获取SELinux状态失败')}: {result.stderr}"
                    if hasattr(self, 'log_message'):
                        self.log_message.emit(error_msg, "red")
                    else:
                        self.status_message.emit(error_msg)
                    
            except Exception as e:
                error_msg = f"❌ {self.tr('验证SELinux状态异常')}: {str(e)}"
                if hasattr(self, 'log_message'):
                    self.log_message.emit(error_msg, "red")
                else:
                    self.status_message.emit(error_msg)
                
        except Exception as e:
            error_msg = f"❌ {self.tr('配置手机失败:')} {str(e)}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_msg, "red")
            else:
                self.status_message.emit(error_msg)
    
    def export_background_logs(self):
        """导出背景日志"""
        self.status_message.emit(self.tr("导出背景日志..."))
        # TODO: 实现导出背景日志逻辑
    
    def analyze_logs(self):
        """分析日志"""
        self.status_message.emit(self.tr("分析日志..."))
        # TODO: 实现日志分析逻辑


class PySide6AppOperationsManager(QObject):
    """APP操作管理器 - 使用完整实现"""
    
    status_message = Signal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 初始化APP操作管理器
        self._init_app_ops_manager()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def _init_app_ops_manager(self):
        """初始化APP操作管理器"""
        # 导入完整的APP操作管理器
        from core.app_operations_manager import AppOperationsManager
        self.app_ops_manager = AppOperationsManager(self.device_manager, self)
        # 连接信号
        self.app_ops_manager.log_message.connect(self.status_message.emit)
    
    def query_package(self):
        """查询package"""
        self.app_ops_manager.query_package()
    
    def query_package_name(self):
        """查询包名"""
        self.app_ops_manager.query_package_name()
    
    def query_install_path(self):
        """查询安装路径"""
        self.app_ops_manager.query_install_path()
    
    def query_find_file(self):
        """查找文件"""
        self.app_ops_manager.query_find_file()
    
    def pull_apk(self):
        """pull apk"""
        self.app_ops_manager.pull_apk()
    
    def push_apk(self):
        """push apk"""
        self.app_ops_manager.push_apk()
    
    def install_apk(self):
        """安装APK"""
        self.app_ops_manager.install_apk()
    
    def view_processes(self):
        """查看进程"""
        self.app_ops_manager.view_processes()
    
    def dump_app(self):
        """dump app"""
        self.app_ops_manager.dump_app()
    
    def enable_app(self):
        """启用app"""
        self.app_ops_manager.enable_app()
    
    def disable_app(self):
        """禁用app"""
        self.app_ops_manager.disable_app()


class DeviceInfoWorker(QThread):
    """设备信息获取工作线程 - 避免阻塞UI"""
    
    finished = Signal(dict)  # 完成信号，返回设备信息字典
    error_occurred = Signal(str)  # 错误信号
    status_updated = Signal(str)  # 状态更新信号
    
    def __init__(self, device, device_info_manager, lang_manager=None):
        super().__init__()
        self.device = device
        self.device_info_manager = device_info_manager
        self.lang_manager = lang_manager
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def run(self):
        """在后台线程中执行设备信息获取"""
        try:
            self.status_updated.emit(self.tr("正在获取设备信息，请稍候..."))
            
            # 调用collect_device_info方法（这个操作比较耗时）
            device_info = self.device_info_manager.collect_device_info(self.device)
            
            # 发送完成信号
            self.finished.emit(device_info)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class PySide6DeviceInfoManager(QObject):
    """设备信息管理器"""
    
    status_message = Signal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 初始化设备信息管理器
        self._init_device_info_manager()
        # 工作线程引用
        self._worker = None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def _init_device_info_manager(self):
        """初始化设备信息管理器"""
        # 导入PySide6版本的DeviceInfoManager
        from core.device_info_manager import DeviceInfoManager
        self.device_info_manager = DeviceInfoManager()
        
    def show_device_info(self):
        """显示手机信息 - 使用后台线程避免阻塞UI"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 如果已经有工作线程在运行，直接返回
        if self._worker and self._worker.isRunning():
            self.status_message.emit(self.tr("设备信息正在获取中，请稍候..."))
            return
        
        try:
            # 创建工作线程
            self._worker = DeviceInfoWorker(device, self.device_info_manager, self.lang_manager)
            self._worker.status_updated.connect(self.status_message.emit)
            self._worker.finished.connect(self._on_device_info_finished)
            self._worker.error_occurred.connect(self._on_device_info_error)
            
            # 启动工作线程（工作线程启动后会发送状态更新）
            self._worker.start()
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("启动设备信息获取失败: ") + str(e))
    
    def _on_device_info_finished(self, device_info):
        """设备信息获取完成后的处理"""
        try:
            # 格式化显示设备信息
            info_text = "=" * 60 + "\n"
            # info_text += self.tr("设备信息\n")
            # info_text += "=" * 60 + "\n\n"
            
            # 设备基本信息
            info_text += self.tr("设备基本信息:\n")
            info_text += f"  {self.tr('设备型号:')} {device_info.get('device_model', self.tr('未知'))}\n"
            info_text += f"  {self.tr('设备品牌:')} {device_info.get('device_brand', self.tr('未知'))}\n"
            info_text += f"  {self.tr('Android版本:')} {device_info.get('android_version', self.tr('未知'))}\n"
            info_text += f"  {self.tr('API级别:')} {device_info.get('api_level', self.tr('未知'))}\n"
            info_text += f"  {self.tr('设备序列号:')} {device_info.get('serial', self.tr('未知'))}\n\n"
            
            # 详细订阅信息
            subscriptions = device_info.get("subscriptions", [])
            if subscriptions and len(subscriptions) > 0:
                info_text += self.tr("详细信息:\n")
                for i, sub in enumerate(subscriptions):
                    slot_name = f"{self.tr('卡槽')} {sub.get('slotIndex', i)}"
                    info_text += f"  {slot_name}:\n"
                    info_text += f"    IMEI: {sub.get('imei', '')}\n"
                    info_text += f"    MSISDN: {sub.get('msisdn', '')}\n"
                    info_text += f"    IMSI: {sub.get('imsi', '')}\n"
                    info_text += f"    ICCID: {sub.get('iccid', '')}\n\n"
            
            # 显示 Fingerprint
            fingerprint = device_info.get('fingerprint', self.tr('未知'))
            info_text += f"Fingerprint: {fingerprint}\n"
            
            # 显示 Antirollback
            antirollback = device_info.get('antirollback', self.tr('未知'))
            info_text += f"Antirollback: {antirollback}\n"
            
            # 显示编译时间
            build_date = device_info.get('build_date', self.tr('未知'))
            info_text += f"{self.tr('编译时间:')} {build_date}\n"
            
            info_text += "=" * 60 + "\n"
            info_text += self.tr("[设备信息] 设备信息获取完成!\n")
            
            # 显示在日志窗口
            self.status_message.emit(info_text)
            
            # 清理工作线程引用
            if self._worker:
                self._worker.deleteLater()
                self._worker = None
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("格式化设备信息失败: ") + str(e))
    
    def _on_device_info_error(self, error_msg):
        """设备信息获取错误处理"""
        self.status_message.emit("❌ " + self.tr("获取手机信息失败: ") + error_msg)
        
        # 清理工作线程引用
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
    
    def cleanup(self):
        """清理工作线程，在窗口关闭时调用"""
        if self._worker and self._worker.isRunning():
            try:
                self._worker.wait(3000)
                if self._worker.isRunning():
                    self._worker.terminate()
                    self._worker.wait(1000)
            except Exception:
                pass
            finally:
                self._worker = None
    
    def set_screen_timeout(self):
        """设置灭屏时间"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        timeout, ok = QInputDialog.getInt(None, self.tr("设置灭屏时间"), self.tr("请输入灭屏时间(秒，0表示永不灭屏):"), 600, 0, 3600)
        if not ok:
            return
        
        try:
            # 如果输入0，表示永不灭屏，设置为2147483647
            if timeout == 0:
                timeout_value = 2147483647
                timeout_display = self.tr("永不灭屏")
            else:
                timeout_value = timeout * 1000
                timeout_display = f"{timeout}{self.tr('秒')}"
            
            subprocess.run(
                ["adb", "-s", device, "shell", "settings", "put", "system", "screen_off_timeout", str(timeout_value)],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.status_message.emit(self.tr("灭屏时间已设置为: ") + str(timeout_display))
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("设置灭屏时间失败: ") + str(e))


class PySide6HeraConfigManager(QObject):
    """赫拉配置管理器"""
    
    status_message = Signal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 导入独立的PySide6赫拉配置管理器
        from core.hera_config_manager import PySide6HeraConfigManager as HeraManager
        self.hera_manager = HeraManager(device_manager, parent=self)
        # 连接信号
        self.hera_manager.status_message.connect(self.status_message.emit)
        
    def configure_hera(self):
        """赫拉配置"""
        self.hera_manager.configure_hera()
    
    def configure_collect_data(self):
        """赫拉测试数据收集"""
        self.hera_manager.configure_collect_data()
    
    def cleanup(self):
        """清理工作线程，在窗口关闭时调用"""
        if hasattr(self, 'hera_manager') and self.hera_manager:
            if hasattr(self.hera_manager, 'cleanup'):
                self.hera_manager.cleanup()


class VenvWorker(QThread):
    """虚拟环境处理工作线程"""
    
    progress_updated = Signal(int)  # 进度 (0-100)
    status_updated = Signal(str)  # 状态消息
    finished = Signal(dict)  # 完成信号，返回结果字典
    error_occurred = Signal(str)  # 错误信号
    request_user_confirm = Signal(str, str)  # 请求用户确认 (title, message)
    
    def __init__(self, elt_path, venv_path, lang_manager=None, parent_manager=None):
        super().__init__()
        self.elt_path = elt_path
        self.venv_path = venv_path
        self.lang_manager = lang_manager
        self.parent_manager = parent_manager
        self.user_response = None
        self.user_response_mutex = None
        from PySide6.QtCore import QMutex
        self.user_response_mutex = QMutex()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def set_user_response(self, response):
        """设置用户响应"""
        if self.user_response_mutex:
            self.user_response_mutex.lock()
        self.user_response = response
        if self.user_response_mutex:
            self.user_response_mutex.unlock()
    
    def wait_for_user_response(self, timeout=300):
        """等待用户响应"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.user_response_mutex:
                self.user_response_mutex.lock()
            response = self.user_response
            if self.user_response_mutex:
                self.user_response_mutex.unlock()
            if response is not None:
                return response
            time.sleep(0.1)
        return None
    
    def run(self):
        """执行虚拟环境处理"""
        try:
            result = self._handle_python37_venv()
            self.finished.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _handle_python37_venv(self):
        """处理 Python 3.7 虚拟环境"""
        # 检查虚拟环境是否存在
        if self._check_venv_exists(self.venv_path):
            self.status_updated.emit(self.tr("检查虚拟环境..."))
            self.progress_updated.emit(20)
            venv_python = self._get_venv_python_path(self.venv_path)
            # 检查 mace 是否已安装
            if not self._check_venv_mace_installed(venv_python):
                # 自动安装 mace
                self.status_updated.emit(self.tr("虚拟环境中未安装 mace，正在安装..."))
                self.progress_updated.emit(40)
                success, error = self._install_mace_in_venv(venv_python, self.elt_path)
                if not success:
                    return {'success': False, 'error': error}
                self.status_updated.emit(self.tr("mace 安装完成"))
                self.progress_updated.emit(100)
            else:
                self.status_updated.emit(self.tr("虚拟环境已就绪"))
                self.progress_updated.emit(100)
            return {'success': True, 'venv_python': venv_python}
        
        # 虚拟环境不存在，需要创建
        # 检查是否有 Python 3.7
        self.status_updated.emit(self.tr("检查 Python 3.7..."))
        self.progress_updated.emit(10)
        has_python37, python37_cmd = self._check_python37_available()
        if not has_python37:
            return {'success': False, 'error': self.tr('Python 3.7 未安装')}
        
        # 请求用户确认
        self.status_updated.emit(self.tr("等待用户确认..."))
        self.request_user_confirm.emit(
            self.tr("创建虚拟环境"),
            self.tr("检测到需要 Python 3.7 虚拟环境。\n\n是否创建虚拟环境？\n\n虚拟环境将创建在：\n") + self.venv_path
        )
        
        # 等待用户响应
        from PySide6.QtWidgets import QMessageBox
        user_response = self.wait_for_user_response()
        if user_response != QMessageBox.StandardButton.Yes:
            return {'success': False, 'error': self.tr('用户取消创建虚拟环境')}
        
        # 创建虚拟环境
        self.status_updated.emit(self.tr("正在创建虚拟环境..."))
        self.progress_updated.emit(30)
        success, error = self._create_venv(self.venv_path, python37_cmd)
        if not success:
            return {'success': False, 'error': error}
        
        self.status_updated.emit(self.tr("虚拟环境创建完成"))
        self.progress_updated.emit(60)
        
        # 在虚拟环境中安装 mace
        venv_python = self._get_venv_python_path(self.venv_path)
        self.status_updated.emit(self.tr("正在虚拟环境中安装 mace..."))
        self.progress_updated.emit(70)
        success, error = self._install_mace_in_venv(venv_python, self.elt_path)
        if not success:
            return {'success': False, 'error': error}
        
        self.status_updated.emit(self.tr("mace 安装完成"))
        self.progress_updated.emit(100)
        
        return {'success': True, 'venv_python': venv_python}
    
    def _check_venv_exists(self, venv_path):
        """检查虚拟环境是否存在且有效"""
        venv_python = self._get_venv_python_path(venv_path)
        return os.path.exists(venv_python)
    
    def _get_venv_python_path(self, venv_path):
        """获取虚拟环境中的 Python 路径"""
        import sys
        if sys.platform == "win32":
            return os.path.join(venv_path, "Scripts", "python.exe")
        else:
            return os.path.join(venv_path, "bin", "python")
    
    def _check_python37_available(self):
        """检查系统是否有 Python 3.7"""
        try:
            # 方法1: 尝试使用 py -3.7 --version
            result = subprocess.run(
                ["py", "-3.7", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        try:
            # 方法2: 使用 py --list 查找
            result = subprocess.run(
                ["py", "--list"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        # 方法3: 检查常见安装路径
        common_paths = [
            r"C:\Python37\python.exe",
            r"C:\Python37-64\python.exe",
            r"C:\Program Files\Python37\python.exe",
            r"C:\Program Files (x86)\Python37\python.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return True, path
        
        return False, None
    
    def _check_venv_mace_installed(self, venv_python):
        """检查虚拟环境中是否安装了 mace"""
        try:
            result = subprocess.run(
                [venv_python, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return "mace" in result.stdout.lower()
        except Exception:
            pass
        return False
    
    def _create_venv(self, venv_path, python37_cmd):
        """创建虚拟环境"""
        try:
            # 如果虚拟环境已存在，先删除
            if os.path.exists(venv_path):
                import shutil
                shutil.rmtree(venv_path)
            
            # 创建虚拟环境
            if python37_cmd.startswith("py -"):
                # 使用 py launcher
                cmd = ["py", "-3.7", "-m", "venv", venv_path]
            else:
                # 使用直接路径
                cmd = [python37_cmd, "-m", "venv", venv_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                return False, f"{self.tr('创建虚拟环境失败:')} {result.stderr}"
            
            # 验证虚拟环境是否创建成功
            venv_python = self._get_venv_python_path(venv_path)
            if not os.path.exists(venv_python):
                return False, self.tr("虚拟环境创建失败：找不到 Python 解释器")
            
            return True, None
        except Exception as e:
            return False, f"{self.tr('创建虚拟环境异常:')} {str(e)}"
    
    def _install_mace_in_venv(self, venv_python, elt_path):
        """在虚拟环境中安装 mace"""
        mace_install_path = os.path.join(elt_path, "Automation", "MACE2", "Mace2Python")
        install_script = os.path.join(mace_install_path, "install.py")
        
        if not os.path.exists(install_script):
            return False, f"{self.tr('找不到 install.py:')} {install_script}"
        
        try:
            result = subprocess.run(
                [venv_python, "install.py"],
                cwd=mace_install_path,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                return False, f"{self.tr('mace 安装失败:')} {result.stderr}"
            return True, None
        except Exception as e:
            return False, f"{self.tr('mace 安装异常:')} {str(e)}"


class OtherOperationsWorker(QThread):
    """其他操作工作线程"""
    
    # 信号定义
    progress_updated = Signal(int)  # 进度 (0-100)
    status_updated = Signal(str)  # 状态消息
    finished = Signal(dict)  # 完成信号，返回结果字典
    error_occurred = Signal(str)  # 错误信号
    
    def __init__(self, operation_type, lang_manager=None, **kwargs):
        super().__init__()
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.stop_flag = False
        self.lang_manager = lang_manager
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def run(self):
        """执行操作"""
        try:
            if self.operation_type == 'merge_mtklog':
                result = self._merge_mtklog()
            elif self.operation_type == 'extract_pcap_from_mtklog':
                result = self._extract_pcap_from_mtklog()
            elif self.operation_type == 'merge_pcap':
                result = self._merge_pcap()
            elif self.operation_type == 'extract_pcap_from_qualcomm_log':
                result = self._extract_pcap_from_qualcomm_log()
            elif self.operation_type == 'mtk_sip_decode':
                result = self._mtk_sip_decode()
            else:
                result = {'success': False, 'error': self.tr('未知操作类型')}
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _merge_mtklog(self):
        """合并MTKlog"""
        try:
            log_folder = self.kwargs['log_folder']
            mtk_tool = self.kwargs['mtk_tool']
            
            # 检查base_path是否存在
            base_path = mtk_tool.get("base_path")
            if not base_path or not os.path.exists(base_path):
                error_msg = (
                    f"{self.tr('找不到MTK ELT工具路径')}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            # 获取MDLogMan.exe路径
            utilities_path = os.path.join(base_path, "Utilities")
            mdlogman_exe = os.path.join(utilities_path, "MDLogMan.exe")
            
            if not os.path.exists(mdlogman_exe):
                error_msg = (
                    f"{self.tr('找不到MDLogMan.exe:')} {mdlogman_exe}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            self.status_updated.emit(self.tr("准备合并环境..."))
            self.progress_updated.emit(10)
            
            # 创建输出文件路径
            merge_elg_path = os.path.join(log_folder, "merge.elg")
            
            self.status_updated.emit(self.tr("正在合并 ") + str(len(self.kwargs['muxz_files'])) + self.tr(" 个muxz文件..."))
            self.progress_updated.emit(50)
            
            # 执行合并命令
            cmd = [
                mdlogman_exe,
                "-i", "*.muxz",
                "-o", "merge.elg"
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=log_folder, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_updated.emit(self.tr("合并完成!"))
                self.progress_updated.emit(100)
                
                # 检查输出文件是否存在
                if os.path.exists(merge_elg_path):
                    # 打开合并后的elg文件所在文件夹
                    os.startfile(log_folder)
                    
                    return {
                        'success': True,
                        'merge_file': merge_elg_path,
                        'file_count': len(self.kwargs['muxz_files'])
                    }
                else:
                    return {'success': False, 'error': self.tr('合并完成但未找到输出文件')}
            else:
                return {'success': False, 'error': f"{self.tr('MDLogMan执行失败:')} {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': self.tr('MDLogMan执行超时')}
        except Exception as e:
            return {'success': False, 'error': f"{self.tr('执行MTKlog合并失败:')} {str(e)}"}
    
    def _extract_pcap_from_mtklog(self):
        """从MTKlog中提取pcap文件"""
        try:
            log_folder = self.kwargs['log_folder']
            muxz_files = self.kwargs['muxz_files']
            mtk_tool = self.kwargs['mtk_tool']
            
            # 检查base_path是否存在
            base_path = mtk_tool.get("base_path")
            if not base_path or not os.path.exists(base_path):
                error_msg = (
                    f"{self.tr('找不到MTK ELT工具路径')}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            # 切换到elgcap目录
            elgcap_path = mtk_tool.get("elgcap_path")
            python_path = mtk_tool.get("python_path")
            
            if not elgcap_path or not os.path.exists(elgcap_path):
                error_msg = (
                    f"{self.tr('找不到elgcap目录:')} {elgcap_path}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            if not python_path or not os.path.exists(python_path):
                error_msg = (
                    f"{self.tr('找不到Python目录:')} {python_path}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            embedded_python = os.path.join(python_path, "EmbeddedPython.exe")
            
            if not os.path.exists(embedded_python):
                error_msg = (
                    f"{self.tr('找不到EmbeddedPython.exe:')} {embedded_python}\n\n"
                    f"{self.tr('请安装MTK ELT工具并且完成注册，并且把路径添加到工具配置中。路径为ELT.exe所在目录。')}\n"
                    f"{self.tr('示例路径:')} C:\\Tool\\ELT_exe_v3.2348.0_customer_x64"
                )
                return {'success': False, 'error': error_msg}
            
            self.status_updated.emit(self.tr("准备提取环境..."))
            self.progress_updated.emit(0)
            
            # 对每个muxz文件执行提取
            total_files = len(muxz_files)
            success_count = 0
            
            for i, muxz_file in enumerate(muxz_files):
                if self.stop_flag:
                    return {'success': False, 'error': self.tr('用户取消操作')}
                
                progress_text = f"{self.tr('正在提取:')} {muxz_file} ({i+1}/{total_files})"
                progress_value = (i / total_files) * 80
                
                self.status_updated.emit(progress_text)
                self.progress_updated.emit(progress_value)
                
                # 执行提取命令
                muxz_path = os.path.join(log_folder, muxz_file)
                cmd = [
                    embedded_python,
                    "main.py",
                    "-sap", "sap_6291",
                    "-pcapng",
                    "-all_payload",
                    muxz_path
                ]
                
                try:
                    result = subprocess.run(
                        cmd, 
                        cwd=elgcap_path, 
                        capture_output=True, 
                        text=True, 
                        encoding='utf-8', 
                        errors='replace', 
                        timeout=3600,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    if result.returncode == 0:
                        success_count += 1
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
            
            # 检查pcap文件数量，决定是否需要合并
            pcap_files = self._find_pcap_files(log_folder)
            
            if len(pcap_files) == 0:
                return {'success': False, 'error': self.tr('未找到pcap文件')}
            elif len(pcap_files) == 1:
                # 只有一个文件，不需要合并，直接使用该文件
                merge_file = pcap_files[0]
                self.status_updated.emit(self.tr("提取完成!"))
                self.progress_updated.emit(100)
                
                return {
                    'success': True,
                    'merge_file': merge_file,
                    'success_count': success_count,
                    'total_files': total_files
                }
            else:
                # 多个文件，需要合并
                self.status_updated.emit(self.tr("合并pcap文件..."))
                self.progress_updated.emit(80)
                
                # 使用通用的合并函数
                merge_success = self._execute_pcap_merge(log_folder)
                
                if merge_success:
                    merge_file = os.path.join(log_folder, 'merge.pcap')
                    self.status_updated.emit(self.tr("提取完成!"))
                    self.progress_updated.emit(100)
                    
                    return {
                        'success': True,
                        'merge_file': merge_file,
                        'success_count': success_count,
                        'total_files': total_files
                    }
                else:
                    return {'success': False, 'error': self.tr('pcap文件合并失败')}
                
        except Exception as e:
            return {'success': False, 'error': f"{self.tr('执行pcap提取失败:')} {str(e)}"}
    
    def _merge_pcap(self):
        """合并PCAP文件"""
        try:
            folder_path = self.kwargs['folder_path']
            
            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                return {'success': False, 'error': f"{self.tr('文件夹不存在:')} {folder_path}"}
            
            # 查找所有pcap文件
            pcap_files = self._find_pcap_files(folder_path)
            if not pcap_files:
                return {'success': False, 'error': f"{self.tr('文件夹中没有找到pcap文件:')} {folder_path}"}
            
            # 检查Wireshark路径
            wireshark_path = self.kwargs.get('wireshark_path')
            
            if not wireshark_path:
                error_msg = (
                    f"{self.tr('未配置Wireshark路径')}\n\n"
                    f"{self.tr('请安装Wireshark，并且在工具配置里配置路径。')}\n"
                    f"{self.tr('示例路径:')} C:\\Program Files\\Wireshark"
                )
                return {'success': False, 'error': error_msg}
            
            if not os.path.exists(wireshark_path):
                error_msg = (
                    f"{self.tr('Wireshark路径不存在:')} {wireshark_path}\n\n"
                    f"{self.tr('请安装Wireshark，并且在工具配置里配置路径。')}\n"
                    f"{self.tr('示例路径:')} C:\\Program Files\\Wireshark"
                )
                return {'success': False, 'error': error_msg}
            
            mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
            
            if not os.path.exists(mergecap_exe):
                error_msg = (
                    f"{self.tr('找不到mergecap.exe:')} {mergecap_exe}\n\n"
                    f"{self.tr('请安装Wireshark，并且在工具配置里配置路径。')}\n"
                    f"{self.tr('示例路径:')} C:\\Program Files\\Wireshark"
                )
                return {'success': False, 'error': error_msg}
            
            self.status_updated.emit(self.tr("正在合并 ") + str(len(pcap_files)) + self.tr(" 个文件..."))
            self.progress_updated.emit(50)
            
            # 创建输出文件路径
            merge_pcap_path = os.path.join(folder_path, "merge.pcap")
            
            # 执行合并命令
            merge_cmd = [mergecap_exe, "-w", merge_pcap_path] + pcap_files
            
            result = subprocess.run(
                merge_cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_updated.emit(self.tr("合并完成!"))
                self.progress_updated.emit(100)
                
                return {'success': True, 'merge_file': merge_pcap_path}
            else:
                return {'success': False, 'error': f"{self.tr('mergecap执行失败:')} {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': self.tr('合并超时，请检查文件大小')}
        except Exception as e:
            return {'success': False, 'error': f"{self.tr('执行PCAP合并失败:')} {str(e)}"}
    
    def _extract_pcap_from_qualcomm_log(self):
        """从高通log提取pcap文件"""
        try:
            log_folder = self.kwargs['log_folder']
            hdf_files = self.kwargs['hdf_files']
            qualcomm_tool = self.kwargs['qualcomm_tool']
            
            # 获取PCAP_Gen_2.0.exe路径
            pcap_gen_exe = qualcomm_tool["pcap_gen_exe"]
            
            if not os.path.exists(pcap_gen_exe):
                error_msg = (
                    f"{self.tr('找不到PCAP_Gen_2.0.exe:')} {pcap_gen_exe}\n\n"
                    f"{self.tr('请安装高通Packet Capture (PCAP) Generator，并且把路径添加到工具配置中。')}\n"
                    f"{self.tr('示例路径:')} PCAP_Generator_PCAP_Gen_2.0 - C:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release"
                )
                return {'success': False, 'error': error_msg}
            
            self.status_updated.emit(self.tr("准备提取环境..."))
            self.progress_updated.emit(0)
            
            # 对每个hdf文件执行提取
            total_files = len(hdf_files)
            success_count = 0
            
            for i, hdf_file in enumerate(hdf_files):
                if self.stop_flag:
                    return {'success': False, 'error': self.tr('用户取消操作')}
                
                progress_text = f"{self.tr('正在提取:')} {hdf_file} ({i+1}/{total_files})"
                progress_value = (i / total_files) * 80
                
                self.status_updated.emit(progress_text)
                self.progress_updated.emit(progress_value)
                
                # 执行提取命令
                hdf_path = os.path.join(log_folder, hdf_file)
                cmd = [pcap_gen_exe, hdf_path, log_folder]
                
                try:
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        encoding='utf-8', 
                        errors='replace', 
                        timeout=3600,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    if result.returncode == 0:
                        success_count += 1
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
            
            # 合并pcap文件
            self.status_updated.emit(self.tr("合并pcap文件..."))
            self.progress_updated.emit(80)
            
            # 使用通用的合并函数
            merge_success = self._execute_pcap_merge(log_folder)
            
            if merge_success:
                merge_file = os.path.join(log_folder, 'merge.pcap')
                self.status_updated.emit(self.tr("提取完成!"))
                self.progress_updated.emit(100)
                
                return {
                    'success': True,
                    'merge_file': merge_file,
                    'success_count': success_count,
                    'total_files': total_files
                }
            else:
                return {'success': False, 'error': self.tr('pcap文件合并失败')}
                
        except Exception as e:
            return {'success': False, 'error': f"{self.tr('执行高通pcap提取失败:')} {str(e)}"}
    
    def _execute_pcap_merge(self, folder_path):
        """执行PCAP合并的通用函数"""
        try:
            # 查找所有pcap文件
            pcap_files = self._find_pcap_files(folder_path)
            if not pcap_files:
                return False
            
            # 检查Wireshark路径
            wireshark_path = self.kwargs.get('wireshark_path')
            if not wireshark_path:
                return False
            
            mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
            
            if not os.path.exists(mergecap_exe):
                return False
            
            # 创建输出文件路径
            merge_pcap_path = os.path.join(folder_path, "merge.pcap")
            
            # 执行合并命令
            merge_cmd = [mergecap_exe, "-w", merge_pcap_path] + pcap_files
            
            result = subprocess.run(
                merge_cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            return result.returncode == 0
                
        except Exception:
            return False
    
    def _find_pcap_files(self, folder_path):
        """查找文件夹中的所有pcap文件"""
        try:
            pcap_files = []
            
            # 查找所有pcap相关文件
            for file in os.listdir(folder_path):
                if any(file.lower().endswith(ext) for ext in ['.pcap', '.pcapng', '.cap']):
                    pcap_files.append(os.path.join(folder_path, file))
            
            return pcap_files
            
        except Exception:
            return []
    
    def _mtk_sip_decode(self):
        """MTK SIP DECODE"""
        try:
            import sys
            import re
            import shutil
            from pathlib import Path
            
            log_folder = self.kwargs['log_folder']
            muxz_files = self.kwargs.get('muxz_files', [])
            elg_files = self.kwargs.get('elg_files', [])
            mtk_tool = self.kwargs['mtk_tool']
            clear_history = self.kwargs.get('clear_history', False)
            
            # 获取 ELT 路径
            elt_path = mtk_tool["base_path"]
            
            # 检查是否从 kwargs 中获取了 venv_python（由主线程传递）
            # 如果有 venv_python，直接使用虚拟环境，跳过系统 Python 环境的检测
            venv_python = self.kwargs.get('venv_python')
            
            # 如果没有虚拟环境，才检查系统 Python 环境中的 mace
            if not venv_python:
                # 检查 mace 是否安装
                self.status_updated.emit(self.tr("检查 mace 模块..."))
                self.progress_updated.emit(5)
                
                try:
                    result = subprocess.run(
                        ["pip", "list"],
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    mace_installed = "mace" in result.stdout.lower()
                except Exception:
                    mace_installed = False
                
                # 如果未安装，尝试安装
                if not mace_installed:
                    self.status_updated.emit(self.tr("mace 未安装，正在安装..."))
                    self.progress_updated.emit(10)
                    
                    mace_install_path = os.path.join(elt_path, "Automation", "MACE2", "Mace2Python")
                    install_script = os.path.join(mace_install_path, "install.py")
                    
                    if not os.path.exists(install_script):
                        return {'success': False, 'error': f"{self.tr('找不到 install.py:')} {install_script}"}
                    
                    # 尝试使用系统 Python 安装
                    try:
                        result = subprocess.run(
                            ["python", "install.py"],
                            cwd=mace_install_path,
                            capture_output=True,
                            text=True,
                            timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        if result.returncode == 0:
                            # 安装成功，重新检查
                            try:
                                check_result = subprocess.run(
                                    ["pip", "list"],
                                    capture_output=True,
                                    text=True,
                                    shell=True,
                                    timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                                )
                                if "mace" in check_result.stdout.lower():
                                    mace_installed = True
                            except Exception:
                                pass
                        
                        # 如果安装失败且错误信息包含 python3.7，需要处理虚拟环境
                        if result.returncode != 0 and ("python3.7" in result.stderr.lower() or "python 3.7" in result.stderr.lower() or "Please install" in result.stderr):
                            # 需要 Python 3.7，返回特殊错误码让主线程处理
                            return {'success': False, 'error': 'NEED_PYTHON37', 'elt_path': elt_path}
                    except Exception as e:
                        # 检查异常信息中是否包含 python3.7
                        error_str = str(e).lower()
                        if "python3.7" in error_str or "python 3.7" in error_str or "please install" in error_str:
                            return {'success': False, 'error': 'NEED_PYTHON37', 'elt_path': elt_path}
                        # 其他异常直接返回
                        return {'success': False, 'error': f"{self.tr('mace 安装异常:')} {str(e)}"}
            
            # 获取输出文件路径（Wireshark 目录）
            from pathlib import Path
            wireshark_dir = Path.home() / "AppData" / "Roaming" / "Wireshark"
            os.makedirs(wireshark_dir, exist_ok=True)
            output_file = str(wireshark_dir / "esp_sa")
            
            # 调试日志
            self.status_updated.emit(f"[DEBUG] Wireshark 目录: {wireshark_dir}")
            self.status_updated.emit(f"[DEBUG] 输出文件路径: {output_file}")
            print(f"[DEBUG] Wireshark 目录: {wireshark_dir}")
            print(f"[DEBUG] 输出文件路径: {output_file}")
            
            # 如果使用了虚拟环境，需要使用虚拟环境的 Python 来执行解析
            if venv_python:
                # 使用虚拟环境的 Python 执行解析
                return self._execute_parse_with_venv(venv_python, elt_path, log_folder, elg_files, output_file, clear_history, muxz_files)
            
            # 使用当前 Python 环境
            # 动态设置 sys.path 以包含 ELT 路径
            if elt_path not in sys.path:
                sys.path.insert(0, elt_path)
            
            # 导入 mace 模块
            try:
                import mace
            except ImportError as e:
                error_str = str(e).lower()
                # 检查错误信息中是否包含 python3.7 相关提示
                if "python3.7" in error_str or "python 3.7" in error_str or "please install" in error_str:
                    # 需要 Python 3.7，返回特殊错误码让主线程处理
                    return {'success': False, 'error': 'NEED_PYTHON37', 'elt_path': elt_path}
                return {'success': False, 'error': f"{self.tr('无法导入 mace 模块:')} {str(e)}"}
            
            # 处理所有 .elg 和 .muxz 文件
            # 注意：mace.open_log_file() 可以处理 .elg 文件或 .muxz 文件
            # 将所有文件合并到一个列表中，依次处理并追加写入 esp_sa
            success_count = 0
            
            # 合并所有 .elg 和 .muxz 文件
            all_files = elg_files + muxz_files
            
            if not all_files:
                self.status_updated.emit(self.tr("没有找到 .elg 或 .muxz 文件，将跳过 SIP 解码，直接提取 pcap"))
            else:
                total_files = len(all_files)
                self.status_updated.emit(self.tr(f"找到 {total_files} 个文件（{len(elg_files)} 个 .elg, {len(muxz_files)} 个 .muxz），开始处理..."))
                print(f"[DEBUG] 总共找到 {total_files} 个文件: {all_files}")
                
                for i, filename in enumerate(all_files):
                    if self.stop_flag:
                        return {'success': False, 'error': self.tr('用户取消操作')}
                    
                    file_path = os.path.join(log_folder, filename)
                    
                    progress_text = f"{self.tr('正在处理:')} {filename} ({i+1}/{total_files})"
                    progress_value = 10 + (i / total_files) * 60
                    
                    self.status_updated.emit(progress_text)
                    self.progress_updated.emit(progress_value)
                    
                    # 确定文件模式：第一个文件且 clear_history=True 时用 'w'，否则用 'a'
                    file_mode = 'w' if (i == 0 and clear_history) else 'a'
                    
                    try:
                        self.status_updated.emit(f"[DEBUG] 开始处理文件: {filename}, 模式: {file_mode}")
                        print(f"[DEBUG] 开始处理文件: {filename}, 模式: {file_mode}")
                        self._parse_elg_esp_sa(file_path, output_file, file_mode, elt_path)
                        success_count += 1
                        self.status_updated.emit(f"[DEBUG] 文件处理完成: {filename}")
                        print(f"[DEBUG] 文件处理完成: {filename}")
                    except Exception as e:
                        error_msg = f"{self.tr('处理文件失败:')} {filename} - {str(e)}"
                        self.status_updated.emit(error_msg)
                        print(f"[ERROR] {error_msg}")
                        import traceback
                        traceback.print_exc()
            
            # 检查文件是否存在并打印输出文件路径
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                output_msg = f"{self.tr('ESP SA 文件已保存到:')} {output_file} (大小: {file_size} 字节)"
                self.status_updated.emit(output_msg)
                print(f"[INFO] {output_msg}")
            else:
                error_msg = f"[WARNING] ESP SA 文件未找到: {output_file}"
                self.status_updated.emit(error_msg)
                print(f"[WARNING] {error_msg}")
            
            # 最后调用提取 pcap 功能
            self.status_updated.emit(self.tr("开始提取 pcap..."))
            self.progress_updated.emit(80)
            
            # 查找 muxz 文件用于提取 pcap
            if muxz_files:
                extract_result = self._extract_pcap_from_mtklog()
                if extract_result.get('success'):
                    self.progress_updated.emit(100)
                    return {
                        'success': True,
                        'esp_sa_file': output_file,
                        'success_count': success_count,
                        'total_files': len(all_files),
                        'pcap_extracted': True
                    }
                else:
                    return {
                        'success': True,
                        'esp_sa_file': output_file,
                        'success_count': success_count,
                        'total_files': len(all_files),
                        'pcap_extracted': False,
                        'pcap_error': extract_result.get('error', '')
                    }
            else:
                self.progress_updated.emit(100)
                return {
                    'success': True,
                    'esp_sa_file': output_file,
                    'success_count': success_count,
                    'total_files': len(all_files),
                    'pcap_extracted': False,
                    'pcap_error': self.tr('没有找到 muxz 文件，跳过 pcap 提取')
                }
                
        except Exception as e:
            return {'success': False, 'error': f"{self.tr('执行MTK SIP DECODE失败:')} {str(e)}"}
    
    def _execute_parse_with_venv(self, venv_python, elt_path, log_folder, elg_files, output_file, clear_history, muxz_files):
        """使用虚拟环境的 Python 执行解析"""
        import tempfile
        import json
        
        # 创建临时脚本文件
        script_content = f'''# -*- coding: utf-8 -*-
import sys
import os
import re
import shutil
from pathlib import Path

# 设置 ELT 路径
elt_path = r"{elt_path}"
if elt_path not in sys.path:
    sys.path.insert(0, elt_path)

import mace

def extract_ascii_array_lines(msg_text, array_name):
    """从原始 prim_local_buffer_string 中解析 Array[xx] 格式的 ASCII 数据"""
    lines = msg_text.splitlines()
    collecting = False
    hex_vals = []
    
    for line in lines:
        if not collecting:
            if array_name in line and "Array[" in line:
                collecting = True
            continue
        else:
            if re.match(r'^\\S', line):
                break
            m = re.search(r'0x([0-9a-fA-F]{{2}})', line)
            if m:
                hex_vals.append(m.group(1))
    
    if not hex_vals:
        return None
    
    ascii_str = ''.join(bytes.fromhex(h).decode('ascii', errors='ignore') for h in hex_vals)
    return ascii_str.split('\\x00')[0]

def normalize_ip(ip_str):
    """去掉前后空格和中括号，返回干净的 IP 字符串。"""
    if not ip_str:
        return None
    ip_str = ip_str.strip()
    if ip_str.startswith('[') and ip_str.endswith(']'):
        ip_str = ip_str[1:-1]
    return ip_str

def detect_protocol(ip_str):
    """根据 IP 字符串简单判断是 IPv4 还是 IPv6。"""
    if not ip_str:
        return "IPv6"
    if ':' in ip_str:
        return "IPv6"
    if '.' in ip_str:
        return "IPv4"
    return "IPv6"

def parse_ipsec_info_blocks(msg_text):
    """从 MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ 的文本中解析出 ipsec_info[x] 的各项"""
    infos = []
    
    # 用正则把每个 ipsec_info[x] 结构 block 切出来
    pattern = r'(ipsec_info\\[(\\d+)\\] = \\(struct\\)[\\s\\S]*?)(?=ipsec_info\\[\\d+\\] = \\(struct\\)|\\n\\t\\tindex =|\\Z)'
    for block, idx_str in re.findall(pattern, msg_text):
        idx = int(idx_str)
        
        # 复用前面的 ASCII 数组解析函数
        src_ip_raw = extract_ascii_array_lines(block, 'src_ip')
        dst_ip_raw = extract_ascii_array_lines(block, 'dst_ip')
        spi_raw = extract_ascii_array_lines(block, 'spi')
        
        src_ip = normalize_ip(src_ip_raw)
        dst_ip = normalize_ip(dst_ip_raw)
        
        spi_hex = None
        if spi_raw:
            spi_raw = spi_raw.strip()
            # 这里 spi_raw 是十进制字符串，如 "1583052695"
            try:
                spi_int = int(spi_raw)
                # Wireshark 接受 "0x..." 格式，长度不限，这里统一成小写十六进制
                spi_hex = "0x{{:x}}".format(spi_int)
            except ValueError:
                # 如果解析失败，直接原样写入（极少发生）
                spi_hex = spi_raw
        
        # 解析 dir = 0x01 / 0x00
        m_dir = re.search(r'dir\\s*=\\s*0x([0-9a-fA-F]+)', block)
        direction = None
        if m_dir:
            dir_val = int(m_dir.group(1), 16)
            # 一般 1 表示 OUT, 0 表示 IN
            direction = "OUT" if dir_val == 0x1 else "IN"
        
        infos.append({{
            "index": idx,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "spi_hex": spi_hex,
            "direction": direction,
        }})
    
    return infos

def parse_elg_esp_sa(elg_file, output_file, file_mode):
    """解析 ELG 文件提取 ESP SA 信息"""
    import os
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 统计信息（必须在函数开始处初始化）
    item_count = 0
    add_req_count = 0
    ck_ik_found_count = 0
    sa_written_count = 0
    
    log_handle = mace.open_log_file(elg_file)
    itemset = mace.create_itemset(log_handle)
    
    # 只订阅 ADD_REQ 就足够生成 SA 文件了
    itemset.subscribe_primitive('MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ')
    
    seen_sa = set()
    encry_algo = "AES-CBC [RFC3602]"
    integ_algo = "HMAC-SHA-1-96 [RFC2404]"
    
    with open(output_file, file_mode, encoding="utf-8") as out:
        if file_mode == 'w':
            out.write("# This file is automatically generated, DO NOT MODIFY.\\n")
        
        for item in itemset:
            item_count += 1
            if item_count % 1000 == 0:
                print(f"[DEBUG] 已处理 {{item_count}} 条消息...")
            
            msg_text = str(item.message) + "\\n" + str(getattr(item, "prim_local_buffer_string", ""))
            
            if str(item.message_id) != "MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ":
                continue
            
            add_req_count += 1
            
            # ---- 解析 CK / IK ----
            ck_str = extract_ascii_array_lines(msg_text, 'ck')
            ik_str = extract_ascii_array_lines(msg_text, 'ik')
            
            # 输出 ADD_REQ 详细信息到日志
            print(f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] 时间戳: {{item.timestamp}}")
            print(f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] CK: {{ck_str}}")
            print(f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] IK: {{ik_str}}")
            print(f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] 消息内容: {{str(item.message)[:200]}}...")
            
            if not ck_str or not ik_str:
                print(f"[DEBUG] ADD_REQ 中未找到 CK 或 IK")
                continue
            
            # 去掉前面的 "0x"
            ck_hex = ck_str[2:] if ck_str.startswith("0x") else ck_str
            ik_hex = ik_str[2:] if ik_str.startswith("0x") else ik_str
            ck_ik_found_count += 1
            
            # ---- 解析每个 ipsec_info[x] 的 src/dst IP + SPI + dir ----
            ipsec_infos = parse_ipsec_info_blocks(msg_text)
            
            print(f"[DEBUG] 解析到 {{len(ipsec_infos)}} 个 ipsec_info 条目")
            if len(ipsec_infos) == 0:
                print(f"[DEBUG] 警告：未解析到任何 ipsec_info，msg_text 长度: {{len(msg_text)}}")
                # 输出前 500 个字符用于调试
                print(f"[DEBUG] msg_text 前 500 字符: {{msg_text[:500]}}")
            
            for info in ipsec_infos:
                print(f"[DEBUG] 处理 ipsec_info[{{info['index']}}]: src_ip={{info['src_ip']}}, dst_ip={{info['dst_ip']}}, spi={{info['spi_hex']}}")
                src_ip = info["src_ip"]
                dst_ip = info["dst_ip"]
                spi_hex = info["spi_hex"]
                direction = info["direction"] or "?"
                
                if not spi_hex:
                    # 没 spi 的就跳过
                    continue
                
                protocol = detect_protocol(src_ip or dst_ip)
                
                # 用 (protocol, src_ip, dst_ip, spi, ck, ik) 做 key 去重
                sa_key = (protocol, src_ip, dst_ip, spi_hex, ck_hex, ik_hex)
                if sa_key in seen_sa:
                    continue
                seen_sa.add(sa_key)
                
                # 这里用的是"精确 SPI + 精确 IP"，完全符合 Wireshark 格式：
                # Protocol, Src IP, Dest IP, SPI, Encryption, Encryption Key, Authentication, Authentication Key
                out.write(f"\\"{{protocol}}\\",\\"{{src_ip or '*'}}\\",\\"{{dst_ip or '*'}}\\",\\"{{spi_hex}}\\",\\"{{encry_algo}}\\",\\"0x{{ck_hex}}\\",\\"{{integ_algo}}\\",\\"0x{{ik_hex}}\\"\\n")
                sa_written_count += 1
                print(f"[DEBUG] 写入 SA: Protocol={{protocol}}, SrcIP={{src_ip}}, DstIP={{dst_ip}}, SPI={{spi_hex}}, Direction={{direction}}")
        
        print(f"[DEBUG] 解析完成统计:")
        print(f"  - 总消息数: {{item_count}}")
        print(f"  - ADD_REQ 消息数: {{add_req_count}}")
        print(f"  - 找到 CK/IK 数: {{ck_ik_found_count}}")
        print(f"  - 写入 SA 数: {{sa_written_count}}")
        print(f"  - 唯一 SA 数: {{len(seen_sa)}}")

# 主逻辑
log_folder = r"{log_folder}"
elg_files = {json.dumps(elg_files)}
muxz_files = {json.dumps(muxz_files)}
output_file = r"{output_file}"
clear_history = {str(clear_history)}

# 合并所有 .elg 和 .muxz 文件
all_files = elg_files + muxz_files

print(f"[DEBUG] log_folder: {{log_folder}}")
print(f"[DEBUG] elg_files: {{elg_files}}")
print(f"[DEBUG] muxz_files: {{muxz_files}}")
print(f"[DEBUG] all_files: {{all_files}}")
print(f"[DEBUG] all_files count: {{len(all_files)}}")
print(f"[DEBUG] output_file: {{output_file}}")
print(f"[DEBUG] clear_history: {{clear_history}}")

# 确保输出目录存在
output_dir = os.path.dirname(output_file)
if output_dir:
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {{output_dir}}")

success_count = 0
if not all_files:
    print(f"[WARNING] 文件列表为空，将创建空文件")
    # 即使没有文件，也创建输出文件（至少写入文件头）
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# This file is automatically generated, DO NOT MODIFY.\\n")
            f.write("# No SA data found in the processed files.\\n")
        print(f"[DEBUG] 已创建空文件: {{output_file}}")
    except Exception as e:
        print(f"[ERROR] 创建空文件失败: {{str(e)}}")
        import traceback
        traceback.print_exc()
else:
    for i, filename in enumerate(all_files):
        file_path = os.path.join(log_folder, filename)
        file_mode = 'w' if (i == 0 and clear_history) else 'a'
        print(f"[DEBUG] 准备处理文件 {{i+1}}/{{len(all_files)}}: {{filename}}")
        print(f"[DEBUG] 文件路径: {{file_path}}")
        print(f"[DEBUG] 文件模式: {{file_mode}}")
        try:
            parse_elg_esp_sa(file_path, output_file, file_mode)
            success_count += 1
            print(f"Processed: {{filename}}")
        except Exception as e:
            print(f"Error processing {{filename}}: {{str(e)}}")
            import traceback
            traceback.print_exc()

# 检查文件是否存在
if os.path.exists(output_file):
    file_size = os.path.getsize(output_file)
    print(f"Output file exists: {{output_file}} (size: {{file_size}} bytes)")
else:
    print(f"WARNING: Output file does not exist: {{output_file}}")

print(f"Output file: {{output_file}}")
print(f"Success count: {{success_count}}")
'''
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            script_path = f.name
            f.write(script_content)
        
        try:
            # 使用虚拟环境的 Python 执行脚本
            result = subprocess.run(
                [venv_python, script_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 输出结果（处理可能的编码错误）
            if result.stdout:
                try:
                    stdout_text = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='replace')
                    for line in stdout_text.splitlines():
                        self.status_updated.emit(line)
                        print(f"[STDOUT] {line}")
                except Exception as e:
                    print(f"[WARNING] 解析 stdout 失败: {str(e)}")
            
            if result.stderr:
                try:
                    stderr_text = result.stderr if isinstance(result.stderr, str) else result.stderr.decode('utf-8', errors='replace')
                    for line in stderr_text.splitlines():
                        self.status_updated.emit(f"[STDERR] {line}")
                        print(f"[STDERR] {line}")
                except Exception as e:
                    print(f"[WARNING] 解析 stderr 失败: {str(e)}")
            
            if result.returncode != 0:
                stderr_text = result.stderr if isinstance(result.stderr, str) else (result.stderr.decode('utf-8', errors='replace') if result.stderr else '')
                error_msg = f"{self.tr('解析失败:')} {stderr_text}"
                self.status_updated.emit(f"[ERROR] {error_msg}")
                print(f"[ERROR] {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # 检查文件是否存在
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                self.status_updated.emit(f"[DEBUG] 文件已创建: {output_file} (大小: {file_size} 字节)")
                print(f"[DEBUG] 文件已创建: {output_file} (大小: {file_size} 字节)")
            else:
                self.status_updated.emit(f"[WARNING] 文件不存在: {output_file}")
                print(f"[WARNING] 文件不存在: {output_file}")
            
            # 提取成功数量
            success_count = len(elg_files)  # 默认值
            for line in result.stdout.splitlines():
                if "Success count:" in line:
                    try:
                        success_count = int(line.split(":")[-1].strip())
                    except:
                        pass
            
            # 最后调用提取 pcap 功能
            if muxz_files:
                self.status_updated.emit(self.tr("开始提取 pcap..."))
                extract_result = self._extract_pcap_from_mtklog()
                if extract_result.get('success'):
                    return {
                        'success': True,
                        'esp_sa_file': output_file,
                        'success_count': success_count,
                        'total_files': len(elg_files),
                        'pcap_extracted': True
                    }
                else:
                    return {
                        'success': True,
                        'esp_sa_file': output_file,
                        'success_count': success_count,
                        'total_files': len(elg_files),
                        'pcap_extracted': False,
                        'pcap_error': extract_result.get('error', '')
                    }
            else:
                return {
                    'success': True,
                    'esp_sa_file': output_file,
                    'success_count': success_count,
                    'total_files': len(elg_files),
                    'pcap_extracted': False,
                    'pcap_error': self.tr('没有找到 muxz 文件，跳过 pcap 提取')
                }
        finally:
            # 删除临时脚本文件
            try:
                os.unlink(script_path)
            except:
                pass
    
    def _parse_elg_esp_sa(self, elg_file, output_file, file_mode, elt_path):
        """解析 ELG 文件提取 ESP SA 信息"""
        import re
        import sys
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 确保 ELT 路径在 sys.path 中
        if elt_path not in sys.path:
            sys.path.insert(0, elt_path)
        
        import mace
        
        def extract_ascii_array_lines(msg_text, array_name):
            """从原始 prim_local_buffer_string 中解析 Array[xx] 格式的 ASCII 数据"""
            lines = msg_text.splitlines()
            collecting = False
            hex_vals = []
            
            for line in lines:
                if not collecting:
                    if array_name in line and "Array[" in line:
                        collecting = True
                    continue
                else:
                    if re.match(r'^\S', line):
                        break
                    m = re.search(r'0x([0-9a-fA-F]{2})', line)
                    if m:
                        hex_vals.append(m.group(1))
            
            if not hex_vals:
                return None
            
            ascii_str = ''.join(bytes.fromhex(h).decode('ascii', errors='ignore') for h in hex_vals)
            return ascii_str.split('\x00')[0]
        
        def normalize_ip(ip_str):
            """去掉前后空格和中括号，返回干净的 IP 字符串。"""
            if not ip_str:
                return None
            ip_str = ip_str.strip()
            if ip_str.startswith('[') and ip_str.endswith(']'):
                ip_str = ip_str[1:-1]
            return ip_str
        
        def detect_protocol(ip_str):
            """根据 IP 字符串简单判断是 IPv4 还是 IPv6。"""
            if not ip_str:
                return "IPv6"
            if ':' in ip_str:
                return "IPv6"
            if '.' in ip_str:
                return "IPv4"
            return "IPv6"
        
        def parse_ipsec_info_blocks(msg_text):
            """从 MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ 的文本中解析出 ipsec_info[x] 的各项"""
            infos = []
            
            # 用正则把每个 ipsec_info[x] 结构 block 切出来
            pattern = r'(ipsec_info\[(\d+)\] = \(struct\)[\s\S]*?)(?=ipsec_info\[\d+\] = \(struct\)|\n\t\tindex =|\Z)'
            for block, idx_str in re.findall(pattern, msg_text):
                idx = int(idx_str)
                
                # 复用前面的 ASCII 数组解析函数
                src_ip_raw = extract_ascii_array_lines(block, 'src_ip')
                dst_ip_raw = extract_ascii_array_lines(block, 'dst_ip')
                spi_raw = extract_ascii_array_lines(block, 'spi')
                
                src_ip = normalize_ip(src_ip_raw)
                dst_ip = normalize_ip(dst_ip_raw)
                
                spi_hex = None
                if spi_raw:
                    spi_raw = spi_raw.strip()
                    # 这里 spi_raw 是十进制字符串，如 "1583052695"
                    try:
                        spi_int = int(spi_raw)
                        # Wireshark 接受 "0x..." 格式，长度不限，这里统一成小写十六进制
                        spi_hex = "0x{:x}".format(spi_int)
                    except ValueError:
                        # 如果解析失败，直接原样写入（极少发生）
                        spi_hex = spi_raw
                
                # 解析 dir = 0x01 / 0x00
                m_dir = re.search(r'dir\s*=\s*0x([0-9a-fA-F]+)', block)
                direction = None
                if m_dir:
                    dir_val = int(m_dir.group(1), 16)
                    # 一般 1 表示 OUT, 0 表示 IN
                    direction = "OUT" if dir_val == 0x1 else "IN"
                
                infos.append(
                    {
                        "index": idx,
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "spi_hex": spi_hex,
                        "direction": direction,
                    }
                )
            
            return infos
        
        log_handle = mace.open_log_file(elg_file)
        itemset = mace.create_itemset(log_handle)
        
        # 只订阅 ADD_REQ 就足够生成 SA 文件了
        itemset.subscribe_primitive('MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ')
        
        seen_sa = set()
        encry_algo = "AES-CBC [RFC3602]"
        integ_algo = "HMAC-SHA-1-96 [RFC2404]"
        
        print(f"[DEBUG] 打开文件: {output_file}, 模式: {file_mode}")
        
        # 统计信息
        item_count = 0
        add_req_count = 0
        ck_ik_found_count = 0
        sa_written_count = 0
        
        with open(output_file, file_mode, encoding="utf-8") as out:
            if file_mode == 'w':
                out.write("# This file is automatically generated, DO NOT MODIFY.\n")
                print(f"[DEBUG] 写入文件头")
            
            for item in itemset:
                item_count += 1
                if item_count % 1000 == 0:
                    print(f"[DEBUG] 已处理 {item_count} 条消息...")
                
                msg_text = str(item.message) + "\n" + str(getattr(item, "prim_local_buffer_string", ""))
                
                if str(item.message_id) != "MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ":
                    continue
                
                add_req_count += 1
                
                # ---- 解析 CK / IK ----
                ck_str = extract_ascii_array_lines(msg_text, 'ck')
                ik_str = extract_ascii_array_lines(msg_text, 'ik')
                
                # 输出 ADD_REQ 详细信息到日志
                add_req_info = f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] 时间戳: {item.timestamp}\n"
                add_req_info += f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] CK: {ck_str}\n"
                add_req_info += f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] IK: {ik_str}\n"
                add_req_info += f"[MSG_ID_IMCB_IMC_REG_IPSEC_ADD_REQ] 消息内容: {str(item.message)[:200]}..."
                
                self.status_updated.emit(add_req_info)
                print(add_req_info)
                
                if not ck_str or not ik_str:
                    print(f"[DEBUG] ADD_REQ 中未找到 CK 或 IK")
                    continue
                
                # 去掉前面的 "0x"
                ck_hex = ck_str[2:] if ck_str.startswith("0x") else ck_str
                ik_hex = ik_str[2:] if ik_str.startswith("0x") else ik_str
                ck_ik_found_count += 1
                
                # ---- 解析每个 ipsec_info[x] 的 src/dst IP + SPI + dir ----
                ipsec_infos = parse_ipsec_info_blocks(msg_text)
                
                print(f"[DEBUG] 解析到 {len(ipsec_infos)} 个 ipsec_info 条目")
                if len(ipsec_infos) == 0:
                    print(f"[DEBUG] 警告：未解析到任何 ipsec_info，msg_text 长度: {len(msg_text)}")
                    # 输出前 500 个字符用于调试
                    print(f"[DEBUG] msg_text 前 500 字符: {msg_text[:500]}")
                
                for info in ipsec_infos:
                    print(f"[DEBUG] 处理 ipsec_info[{info['index']}]: src_ip={info['src_ip']}, dst_ip={info['dst_ip']}, spi={info['spi_hex']}")
                    src_ip = info["src_ip"]
                    dst_ip = info["dst_ip"]
                    spi_hex = info["spi_hex"]
                    direction = info["direction"] or "?"
                    
                    if not spi_hex:
                        # 没 spi 的就跳过
                        continue
                    
                    protocol = detect_protocol(src_ip or dst_ip)
                    
                    # 用 (protocol, src_ip, dst_ip, spi, ck, ik) 做 key 去重
                    sa_key = (protocol, src_ip, dst_ip, spi_hex, ck_hex, ik_hex)
                    if sa_key in seen_sa:
                        continue
                    seen_sa.add(sa_key)
                    
                    
                    # 这里用的是"精确 SPI + 精确 IP"，完全符合 Wireshark 格式：
                    # Protocol, Src IP, Dest IP, SPI, Encryption, Encryption Key, Authentication, Authentication Key
                    out.write(
                        f"\"{protocol}\","
                        f"\"{src_ip or '*'}\",\"{dst_ip or '*'}\","
                        f"\"{spi_hex}\","
                        f"\"{encry_algo}\",\"0x{ck_hex}\","
                        f"\"{integ_algo}\",\"0x{ik_hex}\"\n"
                    )
                    sa_written_count += 1
                    print(f"[DEBUG] 写入 SA: Protocol={protocol}, SrcIP={src_ip}, DstIP={dst_ip}, SPI={spi_hex}, Direction={direction}")
            
            print(f"[DEBUG] 解析完成统计:")
            print(f"  - 总消息数: {item_count}")
            print(f"  - ADD_REQ 消息数: {add_req_count}")
            print(f"  - 找到 CK/IK 数: {ck_ik_found_count}")
            print(f"  - 写入 SA 数: {sa_written_count}")
            print(f"  - 唯一 SA 数: {len(seen_sa)}")
            if len(seen_sa) == 0:
                print(f"[WARNING] 未找到任何 SA 数据")
    
    def _check_python37_available(self):
        """检查系统是否有 Python 3.7"""
        try:
            # 方法1: 尝试使用 py -3.7 --version
            result = subprocess.run(
                ["py", "-3.7", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        try:
            # 方法2: 使用 py --list 查找
            result = subprocess.run(
                ["py", "--list"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        # 方法3: 检查常见安装路径
        common_paths = [
            r"C:\Python37\python.exe",
            r"C:\Python37-64\python.exe",
            r"C:\Program Files\Python37\python.exe",
            r"C:\Program Files (x86)\Python37\python.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return True, path
        
        return False, None
    
    def _get_venv_python_path(self, venv_path):
        """获取虚拟环境中的 Python 路径"""
        import sys
        if sys.platform == "win32":
            return os.path.join(venv_path, "Scripts", "python.exe")
        else:
            return os.path.join(venv_path, "bin", "python")
    
    def _check_venv_mace_installed(self, venv_python):
        """检查虚拟环境中是否安装了 mace"""
        try:
            result = subprocess.run(
                [venv_python, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return "mace" in result.stdout.lower()
        except Exception:
            pass
        return False
    
    def _install_mace_in_venv(self, venv_python, elt_path):
        """在虚拟环境中安装 mace"""
        mace_install_path = os.path.join(elt_path, "Automation", "MACE2", "Mace2Python")
        install_script = os.path.join(mace_install_path, "install.py")
        
        if not os.path.exists(install_script):
            return False, f"{self.tr('找不到 install.py:')} {install_script}"
        
        try:
            result = subprocess.run(
                [venv_python, "install.py"],
                cwd=mace_install_path,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                return False, f"{self.tr('mace 安装失败:')} {result.stderr}"
            return True, None
        except Exception as e:
            return False, f"{self.tr('mace 安装异常:')} {str(e)}"
    
    def stop(self):
        """停止操作"""
        self.stop_flag = True


class PySide6OtherOperationsManager(QObject):
    """其他操作管理器"""
    
    status_message = Signal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.config_file = os.path.expanduser("~/.netui/tool_config.json")
        self.tool_config = self._load_tool_config()
        self.worker = None
        self.progress_dialog = None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def _load_tool_config(self):
        """加载工具配置"""
        defaults = {
            "mtk_tools": [],
            "qualcomm_tools": [],
            "wireshark_path": "",
            "storage_path": "",
            "last_used_mtk": "",
            "last_used_qualcomm": "",
            "last_used_wireshark": "",
            "update_feed_url": DEFAULT_UPDATE_FEED_URL,
            "update_auto_launch_installer": True,
            "update_timeout": 15,
            "update_last_checked_at": 0
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    stored_config = json.load(f)
                    if isinstance(stored_config, dict):
                        stored_config.pop("update_download_dir", None)
                        defaults.update(stored_config)
        except Exception:
            pass

        defaults["update_feed_url"] = defaults.get("update_feed_url") or DEFAULT_UPDATE_FEED_URL
        defaults["update_last_checked_at"] = float(defaults.get("update_last_checked_at") or 0)

        return defaults
    
    def _save_tool_config(self):
        """保存工具配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tool_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def _check_tool_config(self, check_mtk=True, check_qualcomm=False, check_wireshark=True):
        """检查工具配置"""
        from PySide6.QtWidgets import QMessageBox
        
        if check_mtk and not self.tool_config.get("mtk_tools"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置MTK工具，是否现在配置？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("mtk_tools"))
            return False
        
        if check_qualcomm and not self.tool_config.get("qualcomm_tools"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置高通工具，是否现在配置？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("qualcomm_tools"))
            return False
        
        if check_wireshark and not self.tool_config.get("wireshark_path"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置Wireshark路径，是否现在配置？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("wireshark_path"))
            return False
        
        return True
    
    def _find_muxz_files(self, log_folder):
        """查找muxz文件（递归查找子目录）"""
        try:
            muxz_files = []
            # 递归查找所有 .muxz 文件
            for root, dirs, files in os.walk(log_folder):
                for file in files:
                    if file.endswith('.muxz'):
                        # 保存相对路径（相对于 log_folder）
                        rel_path = os.path.relpath(os.path.join(root, file), log_folder)
                        muxz_files.append(rel_path)
            return muxz_files
        except Exception as e:
            print(f"[ERROR] 查找 muxz 文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _find_hdf_files(self, log_folder):
        """查找hdf文件"""
        try:
            hdf_files = []
            for file in os.listdir(log_folder):
                if file.endswith('.hdf'):
                    hdf_files.append(file)
            return hdf_files
        except Exception:
            return []
    
    def _select_mtk_tool(self):
        """选择MTK工具"""
        try:
            if len(self.tool_config["mtk_tools"]) == 1:
                return self.tool_config["mtk_tools"][0]
            
            # 创建选择对话框
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QMessageBox
            
            dialog = QDialog()
            dialog.setWindowTitle(self.tr("选择MTK工具"))
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            
            label = QLabel(self.tr("请选择一个MTK工具:"))
            layout.addWidget(label)
            
            list_widget = QListWidget()
            for tool in self.tool_config["mtk_tools"]:
                display_text = f"{tool['name']} (Python {tool['python_version']})"
                list_widget.addItem(display_text)
            layout.addWidget(list_widget)
            
            button_layout = QHBoxLayout()
            confirm_btn = QPushButton(self.tr("确定"))
            cancel_btn = QPushButton(self.tr("取消"))
            
            result = [None]
            
            def on_confirm():
                current_item = list_widget.currentItem()
                if current_item:
                    index = list_widget.row(current_item)
                    result[0] = self.tool_config["mtk_tools"][index]
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, self.tr("选择错误"), "请选择一个MTK工具")
            
            def on_cancel():
                dialog.reject()
            
            confirm_btn.clicked.connect(on_confirm)
            cancel_btn.clicked.connect(on_cancel)
            
            button_layout.addStretch()
            button_layout.addWidget(confirm_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                return result[0]
            else:
                return None
            
        except Exception:
            return None
    
    def _select_qualcomm_tool(self):
        """选择高通工具"""
        try:
            # 确保qualcomm_tools键存在
            if "qualcomm_tools" not in self.tool_config:
                self.tool_config["qualcomm_tools"] = []
            
            if len(self.tool_config["qualcomm_tools"]) == 1:
                return self.tool_config["qualcomm_tools"][0]
            
            # 创建选择对话框
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QMessageBox
            
            dialog = QDialog()
            dialog.setWindowTitle(self.tr("选择高通工具"))
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            
            label = QLabel(self.tr("请选择一个高通工具:"))
            layout.addWidget(label)
            
            list_widget = QListWidget()
            for tool in self.tool_config["qualcomm_tools"]:
                display_text = f"{tool['name']}"
                list_widget.addItem(display_text)
            layout.addWidget(list_widget)
            
            button_layout = QHBoxLayout()
            confirm_btn = QPushButton(self.tr("确定"))
            cancel_btn = QPushButton(self.tr("取消"))
            
            result = [None]
            
            def on_confirm():
                current_item = list_widget.currentItem()
                if current_item:
                    index = list_widget.row(current_item)
                    result[0] = self.tool_config["qualcomm_tools"][index]
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, self.tr("选择错误"), "请选择一个高通工具")
            
            def on_cancel():
                dialog.reject()
            
            confirm_btn.clicked.connect(on_confirm)
            cancel_btn.clicked.connect(on_cancel)
            
            button_layout.addStretch()
            button_layout.addWidget(confirm_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                return result[0]
            else:
                return None
            
        except Exception:
            return None
    
    def merge_mtklog(self):
        """合并MTKlog文件"""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # 检查工具配置
            if not self._check_tool_config():
                return
            
            # 选择MTKlog文件夹
            log_folder = QFileDialog.getExistingDirectory(None, self.tr("选择MTKlog文件夹"))
            if not log_folder:
                return
            
            # 检查文件夹中是否有muxz文件
            muxz_files = self._find_muxz_files(log_folder)
            if not muxz_files:
                QMessageBox.critical(None, self.tr("错误"), "选择的文件夹中没有找到muxz文件")
                return
            
            # 选择MTK工具
            mtk_tool = self._select_mtk_tool()
            if not mtk_tool:
                return
            
            # 启动工作线程
            self._start_worker('merge_mtklog', 
                             log_folder=log_folder,
                             muxz_files=muxz_files,
                             mtk_tool=mtk_tool)
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"合并MTKlog失败: {str(e)}")
    
    def extract_pcap_from_mtklog(self):
        """从MTKlog中提取pcap文件"""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # 检查工具配置
            if not self._check_tool_config():
                return
            
            # 选择MTKlog文件夹
            log_folder = QFileDialog.getExistingDirectory(None, self.tr("选择MTKlog文件夹"))
            if not log_folder:
                return
            
            # 检查文件夹中是否有muxz文件
            muxz_files = self._find_muxz_files(log_folder)
            if not muxz_files:
                QMessageBox.critical(None, self.tr("错误"), "选择的文件夹中没有找到muxz文件")
                return
            
            # 选择MTK工具
            mtk_tool = self._select_mtk_tool()
            if not mtk_tool:
                return
            
            # 启动工作线程
            self._start_worker('extract_pcap_from_mtklog',
                             log_folder=log_folder,
                             muxz_files=muxz_files,
                             mtk_tool=mtk_tool,
                             wireshark_path=self.tool_config.get("wireshark_path"))
            
        except Exception as e:
            error_msg = f"❌ {self.tr('提取pcap失败:')} {str(e)}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_msg, "red")
            else:
                self.status_message.emit(error_msg)
    
    def merge_pcap(self):
        """合并PCAP文件"""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # 检查Wireshark配置
            if not self.tool_config.get("wireshark_path"):
                message = (
                    f"{self.tr('未配置Wireshark路径')}\n\n"
                    f"{self.tr('请安装Wireshark，并且在工具配置里配置路径。')}\n"
                    f"{self.tr('示例路径:')} C:\\Program Files\\Wireshark\n\n"
                    f"{self.tr('是否现在配置？')}"
                )
                reply = QMessageBox.question(
                    None, self.tr("配置缺失"), message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.configure_tools()
                    if not self.tool_config.get("wireshark_path"):
                        return
                else:
                    return
            
            # 获取用户输入的文件夹路径
            folder_path = QFileDialog.getExistingDirectory(None, self.tr("选择包含PCAP文件的文件夹"))
            if not folder_path:
                return
            
            # 启动工作线程
            self._start_worker('merge_pcap',
                             folder_path=folder_path,
                             wireshark_path=self.tool_config.get("wireshark_path"))
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"合并PCAP失败: {str(e)}")
    
    def extract_pcap_from_qualcomm_log(self):
        """从高通log提取pcap文件"""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # 检查工具配置
            if not self._check_tool_config(check_mtk=False, check_qualcomm=True, check_wireshark=True):
                return
            
            # 选择高通log文件夹
            log_folder = QFileDialog.getExistingDirectory(None, self.tr("选择高通log文件夹"))
            if not log_folder:
                return
            
            # 检查文件夹中是否有hdf文件
            hdf_files = self._find_hdf_files(log_folder)
            if not hdf_files:
                QMessageBox.critical(None, self.tr("错误"), "选择的文件夹中没有找到hdf文件")
                return
            
            # 选择高通工具
            qualcomm_tool = self._select_qualcomm_tool()
            if not qualcomm_tool:
                return
            
            # 启动工作线程
            self._start_worker('extract_pcap_from_qualcomm_log',
                             log_folder=log_folder,
                             hdf_files=hdf_files,
                             qualcomm_tool=qualcomm_tool,
                             wireshark_path=self.tool_config.get("wireshark_path"))
            
        except Exception as e:
            error_msg = f"❌ {self.tr('提取高通pcap失败:')} {str(e)}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_msg, "red")
            else:
                self.status_message.emit(error_msg)
    
    def _start_worker(self, operation_type, **kwargs):
        """启动工作线程"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
            
            # 保存原始参数（用于重新启动）
            self._last_worker_kwargs = kwargs.copy()
            self._last_operation_type = operation_type
            
            # 创建进度对话框
            self.progress_dialog = QDialog()
            self.progress_dialog.setWindowTitle(self.tr("正在执行操作..."))
            self.progress_dialog.setModal(True)
            self.progress_dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(self.progress_dialog)
            
            self.status_label = QLabel("准备中...")
            layout.addWidget(self.status_label)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            layout.addWidget(self.progress_bar)
            
            cancel_btn = QPushButton(self.tr("取消"))
            cancel_btn.clicked.connect(self._cancel_worker)
            layout.addWidget(cancel_btn)
            
            # 创建工作线程
            self.worker = OtherOperationsWorker(operation_type, lang_manager=self.lang_manager, **kwargs)
            self.worker.operation_type = operation_type  # 保存操作类型
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.finished.connect(self._on_worker_finished)
            self.worker.error_occurred.connect(self._on_worker_error)
            
            # 启动线程
            self.worker.start()
            
            # 显示对话框
            self.progress_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"启动工作线程失败: {str(e)}")
    
    def _cancel_worker(self):
        """取消工作线程"""
        if self.worker:
            self.worker.stop()
            self.worker.terminate()
            self.worker.wait()
            self.worker = None
        
        if self.progress_dialog:
            self.progress_dialog.reject()
            self.progress_dialog = None
    
    def _on_worker_error(self, error_msg):
        """工作线程错误"""
        if self.progress_dialog:
            self.progress_dialog.reject()
            self.progress_dialog = None
        
        # 在日志中显示错误信息
        error_display = f"❌ {self.tr('操作失败:')} {error_msg}"
        if hasattr(self, 'log_message'):
            self.log_message.emit(error_display)
        else:
            self.status_message.emit(error_display)
        
        self.worker = None
    
    def _on_worker_finished(self, result):
        """工作线程完成"""
        if self.progress_dialog:
            self.progress_dialog.accept()
            self.progress_dialog = None
        
        # 检查是否是需要 Python 3.7 的错误
        error_value = result.get('error', '')
        # 检查错误码或错误信息中是否包含 python3.7 相关提示
        is_python37_error = (
            error_value == 'NEED_PYTHON37' or 
            (isinstance(error_value, str) and (
                'python3.7' in error_value.lower() or 
                'python 3.7' in error_value.lower() or 
                'please install' in error_value.lower()
            ))
        )
        
        if not result.get('success', False) and is_python37_error:
            # 检查是否已经有 venv_python，如果有说明虚拟环境已经处理过了，不应该再次处理
            if hasattr(self, '_last_worker_kwargs') and self._last_worker_kwargs.get('venv_python'):
                # 已经有虚拟环境 Python，说明虚拟环境处理过了，但可能安装失败
                # 直接显示错误，不再重复处理虚拟环境
                error_msg = result.get('error', self.tr('操作失败'))
                error_display = f"❌ {self.tr('操作失败:')} {error_msg}"
                if hasattr(self, 'log_message'):
                    self.log_message.emit(error_display)
                else:
                    self.status_message.emit(error_display)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    self.tr("操作失败"),
                    self.tr("虚拟环境已就绪，但操作仍然失败。\n\n错误信息：\n") + error_msg
                )
                return
            
            # 需要在工作线程中处理虚拟环境
            elt_path = result.get('elt_path')
            # 如果没有 elt_path，尝试从保存的参数中获取
            if not elt_path and hasattr(self, '_last_worker_kwargs'):
                mtk_tool = self._last_worker_kwargs.get('mtk_tool')
                if mtk_tool and isinstance(mtk_tool, dict):
                    elt_path = mtk_tool.get('base_path')
            
            if elt_path:
                # 启动虚拟环境处理工作线程
                self._start_venv_worker(elt_path)
                return
        
        if result.get('success', False):
            if result.get('merge_file'):
                # 在日志中显示成功信息
                success_msg = f"✅ {self.tr('PCAP提取成功完成！')}\n"
                success_msg += f"📁 {self.tr('合并文件:')} {result['merge_file']}\n"
                success_msg += f"📊 {self.tr('处理文件:')} {result.get('file_count', result.get('total_files', 0))} {self.tr('个')}"
                
                # 发送到日志栏
                if hasattr(self, 'log_message'):
                    self.log_message.emit(success_msg)
                else:
                    # 如果没有日志信号，使用状态消息
                    self.status_message.emit(success_msg)
                
                # 自动打开pcap文件
                merge_file = result['merge_file']
                if os.path.exists(merge_file):
                    try:
                        os.startfile(merge_file)
                    except Exception as e:
                        error_msg = f"⚠️ {self.tr('自动打开文件失败:')} {str(e)}"
                        if hasattr(self, 'log_message'):
                            self.log_message.emit(error_msg)
                        else:
                            self.status_message.emit(error_msg)
            elif result.get('esp_sa_file'):
                # MTK SIP DECODE 成功
                success_msg = f"✅ {self.tr('MTK SIP DECODE 完成！')}\n"
                success_msg += f"📁 {self.tr('ESP SA 文件:')} {result['esp_sa_file']}\n"
                if result.get('pcap_extracted'):
                    success_msg += f"📊 {self.tr('PCAP 提取:')} {self.tr('成功')}"
                else:
                    success_msg += f"📊 {self.tr('PCAP 提取:')} {self.tr('跳过')}"
                    if result.get('pcap_error'):
                        success_msg += f" ({result['pcap_error']})"
                
                if hasattr(self, 'log_message'):
                    self.log_message.emit(success_msg)
                else:
                    self.status_message.emit(success_msg)
            else:
                # 在日志中显示成功信息
                success_msg = f"✅ {self.tr('操作成功完成！')}"
                if hasattr(self, 'log_message'):
                    self.log_message.emit(success_msg)
                else:
                    self.status_message.emit(success_msg)
        else:
            error_msg = result.get('error', self.tr('未知错误'))
            error_display = f"❌ {self.tr('操作失败:')} {error_msg}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_display)
            else:
                self.status_message.emit(error_display)
        
        self.worker = None
    
    def cleanup(self):
        """清理工作线程，在窗口关闭时调用"""
        if self.worker and self.worker.isRunning():
            try:
                self.worker.wait(3000)
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait(1000)
            except Exception:
                pass
            finally:
                self.worker = None
    
    def configure_tools(self):
        """配置MTK工具和Wireshark路径"""
        try:
            from ui.tools_config_dialog import ToolsConfigDialog
            
            dialog = ToolsConfigDialog(self.tool_config, parent=None)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 保存配置
                self._save_tool_config()
                QMessageBox.information(None, self.tr("成功"), "工具配置已保存")
        except Exception as e:
            QMessageBox.critical(None, self.tr("错误"), f"配置工具失败: {str(e)}")
    
    def show_input_text_dialog(self):
        """显示输入文本对话框"""
        from ui.input_text_dialog import InputTextDialog
        
        device = self.device_manager.validate_device_selection()
        if not device:
            self.status_message.emit(f"{self.tr('输入文本失败:')} {self.tr('请先选择设备')}")
            return
        
        try:
            # 创建并显示对话框
            dialog = InputTextDialog(device, parent=self.parent())
            dialog.exec()
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("输入文本失败: ") + str(e))
    
    def mtk_sip_decode(self):
        """MTK SIP DECODE"""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # 检查工具配置
            if not self._check_tool_config():
                return
            
            # 选择文件夹
            log_folder = QFileDialog.getExistingDirectory(None, self.tr("选择包含 .muxz 或 .elg 文件的文件夹"))
            if not log_folder:
                return
            
            # 查找 .muxz 和 .elg 文件
            muxz_files = self._find_muxz_files(log_folder)
            elg_files = self._find_elg_files(log_folder)
            
            # 调试信息
            print(f"[DEBUG] 查找文件 - log_folder: {log_folder}")
            print(f"[DEBUG] 找到 {len(muxz_files)} 个 .muxz 文件: {muxz_files}")
            print(f"[DEBUG] 找到 {len(elg_files)} 个 .elg 文件: {elg_files}")
            
            if not muxz_files and not elg_files:
                QMessageBox.critical(None, self.tr("错误"), self.tr("选择的文件夹中没有找到 .muxz 或 .elg 文件"))
                return
            
            # 选择MTK工具
            mtk_tool = self._select_mtk_tool()
            if not mtk_tool:
                return
            
            # 询问用户是否要清空历史加密信息
            reply = QMessageBox.question(
                None, 
                self.tr("清空历史加密信息"), 
                self.tr("是否要清空历史加密信息？\n\n选择\"是\"将清空现有的 esp_sa 文件\n选择\"否\"将追加到现有文件"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            clear_history = (reply == QMessageBox.StandardButton.Yes)
            
            # 启动工作线程
            self._start_worker('mtk_sip_decode',
                             log_folder=log_folder,
                             muxz_files=muxz_files,
                             elg_files=elg_files,
                             mtk_tool=mtk_tool,
                             clear_history=clear_history,
                             wireshark_path=self.tool_config.get("wireshark_path"))
            
        except Exception as e:
            error_msg = f"❌ {self.tr('MTK SIP DECODE失败:')} {str(e)}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_msg, "red")
            else:
                self.status_message.emit(error_msg)
    
    def _start_venv_worker(self, elt_path):
        """启动虚拟环境处理工作线程"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
        
        venv_path = self._get_venv_path()
        
        # 创建进度对话框
        self.venv_progress_dialog = QDialog()
        self.venv_progress_dialog.setWindowTitle(self.tr("处理虚拟环境..."))
        self.venv_progress_dialog.setModal(True)
        self.venv_progress_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(self.venv_progress_dialog)
        
        self.venv_status_label = QLabel("准备中...")
        layout.addWidget(self.venv_status_label)
        
        self.venv_progress_bar = QProgressBar()
        self.venv_progress_bar.setRange(0, 100)
        layout.addWidget(self.venv_progress_bar)
        
        cancel_btn = QPushButton(self.tr("取消"))
        layout.addWidget(cancel_btn)
        
        # 创建虚拟环境工作线程
        self.venv_worker = VenvWorker(elt_path, venv_path, self.lang_manager, self)
        self.venv_worker.progress_updated.connect(self.venv_progress_bar.setValue)
        self.venv_worker.status_updated.connect(self._on_venv_status_updated)
        self.venv_worker.finished.connect(self._on_venv_worker_finished)
        self.venv_worker.error_occurred.connect(self._on_venv_worker_error)
        self.venv_worker.request_user_confirm.connect(self._on_venv_request_confirm)
        
        cancel_btn.clicked.connect(self._cancel_venv_worker)
        
        # 启动线程
        self.venv_worker.start()
        
        # 显示对话框
        self.venv_progress_dialog.exec()
    
    def _on_venv_status_updated(self, status):
        """虚拟环境状态更新"""
        self.venv_status_label.setText(status)
        # 同时更新日志窗口
        if hasattr(self, 'log_message'):
            self.log_message.emit(status)
        else:
            self.status_message.emit(status)
    
    def _on_venv_request_confirm(self, title, message):
        """处理虚拟环境工作线程的用户确认请求"""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            None,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.venv_worker.set_user_response(reply)
    
    def _on_venv_worker_finished(self, result):
        """虚拟环境工作线程完成"""
        if self.venv_progress_dialog:
            self.venv_progress_dialog.accept()
            self.venv_progress_dialog = None
        
        if result.get('success'):
            # 虚拟环境处理成功，重新启动工作线程
            venv_python = result['venv_python']
            # 获取原始参数（从保存的参数中获取）
            original_kwargs = self._last_worker_kwargs.copy() if hasattr(self, '_last_worker_kwargs') else {}
            original_kwargs['venv_python'] = venv_python
            
            # 重新启动工作线程
            operation_type = self._last_operation_type if hasattr(self, '_last_operation_type') else 'mtk_sip_decode'
            self.venv_worker = None
            self._start_worker(operation_type, **original_kwargs)
        else:
            # 虚拟环境处理失败
            error_msg = result.get('error', self.tr('虚拟环境处理失败'))
            if error_msg == self.tr('Python 3.7 未安装'):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    self.tr("Python 3.7 未安装"),
                    self.tr("检测到需要 Python 3.7，但系统中未找到。\n\n请先安装 Python 3.7 (64bit)，然后重试。")
                )
            elif error_msg == self.tr('用户取消创建虚拟环境'):
                # 用户取消，不需要显示错误
                pass
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    self.tr("虚拟环境处理失败"),
                    self.tr("虚拟环境处理失败。\n\n错误信息：\n") + error_msg
                )
            
            error_display = f"❌ {self.tr('操作失败:')} {error_msg}"
            if hasattr(self, 'log_message'):
                self.log_message.emit(error_display)
            else:
                self.status_message.emit(error_display)
        
        self.venv_worker = None
    
    def _on_venv_worker_error(self, error_msg):
        """虚拟环境工作线程错误"""
        if self.venv_progress_dialog:
            self.venv_progress_dialog.reject()
            self.venv_progress_dialog = None
        
        error_display = f"❌ {self.tr('虚拟环境处理失败:')} {error_msg}"
        if hasattr(self, 'log_message'):
            self.log_message.emit(error_display)
        else:
            self.status_message.emit(error_display)
        
        self.venv_worker = None
    
    def _cancel_venv_worker(self):
        """取消虚拟环境工作线程"""
        if self.venv_worker:
            self.venv_worker.terminate()
            self.venv_worker.wait()
            self.venv_worker = None
        
        if self.venv_progress_dialog:
            self.venv_progress_dialog.reject()
            self.venv_progress_dialog = None
    
    def _find_elg_files(self, log_folder):
        """查找elg文件（递归查找子目录）"""
        try:
            elg_files = []
            # 递归查找所有 .elg 文件
            for root, dirs, files in os.walk(log_folder):
                for file in files:
                    if file.endswith('.elg'):
                        # 保存相对路径（相对于 log_folder）
                        rel_path = os.path.relpath(os.path.join(root, file), log_folder)
                        elg_files.append(rel_path)
            return elg_files
        except Exception as e:
            print(f"[ERROR] 查找 elg 文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_program_dir(self):
        """获取程序目录（支持打包成 exe）"""
        import sys
        if getattr(sys, 'frozen', False):
            # 打包后的 exe
            return os.path.dirname(sys.executable)
        else:
            # 开发环境
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _get_venv_path(self):
        """获取虚拟环境路径"""
        program_dir = self._get_program_dir()
        return os.path.join(program_dir, "python37")
    
    def _check_python37_available(self):
        """检查系统是否有 Python 3.7"""
        try:
            # 方法1: 尝试使用 py -3.7 --version
            result = subprocess.run(
                ["py", "-3.7", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        try:
            # 方法2: 使用 py --list 查找
            result = subprocess.run(
                ["py", "--list"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and "3.7" in result.stdout:
                return True, "py -3.7"
        except Exception:
            pass
        
        # 方法3: 检查常见安装路径
        common_paths = [
            r"C:\Python37\python.exe",
            r"C:\Python37-64\python.exe",
            r"C:\Program Files\Python37\python.exe",
            r"C:\Program Files (x86)\Python37\python.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return True, path
        
        return False, None
    
    def _get_venv_python_path(self, venv_path):
        """获取虚拟环境中的 Python 路径"""
        import sys
        if sys.platform == "win32":
            return os.path.join(venv_path, "Scripts", "python.exe")
        else:
            return os.path.join(venv_path, "bin", "python")
    
    def _check_venv_exists(self, venv_path):
        """检查虚拟环境是否存在且有效"""
        venv_python = self._get_venv_python_path(venv_path)
        return os.path.exists(venv_python)
    
    def _check_venv_mace_installed(self, venv_python):
        """检查虚拟环境中是否安装了 mace"""
        try:
            result = subprocess.run(
                [venv_python, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return "mace" in result.stdout.lower()
        except Exception:
            pass
        return False
    
    def _create_venv(self, venv_path, python37_cmd):
        """创建虚拟环境"""
        try:
            # 如果虚拟环境已存在，先删除
            if os.path.exists(venv_path):
                import shutil
                shutil.rmtree(venv_path)
            
            # 创建虚拟环境
            if python37_cmd.startswith("py -"):
                # 使用 py launcher
                cmd = ["py", "-3.7", "-m", "venv", venv_path]
            else:
                # 使用直接路径
                cmd = [python37_cmd, "-m", "venv", venv_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                return False, f"{self.tr('创建虚拟环境失败:')} {result.stderr}"
            
            # 验证虚拟环境是否创建成功
            venv_python = self._get_venv_python_path(venv_path)
            if not os.path.exists(venv_python):
                return False, self.tr("虚拟环境创建失败：找不到 Python 解释器")
            
            return True, None
        except Exception as e:
            return False, f"{self.tr('创建虚拟环境异常:')} {str(e)}"
    
    def _install_mace_in_venv(self, venv_python, elt_path):
        """在虚拟环境中安装 mace"""
        mace_install_path = os.path.join(elt_path, "Automation", "MACE2", "Mace2Python")
        install_script = os.path.join(mace_install_path, "install.py")
        
        if not os.path.exists(install_script):
            return False, f"{self.tr('找不到 install.py:')} {install_script}"
        
        try:
            result = subprocess.run(
                [venv_python, "install.py"],
                cwd=mace_install_path,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                return False, f"{self.tr('mace 安装失败:')} {result.stderr}"
            return True, None
        except Exception as e:
            return False, f"{self.tr('mace 安装异常:')} {str(e)}"


# 导出所有管理器
__all__ = [
    'PySide6BackgroundDataManager',
    'PySide6AppOperationsManager',
    'PySide6DeviceInfoManager',
    'PySide6HeraConfigManager',
    'PySide6OtherOperationsManager'
]

