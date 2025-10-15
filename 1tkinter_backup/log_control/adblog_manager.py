#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADBLOG管理模块
负责ADB log的开启和导出
"""

import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import datetime

class ADBLogManager:
    def __init__(self, app_instance):
        self.app = app_instance
        # 连线adb log相关属性
        self._online_logcat_process = None
        self._online_log_file_path = None
    
    def _show_mode_selection_dialog(self):
        """显示模式选择对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("选择ADB Log模式")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        
        # 使对话框模态
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"500x300+{x}+{y}")
        
        # 主框架
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(main_frame, text="请选择ADB Log抓取模式", 
                              font=("微软雅黑", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 结果变量
        result = {"choice": None}
        
        # 离线模式按钮和说明
        offline_frame = tk.Frame(button_frame)
        offline_frame.pack(fill=tk.X, pady=5)
        
        offline_btn = tk.Button(offline_frame, text="离线模式", 
                               font=("微软雅黑", 12, "bold"),
                               bg="#4CAF50", fg="white", 
                               width=12, height=2,
                               command=lambda: self._select_mode(dialog, result, True))
        offline_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        offline_desc = tk.Label(offline_frame, 
                               text="手机可以断开USB连接\n使用nohup在设备上抓取log",
                               font=("微软雅黑", 10),
                               justify=tk.LEFT)
        offline_desc.pack(side=tk.LEFT, anchor=tk.W)
        
        # 连线模式按钮和说明
        online_frame = tk.Frame(button_frame)
        online_frame.pack(fill=tk.X, pady=5)
        
        online_btn = tk.Button(online_frame, text="连线模式", 
                              font=("微软雅黑", 12, "bold"),
                              bg="#2196F3", fg="white", 
                              width=12, height=2,
                              command=lambda: self._select_mode(dialog, result, False))
        online_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        online_desc = tk.Label(online_frame, 
                              text="手机必须保持USB连接\n直接输出到PC本地文件",
                              font=("微软雅黑", 10),
                              justify=tk.LEFT)
        online_desc.pack(side=tk.LEFT, anchor=tk.W)
        
        # 取消按钮框架
        cancel_frame = tk.Frame(main_frame)
        cancel_frame.pack(fill=tk.X, pady=(20, 0))
        
        cancel_btn = tk.Button(cancel_frame, text="取消", 
                              font=("微软雅黑", 10),
                              width=10, height=1,
                              command=lambda: self._select_mode(dialog, result, None))
        cancel_btn.pack()
        
        # 等待对话框关闭
        dialog.wait_window()
        
        return result["choice"]
    
    def _select_mode(self, dialog, result, choice):
        """选择模式并关闭对话框"""
        result["choice"] = choice
        dialog.destroy()
    
    def start_adblog(self):
        """开启adb log"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 让用户选择log抓取模式
        choice = self._show_mode_selection_dialog()
        
        if choice is None:  # 用户点击取消
            return
        
        # 获取log名称
        log_name = simpledialog.askstring("输入log名称", 
            "请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线", 
            parent=self.app.root)
        if not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        if choice:  # True = 离线adb log
            self._start_offline_adblog(device, log_name)
        else:  # False = 连线adb log
            self._start_online_adblog(device, log_name)
    
    def _start_offline_adblog(self, device, log_name):
        """开启离线adb log（原有逻辑）"""
        # 检查/data/local/tmp是否有txt文件
        try:
            ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，询问用户是否清除
                txt_files = result.stdout.strip().split('\n')
                file_count = len([f for f in txt_files if f.strip()])
                
                # 显示文件名列表（最多显示5个）
                file_list = [os.path.basename(f.strip()) for f in txt_files if f.strip()][:5]
                file_display = '\n'.join(file_list)
                if file_count > 5:
                    file_display += '\n...'
                
                response = messagebox.askyesno("发现旧log文件", 
                    f"在设备 {device} 的 /data/local/tmp 目录中发现 {file_count} 个txt文件:\n\n"
                    f"{file_display}\n\n"
                    "是否清除这些旧log文件？\n\n"
                    "选择'是'：清除所有旧文件，然后输入新文件名\n"
                    "选择'否'：保留旧文件，然后输入新文件名")
                
                if response:
                    # 用户选择清除，只删除txt文件
                    self.app.ui.status_var.set(f"正在清除设备 {device} 的旧log文件...")
                    
                    # 只删除txt文件，不影响其他文件
                    rm_cmd = ["adb", "-s", device, "shell", "rm", "-f", "/data/local/tmp/*.txt"]
                    result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=30, 
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    if result.returncode == 0:
                        self.app.ui.status_var.set(f"已清除设备 {device} 的旧log文件")
                    else:
                        print(f"警告: 清除旧文件失败: {result.stderr.strip()}")
                else:
                    # 用户选择保留
                    self.app.ui.status_var.set(f"保留设备 {device} 的旧log文件")
                    
        except Exception as e:
            print(f"检查旧log文件时发生错误: {e}")
            # 继续执行，不中断流程
        
        # 定义后台工作函数
        def adblog_start_worker(progress_var, status_label, progress_dialog, stop_flag):
            # 检查是否被要求停止
            if stop_flag and stop_flag.is_set():
                return {"success": False, "message": "操作已取消"}
            
            # 1. 生成带时间的log文件名
            status_label.config(text="生成log文件名...")
            progress_var.set(20)
            progress_dialog.update()
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{log_name}_{current_time}.txt"
            log_path = f"/data/local/tmp/{log_filename}"
            
            # 2. 启动logcat进程
            status_label.config(text="启动logcat进程...")
            progress_var.set(50)
            progress_dialog.update()
            
            cmd = ["adb", "-s", device, "shell", "nohup", "logcat", "-v", "time", "-b", "all", "-f", log_path, ">", "/dev/null", "2>&1", "&"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"启动logcat失败: {result.stderr.strip()}")
            
            # 3. 检查logcat进程是否存在
            status_label.config(text="检查logcat进程...")
            progress_var.set(80)
            progress_dialog.update()
            
            cmd3 = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(cmd3, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"检查进程失败: {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception("logcat进程不存在，启动失败")
            
            # 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device, "log_filename": log_filename, "log_path": log_path, "mode": "offline"}
        
        # 定义完成回调
        def on_adblog_start_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                # 更新状态
                self.app.ui.status_var.set(f"离线ADB log已开启 - {result['device']} - {result['log_filename']}")
        
        # 定义错误回调
        def on_adblog_start_error(error):
            messagebox.showerror("错误", f"开启离线ADB log时发生错误: {error}")
            self.app.ui.status_var.set("开启离线ADB log失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("开启离线ADB Log", adblog_start_worker, on_adblog_start_done, on_adblog_start_error)
    
    def _start_online_adblog(self, device, log_name):
        """开启连线adb log（新功能）"""
        # 定义后台工作函数
        def online_adblog_worker(progress_var, status_label, progress_dialog, stop_flag):
            # 检查是否被要求停止
            if stop_flag and stop_flag.is_set():
                return {"success": False, "message": "操作已取消"}
            
            # 1. 创建日志目录
            status_label.config(text="创建日志目录...")
            progress_var.set(20)
            progress_dialog.update()
            
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{curredate}"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 创建adblog目录
            adblog_dir = os.path.join(log_dir, "adblog")
            if not os.path.exists(adblog_dir):
                os.makedirs(adblog_dir)
            
            # 2. 生成带时间的log文件名
            status_label.config(text="生成log文件名...")
            progress_var.set(40)
            progress_dialog.update()
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{log_name}_{current_time}.txt"
            log_file_path = os.path.join(adblog_dir, log_filename)
            
            # 3. 启动连线logcat进程（使用nohup在设备上运行，但直接输出到PC文件）
            status_label.config(text="启动连线logcat进程...")
            progress_var.set(60)
            progress_dialog.update()
            
            # 使用adb logcat命令直接输出到PC文件，同时在设备上启动nohup进程
            cmd = ["adb", "-s", device, "shell", "nohup", "logcat", "-b", "all", "-v", "time", ">", "/data/local/tmp/online_logcat.txt", "2>&1", "&"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"启动连线logcat失败: {result.stderr.strip()}")
            
            # 4. 同时启动PC端进程将设备上的log输出到PC文件
            status_label.config(text="启动PC端log输出进程...")
            progress_var.set(70)
            progress_dialog.update()
            
            # 启动PC端进程，将设备log实时输出到PC文件
            pc_cmd = ["adb", "-s", device, "logcat", "-b", "all", "-v", "time"]
            try:
                with open(log_file_path, 'w', encoding='utf-8') as log_file:
                    process = subprocess.Popen(pc_cmd, stdout=log_file, stderr=subprocess.PIPE, 
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                
                # 存储进程对象以供后续停止使用
                self._online_logcat_process = process
                self._online_log_file_path = log_file_path
                
            except Exception as e:
                raise Exception(f"启动PC端log输出进程失败: {str(e)}")
            
            # 5. 验证logcat进程是否存在
            status_label.config(text="验证logcat进程...")
            progress_var.set(80)
            progress_dialog.update()
            
            cmd3 = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(cmd3, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"检查进程失败: {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception("logcat进程不存在，启动失败")
            
            # 6. 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device, "log_filename": log_filename, "log_file_path": log_file_path, "mode": "online"}
        
        # 定义完成回调
        def on_online_adblog_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                # 更新状态
                self.app.ui.status_var.set(f"连线ADB log已开启 - {result['device']} - {result['log_filename']}")
        
        # 定义错误回调
        def on_online_adblog_error(error):
            messagebox.showerror("错误", f"开启连线ADB log时发生错误: {error}")
            self.app.ui.status_var.set("开启连线ADB log失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("开启连线ADB Log", online_adblog_worker, on_online_adblog_done, on_online_adblog_error)
    
    def export_adblog(self):
        """停止adb log并导出"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 检查是否有连线adb log进程正在运行
        if hasattr(self, '_online_logcat_process') and self._online_logcat_process and self._online_logcat_process.poll() is None:
            # 有连线adb log进程，直接停止它
            self._stop_online_adblog()
            return
        
        # 没有连线进程，按原有逻辑处理离线adb log
        self._export_offline_adblog(device)
    
    def _stop_online_adblog(self):
        """停止连线adb log"""
        try:
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return
            
            # 1. 终止PC端logcat进程
            if hasattr(self, '_online_logcat_process') and self._online_logcat_process:
                self._online_logcat_process.terminate()
                try:
                    self._online_logcat_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._online_logcat_process.kill()
                    self._online_logcat_process.wait()
                self._online_logcat_process = None
            
            # 2. 终止设备上的logcat进程
            # 查找并杀掉设备上的logcat进程
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-ef"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                logcat_pids = []
                
                for line in lines:
                    if 'logcat' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                logcat_pids.append(pid)
                                print(f"找到logcat进程 PID: {pid}")
                            except ValueError:
                                continue
                
                # 杀掉找到的logcat进程
                if logcat_pids:
                    for pid in logcat_pids:
                        kill_cmd = ["adb", "-s", device, "shell", "kill", str(pid)]
                        kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30, 
                                                  creationflags=subprocess.CREATE_NO_WINDOW)
                        if kill_result.returncode == 0:
                            print(f"成功停止logcat进程 PID: {pid}")
                        else:
                            print(f"停止进程 PID {pid} 失败: {kill_result.stderr.strip()}")
            
            # 3. 打开日志文件所在目录
            if hasattr(self, '_online_log_file_path') and self._online_log_file_path:
                log_dir = os.path.dirname(self._online_log_file_path)
                os.startfile(log_dir)
                self.app.ui.status_var.set("连线ADB log已停止并保存")
            else:
                self.app.ui.status_var.set("连线ADB log已停止")
            
            print("连线ADB log进程已成功停止")
                
        except Exception as e:
            messagebox.showerror("错误", f"停止连线ADB log时发生错误: {str(e)}")
            self.app.ui.status_var.set("停止连线ADB log失败")
    
    def _export_offline_adblog(self, device):
        """导出离线adb log（原有逻辑）"""
        # 定义后台工作函数
        def adblog_worker(progress_var, status_label, progress_dialog, stop_flag):
            # 检查是否被要求停止
            if stop_flag and stop_flag.is_set():
                return {"success": False, "message": "操作已取消"}
            
            # 1. 检查设备连接状态
            status_label.config(text="检查设备连接状态...")
            progress_var.set(10)
            progress_dialog.update()
            
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception("检查设备连接失败")
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                raise Exception(f"设备 {device} 未连接")
            
            # 2. 检查logcat进程是否存在
            status_label.config(text="检查logcat进程...")
            progress_var.set(25)
            progress_dialog.update()
            
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"检查进程失败: {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception("logcat进程不存在，log抓取异常")
            
            # 3. 精确杀掉nohup启动的logcat进程
            status_label.config(text="停止nohup logcat进程...")
            progress_var.set(40)
            progress_dialog.update()
            
            # 查找nohup启动的logcat进程
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-ef"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
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
                                print(f"找到nohup logcat进程 PID: {pid}")
                            except ValueError:
                                continue
                
                # 杀掉找到的nohup logcat进程
                if nohup_pids:
                    for pid in nohup_pids:
                        kill_cmd = ["adb", "-s", device, "shell", "kill", str(pid)]
                        kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30, 
                                                  creationflags=subprocess.CREATE_NO_WINDOW)
                        if kill_result.returncode == 0:
                            print(f"成功停止nohup logcat进程 PID: {pid}")
                        else:
                            print(f"停止进程 PID {pid} 失败: {kill_result.stderr.strip()}")
                else:
                    print("未找到nohup启动的logcat进程")
            else:
                print(f"获取进程列表失败: {result.stderr.strip()}")
            
            # 4. 创建日志目录
            status_label.config(text="创建日志目录...")
            progress_var.set(50)
            progress_dialog.update()
            
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{curredate}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 5. 导出log文件
            status_label.config(text="导出log文件...")
            progress_var.set(70)
            progress_dialog.update()
            
            # 创建logcat目录
            logcat_dir = os.path.join(log_dir, "logcat")
            if not os.path.exists(logcat_dir):
                os.makedirs(logcat_dir)
            
            # 先获取设备上的所有txt文件列表
            ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，逐个导出
                txt_files = result.stdout.strip().split('\n')
                exported_count = 0
                for txt_file in txt_files:
                    if txt_file.strip():
                        filename = os.path.basename(txt_file.strip())
                        pull_cmd = ["adb", "-s", device, "pull", txt_file.strip(), os.path.join(logcat_dir, filename)]
                        result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=120, 
                                              creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        if result.returncode == 0:
                            exported_count += 1
                            print(f"成功导出: {filename}")
                        else:
                            print(f"警告: {filename} 导出失败: {result.stderr.strip()}")
                
                if exported_count == 0:
                    raise Exception("没有成功导出任何log文件")
            else:
                # 没有找到txt文件，尝试导出整个tmp目录
                status_label.config(text="未找到txt文件，导出整个tmp目录...")
                progress_dialog.update()
                
                pull_cmd = ["adb", "-s", device, "pull", "/data/local/tmp/", logcat_dir]
                result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=120, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    raise Exception(f"导出tmp目录失败: {result.stderr.strip()}")
            
            # 6. 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"log_folder": logcat_dir, "device": device, "operation_type": "offline_adb_export"}
        
        # 定义完成回调
        def on_adblog_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                # 打开日志文件夹
                if result["log_folder"]:
                    os.startfile(result["log_folder"])
                # 更新状态
                self.app.ui.status_var.set(f"离线ADB log已导出 - {result['device']}")
        
        # 定义错误回调
        def on_adblog_error(error):
            if "logcat进程不存在" in str(error):
                messagebox.showerror("错误", "logcat进程不存在，log抓取异常")
                self.app.ui.status_var.set("logcat进程不存在")
            else:
                messagebox.showerror("错误", f"停止并导出离线ADB log时发生错误: {error}")
                self.app.ui.status_var.set("停止并导出离线ADB log失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("停止并导出离线ADB Log", adblog_worker, on_adblog_done, on_adblog_error)
    
    def start_google_adblog(self, device, log_name, target_folder):
        """为Google日志启动ADB log"""
        # 清空/data/local/tmp/目录下的所有文件
        clear_cmd = ["adb", "-s", device, "shell", "rm", "-f", "/data/local/tmp/*"]
        result = subprocess.run(clear_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            print(f"警告: 清空/data/local/tmp/目录失败: {result.stderr.strip()}")
        
        # 生成带时间的log文件名
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{log_name}_{current_time}.txt"
        log_path = f"/data/local/tmp/{log_filename}"
        
        # 启动logcat进程
        cmd = ["adb", "-s", device, "shell", "nohup", "logcat", "-v", "time", "-b", "all", "-f", log_path, ">", "/dev/null", "2>&1", "&"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            print(f"警告: 启动Google logcat失败: {result.stderr.strip()}")
            return False
        
        # 检查logcat进程是否存在
        cmd3 = ["adb", "-s", device, "shell", "ps", "-A"]
        result = subprocess.run(cmd3, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0 and "logcat" in result.stdout:
            print(f"Google ADB log已启动: {log_filename}")
            return True
        else:
            print("Google logcat进程不存在，启动失败")
            return False
    
    def stop_and_export_to_folder(self, device, target_folder):
        """停止ADB log并导出到指定文件夹"""
        # 检查设备连接状态
        devices_cmd = ["adb", "devices"]
        result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0 or device not in result.stdout:
            print(f"设备 {device} 未连接")
            return False
        
        # 检查logcat进程是否存在
        ps_cmd = ["adb", "-s", device, "shell", "ps", "-A"]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0 or "logcat" not in result.stdout:
            print("logcat进程不存在")
            return False
        
        # 停止nohup启动的logcat进程
        ps_cmd = ["adb", "-s", device, "shell", "ps", "-ef"]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            nohup_pids = []
            
            for line in lines:
                if 'logcat' in line and '/data/local/tmp/' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            nohup_pids.append(pid)
                        except ValueError:
                            continue
            
            # 杀掉找到的nohup logcat进程
            for pid in nohup_pids:
                kill_cmd = ["adb", "-s", device, "shell", "kill", str(pid)]
                subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        
        # 导出log文件到指定目录
        ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
        result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        
        if result.returncode == 0 and result.stdout.strip():
            txt_files = result.stdout.strip().split('\n')
            exported_count = 0
            for txt_file in txt_files:
                if txt_file.strip():
                    filename = os.path.basename(txt_file.strip())
                    pull_cmd = ["adb", "-s", device, "pull", txt_file.strip(), os.path.join(target_folder, filename)]
                    result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=120, 
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    if result.returncode == 0:
                        exported_count += 1
                        print(f"成功导出Google log: {filename}")
        
        return exported_count > 0
