#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频录制管理模块
负责设备视频录制功能
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import os
import datetime
import threading
import time

class VideoManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_recording = False
        self.recording_process = None
        self.recording_thread = None
        self.recording_button = None
        
    def set_recording_button(self, button):
        """设置录制按钮引用"""
        self.recording_button = button
    
    def toggle_recording(self):
        """切换录制状态"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """开始录制"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 定义后台工作函数
        def recording_start_worker(progress_var, status_label, progress_dialog):
            # 1. 检查屏幕状态
            status_label.config(text="检查屏幕状态...")
            progress_var.set(20)
            progress_dialog.update()
            
            # 检查屏幕是否亮起
            screen_check_cmd = ["adb", "-s", device, "shell", "dumpsys", "display"]
            result = subprocess.run(screen_check_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                if "mScreenState=OFF" in result.stdout:
                    # 屏幕关闭，需要点亮
                    status_label.config(text="屏幕关闭，正在点亮...")
                    progress_var.set(40)
                    progress_dialog.update()
                    
                    wake_cmd = ["adb", "-s", device, "shell", "input", "keyevent", "KEYCODE_WAKEUP"]
                    subprocess.run(wake_cmd, capture_output=True, text=True, timeout=15, 
                                 creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    # 等待屏幕亮起
                    time.sleep(2)
                else:
                    status_label.config(text="屏幕已亮起")
                    progress_var.set(40)
                    progress_dialog.update()
            else:
                print(f"警告: 检查屏幕状态失败: {result.stderr.strip()}")
            
            # 2. 等待设备连接
            status_label.config(text="等待设备连接...")
            progress_var.set(60)
            progress_dialog.update()
            
            wait_cmd = ["adb", "-s", device, "wait-for-device"]
            result = subprocess.run(wait_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"设备连接失败: {result.stderr.strip()}")
            
            # 3. 设置时钟显示秒数
            status_label.config(text="设置系统参数...")
            progress_var.set(80)
            progress_dialog.update()
            
            clock_cmd = ["adb", "-s", device, "shell", "settings", "put", "secure", "clock_seconds", "1"]
            subprocess.run(clock_cmd, capture_output=True, text=True, timeout=15, 
                         creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 4. 开始录制
            status_label.config(text="开始录制视频...")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device, "status": "recording_started"}
        
        # 定义完成回调
        def on_recording_start_done(result):
            # 开始实际录制
            self._start_actual_recording(result["device"])
            # 更新状态
            self.app.ui.status_var.set(f"视频录制已开始 - {result['device']}")
        
        # 定义错误回调
        def on_recording_start_error(error):
            messagebox.showerror("错误", f"开始录制时发生错误: {error}")
            self.app.ui.status_var.set("开始录制失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("开始录制", recording_start_worker, on_recording_start_done, on_recording_start_error)
    
    def _start_actual_recording(self, device):
        """开始实际录制"""
        self.is_recording = True
        
        # 更新按钮状态
        if self.recording_button:
            self.recording_button.config(text="停止录制")
        
        # 在后台线程中执行录制
        self.recording_thread = threading.Thread(target=self._recording_worker, args=(device,), daemon=True)
        self.recording_thread.start()
    
    def _recording_worker(self, device):
        """录制工作线程"""
        try:
            # 初始化录制文件列表
            if not hasattr(self, 'recorded_files'):
                self.recorded_files = []
                
            while self.is_recording:
                # 生成文件名
                current_time = datetime.datetime.now()
                time_str = current_time.strftime("%Y%m%d_%H%M%S")
                filename = f"video_{time_str}.mp4"
                
                # 检查是否有mtklog文件夹
                check_cmd = ["adb", "-s", device, "shell", "ls", "/sdcard"]
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and "mtklog" in result.stdout:
                    # 有mtklog文件夹，保存到mtklog目录
                    video_path = f"/sdcard/mtklog/{filename}"
                    print(f"录制到mtklog目录: {filename}")
                else:
                    # 没有mtklog文件夹，保存到sdcard根目录
                    video_path = f"/sdcard/{filename}"
                    print(f"录制到sdcard根目录: {filename}")
                
                # 记录实际录制的文件路径
                self.recorded_files.append(video_path)
                
                # 开始录制（限制3分钟，避免某些设备限制）
                record_cmd = ["adb", "-s", device, "shell", "screenrecord", "--time-limit", "180", video_path]
                
                print(f"开始录制: {filename}")
                self.recording_process = subprocess.Popen(record_cmd, 
                                                        stdout=subprocess.PIPE, 
                                                        stderr=subprocess.PIPE,
                                                        creationflags=subprocess.CREATE_NO_WINDOW)
                
                # 等待录制完成或停止
                self.recording_process.wait()
                
                if not self.is_recording:
                    # 用户主动停止，跳出循环
                    break
                
                print(f"录制完成: {filename}，继续录制下一个文件...")
                
                # 短暂等待后继续录制
                time.sleep(1)
                
        except Exception as e:
            print(f"录制过程中发生错误: {e}")
        finally:
            self.is_recording = False
            # 恢复按钮状态
            if self.recording_button:
                self.app.root.after(0, lambda: self.recording_button.config(text="开始录制"))
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # 终止录制进程
        if self.recording_process:
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
            except:
                pass
            self.recording_process = None
        
        # 更新按钮状态
        if self.recording_button:
            self.recording_button.config(text="开始录制")
        
        # 定义后台工作函数 - 保存视频文件
        def save_video_worker(progress_var, status_label, progress_dialog):
            device = self.app.device_manager.get_selected_device()
            if not device:
                raise Exception("未选择设备")
            
            # 1. 创建保存目录
            status_label.config(text="创建保存目录...")
            progress_var.set(20)
            progress_dialog.update()
            
            log_dir = "c:\\log"
            video_dir = os.path.join(log_dir, "video")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            if not os.path.exists(video_dir):
                os.makedirs(video_dir)
            
            # 2. 查找视频文件
            status_label.config(text="查找视频文件...")
            progress_var.set(40)
            progress_dialog.update()
            
            # 查找视频文件 - 优先使用录制时记录的文件路径
            video_files = []
            
            # 方法1: 使用录制时记录的文件路径
            if hasattr(self, 'recorded_files') and self.recorded_files:
                print(f"使用录制时记录的文件路径: {self.recorded_files}")
                video_files = self.recorded_files.copy()
            
            # 方法2: 如果录制记录为空，搜索可能的目录
            if not video_files:
                search_paths = ["/sdcard/mtklog", "/sdcard"]
                
                for search_path in search_paths:
                    try:
                        # 使用ls命令列出目录中的所有mp4文件
                        ls_cmd = ["adb", "-s", device, "shell", "ls", "-1", search_path]
                        result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, 
                                              creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        if result.returncode == 0 and result.stdout.strip():
                            files = result.stdout.strip().split('\n')
                            for file in files:
                                file = file.strip()
                                if file.startswith('video_') and file.endswith('.mp4'):
                                    full_path = f"{search_path}/{file}"
                                    video_files.append(full_path)
                                    print(f"找到视频文件: {full_path}")
                    except Exception as e:
                        print(f"搜索 {search_path} 失败: {e}")
                
                # 方法3: 如果上面没找到，尝试find命令
                if not video_files:
                    try:
                        find_cmd = ["adb", "-s", device, "shell", "find", "/sdcard", "-name", "video_*.mp4", "-type", "f"]
                        result = subprocess.run(find_cmd, capture_output=True, text=True, timeout=30, 
                                              creationflags=subprocess.CREATE_NO_WINDOW)
                        if result.returncode == 0 and result.stdout.strip():
                            video_files.extend([f.strip() for f in result.stdout.strip().split('\n') if f.strip()])
                            print(f"使用find命令找到: {video_files}")
                    except Exception as e:
                        print(f"find命令失败: {e}")
            
            if not video_files:
                raise Exception("未找到录制的视频文件")
            
            # 3. 保存视频文件
            status_label.config(text="保存视频文件...")
            progress_var.set(60)
            progress_dialog.update()
            
            saved_count = 0
            print(f"找到 {len(video_files)} 个视频文件: {video_files}")
            
            for video_file in video_files:
                filename = os.path.basename(video_file)
                local_path = os.path.join(video_dir, filename)
                
                print(f"正在保存: {video_file} -> {local_path}")
                
                # 先检查远程文件是否存在
                check_cmd = ["adb", "-s", device, "shell", "ls", "-la", video_file]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, 
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                
                if check_result.returncode != 0:
                    print(f"远程文件不存在: {video_file}")
                    continue
                
                pull_cmd = ["adb", "-s", device, "pull", video_file, local_path]
                result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=300, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    saved_count += 1
                    print(f"成功保存: {filename}")
                    # 删除远程文件以节省空间
                    try:
                        rm_cmd = ["adb", "-s", device, "shell", "rm", video_file]
                        subprocess.run(rm_cmd, capture_output=True, text=True, timeout=15, 
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                        print(f"已删除远程文件: {video_file}")
                    except:
                        pass
                else:
                    print(f"保存失败: {filename} - {result.stderr.strip()}")
                    print(f"Pull命令输出: {result.stdout.strip()}")
            
            if saved_count == 0:
                raise Exception("没有成功保存任何视频文件")
            
            # 4. 完成 - 清空录制文件记录
            if hasattr(self, 'recorded_files'):
                self.recorded_files.clear()
            
            status_label.config(text="保存完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"video_folder": video_dir, "saved_count": saved_count, "device": device}
        
        # 定义完成回调
        def on_save_done(result):
            # 打开视频文件夹
            if result["video_folder"]:
                os.startfile(result["video_folder"])
            # 更新状态
            self.app.ui.status_var.set(f"视频已保存 - {result['device']} - {result['saved_count']}个文件")
        
        # 定义错误回调
        def on_save_error(error):
            messagebox.showerror("错误", f"保存视频时发生错误: {error}")
            self.app.ui.status_var.set("保存视频失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("保存视频", save_video_worker, on_save_done, on_save_error)
