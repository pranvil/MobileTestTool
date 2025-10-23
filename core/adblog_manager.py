#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 ADB Log管理器
适配原Tkinter版本的ADB Log管理功能
"""

import subprocess
import os
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class OfflineADBLogWorker(QThread):
    """离线ADB Log工作线程"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, device, log_name, lang_manager=None):
        super().__init__()
        self.device = device
        self.log_name = log_name
        self.lang_manager = lang_manager
        
    def run(self):
        """执行离线ADB Log启动"""
        try:
            # 1. 生成带时间的log文件名
            self.progress.emit(self.lang_manager.tr("生成log文件名..."), 20)
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.log_name}_{current_time}.txt"
            log_path = f"/data/local/tmp/{log_filename}"
            
            # 2. 启动logcat进程
            self.progress.emit(self.lang_manager.tr("启动logcat进程..."), 50)
            cmd = ["adb", "-s", self.device, "shell", "nohup", "logcat", "-v", "time", "-b", "all", "-f", log_path, ">", "/dev/null", "2>&1", "&"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('启动logcat失败:')} {result.stderr.strip()}")
            
            # 3. 检查logcat进程是否存在
            self.progress.emit(self.lang_manager.tr("检查logcat进程..."), 80)
            cmd3 = ["adb", "-s", self.device, "shell", "ps", "-A"]
            result = subprocess.run(cmd3, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('检查进程失败:')} {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception(self.lang_manager.tr("logcat进程不存在，启动失败"))
            
            # 完成
            self.progress.emit(self.lang_manager.tr("完成!"), 100)
            self.finished.emit({
                "success": True,
                "device": self.device,
                "log_filename": log_filename,
                "log_path": log_path,
                "mode": "offline"
            })
            
        except Exception as e:
            self.error.emit(str(e))


class OnlineADBLogWorker(QThread):
    """连线ADB Log工作线程"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    usb_disconnected = pyqtSignal(str)  # 设备ID
    usb_reconnected = pyqtSignal(str)   # 设备ID
    
    def __init__(self, device, log_name, online_logcat_process_ref, online_log_file_path_ref, folder=None, lang_manager=None, storage_path_func=None):
        super().__init__()
        self.device = device
        self.log_name = log_name
        self.lang_manager = lang_manager
        self.online_logcat_process_ref = online_logcat_process_ref
        self.online_log_file_path_ref = online_log_file_path_ref
        self.folder = folder  # Google日志文件夹
        self.storage_path_func = storage_path_func  # 存储路径获取函数
        self.stop_flag = False
        self.log_file_path = None
        self.monitor_stop_flag = False  # 监控循环停止标志
        self.normal_stop = False  # 正常停止标志
        
    def run(self):
        """执行连线ADB Log启动"""
        try:
            # 1. 使用传入的文件夹或创建默认目录
            self.progress.emit(self.lang_manager.tr("创建日志目录..."), 20)
            if self.folder:
                # 使用Google日志文件夹
                log_dir = self.folder
            else:
                # 使用存储路径配置
                if self.storage_path_func:
                    log_dir = self.storage_path_func()
                else:
                    # 默认路径
                    current_date = datetime.datetime.now().strftime("%Y%m%d")
                    log_dir = f"c:\\log\\{current_date}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 2. 生成带时间的log文件名
            self.progress.emit(self.lang_manager.tr("生成log文件名..."), 40)
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.log_name}_{current_time}.txt"
            log_file_path = os.path.join(log_dir, log_filename)
            
            # 3. 启动PC端logcat进程（连线模式不需要在设备上启动logcat）
            self.progress.emit(self.lang_manager.tr("启动PC端log输出进程..."), 60)
            self.log_file_path = log_file_path
            
            try:
                self._start_logcat_process(log_file_path, 'w')
            except Exception as e:
                raise Exception(f"{self.lang_manager.tr('启动PC端log输出进程失败:')} {str(e)}")
            
            # 4. 完成（监控在后台线程中运行）
            self.progress.emit(self.lang_manager.tr("完成!"), 100)
            self.finished.emit({
                "success": True,
                "device": self.device,
                "log_filename": log_filename,
                "log_file_path": log_file_path,
                "logcat_process": self.online_logcat_process_ref,
                "mode": "online"
            })
            
            # 5. 在后台监控logcat进程状态
            self._monitor_logcat_process()
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _start_logcat_process(self, log_file_path, mode='w'):
        """启动logcat进程"""
        pc_cmd = ["adb", "-s", self.device, "logcat", "-b", "all", "-v", "time"]
        try:
            # 打开文件（不使用with语句，避免文件过早关闭）
            log_file = open(log_file_path, mode, encoding='utf-8', errors='replace')
            process = subprocess.Popen(pc_cmd, stdout=log_file, stderr=subprocess.PIPE, 
                                    encoding='utf-8', errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 存储进程对象和文件对象以供后续停止使用
            self.online_logcat_process_ref['process'] = process
            self.online_log_file_path_ref['path'] = log_file_path
            self.online_logcat_process_ref['file'] = log_file  # 保存文件对象，避免被垃圾回收
            
            print(f"{self.lang_manager.tr('Logcat进程已启动，PID:')} {process.pid}, {self.lang_manager.tr('模式:')} {mode}")
        except Exception as e:
            raise Exception(f"{self.lang_manager.tr('启动logcat进程失败:')} {str(e)}")
    
    def _monitor_logcat_process(self):
        """监控logcat进程状态，检测USB断线并自动重连"""
        import time
        
        while not self.stop_flag and not self.monitor_stop_flag:
            # 检查是否被要求停止监控（在每次循环开始时检查）
            if self.monitor_stop_flag:
                print(self.lang_manager.tr("监控循环收到停止信号"))
                break
            
            # 检查是否被要求正常停止
            if self.normal_stop:
                print(self.lang_manager.tr("监控循环收到正常停止信号"))
                break
            
            process = self.online_logcat_process_ref.get('process')
            if process is None:
                print(self.lang_manager.tr("进程引用为None，退出监控循环"))
                break
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                # 进程已退出，检查是否是USB断开
                print(f"{self.lang_manager.tr('Logcat进程已退出，退出码:')} {process.returncode}")
                
                # 再次检查是否被要求停止监控
                if self.monitor_stop_flag or self.normal_stop:
                    print(self.lang_manager.tr("监控循环收到停止信号"))
                    break
                
                # 检查设备是否还在线
                try:
                    check_cmd = ["adb", "devices"]
                    result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10,
                                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    
                    if self.device not in result.stdout:
                        # USB断开
                        print(self.lang_manager.tr("检测到USB断开"))
                        self.usb_disconnected.emit(self.device)
                        
                        # 等待设备重连
                        self.progress.emit(self.lang_manager.tr("等待USB重连..."), 50)
                        wait_cmd = ["adb", "wait-for-device"]
                        subprocess.run(wait_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
                                     creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                        
                        print(self.lang_manager.tr("USB已重连"))
                        
                        # 重新启动logcat进程，追加模式
                        try:
                            self.progress.emit(self.lang_manager.tr("重新启动logcat进程..."), 70)
                            self._start_logcat_process(self.log_file_path, 'a')  # 追加模式
                            print(f"{self.lang_manager.tr('Logcat进程已重新启动，追加模式')}")
                            
                            # 启动成功后，发送信号通知管理器进程已更新
                            self.usb_reconnected.emit(self.device)
                        except Exception as e:
                            print(f"{self.lang_manager.tr('重新启动logcat进程失败:')} {e}")
                            self.error.emit(f"{self.lang_manager.tr('重新启动logcat进程失败:')} {str(e)}")
                            break
                    else:
                        # 设备在线但进程退出，检查是否是正常停止
                        if self.normal_stop:
                            print(self.lang_manager.tr("Logcat进程正常停止"))
                            break
                        else:
                            # 设备在线但进程退出，可能是其他原因
                            print(self.lang_manager.tr("设备在线但logcat进程退出"))
                            self.error.emit(self.lang_manager.tr("Logcat进程意外退出"))
                            break
                except Exception as e:
                    print(f"{self.lang_manager.tr('检查设备状态时发生错误:')} {e}")
                    # 如果检查设备状态失败，也退出监控循环
                    break
            
            # 短暂休眠，避免CPU占用过高
            time.sleep(1)  # 减少到1秒检查一次，提高响应速度
        
        print(self.lang_manager.tr("监控循环已退出"))


class ExportADBLogWorker(QThread):
    """导出ADB Log工作线程"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, device, lang_manager=None, storage_path_func=None):
        super().__init__()
        self.device = device
        self.lang_manager = lang_manager
        self.storage_path_func = storage_path_func  # 存储路径获取函数
        
    def run(self):
        """执行ADB Log导出"""
        try:
            # 1. 检查设备连接状态
            self.progress.emit(self.lang_manager.tr("检查设备连接状态..."), 10)
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(self.lang_manager.tr("检查设备连接失败"))
            
            # 检查设备是否在列表中
            if self.device not in result.stdout:
                raise Exception(f"{self.lang_manager.tr('设备')} {self.device} {self.lang_manager.tr('未连接')}")
            
            # 2. 检查logcat进程是否存在
            self.progress.emit(self.lang_manager.tr("检查logcat进程..."), 25)
            ps_cmd = ["adb", "-s", self.device, "shell", "ps", "-A"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('检查进程失败:')} {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception(self.lang_manager.tr("logcat进程不存在，log抓取异常"))
            
            # 3. 精确杀掉nohup启动的logcat进程
            self.progress.emit(self.lang_manager.tr("停止nohup logcat进程..."), 40)
            ps_cmd = ["adb", "-s", self.device, "shell", "ps", "-ef"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                # 解析进程列表，找到包含/data/local/tmp/的logcat进程
                lines = result.stdout.strip().split('\n')
                nohup_pids = []
                
                for line in lines:
                    if 'logcat' in line and '/data/local/tmp/' in line:
                        # 提取PID（第二列）
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                nohup_pids.append(pid)
                                print(f"{self.lang_manager.tr('找到nohup logcat进程 PID:')} {pid}")
                            except ValueError:
                                continue
                
                # 杀掉找到的nohup logcat进程
                if nohup_pids:
                    for pid in nohup_pids:
                        kill_cmd = ["adb", "-s", self.device, "shell", "kill", str(pid)]
                        kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                        if kill_result.returncode == 0:
                            print(f"{self.lang_manager.tr('成功停止nohup logcat进程 PID:')} {pid}")
                        else:
                            print(f"{self.lang_manager.tr('停止进程 PID')} {pid} {self.lang_manager.tr('失败:')} {kill_result.stderr.strip()}")
                else:
                    print(self.lang_manager.tr("未找到nohup启动的logcat进程"))
            else:
                print(f"{self.lang_manager.tr('获取进程列表失败:')} {result.stderr.strip()}")
            
            # 4. 创建日志目录
            self.progress.emit(self.lang_manager.tr("创建日志目录..."), 50)
            if self.storage_path_func:
                log_dir = self.storage_path_func()
            else:
                # 默认路径
                current_date = datetime.datetime.now().strftime("%Y%m%d")
                log_dir = f"c:\\log\\{current_date}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 5. 导出log文件
            self.progress.emit(self.lang_manager.tr("导出log文件..."), 70)
            logcat_dir = os.path.join(log_dir, "logcat")
            if not os.path.exists(logcat_dir):
                os.makedirs(logcat_dir)
            
            # 先获取设备上的所有txt文件列表
            ls_cmd = ["adb", "-s", self.device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，逐个导出
                txt_files = result.stdout.strip().split('\n')
                exported_count = 0
                for txt_file in txt_files:
                    if txt_file.strip():
                        filename = os.path.basename(txt_file.strip())
                        pull_cmd = ["adb", "-s", self.device, "pull", txt_file.strip(), os.path.join(logcat_dir, filename)]
                        result = subprocess.run(pull_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120, 
                                              creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                        
                        if result.returncode == 0:
                            exported_count += 1
                            print(f"{self.lang_manager.tr('成功导出:')} {filename}")
                        else:
                            print(f"{self.lang_manager.tr('警告:')} {filename} {self.lang_manager.tr('导出失败:')} {result.stderr.strip()}")
                
                if exported_count == 0:
                    raise Exception(self.lang_manager.tr("没有成功导出任何log文件"))
            else:
                # 没有找到txt文件，尝试导出整个tmp目录
                self.progress.emit(self.lang_manager.tr("未找到txt文件，导出整个tmp目录..."), 70)
                pull_cmd = ["adb", "-s", self.device, "pull", "/data/local/tmp/", logcat_dir]
                result = subprocess.run(pull_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120, 
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                
                if result.returncode != 0:
                    raise Exception(f"{self.lang_manager.tr('导出tmp目录失败:')} {result.stderr.strip()}")
            
            # 6. 完成
            self.progress.emit(self.lang_manager.tr("完成!"), 100)
            self.finished.emit({
                "success": True,
                "log_folder": logcat_dir,
                "device": self.device,
                "operation_type": "offline_adb_export"
            })
            
        except Exception as e:
            self.error.emit(str(e))


class PyQtADBLogManager(QObject):
    """PyQt5 ADB Log管理器"""
    
    # 信号定义
    mode_selection_required = pyqtSignal()  # 需要选择模式
    adblog_started = pyqtSignal(str, str)  # device, log_filename
    adblog_stopped = pyqtSignal()
    adblog_exported = pyqtSignal(str)  # export_path
    status_message = pyqtSignal(str)
    clear_old_logs_required = pyqtSignal(str, int, list)  # device, file_count, txt_files
    online_mode_started = pyqtSignal()  # 连线模式已启动
    online_mode_stopped = pyqtSignal()  # 连线模式已停止
    usb_disconnected = pyqtSignal(str)  # USB断开
    usb_reconnected = pyqtSignal(str)   # USB重连
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        # 初始化ADB Log相关变量
        self._init_adblog_variables()
    
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
        
    def _init_adblog_variables(self):
        """初始化ADB Log相关变量"""
        self.worker = None
        self.is_running = False
        self.current_mode = None  # "offline" or "online"
        self.current_device = None
        self.current_log_filename = None
        self.pending_log_name = None  # 用于存储待启动的log名称
        
        # 连线模式相关
        self._online_logcat_process = None
        self._online_log_file_path = None
        
    def start_adblog(self, mode, log_name):
        """开启ADB Log
        
        Args:
            mode: "offlineself.lang_manager.tr(" 或 ")online"
            log_name: log文件名（不含扩展名）
        """
        device = self.device_manager.validate_device_selection()
        if not device:
            self.status_message.emit(self.lang_manager.tr("请先选择设备"))
            return
        
        if self.is_running:
            self.status_message.emit(self.lang_manager.tr("ADB Log已经在运行中"))
            return
        
        self.current_device = device
        self.current_mode = mode
        
        if mode == "offline":
            self._start_offline_adblog(device, log_name)
        else:
            self._start_online_adblog(device, log_name)
    
    def _start_offline_adblog(self, device, log_name):
        """开启离线adb log"""
        # 检查/data/local/tmp是否有txt文件
        try:
            ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，询问用户是否清除
                txt_files = result.stdout.strip().split('\n')
                file_count = len([f for f in txt_files if f.strip()])
                
                # 保存log_name以便后续使用
                self.pending_log_name = log_name
                
                # 发送信号通知UI显示清除对话框
                self.clear_old_logs_required.emit(device, file_count, txt_files)
                return
                
        except Exception as e:
            print(f"{self.lang_manager.tr('检查旧log文件时发生错误:')} {e}")
            # 继续执行，不中断流程
        
        # 没有旧文件或用户选择不检查，直接启动
        self._do_start_offline_adblog(device, log_name)
    
    def handle_clear_old_logs_decision(self, clear_old):
        """处理用户对清除旧log文件的选择"""
        if self.pending_log_name is None:
            return
        
        log_name = self.pending_log_name
        self.pending_log_name = None
        
        # 调用启动方法，传入是否清除旧文件的标志
        self._do_start_offline_adblog(self.current_device, log_name, clear_old)
    
    def _do_start_offline_adblog(self, device, log_name, clear_old=False):
        """执行离线adb log启动"""
        if clear_old:
            # 清除旧文件
            try:
                self.status_message.emit(self.tr("正在清除设备 ") + device + self.tr(" 的旧log文件..."))
                rm_cmd = ["adb", "-s", device, "shell", "rm", "-f", "/data/local/tmp/*.txt"]
                result = subprocess.run(rm_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                if result.returncode == 0:
                    self.status_message.emit(self.tr("已清除设备 ") + device + self.tr(" 的旧log文件"))
                else:
                    print(f"{self.lang_manager.tr('警告: 清除旧文件失败:')} {result.stderr.strip()}")
            except Exception as e:
                print(f"{self.lang_manager.tr('清除旧文件时发生错误:')} {e}")
        else:
            # 用户选择保留旧文件
            self.status_message.emit(self.tr("保留设备 ") + device + self.tr(" 的旧log文件"))
        
        # 创建工作线程
        self.worker = OfflineADBLogWorker(device, log_name, self.lang_manager)
        self.worker.finished.connect(self._on_offline_adblog_started)
        self.worker.error.connect(self._on_offline_adblog_error)
        self.worker.start()
    
    def _on_offline_adblog_started(self, result):
        """离线ADB log启动成功"""
        self.is_running = True
        self.current_log_filename = result['log_filename']
        self.adblog_started.emit(result['device'], result['log_filename'])
        self.status_message.emit(f"{self.lang_manager.tr('离线ADB log已开启 - {device} - {filename}').format(device=result['device'], filename=result['log_filename'])}")
    
    def _on_offline_adblog_error(self, error):
        """离线ADB log启动失败"""
        self.status_message.emit(f"{self.tr('开启离线ADB log失败: ')}{error}")
    
    def _start_online_adblog(self, device, log_name):
        """开启连线adb log"""
        # 创建工作线程
        online_logcat_process_ref = {'process': None}
        online_log_file_path_ref = {'path': None}
        
        self.worker = OnlineADBLogWorker(device, log_name, online_logcat_process_ref, online_log_file_path_ref, lang_manager=self.lang_manager, storage_path_func=self.get_storage_path)
        self.worker.finished.connect(lambda result: self._on_online_adblog_started_with_refs(result, online_logcat_process_ref, online_log_file_path_ref))
        self.worker.error.connect(self._on_online_adblog_error)
        self.worker.usb_disconnected.connect(self._on_usb_disconnected)
        self.worker.usb_reconnected.connect(self._on_usb_reconnected)
        self.worker.start()
    
    def _on_online_adblog_started_with_refs(self, result, process_ref, path_ref):
        """连线ADB log启动成功（带进程引用）"""
        # 保存进程引用
        self._online_logcat_process = process_ref['process']
        self._online_log_file_path = path_ref['path']
        
        self.is_running = True
        self.current_log_filename = result['log_filename']
        print(self.tr("连线ADB log启动成功，设置is_running=True"))
        self.adblog_started.emit(result['device'], result['log_filename'])
        self.status_message.emit(f"{self.lang_manager.tr('连线ADB log已开启 - {device} - {filename}').format(device=result['device'], filename=result['log_filename'])}")
        
        # 发送连线模式已启动信号
        self.online_mode_started.emit()
        
        # 保存引用以便监控线程更新
        self._online_logcat_process_ref = process_ref
        self._online_log_file_path_ref = path_ref
    
    def _on_usb_disconnected(self, device):
        """USB断开"""
        self.status_message.emit(self.tr("检测到USB断开，等待重连..."))
        self.usb_disconnected.emit(device)
    
    def _on_usb_reconnected(self, device):
        """USB重连"""
        print(f"{self.lang_manager.tr('=== USB重连:')} {device} {self.lang_manager.tr('===')}")
        self.status_message.emit(self.tr("USB已重连，继续抓取log..."))
        self.usb_reconnected.emit(device)
        
        # 更新进程引用（因为重连后启动了新的logcat进程）
        if hasattr(self, '_online_logcat_process_ref'):
            old_process = self._online_logcat_process
            self._online_logcat_process = self._online_logcat_process_ref.get('process')
            print(f"{self.lang_manager.tr('进程引用更新:')} {old_process.pid if old_process else 'None'} -> {self._online_logcat_process.pid if self._online_logcat_process else 'None'}")
            print(f"{self.lang_manager.tr('日志文件路径:')} {self._online_log_file_path}")
        else:
            print(self.lang_manager.tr("警告: _online_logcat_process_ref 不存在"))
    
    def _on_online_adblog_error(self, error):
        """连线ADB log启动失败"""
        self.status_message.emit("❌ " + self.tr("开启连线ADB log失败: ") + str(error))
    
    def stop_online_adblog(self):
        """停止连线logcat进程（只处理连线模式）"""
        print(self.lang_manager.tr("=== stop_online_adblog 被调用 ==="))
        print(f"{self.lang_manager.tr('当前模式:')} {self.current_mode}")
        print(f"{self.lang_manager.tr('进程引用:')} {self._online_logcat_process}")
        print(f"{self.lang_manager.tr('is_running状态:')} {self.is_running}")
        
        device = self.device_manager.validate_device_selection()
        if not device:
            print(self.lang_manager.tr("设备未选择"))
            return
        
        # 调用停止连线logcat的方法
        self._stop_online_adblog()
    
    def export_offline_adblog(self):
        """导出离线logcat进程（只处理离线模式）"""
        print(self.lang_manager.tr("=== export_offline_adblog 被调用 ==="))
        print(f"{self.lang_manager.tr('当前模式:')} {self.current_mode}")
        
        device = self.device_manager.validate_device_selection()
        if not device:
            print(self.lang_manager.tr("设备未选择"))
            return
        
        # 调用导出离线logcat的方法
        self._export_offline_adblog(device)
    
    def _stop_online_adblog(self):
        """停止连线adb log"""
        try:
            print(self.lang_manager.tr("=== 开始停止连线ADB log ==="))
            print(f"{self.lang_manager.tr('当前模式:')} {self.current_mode}")
            print(f"{self.lang_manager.tr('进程引用:')} {self._online_logcat_process}")
            print(f"{self.lang_manager.tr('日志文件路径:')} {self._online_log_file_path}")
            
            device = self.device_manager.validate_device_selection()
            if not device:
                print(self.lang_manager.tr("设备未选择"))
                return
            
            # 0. 首先设置正常停止标志，避免监控线程报错
            if self.worker and hasattr(self.worker, 'normal_stop'):
                print(self.lang_manager.tr("设置正常停止标志"))
                self.worker.normal_stop = True
            
            # 1. 停止监控循环
            if self.worker and hasattr(self.worker, 'monitor_stop_flag'):
                print(self.lang_manager.tr("设置监控循环停止标志"))
                self.worker.monitor_stop_flag = True
            
            # 2. 尝试通过PC端进程对象杀掉logcat进程
            if self._online_logcat_process is not None:
                # 检查进程是否还在运行
                if self._online_logcat_process.poll() is None:
                    # 进程还在运行，终止它
                    print(f"{self.lang_manager.tr('正在终止logcat进程，PID:')} {self._online_logcat_process.pid}")
                    try:
                        # 先尝试优雅终止
                        self._online_logcat_process.terminate()
                        # 等待进程结束，最多等待3秒
                        self._online_logcat_process.wait(timeout=3)
                        print(self.lang_manager.tr("Logcat进程已成功终止"))
                    except subprocess.TimeoutExpired:
                        print(self.lang_manager.tr("Logcat进程终止超时，强制kill"))
                        try:
                            self._online_logcat_process.kill()
                            self._online_logcat_process.wait(timeout=2)
                            print(self.lang_manager.tr("Logcat进程已强制终止"))
                        except subprocess.TimeoutExpired:
                            print(self.lang_manager.tr("警告: 无法完全终止logcat进程"))
                    except Exception as e:
                        print(f"{self.lang_manager.tr('终止logcat进程时发生错误:')} {e}")
                else:
                    # 进程已经退出
                    print(f"{self.lang_manager.tr('Logcat进程已退出，退出码:')} {self._online_logcat_process.returncode}")
                
                # 清理进程引用
                self._online_logcat_process = None
            
            # 3. 关闭文件对象
            if hasattr(self, '_online_logcat_process_ref') and self._online_logcat_process_ref:
                try:
                    if 'file' in self._online_logcat_process_ref and self._online_logcat_process_ref['file']:
                        file_obj = self._online_logcat_process_ref['file']
                        file_obj.close()
                        print(self.lang_manager.tr("日志文件已关闭"))
                except Exception as e:
                    print(f"{self.lang_manager.tr('关闭日志文件时发生错误:')} {e}")
                
                # 清理进程引用字典
                self._online_logcat_process_ref = None
            
            # 4. 备用方案：通过adb命令杀掉设备上的logcat进程（PPID != 1的进程）
            print(self.lang_manager.tr("尝试通过adb命令杀掉设备上的连线logcat进程..."))
            try:
                ps_cmd = ["adb", "-s", device, "shell", "ps", "-A"]
                result = subprocess.run(ps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    killed_count = 0
                    for line in lines:
                        if 'logcat' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                pid = parts[1]
                                ppid = parts[2]
                                # 只杀掉PPID != 1的logcat进程（连线logcat）
                                if ppid != '1':
                                    print(f"{self.lang_manager.tr('找到连线logcat进程，PID:')} {pid}, PPID: {ppid}")
                                    kill_cmd = ["adb", "-s", device, "shell", "kill", pid]
                                    kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
                                                              creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                                    if kill_result.returncode == 0:
                                        print(f"{self.lang_manager.tr('成功杀掉连线logcat进程 PID:')} {pid}")
                                        killed_count += 1
                                    else:
                                        print(f"{self.lang_manager.tr('杀掉进程 PID')} {pid} {self.lang_manager.tr('失败:')} {kill_result.stderr.strip()}")
                    
                    if killed_count == 0:
                        print(self.lang_manager.tr("未找到需要停止的连线logcat进程"))
                else:
                    print(f"{self.lang_manager.tr('获取进程列表失败:')} {result.stderr.strip()}")
            except Exception as e:
                print(f"{self.lang_manager.tr('通过adb命令停止进程时发生错误:')} {e}")
            
            # 5. 打开日志文件所在目录
            if self._online_log_file_path and os.path.exists(self._online_log_file_path):
                log_dir = os.path.dirname(self._online_log_file_path)
                print(f"{self.lang_manager.tr('打开日志文件夹:')} {log_dir}")
                try:
                    os.startfile(log_dir)
                    self.status_message.emit(self.lang_manager.tr("连线ADB log已停止并保存"))
                except Exception as e:
                    print(f"{self.lang_manager.tr('打开日志文件夹失败:')} {e}")
                    self.status_message.emit(self.lang_manager.tr("连线ADB log已停止"))
            else:
                print(self.lang_manager.tr("日志文件路径为空或文件不存在"))
                self.status_message.emit(self.lang_manager.tr("连线ADB log已停止"))
            
            # 6. 清理状态
            self.is_running = False
            self.current_mode = None
            self.current_device = None
            self.current_log_filename = None
            self._online_log_file_path = None
            print(self.tr("连线ADB log停止完成，设置is_running=False"))
            
            # 7. 发送完成信号
            self.adblog_stopped.emit()
            self.online_mode_stopped.emit()
            print(self.lang_manager.tr("=== 连线ADB log进程已成功停止 ==="))
                
        except Exception as e:
            print(self.lang_manager.tr("停止连线ADB log异常:") + " " + str(e))
            import traceback
            traceback.print_exc()
            self.status_message.emit("❌ " + self.tr("停止连线ADB log失败: ") + str(e))
            
            # 即使出错也要清理状态
            self.is_running = False
            self.current_mode = None
            self.current_device = None
            self.current_log_filename = None
            self._online_log_file_path = None
            
            self.adblog_stopped.emit()
            self.online_mode_stopped.emit()
    
    def _export_offline_adblog(self, device):
        """导出离线adb log"""
        # 创建工作线程
        self.worker = ExportADBLogWorker(device, self.lang_manager, self.get_storage_path)
        self.worker.finished.connect(self._on_offline_adblog_exported)
        self.worker.error.connect(self._on_offline_adblog_export_error)
        self.worker.start()
    
    def _on_offline_adblog_exported(self, result):
        """离线ADB log导出成功"""
        self.is_running = False
        self.adblog_stopped.emit()
        
        # 打开日志文件夹
        if result["log_folder"]:
            os.startfile(result["log_folder"])
        
        self.adblog_exported.emit(result["log_folder"])
        self.status_message.emit(f"{self.lang_manager.tr('离线ADB log已导出 - {device}').format(device=result['device'])}")
    
    def _on_offline_adblog_export_error(self, error):
        """离线ADB log导出失败"""
        if self.lang_manager.tr("logcat进程不存在") in error:
            self.status_message.emit(self.lang_manager.tr("logcat进程不存在，log抓取异常"))
        else:
            self.status_message.emit("❌ " + self.tr("停止并导出离线ADB log失败: ") + str(error))
    
    def start_google_adblog(self, device, log_name, folder):
        """启动Google日志专用的ADB日志（连线模式）
        
        Args:
            device: 设备ID
            log_name: 日志文件名
            folder: 保存目录
        """
        if self.is_running:
            self.status_message.emit(self.lang_manager.tr("ADB Log已经在运行中"))
            return False
        
        self.current_device = device
        self.current_mode = "online"
        
        # 生成日志文件路径
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{log_name}_{current_time}.txt"
        log_file_path = os.path.join(folder, log_filename)
        
        # 初始化进程引用（使用字典）
        online_logcat_process_ref = {}
        online_log_file_path_ref = {}
        
        # 创建工作线程（连线模式）
        self.worker = OnlineADBLogWorker(device, log_name, 
                                        online_logcat_process_ref, 
                                        online_log_file_path_ref,
                                        folder,  # 传入Google日志文件夹
                                        self.lang_manager,
                                        self.get_storage_path)
        self.worker.finished.connect(lambda result: self._on_google_adblog_started(result, folder, log_file_path))
        self.worker.error.connect(self._on_google_adblog_error)
        self.worker.start()
        
        return True
    
    def _on_google_adblog_started(self, result, folder, log_file_path):
        """Google ADB日志启动成功"""
        if result.get("success"):
            self.is_running = True
            self.current_log_filename = result.get("log_filename")
            self._online_log_file_path = log_file_path  # 保存日志文件路径
            self._online_logcat_process_ref = result.get("logcat_process", {})  # 保存整个字典引用
            self.status_message.emit(self.tr("Google ADB日志已启动: ") + result['device'])
        else:
            self.status_message.emit("❌ " + self.tr("启动Google ADB日志失败: ") + str(result.get('error')))
    
    def _on_google_adblog_error(self, error):
        """Google ADB日志错误"""
        self.status_message.emit("❌ " + self.tr("Google ADB日志操作失败: ") + str(error))
    
    def stop_and_export_to_folder(self, device, folder):
        """停止ADB日志（连线模式，直接杀死logcat进程）
        
        Args:
            device: 设备ID
            folder: 目标文件夹（未使用，保持兼容性）
        """
        if not self.is_running:
            self.status_message.emit(self.lang_manager.tr("ADB Log未运行"))
            return False
        
        try:
            # 直接杀死logcat进程
            import subprocess
            
            # 查找logcat进程
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                # 解析进程列表，找到logcat进程
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'logcat' in line:
                        # 提取PID（第二列）
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                # 杀死进程
                                kill_cmd = ["adb", "-s", device, "shell", "kill", str(pid)]
                                subprocess.run(kill_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, 
                                             creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                                print(f"{self.lang_manager.tr('成功停止logcat进程 PID:')} {pid}")
                            except ValueError:
                                continue
            
            # 停止logcat进程（如果有）
            if hasattr(self, '_online_logcat_process_ref') and self._online_logcat_process_ref:
                try:
                    # 设置正常停止标志，避免监控线程报错
                    if hasattr(self, 'worker') and self.worker and hasattr(self.worker, 'normal_stop'):
                        self.worker.normal_stop = True
                    
                    # 终止进程
                    if 'process' in self._online_logcat_process_ref:
                        process = self._online_logcat_process_ref['process']
                        process.terminate()
                        process.wait(timeout=5)
                    
                    # 关闭文件对象
                    if 'file' in self._online_logcat_process_ref:
                        file_obj = self._online_logcat_process_ref['file']
                        file_obj.close()
                except Exception as e:
                    pass
                
                self._online_logcat_process_ref = None
            
            # 标记为已停止
            self.is_running = False
            
            # 直接发送完成信号
            self.adblog_exported.emit(folder)
            self.status_message.emit(f"{self.lang_manager.tr('ADB日志已停止，准备生成bugreport...')}")
            
            return True
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("停止ADB日志失败: ") + str(e))
            self.is_running = False
            self.adblog_exported.emit(folder)
            return False
    
    def stop_adblog(self):
        """停止ADB Log（通用方法，兼容应用程序关闭时调用）"""
        if not self.is_running:
            return
        
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 根据当前模式调用相应的停止方法
        if hasattr(self, 'current_mode') and self.current_mode == 'online':
            self.stop_online_adblog()
        else:
            # 对于离线模式或其他情况，直接停止
            self.is_running = False
            self.status_message.emit(self.lang_manager.tr("ADB Log已停止"))
            self.adblog_stopped.emit()
    