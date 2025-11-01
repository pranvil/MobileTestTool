#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 剩余管理器集合
包含背景数据、APP操作、设备信息、赫拉配置、其他操作等管理器
"""

import subprocess
import os
import datetime
import json
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QDialog

from core.update_manager import DEFAULT_UPDATE_FEED_URL


class PyQtBackgroundDataManager(QObject):
    """背景数据管理器 - 使用完整实现"""
    
    status_message = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # text, color
    
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


class PyQtAppOperationsManager(QObject):
    """APP操作管理器 - 使用完整实现"""
    
    status_message = pyqtSignal(str)
    
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


class PyQtDeviceInfoManager(QObject):
    """设备信息管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 初始化设备信息管理器
        self._init_device_info_manager()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def _init_device_info_manager(self):
        """初始化设备信息管理器"""
        # 导入PyQt5版本的DeviceInfoManager
        from core.device_info_manager import DeviceInfoManager
        self.device_info_manager = DeviceInfoManager()
        
    def show_device_info(self):
        """显示手机信息"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            self.status_message.emit(self.tr("获取手机信息..."))
            
            # 调用原始的collect_device_info方法
            device_info = self.device_info_manager.collect_device_info(device)
            
            # 格式化显示设备信息
            info_text = "=" * 60 + "\n"
            info_text += self.tr("设备信息\n")
            info_text += "=" * 60 + "\n\n"
            
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
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("获取手机信息失败: ") + str(e))
    
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


class PyQtHeraConfigManager(QObject):
    """赫拉配置管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 导入独立的PyQt5赫拉配置管理器
        from core.hera_config_manager import PyQtHeraConfigManager as HeraManager
        self.hera_manager = HeraManager(device_manager, parent=self)
        # 连接信号
        self.hera_manager.status_message.connect(self.status_message.emit)
        
    def configure_hera(self):
        """赫拉配置"""
        self.hera_manager.configure_hera()
    
    def configure_collect_data(self):
        """赫拉测试数据收集"""
        self.hera_manager.configure_collect_data()


class OtherOperationsWorker(QThread):
    """其他操作工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(int)  # 进度 (0-100)
    status_updated = pyqtSignal(str)  # 状态消息
    finished = pyqtSignal(dict)  # 完成信号，返回结果字典
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, operation_type, **kwargs):
        super().__init__()
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.stop_flag = False
        
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
            
            # 获取MDLogMan.exe路径
            utilities_path = os.path.join(mtk_tool["base_path"], "Utilities")
            mdlogman_exe = os.path.join(utilities_path, "MDLogMan.exe")
            
            if not os.path.exists(mdlogman_exe):
                return {'success': False, 'error': f"{self.tr('找不到MDLogMan.exe:')} {mdlogman_exe}"}
            
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
                timeout=300,
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
            
            # 切换到elgcap目录
            elgcap_path = mtk_tool["elgcap_path"]
            python_path = mtk_tool["python_path"]
            embedded_python = os.path.join(python_path, "EmbeddedPython.exe")
            
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
                        timeout=300,
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
            wireshark_path = self.kwargs['wireshark_path']
            mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
            
            if not os.path.exists(mergecap_exe):
                return {'success': False, 'error': f"{self.tr('找不到mergecap.exe:')} {mergecap_exe}"}
            
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
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_updated.emit(self.tr("合并完成!"))
                self.progress_updated.emit(100)
                
                # 打开合并后的pcap文件
                os.startfile(merge_pcap_path)
                
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
                return {'success': False, 'error': f"{self.tr('找不到PCAP_Gen_2.0.exe:')} {pcap_gen_exe}"}
            
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
                        timeout=300,
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
                timeout=120,
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
    
    def stop(self):
        """停止操作"""
        self.stop_flag = True


class PyQtOtherOperationsManager(QObject):
    """其他操作管理器"""
    
    status_message = pyqtSignal(str)
    
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
        from PyQt5.QtWidgets import QMessageBox
        
        if check_mtk and not self.tool_config.get("mtk_tools"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置MTK工具，是否现在配置？"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("mtk_tools"))
            return False
        
        if check_qualcomm and not self.tool_config.get("qualcomm_tools"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置高通工具，是否现在配置？"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("qualcomm_tools"))
            return False
        
        if check_wireshark and not self.tool_config.get("wireshark_path"):
            reply = QMessageBox.question(
                None, self.tr("配置缺失"), self.tr("未配置Wireshark路径，是否现在配置？"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.configure_tools()
                return bool(self.tool_config.get("wireshark_path"))
            return False
        
        return True
    
    def _find_muxz_files(self, log_folder):
        """查找muxz文件"""
        try:
            muxz_files = []
            for file in os.listdir(log_folder):
                if file.endswith('.muxz'):
                    muxz_files.append(file)
            return muxz_files
        except Exception:
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
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QMessageBox
            
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
            
            if dialog.exec_() == QDialog.Accepted:
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
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QMessageBox
            
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
            
            if dialog.exec_() == QDialog.Accepted:
                return result[0]
            else:
                return None
            
        except Exception:
            return None
    
    def merge_mtklog(self):
        """合并MTKlog文件"""
        try:
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            
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
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            
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
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            
            # 检查Wireshark配置
            if not self.tool_config.get("wireshark_path"):
                reply = QMessageBox.question(
                    None, self.tr("配置缺失"), self.tr("未配置Wireshark路径，是否现在配置？"),
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
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
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            
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
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
            
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
            self.worker = OtherOperationsWorker(operation_type, **kwargs)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.finished.connect(self._on_worker_finished)
            self.worker.error_occurred.connect(self._on_worker_error)
            
            # 启动线程
            self.worker.start()
            
            # 显示对话框
            self.progress_dialog.exec_()
            
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
    
    def _on_worker_finished(self, result):
        """工作线程完成"""
        if self.progress_dialog:
            self.progress_dialog.accept()
            self.progress_dialog = None
        
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
    
    def configure_tools(self):
        """配置MTK工具和Wireshark路径"""
        try:
            from ui.tools_config_dialog import ToolsConfigDialog
            
            dialog = ToolsConfigDialog(self.tool_config, parent=None)
            if dialog.exec_() == QDialog.Accepted:
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
            dialog.exec_()
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("输入文本失败: ") + str(e))


# 导出所有管理器
__all__ = [
    'PyQtBackgroundDataManager',
    'PyQtAppOperationsManager',
    'PyQtDeviceInfoManager',
    'PyQtHeraConfigManager',
    'PyQtOtherOperationsManager'
]

