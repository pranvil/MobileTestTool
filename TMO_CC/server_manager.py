#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC服务器管理模块
负责PROD服务器和STG服务器相关功能
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import re
import time

class ServerManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def start_entitlement_activity(self, server_type):
        """启动Entitlement活动"""
        # 检查设备选择
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 使用模态执行器显示进度
        def server_worker(progress_var, status_label, progress_dialog, stop_flag):
            try:
                # 1. 确保屏幕亮屏且解锁
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                status_label.config(text="检查屏幕状态...")
                progress_var.set(20)
                progress_dialog.update()
                
                if not self.app.device_manager.ensure_screen_unlocked(device):
                    raise Exception("无法确保屏幕状态")
                
                # 2. 启动Entitlement活动
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                status_label.config(text=f"启动{server_type}服务器活动...")
                progress_var.set(40)
                progress_dialog.update()
                
                cmd = ["adb", "-s", device, "shell", "am", "start", "com.tct.entitlement/.EditEntitlementEndpointActivity"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    raise Exception(f"启动{server_type}服务器活动失败: {error_msg}")
                
                # 3. 等待界面加载
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                status_label.config(text="等待界面加载...")
                progress_var.set(60)
                progress_dialog.update()
                
                if not self._wait_for_entitlement_loaded(device, timeout=8):
                    raise Exception("等待界面加载超时")
                
                # 4. 设置URL
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                status_label.config(text="设置服务器URL...")
                progress_var.set(80)
                progress_dialog.update()
                
                self._set_entitlement_urls(device, server_type)
                
                # 5. 完成
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                progress_var.set(100)
                return {"success": True, "server_type": server_type, "device": device}
                
            except subprocess.TimeoutExpired:
                raise Exception("启动活动超时，请检查设备连接")
            except FileNotFoundError:
                raise Exception("未找到adb命令，请确保Android SDK已安装并配置PATH")
            except Exception as e:
                raise Exception(str(e))
        
        def on_server_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                self.app.ui.status_var.set(f"{result['server_type']}服务器活动已启动 - {result['device']}")
        
        def on_server_error(error):
            error_str = str(error)
            self.app.ui.status_var.set(f"启动{server_type}服务器活动失败: {error_str}")
            messagebox.showerror("错误", f"启动{server_type}服务器活动失败:\n{error_str}")
        
        # 使用模态执行器
        self.app.ui.run_with_modal(f"启动{server_type}服务器", server_worker, on_server_done, on_server_error)
    
    def prod_server(self):
        """PROD服务器"""
        self.start_entitlement_activity("PROD")
    
    def stg_server(self):
        """STG服务器"""
        self.start_entitlement_activity("STG")
    
    def _adb(self, args, device, timeout=15):
        """执行adb命令的辅助方法"""
        return subprocess.run(["adb", "-s", device] + args,
                              capture_output=True, text=True, timeout=timeout,
                              creationflags=subprocess.CREATE_NO_WINDOW)

    def _dump_ui_and_get(self, device):
        """生成并读取UI dump"""
        r = self._adb(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"], device, 10)
        if r.returncode != 0:
            return None
        r2 = self._adb(["shell", "cat", "/sdcard/ui_dump.xml"], device, 10)
        return r2.stdout if r2.returncode == 0 else None

    def _wait_for_entitlement_loaded(self, device, timeout=8):
        """等待页面出现两个EditText（最多timeout秒）"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            xml = self._dump_ui_and_get(device)
            if not xml:
                time.sleep(0.6)
                continue
            # 粗匹配两个EditText（class=EditText）
            if xml.count('class="android.widget.EditText"') >= 2:
                return True
            time.sleep(0.6)
        return False

    def _bounds_center(self, bounds_str):
        """计算bounds的中心点坐标"""
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", bounds_str))
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _tap(self, device, x, y):
        """点击指定坐标"""
        result = self._adb(["shell", "input", "tap", str(x), str(y)], device, 5)
        return result

    def _long_press(self, device, x, y, dur_ms=800):
        """长按指定坐标"""
        # 长按用"起点=终点"的swipe实现
        result = self._adb(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(dur_ms)], device, 5)
        return result

    def _select_all_then_replace(self, device, replacement_text):
        """长按后自动全选，直接输入文本替换"""
        # 直接输入文本替换（长按后已经自动全选了）
        result = self._adb(["shell", "input", "text", replacement_text], device, 5)
        return result.returncode == 0

    def _replace_edittext_by_bounds(self, device, bounds, replacement_text):
        """对给定EditText的bounds执行长按→自动全选→替换"""
        cx, cy = self._bounds_center(bounds)
        
        # 聚焦
        tap_result = self._tap(device, cx, cy)
        time.sleep(0.15)
        
        # 长按自动全选
        long_press_result = self._long_press(device, cx, cy, 700)
        time.sleep(1.0)  # 增加1秒保护时间，确保全选完成
        
        # 直接输入文本替换（长按后已自动全选）
        ok = self._select_all_then_replace(device, replacement_text)
        return ok

    def _set_entitlement_urls(self, device, server_type):
        """
        设置两个EditText的URL。根据server_type设置不同的URL。
        """
        xml = self._dump_ui_and_get(device)
        if not xml:
            return

        # 抓两个EditText的bounds
        edit_bounds = re.findall(r'class="android\.widget\.EditText"[^>]*bounds="(\[[^"]+\])"', xml)
        
        if len(edit_bounds) < 2:
            return

        # 根据服务器类型设置URL
        if server_type == "PROD":
            url = "https://eas3.msg.t-mobile.com/generic_devices"
        elif server_type == "STG":
            url = "https://easstg1.msg.t-mobile.com/generic_devices"
        else:
            return

        # 依次设置两个EditText
        for i, b in enumerate(edit_bounds[:2], start=1):
            self._replace_edittext_by_bounds(device, b, url)
            time.sleep(0.5)  # 增加等待时间，确保操作完成

        # 设置完成后点击OK按钮
        self._click_ok_button(device)

    def _click_ok_button(self, device):
        """点击OK按钮"""
        try:
            # 获取UI dump
            xml = self._dump_ui_and_get(device)
            if not xml:
                return False
            
            # 查找OK按钮（可能是"OK"、"确定"、"Done"等）
            ok_patterns = [
                r'text="OK".*?bounds="(\[[^"]+\])"',
                r'text="确定".*?bounds="(\[[^"]+\])"',
                r'text="Done".*?bounds="(\[[^"]+\])"',
                r'text="完成".*?bounds="(\[[^"]+\])"',
                r'content-desc="OK".*?bounds="(\[[^"]+\])"',
                r'content-desc="确定".*?bounds="(\[[^"]+\])"',
                r'content-desc="Done".*?bounds="(\[[^"]+\])"'
            ]
            
            ok_bounds = None
            for pattern in ok_patterns:
                match = re.search(pattern, xml)
                if match:
                    ok_bounds = match.group(1)
                    break
            
            if ok_bounds:
                cx, cy = self._bounds_center(ok_bounds)
                self._tap(device, cx, cy)
                return True
            else:
                return False
                
        except Exception as e:
            return False
