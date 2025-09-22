#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络Ping工具模块
负责网络连通性测试和状态监控
"""

import subprocess
import threading
import time
from typing import Optional

class PingManager:
    """Ping管理器"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_ping_running = False
        self.ping_thread = None
        self.ping_process = None
    
    def start_network_ping(self):
        """开始网络Ping测试"""
        try:
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return
            
            if self.is_ping_running:
                from tkinter import messagebox
                messagebox.showwarning("警告", "Ping测试已在运行中")
                return
            
            self.is_ping_running = True
            self.app.ui.network_ping_button.config(text="停止")
            
            # 显示初始状态
            self._update_ping_status("正在测试...", "blue")
            
            # 启动Ping线程
            self.ping_thread = threading.Thread(target=self._ping_worker, args=(device,), daemon=True)
            self.ping_thread.start()
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("错误", f"启动Ping测试失败: {str(e)}")
            self.is_ping_running = False
            self.app.ui.network_ping_button.config(text="Ping")
    
    def stop_network_ping(self):
        """停止网络Ping测试"""
        try:
            print("[DEBUG] 开始停止ping...")
            self.is_ping_running = False
            
            # 强制终止ping进程
            if self.ping_process:
                try:
                    print("[DEBUG] 终止ping进程...")
                    self.ping_process.terminate()
                    try:
                        self.ping_process.wait(timeout=1)
                        print("[DEBUG] ping进程已正常终止")
                    except subprocess.TimeoutExpired:
                        print("[DEBUG] ping进程未响应，强制杀死...")
                        self.ping_process.kill()
                        self.ping_process.wait()
                        print("[DEBUG] ping进程已被强制杀死")
                except Exception as e:
                    print(f"[DEBUG] 终止ping进程失败: {str(e)}")
                finally:
                    self.ping_process = None
            
            # 等待工作线程结束
            if self.ping_thread and self.ping_thread.is_alive():
                print("[DEBUG] 等待ping工作线程结束...")
                self.ping_thread.join(timeout=3)
                if self.ping_thread.is_alive():
                    print("[DEBUG] ping工作线程未正常结束")
            
            # 更新UI
            self._safe_update_ui()
            
            print("[DEBUG] ping已完全停止")
            
        except Exception as e:
            print(f"[DEBUG] 停止Ping测试失败: {str(e)}")
    
    def _safe_update_ui(self):
        """安全更新UI"""
        try:
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'root'):
                # 检查窗口是否还存在
                if hasattr(self.app.ui.root, 'winfo_exists') and self.app.ui.root.winfo_exists():
                    self.app.ui.network_ping_button.config(text="Ping")
                    if hasattr(self.app.ui, 'network_ping_status_label'):
                        self.app.ui.network_ping_status_label.config(text="Ping已停止", foreground="gray")
        except Exception as e:
            print(f"[DEBUG] UI更新失败: {str(e)}")
    
    def _ping_worker(self, device):
        """Ping工作线程"""
        try:
            # 执行ping命令 - 使用更兼容的参数
            # 使用-i 0.5提高响应速度，但不限制包数，直到手动停止
            cmd = f"adb -s {device} shell ping -i 0.5 www.google.com"
            
            # 启动ping进程
            creation_flags = 0
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            self.ping_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )
            
            # 启动输出读取线程
            stdout_thread = threading.Thread(target=self._read_ping_stdout, daemon=True)
            stderr_thread = threading.Thread(target=self._read_ping_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            
            # 给ping进程一些时间来启动和发送数据包
            print("[DEBUG] 等待ping进程启动...")
            time.sleep(2)  # 等待2秒让ping进程启动并发送第一个包
            
            # 监控ping进程状态
            while self.is_ping_running and self.ping_process:
                try:
                    if self.ping_process.poll() is not None:
                        # 进程已结束，可能是网络问题或正常停止
                        if self.is_ping_running:  # 只有在用户没有主动停止时才显示异常
                            print("[DEBUG] ping进程意外结束，显示网络异常")
                            self._update_ping_status("网络异常", "red")
                        else:
                            print("[DEBUG] ping进程正常结束")
                        break
                    time.sleep(2)  # 延长检查间隔到2秒，减少CPU占用
                except Exception as e:
                    print(f"[DEBUG] Ping监控异常: {str(e)}")
                    if self.is_ping_running:
                        self._update_ping_status("网络异常", "red")
                    break
            
            # 等待输出读取线程结束
            print("[DEBUG] 等待输出读取线程结束...")
            stdout_thread.join(timeout=3)
            stderr_thread.join(timeout=3)
            
            if stdout_thread.is_alive():
                print("[DEBUG] stdout线程未正常结束")
            if stderr_thread.is_alive():
                print("[DEBUG] stderr线程未正常结束")
                
        except Exception as e:
            print(f"[DEBUG] Ping测试异常: {str(e)}")
            self._update_ping_status("网络异常", "red")
        finally:
            print("[DEBUG] 清理ping工作线程...")
            self.is_ping_running = False
            self.ping_process = None
            
            # 安全更新UI
            self._safe_update_ui()
    
    def _read_ping_stdout(self):
        """读取ping标准输出"""
        try:
            # 使用iter逐行读取，避免select兼容性问题
            for line in iter(self.ping_process.stdout.readline, ''):
                if not self.is_ping_running:
                    break
                
                line_lower = line.lower().strip()
                print(f"[DEBUG] ping输出: {line.strip()}")  # 添加调试输出
                
                # 检查成功响应 - 改进检测逻辑
                if any(keyword in line_lower for keyword in ["bytes from", "icmp_seq", "time="]):
                    # ping成功，显示绿色的"网络正常"
                    print("[DEBUG] 检测到ping成功")
                    self._update_ping_status("网络正常", "green")
                elif "ping:" in line_lower and ("unknown host" in line_lower or "name or service not known" in line_lower):
                    # DNS解析失败
                    print("[DEBUG] DNS解析失败")
                    self._update_ping_status("网络异常", "red")
                elif "ping:" in line_lower and ("network is unreachable" in line_lower or "destination host unreachable" in line_lower):
                    # 网络不可达
                    print("[DEBUG] 网络不可达")
                    self._update_ping_status("网络异常", "red")
                elif "ping:" in line_lower and ("timeout" in line_lower or "no answer" in line_lower):
                    # 请求超时
                    print("[DEBUG] 请求超时")
                    self._update_ping_status("网络异常", "red")
                elif "packets transmitted" in line_lower and "packet loss" in line_lower:
                    # ping统计信息
                    print("[DEBUG] ping统计信息")
                    if "0% packet loss" in line_lower:
                        self._update_ping_status("网络正常", "green")
                    else:
                        self._update_ping_status("网络异常", "red")
                        
        except Exception as e:
            print(f"[DEBUG] 读取ping stdout异常: {str(e)}")
            if self.is_ping_running:  # 只有在未停止时才显示异常
                self._update_ping_status("网络异常", "red")
    
    def _read_ping_stderr(self):
        """读取ping错误输出"""
        try:
            # 使用iter逐行读取，避免select兼容性问题
            for line in iter(self.ping_process.stderr.readline, ''):
                if not self.is_ping_running:
                    break
                
                line_lower = line.lower().strip()
                print(f"[DEBUG] ping错误输出: {line.strip()}")  # 添加调试输出
                
                # 检测各种网络错误，统一显示为"网络异常"
                if any(keyword in line_lower for keyword in [
                    "network is unreachable", 
                    "destination host unreachable",
                    "unknown host", 
                    "name or service not known",
                    "bad address",
                    "time to live exceeded",
                    "request timeout", 
                    "timeout",
                    "sendmsg:",
                    "sendto:",
                    "no route to host",
                    "connection refused"
                ]):
                    print("[DEBUG] 检测到网络错误")
                    self._update_ping_status("网络异常", "red")
                        
        except Exception as e:
            print(f"[DEBUG] 读取ping stderr异常: {str(e)}")
            if self.is_ping_running:  # 只有在未停止时才显示异常
                self._update_ping_status("网络异常", "red")
    
    def _update_ping_status(self, status_text, color):
        """更新Ping状态显示"""
        try:
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'root'):
                # 检查窗口是否还存在
                if hasattr(self.app.ui.root, 'winfo_exists') and self.app.ui.root.winfo_exists():
                    if hasattr(self.app.ui, 'network_ping_status_label'):
                        self.app.ui.network_ping_status_label.config(text=status_text, foreground=color)
        except Exception as e:
            print(f"[DEBUG] 更新Ping状态失败: {str(e)}")
