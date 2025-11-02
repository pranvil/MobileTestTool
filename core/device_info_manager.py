#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备信息管理器 - PyQt5版本
负责获取设备的IMEI、ICCID、IMSI、MSISDN等信息
完整迁移自Device_Settings/device_info_manager.py
"""

import subprocess
import re
from typing import Optional, List, Tuple, Dict, Any


class DeviceInfoManager:
    """设备信息管理器 - PyQt5版本"""
    
    def __init__(self):
        """初始化设备信息管理器"""
        pass
    
    def run_adb_command(self, cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
        """执行ADB命令"""
        try:
            result = subprocess.run(
                cmd.split(), 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
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
        只收集 '0'..'9self.lang_manager.tr(' (0x0030..0x0039)，并识别可选 ')+' (0x002b) 前缀。
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
            valid_pairs = [(s, p) for s, p in pairs if s > 0 and s < 1000]
            
            # 去重并按phoneId排序
            seen = set()
            unique_pairs = []
            for s, p in valid_pairs:
                if (s, p) not in seen:
                    seen.add((s, p))
                    unique_pairs.append((s, p))
            
            unique_pairs.sort(key=lambda x: x[1])
            
            # 转换为订阅列表
            subs = [{"subId": s, "slotIndex": p, "carrier": None} for s, p in unique_pairs[:2]]
            
            if subs:
                return subs
        
        # 尝试 dumpsys telephony.registry 的备用方法
        rc2, out2, _ = self.adb_shell(serial, "dumpsys telephony.registry")
        if rc2 == 0 and out2:
            subs = []
            for line in out2.splitlines():
                if "mSubId=" in line and "mPhoneId=" in line:
                    sub_match = re.search(r'mSubId=(\d+)', line)
                    phone_match = re.search(r'mPhoneId=(\d+)', line)
                    if sub_match and phone_match:
                        sub_id = int(sub_match.group(1))
                        phone_id = int(phone_match.group(1))
                        if 0 < sub_id < 1000:
                            subs.append({"subId": sub_id, "slotIndex": phone_id, "carrier": None})
            
            if subs:
                subs.sort(key=lambda x: x["slotIndex"])
                return subs[:2]
        
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
    
    def check_sim_present(self, serial: str, sub_id: int) -> bool:
        """
        快速检查指定订阅是否有SIM卡存在
        通过尝试获取ICCID来判断（只尝试最常见的code和格式，快速失败）
        返回True表示有SIM卡，False表示没有SIM卡
        """
        # 只尝试最常见的ICCID code (15) 和最常用的2种命令格式
        # 这样可以快速判断，避免执行大量无效命令
        quick_commands = [
            f"service call iphonesubinfo 15 i32 {sub_id} s16 com.android.shell",
            f"service call iphonesubinfo 15 i32 {sub_id}"
        ]
        
        for cmd in quick_commands:
            rc, out, err = self.adb_shell(serial, cmd)
            
            # 检查错误标记
            error_markers = ["Parcel data not fully consumed", "fffffff", "Transaction failed", "SecurityException"]
            has_error = any(marker in out.lower() or marker in err.lower() for marker in error_markers)
            if has_error:
                continue
            
            if rc == 0 and out:
                result = self.parse_service_call_digits(out)
                # 如果成功获取到非空的ICCID，说明有SIM卡
                if result and len(result) > 0:
                    return True
        
        # 如果快速检查都失败，认为没有SIM卡
        return False
    
    def collect_field_for_slot(self, serial: str, field_name: str, sub_id: int, slot_index: int) -> str:
        """
        为指定卡槽收集指定字段的数据
        返回字段值，如果获取失败返回空字符串
        """
        # 字段对应的code列表
        field_codes = {
            "IMEI": [1, 2],
            "MSISDN": [17, 16, 20],
            "IMSI": [10, 9, 8],
            "ICCID": [15, 14, 13, 12]
        }
        
        if field_name not in field_codes:
            return ""
        
        codes = field_codes[field_name]
        
        # 尝试每个code，直到获取成功
        for code in codes:
            value = self.service_call_with_priority(serial, code, sub_id)
            if value:
                return value
        
        return ""
    
    def collect_field_for_slots(self, serial: str, field_name: str, subscriptions: List[Dict[str, Any]], sim_present_map: Dict[int, bool] = None) -> Dict[str, str]:
        """
        为指定字段收集所有卡槽的数据，并处理重复值
        sim_present_map: {slot_index: bool} 表示每个卡槽是否有SIM卡
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
        
        # IMEI是设备级别的，不需要SIM卡也能获取
        # 其他字段（MSISDN、IMSI、ICCID）需要SIM卡
        requires_sim = field_name != "IMEI"
        
        # 先查询slot 0
        slot0_sub = next((sub for sub in subscriptions if sub["slotIndex"] == 0), None)
        slot0_value = ""
        if slot0_sub:
            # 检查是否需要SIM卡，以及是否有SIM卡
            # 如果不需要SIM卡（IMEI），或者sim_present_map为None（兼容旧代码），或者该卡槽有SIM卡，则获取
            if not requires_sim or not sim_present_map or sim_present_map.get(0, True):
                for code in codes:
                    slot0_value = self.service_call_with_priority(serial, code, slot0_sub["subId"])
                    if slot0_value:
                        break
            slot_values[0] = slot0_value
        
        # 再查询slot 1
        slot1_sub = next((sub for sub in subscriptions if sub["slotIndex"] == 1), None)
        if slot1_sub:
            # 检查是否需要SIM卡，以及是否有SIM卡
            if not requires_sim or not sim_present_map or sim_present_map.get(1, True):
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
            else:
                slot_values[1] = ""  # 没有SIM卡，返回空值
        
        return slot_values
    
    def collect_device_info(self, serial: str) -> Dict[str, Any]:
        """
        收集设备信息 - 优化版本：先检查SIM卡，无SIM卡时只获取IMEI
        """
        # Step 1: 校验设备状态
        rc, _, err = self.run_adb_command(f"adb -s {serial} get-state")
        if rc != 0:
            raise Exception(f"{self.lang_manager.tr('设备状态检查失败:')} {err}")
        
        # Step 2: 发现订阅
        subscriptions = self.discover_subscriptions(serial)
        
        result = {
            "serial": serial,
            "fingerprint": self.getprop(serial, "ro.build.fingerprint"),
            "antirollback": self.getprop(serial, "ro.boot.antirollback"),
            "build_date": self.getprop(serial, "ro.build.date"),
            "device_model": self.getprop(serial, "ro.product.model"),
            "device_brand": self.getprop(serial, "ro.product.brand"),
            "android_version": self.getprop(serial, "ro.build.version.release"),
            "api_level": self.getprop(serial, "ro.build.version.sdk"),
            "subscriptions": [],
            "flat": {}
        }
        
        # Step 3: 快速检查每个卡槽是否有SIM卡
        # sim_present_map: {slot_index: bool} 表示每个卡槽是否有SIM卡
        sim_present_map: Dict[int, bool] = {}
        for sub in subscriptions:
            slot_idx = sub["slotIndex"]
            sub_id = sub["subId"]
            # 快速检查SIM卡是否存在（只尝试最常见的ICCID获取方式）
            sim_present_map[slot_idx] = self.check_sim_present(serial, sub_id)
        
        # Step 4: 根据SIM卡检查结果收集字段数据
        # IMEI是设备级别的，无论是否有SIM卡都获取
        imei_data = self.collect_field_for_slots(serial, "IMEI", subscriptions, sim_present_map)
        
        # 只有在有SIM卡的情况下才获取这些字段
        # 检查是否有任何卡槽有SIM卡
        has_any_sim = any(sim_present_map.values()) if sim_present_map else False
        
        msisdn_data: Dict[int, str] = {}
        imsi_data: Dict[int, str] = {}
        iccid_data: Dict[int, str] = {}
        
        if has_any_sim:
            # 只对有SIM卡的卡槽获取SIM相关信息
            msisdn_data = self.collect_field_for_slots(serial, "MSISDN", subscriptions, sim_present_map)
            imsi_data = self.collect_field_for_slots(serial, "IMSI", subscriptions, sim_present_map)
            iccid_data = self.collect_field_for_slots(serial, "ICCID", subscriptions, sim_present_map)
        else:
            # 如果没有SIM卡，这些字段都为空
            for sub in subscriptions:
                slot_idx = sub["slotIndex"]
                msisdn_data[slot_idx] = ""
                imsi_data[slot_idx] = ""
                iccid_data[slot_idx] = ""
        
        # Step 5: 组装订阅数据
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
        
        # Step 6: 生成扁平化映射
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
        
        return result

