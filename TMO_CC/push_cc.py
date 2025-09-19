#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC文件推送模块
负责向设备推送CC文件
"""

import subprocess
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

class PushCCManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def push_cc_file(self):
        """推CC文件"""
        # 检查设备选择
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 1) 先做本地同步权限检查（只检查root权限）
        try:
            print(f"[DEBUG] 开始检查设备root权限，设备: {device}")
            
            # 检查adb root
            cmd = ["adb", "-s", device, "root"]
            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            output = result.stdout + result.stderr
            print(f"[DEBUG] adb root命令输出: {output}")
            
            if "adbd cannot run as root in production builds" in output:
                messagebox.showerror("错误", "设备没有root权限，操作无法执行")
                self.app.ui.status_var.set("设备没有root权限")
                return
            
            # root权限检查通过，继续文件选择
            print(f"[DEBUG] Root权限检查成功")
            self._select_and_push_files(device)
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 权限检查超时")
            messagebox.showerror("错误", "权限检查超时")
            self.app.ui.status_var.set("权限检查超时")
        except FileNotFoundError:
            print(f"[DEBUG] 未找到adb命令")
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.app.ui.status_var.set("未找到adb命令")
        except Exception as e:
            print(f"[DEBUG] 权限检查异常: {str(e)}")
            messagebox.showerror("错误", f"权限检查失败:\n{str(e)}")
            self.app.ui.status_var.set(f"权限检查失败: {str(e)}")
    
    def _select_and_push_files(self, device):
        """选择文件并推送"""
        # 显示文件选择对话框
        file_paths = filedialog.askopenfilenames(
            title="选择要推送的CC文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("文本文件", "*.txt"),
                ("配置文件", "*.conf"),
                ("设备信息文件", "deviceInfo*")
            ],
            parent=self.app.root
        )
        
        if not file_paths:
            print(f"[DEBUG] 用户取消文件选择")
            self.app.ui.status_var.set("用户取消文件选择")
            return
        
        print(f"[DEBUG] 用户选择了 {len(file_paths)} 个文件: {file_paths}")
        
        # 直接执行推送操作，不使用模态执行器
        try:
            print(f"[DEBUG] 开始推送文件到设备: {device}")
            
            total_files = len(file_paths)
            success_count = 0
            failed_files = []
            
            for i, file_path in enumerate(file_paths):
                file_name = os.path.basename(file_path)
                print(f"[DEBUG] 推送文件 {i+1}/{total_files}: {file_name}")
                
                # 执行adb push命令
                push_cmd = ["adb", "-s", device, "push", file_path, f"/data/deviceInfo/{file_name}"]
                result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=60, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                print(f"[DEBUG] push命令返回码: {result.returncode}")
                print(f"[DEBUG] push命令输出: {result.stdout}")
                print(f"[DEBUG] push命令错误: {result.stderr}")
                
                if result.returncode == 0:
                    success_count += 1
                    print(f"[DEBUG] 文件推送成功: {file_name}")
                else:
                    failed_files.append(f"{file_name}: {result.stderr.strip()}")
                    print(f"[DEBUG] 文件推送失败: {file_name} - {result.stderr.strip()}")
            
            print(f"[DEBUG] 推送操作完成: 成功 {success_count}/{total_files}")
            
            # 处理推送结果
            if success_count == total_files:
                # 全部成功
                self.app.ui.status_var.set(f"CC文件推送完成 - {device} - 成功推送 {success_count} 个文件")
                
                # 推送成功后启动Entitlement界面
                self._start_entitlement_activity(device)
                
            elif success_count > 0:
                # 部分成功
                self.app.ui.status_var.set(f"CC文件部分推送完成 - {device} - 成功 {success_count}/{total_files}")
                
                # 部分成功也启动Entitlement界面
                self._start_entitlement_activity(device)
                
            else:
                # 全部失败
                failed_info = "\n".join(failed_files)
                self.app.ui.status_var.set(f"CC文件推送失败 - {device}")
                messagebox.showerror("推送失败", 
                    f"所有文件推送失败!\n\n"
                    f"设备: {device}\n"
                    f"失败文件:\n{failed_info}")
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 推送操作超时")
            self.app.ui.status_var.set("CC文件推送超时")
            messagebox.showerror("错误", "推送操作超时，请检查设备连接")
        except FileNotFoundError:
            print(f"[DEBUG] 未找到adb命令")
            self.app.ui.status_var.set("未找到adb命令")
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            error_str = str(e)
            print(f"[DEBUG] 推送异常: {error_str}")
            self.app.ui.status_var.set(f"CC文件推送失败: {error_str}")
            messagebox.showerror("错误", f"CC文件推送失败:\n{error_str}")
    
    def _start_entitlement_activity(self, device):
        """启动Entitlement活动并点击NO CARD按钮"""
        try:
            print(f"[DEBUG] 推送成功后启动Entitlement活动，设备: {device}")
            
            # 确保屏幕亮屏且解锁
            if not self.app.device_manager.ensure_screen_unlocked(device):
                return
            
            # 执行adb命令启动活动
            cmd = ["adb", "-s", device, "shell", "am", "start", "com.tct.entitlement/.EditEntitlementEndpointActivity"]
            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            print(f"[DEBUG] 命令返回码: {result.returncode}")
            print(f"[DEBUG] 命令输出: {result.stdout}")
            print(f"[DEBUG] 命令错误: {result.stderr}")
            
            if result.returncode == 0:
                print(f"[DEBUG] Entitlement活动启动成功")
                
                # 等待界面加载，然后点击NO CARD按钮
                import time
                time.sleep(3)  # 等待3秒让界面完全加载
                
                # 使用uiautomator点击NO CARD按钮
                self._click_no_card_button_with_uiautomator(device)
                
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                print(f"[DEBUG] Entitlement活动启动失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 启动Entitlement活动超时")
        except FileNotFoundError:
            print(f"[DEBUG] 未找到adb命令")
        except Exception as e:
            print(f"[DEBUG] 启动Entitlement活动异常: {str(e)}")
    
    def _click_no_card_button_with_uiautomator(self, device):
        """使用uiautomator点击NO CARD按钮"""
        try:
            print(f"[DEBUG] 开始使用uiautomator点击NO CARD按钮，设备: {device}")
            
            # 使用uiautomator命令查找并点击NO CARD按钮
            # 通过文本内容查找按钮
            cmd = ["adb", "-s", device, "shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"]
            print(f"[DEBUG] 执行uiautomator dump命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print(f"[DEBUG] UI dump成功")
                
                # 获取UI dump内容
                cmd_get_dump = ["adb", "-s", device, "shell", "cat", "/sdcard/ui_dump.xml"]
                dump_result = subprocess.run(cmd_get_dump, capture_output=True, text=True, timeout=10, 
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                
                if dump_result.returncode == 0:
                    ui_content = dump_result.stdout
                    print(f"[DEBUG] 获取到UI内容，长度: {len(ui_content)}")
                    
                    # 查找NO CARD按钮的坐标
                    import re
                    # 查找包含"NO CARD"文本的节点
                    pattern = r'text="NO CARD"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                    match = re.search(pattern, ui_content)
                    
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        print(f"[DEBUG] 找到NO CARD按钮，坐标: ({center_x}, {center_y})")
                        
                        # 点击按钮
                        click_cmd = ["adb", "-s", device, "shell", "input", "tap", str(center_x), str(center_y)]
                        print(f"[DEBUG] 执行点击命令: {' '.join(click_cmd)}")
                        
                        click_result = subprocess.run(click_cmd, capture_output=True, text=True, timeout=10, 
                                                     creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        if click_result.returncode == 0:
                            print(f"[DEBUG] NO CARD按钮点击成功")
                        else:
                            print(f"[DEBUG] NO CARD按钮点击失败: {click_result.stderr}")
                            messagebox.showerror("点击失败", 
                                f"NO CARD按钮点击失败!\n\n"
                                f"设备: {device}\n"
                                f"坐标: ({center_x}, {center_y})\n"
                                f"错误: {click_result.stderr.strip() if click_result.stderr else '未知错误'}\n\n"
                                f"请手动点击NO CARD按钮")
                    else:
                        print(f"[DEBUG] 未找到NO CARD按钮")
                        # 尝试其他可能的文本
                        alt_patterns = [
                            r'text="No Card"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                            r'text="no card"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                            r'text="NO CARD"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                        ]
                        
                        found_button = False
                        for alt_pattern in alt_patterns:
                            match = re.search(alt_pattern, ui_content)
                            if match:
                                x1, y1, x2, y2 = map(int, match.groups())
                                center_x = (x1 + x2) // 2
                                center_y = (y1 + y2) // 2
                                
                                print(f"[DEBUG] 找到NO CARD按钮(备用模式)，坐标: ({center_x}, {center_y})")
                                
                                click_cmd = ["adb", "-s", device, "shell", "input", "tap", str(center_x), str(center_y)]
                                click_result = subprocess.run(click_cmd, capture_output=True, text=True, timeout=10, 
                                                             creationflags=subprocess.CREATE_NO_WINDOW)
                                
                                if click_result.returncode == 0:
                                    print(f"[DEBUG] NO CARD按钮点击成功(备用模式)")
                                    found_button = True
                                    break
                                else:
                                    print(f"[DEBUG] NO CARD按钮点击失败(备用模式): {click_result.stderr}")
                                    messagebox.showerror("点击失败", 
                                        f"NO CARD按钮点击失败!\n\n"
                                        f"设备: {device}\n"
                                        f"坐标: ({center_x}, {center_y})\n"
                                        f"错误: {click_result.stderr.strip() if click_result.stderr else '未知错误'}\n\n"
                                        f"请手动点击NO CARD按钮")
                                    found_button = True
                                    break
                        
                        if not found_button:
                            print(f"[DEBUG] 完全未找到NO CARD按钮")
                            messagebox.showerror("未找到按钮", 
                                f"未找到NO CARD按钮!\n\n"
                                f"设备: {device}\n"
                                f"界面可能未完全加载或按钮文本不匹配\n\n"
                                f"请手动点击NO CARD按钮")
                else:
                    print(f"[DEBUG] 获取UI dump内容失败: {dump_result.stderr}")
                    messagebox.showerror("获取界面信息失败", 
                        f"无法获取设备界面信息!\n\n"
                        f"设备: {device}\n"
                        f"错误: {dump_result.stderr.strip() if dump_result.stderr else '未知错误'}\n\n"
                        f"请手动点击NO CARD按钮")
            else:
                print(f"[DEBUG] UI dump失败: {result.stderr}")
                messagebox.showerror("界面分析失败", 
                    f"无法分析设备界面!\n\n"
                    f"设备: {device}\n"
                    f"错误: {result.stderr.strip() if result.stderr else '未知错误'}\n\n"
                    f"请手动点击NO CARD按钮")
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 点击NO CARD按钮超时")
            messagebox.showerror("操作超时", 
                f"点击NO CARD按钮超时!\n\n"
                f"设备: {device}\n"
                f"请检查设备连接状态\n\n"
                f"请手动点击NO CARD按钮")
        except FileNotFoundError:
            print(f"[DEBUG] 未找到adb命令")
            messagebox.showerror("命令未找到", 
                f"未找到adb命令!\n\n"
                f"请确保Android SDK已安装并配置PATH\n\n"
                f"请手动点击NO CARD按钮")
        except Exception as e:
            print(f"[DEBUG] 点击NO CARD按钮异常: {str(e)}")
            messagebox.showerror("操作异常", 
                f"点击NO CARD按钮时发生异常!\n\n"
                f"设备: {device}\n"
                f"错误: {str(e)}\n\n"
                f"请手动点击NO CARD按钮")
