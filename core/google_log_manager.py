#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 Google日志管理器
适配原Tkinter版本的Google日志管理功能
"""

import subprocess
import os
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QProgressDialog


class BugreportWorker(QThread):
    """Bugreport工作线程"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, device, folder, lang_manager=None):
        super().__init__()
        self.device = device
        self.folder = folder
        self.lang_manager = lang_manager
        
    def run(self):
        """执行bugreport"""
        try:
            import subprocess
            bugreport_cmd = ["adb", "-s", self.device, "bugreport", self.folder]
            result = subprocess.run(bugreport_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                self.finished.emit({"success": False, "error": result.stderr.strip()})
            else:
                self.finished.emit({"success": True, "folder": self.folder})
        except Exception as e:
            self.error.emit(str(e))


class DeleteBugreportWorker(QThread):
    """删除Bugreport工作线程"""
    
    finished = pyqtSignal(bool, str)
    
    def __init__(self, device, lang_manager=None):
        super().__init__()
        self.device = device
        self.lang_manager = lang_manager
        
    def run(self):
        """执行删除bugreport"""
        try:
            delete_cmd = ["adb", "-s", self.device, "shell", "rm", "-rf", "/data/user_de/0/com.android.shell/files/bugreports"]
            result = subprocess.run(delete_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                self.finished.emit(False, result.stderr.strip())
            else:
                self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class GoogleLogWorker(QThread):
    """Google日志工作线程"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, device, operation, google_log_folder=None, lang_manager=None):
        super().__init__()
        self.device = device
        self.operation = operation
        self.google_log_folder = google_log_folder
        self.lang_manager = lang_manager
        
    def run(self):
        """执行Google日志操作"""
        try:
            if self.operation == 'start':
                result = self._start_google_log()
            elif self.operation == 'stop':
                result = self._stop_google_log()
            elif self.operation == 'bugreport_only':
                result = self._bugreport_only()
            elif self.operation == 'pull_bugreport':
                result = self._pull_bugreport()
            else:
                result = {"success": False, "error": self.lang_manager.tr("未知操作类型")}
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _start_google_log(self):
        """启动Google日志收集"""
        try:
            # 1. 创建日志目录
            self.progress.emit(self.lang_manager.tr("创建Google日志目录..."), 10)
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            self.google_log_folder = f"C:\\log\\{current_date}\\Google_log_{current_time}"
            
            if not os.path.exists(self.google_log_folder):
                os.makedirs(self.google_log_folder)
            
            # 2. 执行Google日志相关命令
            self.progress.emit(self.lang_manager.tr("配置Google日志设置..."), 20)
            
            commands = [
                ["adb", "-s", self.device, "shell", "logcat", "-G", "16M"],
                ["adb", "-s", self.device, "logcat", "-c"],
                ["adb", "-s", self.device, "shell", "getprop", "|", "findstr", "fingerprint"],
                ["adb", "-s", self.device, "shell", "getprop", "|", "findstr", "gms"],
                ["adb", "-s", self.device, "shell", "getprop", "|", "findstr", "model"],
                ["adb", "-s", self.device, "shell", "wm", "size"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.Telecom", "VERBOSE"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.Telephony", "VERBOSE"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.InCall", "VERBOSE"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.TelecomFramework", "VERBOSE"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.ImsCall", "VERBOSE"],
                ["adb", "-s", self.device, "shell", "setprop", "log.tag.Dialer", "VERBOSE"]
            ]
            
            # 执行命令
            other_info_file = os.path.join(self.google_log_folder, "otherInfo.txt")
            
            # 前两个命令直接执行
            for i in range(2):
                self.progress.emit(f"{self.lang_manager.tr('执行命令')} {i+1}/2...", 20 + (i * 5))
                subprocess.run(commands[i], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                             creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 后面的命令需要写入文件
            with open(other_info_file, 'w', encoding='utf-8') as f:
                for i in range(2, len(commands)):
                    self.progress.emit(f"{self.lang_manager.tr('收集设备信息')} {i-1}/{len(commands)-2}...", 30 + ((i-2) * 8))
                    
                    # 重新构建命令，使用shell执行管道
                    if i == 2:  # fingerprint
                        cmd_str = f"adb -s {self.device} shell getprop | findstr fingerprint"
                    elif i == 3:  # gms
                        cmd_str = f"adb -s {self.device} shell getprop | findstr gms"
                    elif i == 4:  # model
                        cmd_str = f"adb -s {self.device} shell getprop | findstr model"
                    elif i == 5:  # wm size
                        cmd_str = f"adb -s {self.device} shell wm size"
                    
                    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
                    if result.returncode == 0 and result.stdout.strip():
                        f.write(result.stdout + "\n")
                
                # 执行setprop命令
                for i in range(6, len(commands)):
                    self.progress.emit(f"{self.lang_manager.tr('设置日志级别')} {i-5}/{len(commands)-6}...", 60 + ((i-6) * 3))
                    subprocess.run(commands[i], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                 creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 3. 启动ADB日志
            self.progress.emit(self.lang_manager.tr("启动ADB日志..."), 80)
            
            # 注意：这里需要通过信号或回调来调用adblog_manager
            # 由于在worker线程中，无法直接调用主线程的manager
            # 需要将folder信息保存，让主线程调用
            
            # 4. 启动视频录制
            self.progress.emit(self.lang_manager.tr("启动视频录制..."), 90)
            
            # 注意：同上，需要通过主线程调用video_manager
            
            # 5. 完成
            self.progress.emit(self.lang_manager.tr("Google日志收集已启动!"), 100)
            
            return {"success": True, "folder": self.google_log_folder, "device": self.device}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _stop_google_log(self):
        """停止Google日志收集"""
        try:
            # Worker线程中不执行任何操作，只是返回成功
            # 实际的导出操作在主线程回调中按顺序执行
            self.progress.emit(self.lang_manager.tr("准备停止Google日志收集..."), 100)
            
            return {"success": True, "folder": self.google_log_folder, "device": self.device}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _bugreport_only(self):
        """仅执行bugreport"""
        try:
            # 1. 创建日志目录
            self.progress.emit(self.lang_manager.tr("创建bugreport目录..."), 20)
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            self.google_log_folder = f"C:\\{current_date}\\bugreport"
            
            if not os.path.exists(self.google_log_folder):
                os.makedirs(self.google_log_folder)
            
            # 2. 执行bugreport
            self.progress.emit(self.lang_manager.tr("生成bugreport..."), 50)
            
            bugreport_cmd = ["adb", "-s", self.device, "bugreport", self.google_log_folder]
            result = subprocess.run(bugreport_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('bugreport执行失败:')} {result.stderr.strip()}")
            
            # 3. 完成
            self.progress.emit(self.lang_manager.tr("bugreport生成完成!"), 100)
            
            return {"success": True, "folder": self.google_log_folder, "device": self.device}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _pull_bugreport(self):
        """Pull bugreport"""
        try:
            # 1. 创建日志目录
            self.progress.emit(self.lang_manager.tr("创建bugreport目录..."), 20)
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            bugreport_folder = f"C:\\{current_date}\\bugreport"
            
            if not os.path.exists(bugreport_folder):
                os.makedirs(bugreport_folder)
            
            # 2. 执行pull命令
            self.progress.emit(self.lang_manager.tr("正在pull bugreport..."), 50)
            
            pull_cmd = f"adb -s {self.device} pull /data/user_de/0/com.android.shell/files/bugreports {bugreport_folder}"
            result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('pull bugreport失败:')} {result.stderr.strip()}")
            
            # 3. 完成
            self.progress.emit(self.lang_manager.tr("pull bugreport完成!"), 100)
            
            return {"success": True, "folder": bugreport_folder, "device": self.device}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class PyQtGoogleLogManager(QObject):
    """PyQt5 Google日志管理器"""
    
    status_message = pyqtSignal(str)
    google_log_started = pyqtSignal()
    google_log_stopped = pyqtSignal()
    
    def __init__(self, device_manager, parent=None, adblog_manager=None, video_manager=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.adblog_manager = adblog_manager
        self.video_manager = video_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.worker = None
        self.google_log_running = False
        self.google_log_folder = None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def start_google_log(self):
        """开始Google日志收集"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = GoogleLogWorker(device, 'start', lang_manager=self.lang_manager)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_google_log_started)
        self.worker.error.connect(self._on_google_log_error)
        self.worker.start()
    
    def stop_google_log(self):
        """停止Google日志收集"""
        if not self.google_log_running:
            self.status_message.emit(self.lang_manager.tr("Google日志未运行"))
            return
        
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = GoogleLogWorker(device, 'stop', self.google_log_folder, self.lang_manager)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_google_log_stopped)
        self.worker.error.connect(self._on_google_log_error)
        self.worker.start()
    
    def start_bugreport_only(self):
        """仅执行bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = GoogleLogWorker(device, 'bugreport_only', lang_manager=self.lang_manager)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_bugreport_finished)
        self.worker.error.connect(self._on_google_log_error)
        self.worker.start()
    
    def start_pull_bugreport(self):
        """Pull bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = GoogleLogWorker(device, 'pull_bugreport', lang_manager=self.lang_manager)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_pull_bugreport_finished)
        self.worker.error.connect(self._on_google_log_error)
        self.worker.start()
    
    def delete_bugreport(self):
        """删除设备上的bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            None,
            self.lang_manager.tr("确认删除"),
            self.lang_manager.tr("确定要删除设备上的bugreport吗？此操作不可恢复。"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建工作线程
        self.delete_worker = DeleteBugreportWorker(device, self.lang_manager)
        self.delete_worker.finished.connect(self._on_delete_bugreport_finished)
        self.delete_worker.start()
        self.status_message.emit(self.lang_manager.tr("正在删除bugreport..."))
    
    def _on_progress(self, message, progress):
        """进度更新"""
        self.status_message.emit(f"{message}")
    
    def _on_google_log_started(self, result):
        """Google日志启动完成"""
        if result.get("success"):
            self.google_log_running = True
            self.google_log_folder = result.get("folder")
            device = result.get("device")
            
            # 启动ADB日志
            if self.adblog_manager:
                log_name = f"adb_log"
                success = self.adblog_manager.start_google_adblog(device, log_name, self.google_log_folder)
                if not success:
                    self.status_message.emit(self.lang_manager.tr("启动ADB日志失败"))
            
            # 启动视频录制
            if self.video_manager:
                success = self.video_manager.start_google_recording(device, self.google_log_folder)
                if not success:
                    self.status_message.emit(self.lang_manager.tr("启动视频录制失败"))
            
            self.status_message.emit(self.tr("Google日志收集已启动 - ") + self.google_log_folder)
            self.google_log_started.emit()  # 发送启动信号
        else:
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"启动Google日志收集失败: {result.get('error')}")
            self.status_message.emit(self.lang_manager.tr("启动Google日志收集失败"))
    
    def _on_google_log_stopped(self, result):
        """Google日志停止完成"""
        if result.get("success"):
            folder = result.get("folder")
            device = result.get("device")
            
            # 保存导出参数
            self.export_device = device
            self.export_folder = folder
            self.export_video_done = False
            self.export_adblog_done = False
            
            # 1. 先导出视频
            self.status_message.emit(self.lang_manager.tr("正在导出视频..."))
            if self.video_manager:
                # 连接视频导出完成信号
                self.video_manager.video_saved.connect(self._on_video_exported)
                success = self.video_manager.stop_and_export_to_video_dir(device, folder)
                if not success:
                    self.status_message.emit(self.lang_manager.tr("停止视频录制失败"))
                    self._on_video_exported(folder, 0)
            else:
                self._on_video_exported(folder, 0)
        else:
            self.google_log_running = False
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"停止Google日志收集失败: {result.get('error')}")
            self.status_message.emit(self.lang_manager.tr("停止Google日志收集失败"))
            self.google_log_stopped.emit()
    
    def _on_video_exported(self, folder, count):
        """视频导出完成，开始导出ADB日志"""
        self.export_video_done = True
        
        # 2. 导出ADB日志
        self.status_message.emit(self.lang_manager.tr("视频已保存，正在停止ADB日志..."))
        if self.adblog_manager:
            # 连接ADB日志导出完成信号
            self.adblog_manager.adblog_exported.connect(self._on_adblog_exported)
            success = self.adblog_manager.stop_and_export_to_folder(self.export_device, self.export_folder)
            if not success:
                self.status_message.emit(self.lang_manager.tr("停止ADB日志失败"))
                self._on_adblog_exported(self.export_folder)
        else:
            self._on_adblog_exported(self.export_folder)
    
    def _on_adblog_exported(self, folder):
        """ADB日志导出完成，生成bugreport"""
        self.export_adblog_done = True
        
        # 3. 最后生成bugreport（在后台线程中执行）
        self.status_message.emit(self.lang_manager.tr("正在生成bugreport..."))
        
        # 显示进度对话框
        self.progress_dialog = QProgressDialog(self.lang_manager.tr("正在生成bugreport...\n这可能需要2-5分钟，请耐心等待"), None, 0, 0)
        self.progress_dialog.setWindowTitle(self.lang_manager.tr("Google日志收集"))
        self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
        self.progress_dialog.setWindowModality(2)  # 模态对话框
        self.progress_dialog.show()
        
        # 创建bugreport工作线程
        self.bugreport_worker = BugreportWorker(self.export_device, self.export_folder, self.lang_manager)
        self.bugreport_worker.finished.connect(self._on_bugreport_finished)
        self.bugreport_worker.error.connect(self._on_bugreport_error)
        self.bugreport_worker.start()
    
    def _on_bugreport_finished(self, result):
        """Bugreport完成"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        if result.get("success"):
            folder = result.get("folder")
            self.status_message.emit(self.tr("bugreport生成完成 - ") + folder)
            
            # 完成
            self.google_log_running = False
            self.google_log_stopped.emit()
            
            # 打开日志文件夹
            if folder:
                os.startfile(folder)
        else:
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"生成bugreport失败: {result.get('error')}")
            self.status_message.emit(self.lang_manager.tr("生成bugreport失败"))
            self.google_log_running = False
            self.google_log_stopped.emit()
    
    def _on_bugreport_error(self, error):
        """Bugreport错误"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        QMessageBox.critical(None, self.lang_manager.tr("错误"), self.tr("生成bugreport失败: ") + str(error))
        self.status_message.emit("❌ " + self.tr("生成bugreport失败: ") + str(error))
        self.google_log_running = False
        self.google_log_stopped.emit()
    
    def _on_pull_bugreport_finished(self, result):
        """Pull bugreport完成"""
        if result.get("success"):
            folder = result.get("folder")
            self.status_message.emit(self.tr("pull bugreport完成 - ") + folder)
            
            # 打开日志文件夹
            if folder:
                os.startfile(folder)
        else:
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"pull bugreport失败: {result.get('error')}")
            self.status_message.emit(self.lang_manager.tr("pull bugreport失败"))
    
    def _on_google_log_error(self, error):
        """Google日志错误"""
        QMessageBox.critical(None, self.lang_manager.tr("错误"), self.tr("Google日志操作失败: ") + str(error))
        self.status_message.emit("❌ " + self.tr("Google日志操作失败: ") + str(error))
    
    def _on_delete_bugreport_finished(self, success, error):
        """删除bugreport完成"""
        if success:
            self.status_message.emit(self.lang_manager.tr("bugreport已删除"))
            QMessageBox.information(None, self.lang_manager.tr("成功"), "bugreport已成功删除")
        else:
            self.status_message.emit("❌ " + self.tr("删除bugreport失败: ") + str(error))
            QMessageBox.critical(None, self.lang_manager.tr("错误"), self.tr("删除bugreport失败: ") + str(error))
    
    def toggle_google_log(self):
        """切换Google日志状态（启动/停止）"""
        if self.google_log_running:
            self.stop_google_log()
        else:
            self.start_google_log()

