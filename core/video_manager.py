#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 录制管理器
适配原Tkinter版本的视频录制功能
"""

import subprocess
import os
import datetime
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMetaObject, Qt
from PyQt5.QtWidgets import QMessageBox


class VideoManager(QObject):
    """录制管理器"""
    
    # 信号定义
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    video_saved = pyqtSignal(str, int)  # video_dir, count
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.is_recording = False
        self.recording_process = None
        self.recording_thread = None
        self.recorded_files = []
        
    def toggle_recording(self):
        """切换录制状态"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """开始录制"""
        device = self.device_manager.validate_device_selection()
        if not device:
            # 录制开始失败，发送停止信号以重置按钮状态
            self.recording_stopped.emit()
            return
        
        if self.is_recording:
            self.status_message.emit(self.lang_manager.tr("录制已在进行中"))
            # 录制已在进行中，发送停止信号以重置按钮状态
            self.recording_stopped.emit()
            return
        
        # 检查屏幕状态
        try:
            screen_check_cmd = ["adb", "-s", device, "shell", "dumpsys", "display"]
            result = subprocess.run(
                screen_check_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0 and result.stdout and "mScreenState=OFF" in result.stdout:
                # 屏幕关闭，点亮屏幕
                wake_cmd = ["adb", "-s", device, "shell", "input", "keyevent", "KEYCODE_WAKEUP"]
                subprocess.run(
                    wake_cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                time.sleep(2)
            
            # 设置时钟显示秒数
            clock_cmd = ["adb", "-s", device, "shell", "settings", "put", "secure", "clock_seconds", "1"]
            subprocess.run(
                clock_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('准备录制失败:')} {str(e)}")
            # 准备录制失败，发送停止信号以重置按钮状态
            self.recording_stopped.emit()
            return
        
        # 开始实际录制
        self.is_recording = True
        self.recorded_files.clear()
        
        # 在后台线程中执行录制
        self.recording_thread = threading.Thread(target=self._recording_worker, args=(device,), daemon=True)
        self.recording_thread.start()
        
        self.recording_started.emit()
        self.status_message.emit(f"{self.lang_manager.tr('视频录制已开始 -')} {device}")
    
    def _recording_worker(self, device):
        """录制工作线程"""
        try:
            while self.is_recording:
                # 生成文件名
                current_time = datetime.datetime.now()
                time_str = current_time.strftime("%Y%m%d_%H%M%S")
                filename = f"video_{time_str}.mp4"
                
                # 检查是否有mtklog文件夹
                check_cmd = ["adb", "-s", device, "shell", "ls", "/sdcard"]
                result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0 and result.stdout:
                    video_path = f"/sdcard/Recorders/{filename}"
                
                # 记录录制的文件路径
                self.recorded_files.append(video_path)
                
                # 智能录制：先尝试无限时间(0)，如果失败则使用180秒
                time_limit = "0"  # 默认尝试无限时间
                record_cmd = ["adb", "-s", device, "shell", "screenrecord", "--time-limit", time_limit, video_path]
                
                # 先测试命令是否支持time-limit 0
                test_cmd = ["adb", "-s", device, "shell", "screenrecord", "--time-limit", "0", "/dev/null"]
                test_result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # 如果测试失败，说明不支持time-limit 0，使用180秒
                if test_result.returncode != 0 and "outside acceptable range" in test_result.stderr:
                    time_limit = "180"
                    record_cmd = ["adb", "-s", device, "shell", "screenrecord", "--time-limit", time_limit, video_path]
                    print(f"设备不支持time-limit 0，使用180秒限制")
                else:
                    print(f"设备支持time-limit 0，使用无限时间录制")
                
                self.recording_process = subprocess.Popen(
                    record_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # 等待录制完成或停止
                self.recording_process.wait()
                
                if not self.is_recording:
                    break
                
                # 短暂等待后继续录制
                time.sleep(1)
                
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('录制过程中发生错误:')} {str(e)}")
        finally:
            self.is_recording = False
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # 终止录制进程
        if self.recording_process:
            try:
                # 发送SIGTERM信号，让进程优雅退出
                self.recording_process.terminate()
                # 等待进程完成，给更多时间让文件写入完成
                self.recording_process.wait(timeout=10)
            except:
                # 如果优雅退出失败，强制终止
                try:
                    self.recording_process.kill()
                    self.recording_process.wait(timeout=3)
                except:
                    pass
            self.recording_process = None
        
        # 等待一段时间确保文件写入完成
        time.sleep(2)
        
        # 在后台线程中保存视频
        save_thread = threading.Thread(target=self._save_videos, daemon=True)
        save_thread.start()
        
        self.recording_stopped.emit()
        self.status_message.emit(self.lang_manager.tr("正在保存视频..."))
    
    def _save_videos(self):
        """保存视频文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 创建保存目录
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            log_dir = f"c:\\log\\{date_str}"
            video_dir = os.path.join(log_dir, "video")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            if not os.path.exists(video_dir):
                os.makedirs(video_dir)
            
            # 查找视频文件
            video_files = []
            
            # 使用录制时记录的文件路径
            if self.recorded_files:
                video_files = self.recorded_files.copy()
                print(f"使用录制的文件路径: {video_files}")
            
            # 如果录制记录为空，搜索可能的目录
            if not video_files:
                print("录制记录为空，开始搜索视频文件...")
                search_paths = ["/sdcard/mtklog", "/sdcard"]
                
                for search_path in search_paths:
                    try:
                        ls_cmd = ["adb", "-s", device, "shell", "ls", "-1", search_path]
                        result = subprocess.run(
                            ls_cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            files = result.stdout.strip().split('\n')
                            for file in files:
                                file = file.strip()
                                if file.startswith('video_') and file.endswith('.mp4'):
                                    full_path = f"{search_path}/{file}"
                                    video_files.append(full_path)
                    except Exception as e:
                        print(f"{self.lang_manager.tr('搜索')} {search_path} {self.lang_manager.tr('失败:')} {e}")
            
            if not video_files:
                self.status_message.emit(self.lang_manager.tr("未找到录制的视频文件"))
                self.video_saved.emit(video_dir, 0)  # 发送信号，避免卡住
                return
            
            # 保存视频文件
            saved_count = 0
            
            for video_file in video_files:
                filename = os.path.basename(video_file)
                local_path = os.path.join(video_dir, filename)
                print(f"尝试保存视频文件: {video_file} -> {local_path}")
                
                # 先检查远程文件是否存在
                check_cmd = ["adb", "-s", device, "shell", "ls", "-la", video_file]
                check_result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if check_result.returncode != 0:
                    print(f"远程文件不存在: {video_file}")
                    continue
                
                print(f"远程文件存在，开始pull: {video_file}")
                pull_cmd = ["adb", "-s", device, "pull", video_file, local_path]
                result = subprocess.run(
                    pull_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                print(f"Pull命令结果: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}")
                
                if result.returncode == 0:
                    saved_count += 1
                    print(f"成功保存: {local_path}")
                    # 删除远程文件
                    try:
                        rm_cmd = ["adb", "-s", device, "shell", "rm", video_file]
                        subprocess.run(
                            rm_cmd,
                            capture_output=True,
                            text=True,
                            timeout=15,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                    except:
                        pass
            
            # 清空录制文件记录
            self.recorded_files.clear()
            
            if saved_count > 0:
                # 打开视频文件夹
                os.startfile(video_dir)
                self.video_saved.emit(video_dir, saved_count)
                self.status_message.emit(f"{self.lang_manager.tr('视频已保存 -')} {saved_count}{self.lang_manager.tr('个文件')}")
            else:
                self.status_message.emit(self.lang_manager.tr("没有成功保存任何视频文件"))
                
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('保存视频失败:')} {str(e)}")
    
    def start_google_recording(self, device, video_dir):
        """启动Google日志专用的视频录制
        
        Args:
            device: 设备ID
            video_dir: 保存目录
        """
        if self.is_recording:
            self.status_message.emit(self.lang_manager.tr("录制已在进行中"))
            return False
        
        # 检查屏幕状态
        try:
            screen_check_cmd = ["adb", "-s", device, "shell", "dumpsys", "display"]
            result = subprocess.run(
                screen_check_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0 and result.stdout and "mScreenState=OFF" in result.stdout:
                # 屏幕关闭，点亮屏幕
                wake_cmd = ["adb", "-s", device, "shell", "input", "keyevent", "KEYCODE_WAKEUP"]
                subprocess.run(
                    wake_cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                time.sleep(2)
            
            # 设置时钟显示秒数
            clock_cmd = ["adb", "-s", device, "shell", "settings", "put", "secure", "clock_seconds", "1"]
            subprocess.run(
                clock_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('准备录制失败:')} {str(e)}")
            return False
        
        # 开始实际录制
        self.is_recording = True
        self.recorded_files.clear()
        
        # 在后台线程中执行录制
        self.recording_thread = threading.Thread(target=self._recording_worker, args=(device,), daemon=True)
        self.recording_thread.start()
        
        self.status_message.emit(f"{self.lang_manager.tr('Google视频录制已开始 -')} {device}")
        return True
    
    def stop_and_export_to_video_dir(self, device, video_dir):
        """停止录制并导出到指定文件夹
        
        Args:
            device: 设备ID
            video_dir: 目标文件夹
        """
        if not self.is_recording:
            self.status_message.emit(self.lang_manager.tr("录制未运行"))
            return False
        
        self.is_recording = False
        
        # 终止录制进程
        if self.recording_process:
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
            except:
                pass
            self.recording_process = None
        
        # 在后台线程中保存视频到指定文件夹
        save_thread = threading.Thread(target=self._save_videos_to_video_dir, args=(device, video_dir), daemon=True)
        save_thread.start()
        
        self.status_message.emit(self.lang_manager.tr("正在保存Google视频..."))
        return True
    
    def _save_videos_to_video_dir(self, device, video_dir):
        """保存视频文件到指定文件夹"""
        try:
            # 确保文件夹存在
            if not os.path.exists(video_dir):
                os.makedirs(video_dir)
            
            # 查找视频文件
            video_files = []
            
            # 使用录制时记录的文件路径
            if self.recorded_files:
                video_files = self.recorded_files.copy()
            
            # 如果录制记录为空，搜索可能的目录
            if not video_files:
                search_paths = ["/sdcard/mtklog", "/sdcard"]
                
                for search_path in search_paths:
                    try:
                        ls_cmd = ["adb", "-s", device, "shell", "ls", "-1", search_path]
                        result = subprocess.run(
                            ls_cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            files = result.stdout.strip().split('\n')
                            for file in files:
                                file = file.strip()
                                if file.startswith('video_') and file.endswith('.mp4'):
                                    full_path = f"{search_path}/{file}"
                                    video_files.append(full_path)
                    except Exception as e:
                        print(f"{self.lang_manager.tr('搜索')} {search_path} {self.lang_manager.tr('失败:')} {e}")
            
            if not video_files:
                self.status_message.emit(self.lang_manager.tr("未找到录制的视频文件"))
                self.video_saved.emit(video_dir, 0)  # 发送信号，避免卡住
                return
            
            # 保存视频文件
            saved_count = 0
            
            for i, video_file in enumerate(video_files, 1):
                filename = os.path.basename(video_file)
                local_path = os.path.join(video_dir, filename)
                
                # 先检查远程文件是否存在
                check_cmd = ["adb", "-s", device, "shell", "ls", "-la", video_file]
                check_result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if check_result.returncode != 0:
                    continue
                
                pull_cmd = ["adb", "-s", device, "pull", video_file, local_path]
                result = subprocess.run(
                    pull_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    saved_count += 1
                    # 删除远程文件
                    try:
                        rm_cmd = ["adb", "-s", device, "shell", "rm", video_file]
                        subprocess.run(
                            rm_cmd,
                            capture_output=True,
                            text=True,
                            timeout=15,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                    except:
                        pass
            
            # 清空录制文件记录
            self.recorded_files.clear()
            
            if saved_count > 0:
                self.status_message.emit(f"{self.lang_manager.tr('Google视频已保存到:')} {video_dir} ({saved_count}{self.lang_manager.tr('个文件')})")
                self.video_saved.emit(video_dir, saved_count)  # 发送视频保存完成信号
            else:
                self.status_message.emit(self.lang_manager.tr("没有成功保存任何视频文件"))
                self.video_saved.emit(video_dir, 0)  # 即使没有保存也发送信号
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_message.emit(f"{self.lang_manager.tr('保存Google视频失败:')} {str(e)}")
            self.video_saved.emit(video_dir, 0)  # 出错也发送信号

