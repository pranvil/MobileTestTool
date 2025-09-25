#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备信息管理器
负责获取设备的IMEI、ICCID、IMSI、MSISDN等信息
"""

import subprocess
import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Tuple, Dict, Any
import threading

class DeviceInfoManager:
    def __init__(self, app_instance):
        """
        初始化设备信息管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager

    def run_adb_command(self, cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
        """执行ADB命令"""
        try:
            result = subprocess.run(
                cmd.split(), 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令执行超时"
        except Exception as e:
            return -1, "", str(e)

    def adb_shell(self, serial: Optional[str], shell_cmd: str) -> Tuple[int, str, str]:
        """执行adb shell命令"""
        base = ["adb"]
        if serial:
            base += ["-s", serial]
        base += ["shell"] + shell_cmd.split()
        cmd = " ".join(base)
        return self.run_adb_command(cmd)

    def getprop(self, serial: Optional[str], prop: str) -> str:
        """获取系统属性"""
        rc, out, _ = self.adb_shell(serial, f"getprop {prop}")
        return out.strip() if rc == 0 else ""

    def parse_parcel_utf16_digits(self, output: str) -> str:
        """
        解析 adb service call 的 Parcel(UTF-16) 十六进制转储。
        关键点：每个 32bit 字小端，需要按 [低16, 高16] 顺序取半字。
        只收集 '0'..'9' (0x0030..0x0039)，并识别可选 '+' (0x002b) 前缀。
        """
        # 报错"not fully consumed"直接判失败
        if "not fully" in output.lower() and "consum" in output.lower():
            return ""
        words = [m.group(1).lower() for m in re.finditer(r'(?:0x)?([0-9A-Fa-f]{8})', output)]
        digits, has_plus = [], False
        for w in words:
            hi, lo = w[:4], w[4:]
            for half in (lo, hi):  # 小端半字顺序
                if half == "002b":
                    has_plus = True
                if half.startswith("003") and half[-1] in "0123456789":
                    digits.append(chr(int(half[-2:], 16)))
        s = "".join(digits)
        return ("+" + s) if (has_plus and s) else s

    def parse_service_call_digits(self, output: str) -> str:
        """解析service call输出中的数字"""
        # 报错"not fully consumed"直接判失败
        if "not fully" in output.lower() and "consum" in output.lower():
            return ""
        # 先尝试 '...'
        parts = re.findall(r"'(.*?)'", output)
        if parts:
            s = "".join("".join(re.findall(r"[0-9+]", p)) for p in parts)
            if s:
                return s
        # 再尝试 Parcel UTF-16
        return self.parse_parcel_utf16_digits(output)


    def service_call_with_priority(self, serial: str, code: int, sub_id: int) -> str:
        """
        按优先级尝试service call命令
        优先级：
        1. service call iphonesubinfo <code> i32 <subid> s16 com.android.shell
        2. service call iphonesubinfo <code> i32 <subid>
        3. service call iphonesubinfo <code> s16 com.android.shell
        4. service call iphonesubinfo <code>
        """
        commands = [
            f"service call iphonesubinfo {code} i32 {sub_id} s16 com.android.shell",
            f"service call iphonesubinfo {code} i32 {sub_id}",
            f"service call iphonesubinfo {code} s16 com.android.shell",
            f"service call iphonesubinfo {code}"
        ]
        
        for cmd in commands:
            rc, out, err = self.adb_shell(serial, cmd)
            
            # 检查错误标记
            error_markers = ["Parcel data not fully consumed", "fffffff", "Transaction failed", "SecurityException"]
            has_error = any(marker in out.lower() or marker in err.lower() for marker in error_markers)
            if has_error:
                continue
            
            if rc == 0 and out and not err:
                result = self.parse_service_call_digits(out)
                if result:
                    return result
        
        return ""

    def discover_subscriptions(self, serial: str) -> List[Dict[str, Any]]:
        """发现活跃的订阅信息"""
        # 使用 dumpsys telephony.registry 作为主要方法
        rc, out, _ = self.adb_shell(serial, "dumpsys telephony.registry")
        if rc == 0 and out:
            pairs: List[Tuple[int, int]] = []
            for line in out.splitlines():
                m = re.search(r'\bsubId=(\d+)\b.*?\bphoneId=(\d+)\b', line, re.IGNORECASE)
                if not m:
                    m = re.search(r'\bphoneId=(\d+)\b.*?\bsubId=(\d+)\b', line, re.IGNORECASE)
                    if m:
                        pairs.append((int(m.group(2)), int(m.group(1))))  # (subId, phoneId)
                else:
                    pairs.append((int(m.group(1)), int(m.group(2))))  # (subId, phoneId)
            
            # 过滤掉无效的subId（占位值）
            valid_pairs = []
            invalid_subids = [2147483646, 2147483647, -1]  # 占位值
            for sub_id, phone_id in pairs:
                if sub_id not in invalid_subids and sub_id > 0:
                    valid_pairs.append((sub_id, phone_id))
            
            # 按phoneId去重，保留第一次出现
            by_phone_id: Dict[int, Dict[str, Any]] = {}
            for sub_id, phone_id in valid_pairs:
                if phone_id not in by_phone_id:
                    by_phone_id[phone_id] = {"subId": sub_id, "slotIndex": phone_id, "carrier": None}
            
            # 按phoneId排序，限制最多2个
            subs = list(by_phone_id.values())
            subs.sort(key=lambda x: x["slotIndex"])
            return subs[:2]
        
        # 如果telephony.registry失败，尝试其他方法
        return self._fallback_subscription_discovery(serial)
    
    def _fallback_subscription_discovery(self, serial: str) -> List[Dict[str, Any]]:
        """备用订阅发现方法"""
        # Android 12+ 方法
        rc, out, _ = self.adb_shell(serial, "cmd phone subscription-info list -f")
        if rc == 0 and out:
            subs = []
            blocks = re.split(r'\n\s*\n', out.strip())
            for blk in blocks:
                sid = re.search(r'\bsubId\s*=\s*(\d+)', blk)
                if not sid:
                    continue
                slot = None
                for pat in (r'\bslotIndex\s*=\s*(-?\d+)', r'\bsimSlotIndex\s*=\s*(-?\d+)', r'\bmSlotIndex\s*=\s*(-?\d+)'):
                    m = re.search(pat, blk)
                    if m:
                        try:
                            slot = int(m.group(1))
                        except:
                            slot = None
                        break
                carrier = re.search(r'\bcarrierName\s*=\s*([^\n]+)', blk)
                subs.append({"subId": int(sid.group(1)), "slotIndex": slot, "carrier": carrier.group(1).strip() if carrier else None})
            
            if subs:
                uniq = {s["subId"]: s for s in subs}
                return list(uniq.values())[:2]
        
        # 旧接口方法
        rc2, out2, _ = self.adb_shell(serial, "cmd phone list-subs")
        if rc2 == 0 and out2:
            subs = []
            for line in out2.splitlines():
                m1 = re.search(r'\bsubId=(\d+)', line)
                m2 = re.search(r'\bslot(Id|)=(\d+)', line, re.IGNORECASE)
                if m1:
                    subs.append({"subId": int(m1.group(1)), "slotIndex": int(m2.group(2)) if m2 else None, "carrier": None})
            
            if subs:
                uniq = {s["subId"]: s for s in subs}
                return list(uniq.values())[:2]
        
        # 尝试 dumpsys isub 作为兜底
        rc3, out3, _ = self.adb_shell(serial, "dumpsys isub")
        if rc3 == 0 and out3:
            subs = []
            for line in out3.splitlines():
                if "Logical SIM slot" in line and "subId=" in line:
                    slot_match = re.search(r'Logical SIM slot (\d+): subId=(\d+)', line)
                    if slot_match:
                        slot_idx = int(slot_match.group(1))
                        sub_id = int(slot_match.group(2))
                        subs.append({"subId": sub_id, "slotIndex": slot_idx, "carrier": None})
            
            if subs:
                subs.sort(key=lambda x: x["slotIndex"])
                return subs[:2]
        
        # 如果都失败，返回单卡兜底
        return [{"subId": 1, "slotIndex": 0, "carrier": None}]

    
    def collect_field_for_slots(self, serial: str, field_name: str, subscriptions: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        为指定字段收集所有卡槽的数据，并处理重复值
        """
        # 字段对应的code列表
        field_codes = {
            "IMEI": [1, 2],
            "MSISDN": [17, 16, 20],
            "IMSI": [10, 9, 8],
            "ICCID": [15, 14, 13, 12]
        }
        
        if field_name not in field_codes:
            return {}
        
        codes = field_codes[field_name]
        slot_values = {}  # {slot_idx: value}
        
        # 先查询slot 0
        slot0_sub = next((sub for sub in subscriptions if sub["slotIndex"] == 0), None)
        slot0_value = ""
        if slot0_sub:
            for code in codes:
                slot0_value = self.service_call_with_priority(serial, code, slot0_sub["subId"])
                if slot0_value:
                    break
            slot_values[0] = slot0_value
        
        # 再查询slot 1
        slot1_sub = next((sub for sub in subscriptions if sub["slotIndex"] == 1), None)
        if slot1_sub:
            slot1_value = ""
            for code in codes:
                slot1_value = self.service_call_with_priority(serial, code, slot1_sub["subId"])
                if slot1_value:
                    # 如果slot 0没有值，或者slot 1的值与slot 0不同，则保留
                    if not slot0_value or slot1_value != slot0_value:
                        break
                    # 如果slot 1的值与slot 0相同，继续尝试下一个code
                    slot1_value = ""  # 重置，继续尝试下一个code
            
            # 最终决定slot 1的值
            if slot1_value and slot1_value != slot0_value:
                slot_values[1] = slot1_value
            elif slot1_value and slot1_value == slot0_value:
                slot_values[1] = ""  # 清空相同值
            else:
                slot_values[1] = ""  # 没有获取到值
        
        return slot_values

    def collect_device_info(self, serial: str) -> Dict[str, Any]:
        """
        收集设备信息 - 按字段一次性查询所有卡槽
        """
        # Step 1: 校验设备状态
        rc, _, err = self.run_adb_command(f"adb -s {serial} get-state")
        if rc != 0:
            raise Exception(f"设备状态检查失败: {err}")
        
        # Step 2: 发现订阅
        subscriptions = self.discover_subscriptions(serial)
        
        result = {
            "serial": serial,
            "device_model": self.getprop(serial, "ro.product.model"),
            "device_brand": self.getprop(serial, "ro.product.brand"),
            "android_version": self.getprop(serial, "ro.build.version.release"),
            "api_level": self.getprop(serial, "ro.build.version.sdk"),
            "subscriptions": [],
            "flat": {}
        }
        
        # Step 3: 一次性查询所有字段的所有卡槽
        # 收集各字段的卡槽数据
        imei_data = self.collect_field_for_slots(serial, "IMEI", subscriptions)
        msisdn_data = self.collect_field_for_slots(serial, "MSISDN", subscriptions)
        imsi_data = self.collect_field_for_slots(serial, "IMSI", subscriptions)
        iccid_data = self.collect_field_for_slots(serial, "ICCID", subscriptions)
        
        # Step 4: 组装订阅数据
        for sub in subscriptions:
            slot_idx = sub["slotIndex"]
            subscription_data = {
                "subId": sub["subId"],
                "slotIndex": slot_idx,
                "carrier": sub.get("carrier"),
                "imei": imei_data.get(slot_idx, ""),
                "msisdn": msisdn_data.get(slot_idx, ""),
                "imsi": imsi_data.get(slot_idx, ""),
                "iccid": iccid_data.get(slot_idx, "")
            }
            result["subscriptions"].append(subscription_data)
        
        # Step 5: 生成扁平化映射
        subs_sorted = sorted(result["subscriptions"], key=lambda r: (999 if r["slotIndex"] is None else r["slotIndex"]))
        for i, rec in enumerate(subs_sorted[:2], start=1):
            result["flat"][f"IMEI{i}"] = rec.get("imei", "")
            result["flat"][f"ICCID{i}"] = rec.get("iccid", "")
            result["flat"][f"IMSI{i}"] = rec.get("imsi", "")
            result["flat"][f"MSISDN{i}"] = rec.get("msisdn", "")
        
        # 确保所有字段都存在
        for i in (1, 2):
            result["flat"].setdefault(f"IMEI{i}", "")
            result["flat"].setdefault(f"ICCID{i}", "")
            result["flat"].setdefault(f"IMSI{i}", "")
            result["flat"].setdefault(f"MSISDN{i}", "")
        
        print("设备信息收集完成")
        return result

    def show_device_info_dialog(self):
        """显示设备信息对话框"""
        # 验证设备选择
        device = self.device_manager.validate_device_selection()
        if not device:
            return

        # 创建对话框
        dialog = tk.Toplevel(self.app.root)
        dialog.title("手机信息")
        dialog.geometry("400x600")
        dialog.resizable(True, True)
        dialog.transient(self.app.root)
        
        # 设置窗口属性，确保可以重新激活
        dialog.grab_set()  # 设置为模态
        
        # 绑定对话框的焦点事件
        dialog.bind("<FocusOut>", lambda e: self._on_dialog_focus_out(dialog))
        dialog.bind("<Map>", lambda e: self._on_dialog_map(dialog))
        dialog.bind("<Unmap>", lambda e: self._on_dialog_unmap(dialog))
        
        # 窗口关闭时的处理
        def on_closing():
            dialog.grab_release()  # 释放模态
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_closing)

        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 800) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 600) // 2
        ))

        # 主框架
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="正在获取设备信息...", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(main_frame, variable=progress_var, maximum=100, length=400)
        progress_bar.pack(pady=(0, 10))

        # 状态标签
        status_label = ttk.Label(main_frame, text="准备中...", font=('Arial', 10))
        status_label.pack(pady=(0, 10))

        # 信息显示框架
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)

        # 关闭按钮
        close_button = ttk.Button(main_frame, text="关闭", command=on_closing)
        close_button.pack(pady=(10, 0))

        # 在后台线程中获取设备信息
        def get_info_worker():
            try:
                # 更新状态
                dialog.after(0, lambda: status_label.config(text="正在获取设备基本信息..."))
                dialog.after(0, lambda: progress_var.set(20))
                
                # 获取设备信息
                device_info = self.collect_device_info(device)
                
                dialog.after(0, lambda: status_label.config(text="正在格式化显示..."))
                dialog.after(0, lambda: progress_var.set(80))
                
                # 更新UI显示
                dialog.after(0, lambda: self._update_info_display(info_frame, device_info))
                dialog.after(0, lambda: title_label.config(text=f"设备信息 - {device_info['device_model']}"))
                dialog.after(0, lambda: progress_var.set(100))
                dialog.after(0, lambda: status_label.config(text="获取完成"))
                
            except Exception as e:
                dialog.after(0, lambda: status_label.config(text=f"获取失败: {str(e)}"))
                dialog.after(0, lambda: messagebox.showerror("错误", f"获取设备信息失败:\n{str(e)}"))

        # 启动后台线程
        thread = threading.Thread(target=get_info_worker, daemon=True)
        thread.start()

    def _update_info_display(self, parent_frame, device_info):
        """更新信息显示"""
        # 清空原有内容
        for widget in parent_frame.winfo_children():
            widget.destroy()

        # 创建滚动容器
        canvas = tk.Canvas(parent_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 设备基本信息
        basic_frame = ttk.LabelFrame(scrollable_frame, text="设备基本信息", padding="10")
        basic_frame.pack(fill="x", padx=5, pady=5)

        basic_info = [
            ("设备型号", device_info.get("device_model", "未知")),
            ("设备品牌", device_info.get("device_brand", "未知")),
            ("Android版本", device_info.get("android_version", "未知")),
            ("API级别", device_info.get("api_level", "未知")),
            ("设备序列号", device_info.get("serial", "未知")),
        ]

        for i, (label, value) in enumerate(basic_info):
            ttk.Label(basic_frame, text=f"{label}:", font=('Arial', 10, 'bold')).grid(row=i, column=0, sticky="w", padx=(0, 10))
            ttk.Label(basic_frame, text=str(value), font=('Arial', 10)).grid(row=i, column=1, sticky="w")

        # 详细订阅信息（按图片格式）
        subscriptions = device_info.get("subscriptions", [])
        if subscriptions and len(subscriptions) > 0:
            detail_frame = ttk.LabelFrame(scrollable_frame, text="详细订阅信息", padding="10")
            detail_frame.pack(fill="x", padx=5, pady=5)

            for i, sub in enumerate(subscriptions):
                slot_name = f"订阅 {sub.get('subId', 'N/A')} (卡槽 {sub.get('slotIndex', i)})"
                
                sub_frame = ttk.Frame(detail_frame)
                sub_frame.pack(fill="x", padx=5, pady=2)

                ttk.Label(sub_frame, text=f"{slot_name}:", font=('Arial', 10, 'bold')).pack(anchor="w")
                
                sub_info = [
                    ("IMEI", sub.get("imei", "")),
                    ("MSISDN", sub.get("msisdn", "")),
                    ("IMSI", sub.get("imsi", "")),
                    ("ICCID", sub.get("iccid", "")),
                ]

                for j, (label, value) in enumerate(sub_info):
                    info_frame = ttk.Frame(sub_frame)
                    info_frame.pack(fill="x", padx=(20, 0), pady=1)
                    ttk.Label(info_frame, text=f"  {label}:", font=('Arial', 9, 'bold')).pack(side="left")
                    # 使用Text widget来支持复制
                    text_widget = tk.Text(info_frame, height=1, width=30, wrap=tk.NONE, font=('Arial', 9))
                    text_widget.insert(tk.END, str(value))
                    text_widget.config(state=tk.DISABLED)
                    text_widget.pack(side="left", padx=(5, 0))

        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind("<MouseWheel>", on_mousewheel)
    
    def _on_dialog_focus_out(self, dialog):
        """对话框失去焦点时的处理"""
        try:
            # 检查对话框是否仍然存在
            if dialog.winfo_exists():
                # 延迟检查，如果对话框仍然可见，尝试重新获得焦点
                dialog.after(100, lambda: self._check_dialog_focus(dialog))
        except Exception as e:
            print(f"对话框焦点处理失败: {e}")
    
    def _on_dialog_map(self, dialog):
        """对话框显示时的处理"""
        try:
            # 确保对话框获得焦点
            dialog.focus_force()
        except Exception as e:
            print(f"对话框显示处理失败: {e}")
    
    def _check_dialog_focus(self, dialog):
        """检查对话框焦点状态"""
        try:
            if dialog.winfo_exists() and dialog.winfo_viewable():
                # 如果对话框可见但没有焦点，尝试重新获得焦点
                if not dialog.focus_get():
                    dialog.focus_force()
        except Exception as e:
            print(f"检查对话框焦点失败: {e}")
    
    def _on_dialog_unmap(self, dialog):
        """对话框隐藏时的处理"""
        try:
            # 释放模态锁定
            dialog.grab_release()
            # 恢复主窗口焦点
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'restore_focus_after_dialog'):
                self.app.ui.restore_focus_after_dialog()
        except Exception as e:
            print(f"对话框隐藏处理失败: {e}")
