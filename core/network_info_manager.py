#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 网络信息管理器
适配原Tkinter版本的网络信息功能
"""

import subprocess
import threading
import re
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox

# 导入原始解析模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from Network_info.telephony_parser import compute_rows_for_registry
from Network_info.utilities_wifi_info import WifiInfoParser


class NetworkInfoWorker(threading.Thread):
    """网络信息工作线程"""
    
    def __init__(self, device, callback, stop_event):
        super().__init__()
        self.device = device
        self.callback = callback
        self.stop_event = stop_event
        self.wifi_parser = WifiInfoParser()
        
    def run(self):
        """获取网络信息"""
        while not self.stop_event.is_set():
            try:
                # 获取网络信息
                network_info = self._get_network_info()
                
                if network_info:
                    self.callback(network_info)
                
                # 等待1秒后再次获取
                self.stop_event.wait(1)
                
            except Exception as e:
                # 返回错误信息
                self.callback([{"error": str(e)}])
                self.stop_event.wait(1)
    
    def _get_network_info(self):
        """获取网络信息（包括WiFi）"""
        try:
            # 获取Telephony信息
            tel_result = subprocess.run(
                ["adb", "-s", self.device, "shell", "dumpsys", "telephony.registry"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            info_list = []
            if tel_result.returncode == 0:
                info_list = self._parse_network_info(tel_result.stdout)
            
            # 获取WiFi信息
            wifi_info = self._get_wifi_info()
            if wifi_info:
                info_list.append(wifi_info)
            
            return info_list
                
        except Exception as e:
            return [{"error": str(e)}]
    
    def _get_wifi_info(self):
        """获取WiFi信息 - 使用原始解析器"""
        try:
            # 获取WiFi信息
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "dumpsys", "wifi"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 使用原始的WifiInfoParser解析
                wifi = self.wifi_parser.parse_wifi(result.stdout)
                
                # 如果WiFi已连接，转换为Tab期望的格式
                if wifi.get('connected'):
                    wifi_info = {
                        'sim': 'WIFI',
                        'cc': 'WIFI',
                        'rat': 'WIFI',
                        'band': wifi.get('band', ''),
                        'dl_arfcn': wifi.get('freqMHz', 0),
                        'ul_arfcn': 0,
                        'pci': 0,
                        'rsrp': None,  # WIFI没有RSRP
                        'rsrq': None,
                        'sinr': None,
                        'rssi': wifi.get('rssi'),  # WIFI只有RSSI
                        'bw_dl': 0,
                        'bw_ul': 0,
                        'ca_endc': '',  # WIFI不需要CA_ENDC
                        'cqi': None,
                        'note': f"SSID: {wifi.get('ssid', '')}"
                    }
                    return wifi_info
            return None
                
        except Exception as e:
            print(f"获取WiFi信息失败: {e}")
            return None
    
    def _parse_network_info(self, output):
        """解析网络信息 - 使用原始解析器"""
        try:
            # 使用原始的telephony_parser进行解析
            rows = compute_rows_for_registry(output)
            
            # 转换为Tab期望的格式
            info_list = []
            for row in rows:
                info = {
                    'sim': row.get('SIM', ''),
                    'cc': row.get('CC', ''),
                    'rat': row.get('RAT', ''),
                    'band': row.get('BAND', ''),
                    'dl_arfcn': row.get('DL_ARFCN', ''),
                    'ul_arfcn': row.get('UL_ARFCN', ''),
                    'pci': row.get('PCI', ''),
                    'rsrp': row.get('RSRP', ''),
                    'rsrq': row.get('RSRQ', ''),
                    'sinr': row.get('SINR', ''),
                    'rssi': row.get('RSSI', ''),
                    'bw_dl': row.get('BW_DL', ''),
                    'bw_ul': row.get('BW_UL', ''),
                    'ca_endc': row.get('CA_ENDC', ''),
                    'cqi': row.get('CQI', ''),
                    'note': row.get('NOTE', '')
                }
                info_list.append(info)
            
            return info_list
            
        except Exception as e:
            print(f"解析网络信息失败: {e}")
            return []


class PingWorker(threading.Thread):
    """Ping工作线程"""
    
    def __init__(self, device, callback, stop_event):
        super().__init__()
        self.device = device
        self.callback = callback
        self.stop_event = stop_event
        self.ping_process = None
        self.last_status = None  # 记录上次的网络状态
        
    def _update_status(self, status):
        """更新网络状态，只在状态变化时输出"""
        if self.last_status != status:
            self.last_status = status
            self.callback(status)
    
    def run(self):
        """执行Ping测试"""
        try:
            # 执行ping命令 - 使用更兼容的参数
            # 使用-i 0.5提高响应速度，但不限制包数，直到手动停止
            cmd = f"adb -s {self.device} shell ping -i 0.5 www.google.com"
            
            # 启动ping进程
            creation_flags = 0
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            # 在Windows上，不使用shell=True，直接启动adb进程
            # 这样可以确保能够正确终止所有子进程
            import platform
            if platform.system() == 'Windows':
                # Windows上直接启动adb，不使用shell
                self.ping_process = subprocess.Popen(
                    ["adb", "-s", self.device, "shell", "ping", "-i", "0.5", "www.google.com"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=creation_flags
                )
            else:
                # 非Windows系统使用shell
                self.ping_process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=creation_flags
                )
            # 启动输出读取线程（初始启动）
            stdout_thread = threading.Thread(target=self._read_ping_stdout, daemon=True)
            stderr_thread = threading.Thread(target=self._read_ping_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            
            # 用于存储当前活动的读取线程
            active_stdout_thread = stdout_thread
            active_stderr_thread = stderr_thread
            
            # 给ping进程一些时间来启动和发送数据包
            import time
            time.sleep(2)  # 等待2秒让ping进程启动并发送第一个包
            
            # 监控ping进程状态
            retry_count = 0
            max_retries = 3  # 最多重试3次
            
            while not self.stop_event.is_set():
                try:
                    if self.ping_process and self.ping_process.poll() is not None:
                        # 进程已结束，可能是网络问题或正常停止
                        if not self.stop_event.is_set():  # 只有在用户没有主动停止时才显示异常
                            self._update_status("网络异常")
                            
                            
                            # 如果重试次数未达到上限，尝试重新启动ping进程
                            if retry_count < max_retries:
                                retry_count += 1
                                
                                # 清理旧进程
                                if self.ping_process:
                                    try:
                                        self.ping_process.terminate()
                                        self.ping_process.wait(timeout=1)
                                    except:
                                        pass
                                    self.ping_process = None
                                
                                # 等待一小段时间后重新启动
                                time.sleep(2)
                                
                                # 重新启动ping进程
                                if platform.system() == 'Windows':
                                    self.ping_process = subprocess.Popen(
                                        ["adb", "-s", self.device, "shell", "ping", "-i", "0.5", "www.google.com"],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,
                                        bufsize=1,
                                        universal_newlines=True,
                                        creationflags=creation_flags
                                    )
                                else:
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
                                
                                # 重新启动输出读取线程
                                active_stdout_thread = threading.Thread(target=self._read_ping_stdout, daemon=True)
                                active_stderr_thread = threading.Thread(target=self._read_ping_stderr, daemon=True)
                                active_stdout_thread.start()
                                active_stderr_thread.start()
                                
                                continue  # 继续监控新进程
                            else:
                                # 已达到最大重试次数，记录日志并停止
                                self.callback(f"Ping测试失败：已达到最大重试次数({max_retries}次)")
                                self._update_status("网络异常")
                                self.stop_event.set()
                                break
                        else:
                            # 用户主动停止
                            break
                    
                    time.sleep(0.5)  # 缩短检查间隔，提高响应速度
                except Exception as e:
                    if not self.stop_event.is_set():
                        self._update_status("网络异常")
                        # 如果重试次数未达到上限，尝试重新启动
                        if retry_count < max_retries:
                            retry_count += 1
                            
                            # 清理旧进程
                            if self.ping_process:
                                try:
                                    self.ping_process.terminate()
                                    self.ping_process.wait(timeout=1)
                                except:
                                    pass
                                self.ping_process = None
                            
                            # 等待一小段时间后重新启动
                            time.sleep(2)
                            
                            # 重新启动ping进程
                            try:
                                if platform.system() == 'Windows':
                                    self.ping_process = subprocess.Popen(
                                        ["adb", "-s", self.device, "shell", "ping", "-i", "0.5", "www.google.com"],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,
                                        bufsize=1,
                                        universal_newlines=True,
                                        creationflags=creation_flags
                                    )
                                else:
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
                                
                                # 重新启动输出读取线程
                                active_stdout_thread = threading.Thread(target=self._read_ping_stdout, daemon=True)
                                active_stderr_thread = threading.Thread(target=self._read_ping_stderr, daemon=True)
                                active_stdout_thread.start()
                                active_stderr_thread.start()
                            except Exception as e2:
                                self.callback(f"Ping测试失败：重新启动进程失败 - {str(e2)}")
                                self.stop_event.set()
                                break
                        else:
                            # 已达到最大重试次数，记录日志并停止
                            self.callback(f"Ping测试失败：已达到最大重试次数({max_retries}次)")
                            self._update_status("网络异常")
                            self.stop_event.set()
                            break
            
            # 等待输出读取线程结束
            active_stdout_thread.join(timeout=3)
            active_stderr_thread.join(timeout=3)
                
        except Exception as e:
            self.callback(f"Ping测试异常：{str(e)}")
            self._update_status("网络异常")
        finally:
            # 通知 ping 已停止
            self.callback("ping_stopped")
            # 清理ping进程
            if self.ping_process:
                try:
                    self.ping_process.terminate()
                    try:
                        self.ping_process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self.ping_process.kill()
                        self.ping_process.wait()
                except Exception:
                    pass
                finally:
                    self.ping_process = None
    
    def _read_ping_stdout(self):
        """读取ping标准输出"""
        try:
            # 使用iter逐行读取，避免select兼容性问题
            for line in iter(self.ping_process.stdout.readline, ''):
                if self.stop_event.is_set():
                    break
                
                line_lower = line.lower().strip()
                
                # 检查成功响应 - 改进检测逻辑
                if any(keyword in line_lower for keyword in ["bytes from", "icmp_seq", "time="]):
                    # ping成功，显示绿色的"网络正常"
                    self._update_status("网络正常")
                elif "ping:" in line_lower and ("unknown host" in line_lower or "name or service not known" in line_lower):
                    # DNS解析失败
                    self._update_status("网络异常")
                elif "ping:" in line_lower and ("network is unreachable" in line_lower or "destination host unreachable" in line_lower):
                    # 网络不可达
                    self._update_status("网络异常")
                elif "ping:" in line_lower and ("timeout" in line_lower or "no answer" in line_lower):
                    # 请求超时
                    self._update_status("网络异常")
                elif "packets transmitted" in line_lower and "packet loss" in line_lower:
                    # ping统计信息
                    if "0% packet loss" in line_lower:
                        self._update_status("网络正常")
                    else:
                        self._update_status("网络异常")
                        
        except Exception as e:
            if not self.stop_event.is_set():  # 只有在未停止时才显示异常
                self._update_status("网络异常")
    
    def _read_ping_stderr(self):
        """读取ping错误输出"""
        try:
            # 使用iter逐行读取，避免select兼容性问题
            for line in iter(self.ping_process.stderr.readline, ''):
                if self.stop_event.is_set():
                    break
                
                line_lower = line.lower().strip()
                
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
                    self._update_status("网络异常")
                        
        except Exception as e:
            if not self.stop_event.is_set():  # 只有在未停止时才显示异常
                self._update_status("网络异常")
    
    def stop(self):
        """停止ping"""
        # 先设置停止事件，让读取线程能够退出
        self.stop_event.set()
        
        # 立即终止ping进程（不等待循环检查stop_event）
        if self.ping_process:
            try:
                # 直接终止进程
                self.ping_process.terminate()
                try:
                    # 等待进程退出，最多等待1秒
                    self.ping_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # 如果进程没有在1秒内退出，强制杀死
                    self.ping_process.kill()
                    self.ping_process.wait()
            except Exception:
                # 如果终止失败，尝试强制杀死
                try:
                    if self.ping_process:
                        self.ping_process.kill()
                        self.ping_process.wait()
                except Exception:
                    pass
            finally:
                self.ping_process = None


class PyQtNetworkInfoManager(QObject):
    """PyQt5 网络信息管理器"""
    
    # 信号定义
    network_info_updated = pyqtSignal(list)  # network_info (列表格式)
    ping_result = pyqtSignal(str)  # ping_result
    ping_stopped = pyqtSignal()  # ping 已停止
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.network_worker = None
        self.ping_worker = None
        self.stop_event = None
        self.is_running = False
        self.wifi_parser = WifiInfoParser()
        
    def start_network_info(self):
        """开始获取网络信息"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if self.is_running:
            self.status_message.emit("网络信息获取已经在运行中")
            return
        
        try:
            # 创建停止事件
            self.stop_event = threading.Event()
            
            # 创建工作线程
            self.network_worker = NetworkInfoWorker(
                device,
                self._on_network_info_updated,
                self.stop_event
            )
            self.network_worker.start()
            
            self.is_running = True
            self.status_message.emit("网络信息获取已启动")
            
        except Exception as e:
            self.status_message.emit(f"启动网络信息获取失败: {str(e)}")
    
    def stop_network_info(self):
        """停止获取网络信息"""
        if not self.is_running:
            try:
                self.status_message.emit("网络信息获取未运行")
            except RuntimeError:
                pass
            return
        
        try:
            # 停止worker
            if self.stop_event:
                self.stop_event.set()
            
            if self.network_worker:
                self.network_worker.join(timeout=5)
            
            self.is_running = False
            try:
                self.status_message.emit("网络信息获取已停止")
            except RuntimeError:
                pass
            
        except Exception as e:
            try:
                self.status_message.emit(f"停止网络信息获取失败: {str(e)}")
            except RuntimeError:
                pass
    
    def start_ping(self):
        """开始Ping测试"""
        # 检查是否已经在运行
        if self.ping_worker and self.ping_worker.is_alive():
            try:
                self.status_message.emit("Ping测试已经在运行中")
            except RuntimeError:
                pass
            return
        
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 创建停止事件
            self.stop_event = threading.Event()
            
            # 创建工作线程
            self.ping_worker = PingWorker(
                device,
                self._on_ping_result,
                self.stop_event
            )
            self.ping_worker.start()
            
            try:
                self.status_message.emit("Ping测试已启动")
            except RuntimeError:
                pass
            
        except Exception as e:
            try:
                self.status_message.emit(f"启动Ping测试失败: {str(e)}")
            except RuntimeError:
                pass
    
    def stop_ping(self):
        """停止Ping测试"""
        try:
            # 先设置停止事件，让循环能够退出
            if self.stop_event:
                self.stop_event.set()
            
            # 停止ping worker（这会终止ping进程）
            if self.ping_worker:
                # 调用worker的stop方法终止ping进程
                self.ping_worker.stop()
                # 等待worker线程结束
                self.ping_worker.join(timeout=3)
                self.ping_worker = None
            
            # 重置停止事件，为下次启动做准备
            self.stop_event = None
            
            try:
                self.status_message.emit("Ping测试已停止")
            except RuntimeError:
                pass
        except Exception as e:
            try:
                self.status_message.emit(f"停止Ping测试失败: {str(e)}")
            except RuntimeError:
                pass
            finally:
                # 确保资源被清理
                self.ping_worker = None
                self.stop_event = None
    
    def _on_network_info_updated(self, network_info):
        """网络信息更新"""
        try:
            self.network_info_updated.emit(network_info)
        except RuntimeError:
            # 对象已被销毁，忽略
            pass
        
    def _on_ping_result(self, result):
        """Ping结果"""
        try:
            self.ping_result.emit(result)
        except RuntimeError:
            # 对象已被销毁，忽略
            pass

