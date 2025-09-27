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
        """显示设备信息到主界面日志窗口"""
        # 验证设备选择
        device = self.device_manager.validate_device_selection()
        if not device:
            return

        # 在后台线程中获取设备信息
        def get_info_worker():
            try:
                # 记录开始获取信息
                self._log_message("[设备信息] 开始获取设备信息...")
                
                # 获取设备信息
                device_info = self.collect_device_info(device)
                
                # 显示设备信息到主界面日志窗口
                self.app.root.after(0, lambda: self._display_device_info(device_info))
                
            except Exception as e:
                error_msg = f"获取设备信息失败: {str(e)}"
                self.app.root.after(0, lambda: self._log_message(f"[设备信息] 错误: {error_msg}"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))

        # 启动后台线程
        thread = threading.Thread(target=get_info_worker, daemon=True)
        thread.start()
    
    def _log_message(self, message):
        """记录日志消息到主界面日志窗口"""
        try:
            # 确保在主线程中更新UI
            self.app.root.after(0, lambda: self._update_log_display(message))
        except Exception as e:
            print(f"记录日志消息失败: {e}")
    
    def _update_log_display(self, message):
        """更新日志显示"""
        try:
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'log_text'):
                # 确保控件可编辑
                self.app.ui.log_text.config(state=tk.NORMAL)
                self.app.ui.log_text.insert(tk.END, f"{message}\n")
                self.app.ui.log_text.see(tk.END)
                # 保持原有状态（如果正在过滤则保持DISABLED）
                if hasattr(self.app, 'is_running') and self.app.is_running:
                    self.app.ui.log_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"更新日志显示失败: {e}")
    
    def _display_device_info(self, device_info):
        """显示设备信息到主界面日志窗口"""
        try:
            # 清空日志窗口
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'log_text'):
                self.app.ui.log_text.delete(1.0, tk.END)
            
            # 显示设备基本信息
            self._log_message("=" * 60)
            self._log_message("设备信息")
            self._log_message("=" * 60)
            
            # 设备基本信息
            self._log_message("设备基本信息:")
            self._log_message(f"  设备型号: {device_info.get('device_model', '未知')}")
            self._log_message(f"  设备品牌: {device_info.get('device_brand', '未知')}")
            self._log_message(f"  Android版本: {device_info.get('android_version', '未知')}")
            self._log_message(f"  API级别: {device_info.get('api_level', '未知')}")
            self._log_message(f"  设备序列号: {device_info.get('serial', '未知')}")
            self._log_message("")
            
            # 详细订阅信息
            subscriptions = device_info.get("subscriptions", [])
            if subscriptions and len(subscriptions) > 0:
                self._log_message("详细信息:")
                for i, sub in enumerate(subscriptions):
                    # slot_name = f"订阅 {sub.get('subId', 'N/A')} (卡槽 {sub.get('slotIndex', i)})"
                    slot_name = f"卡槽 {sub.get('slotIndex', i)}"
                    self._log_message(f"  {slot_name}:")
                    self._log_message(f"    IMEI: {sub.get('imei', '')}")
                    self._log_message(f"    MSISDN: {sub.get('msisdn', '')}")
                    self._log_message(f"    IMSI: {sub.get('imsi', '')}")
                    self._log_message(f"    ICCID: {sub.get('iccid', '')}")
                    self._log_message("")
            
            self._log_message("=" * 60)
            self._log_message("[设备信息] 设备信息获取完成!")
            
        except Exception as e:
            self._log_message(f"[设备信息] 显示设备信息失败: {str(e)}")

