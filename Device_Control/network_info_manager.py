#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络信息管理模块 V2
按照 ca_endc_table_multi_cmd_spec.json 规范重构
负责获取和显示设备网络信息，支持CA/ENDC表格
"""

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

MAXINT = 2147483647

class CarrierInfo:
    """载波信息类"""
    def __init__(self):
        self.sim = ""
        self.cc = ""  # PCC/SCC1/SpCell/SCells#1
        self.rat = ""  # LTE/NR
        self.band = ""  # B66/n41
        self.dl_arfcn = 0
        self.ul_arfcn = 0
        self.pci = 0
        self.rsrp = None
        self.rsrq = None
        self.sinr = None
        self.rssi = None
        self.bw_dl = 0  # MHz
        self.bw_ul = 0  # MHz
        self.ca_endc = ""  # CA/ENDC摘要
        self.cqi = None
        self.note = ""

class NetworkInfoManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_running = False
        self.network_info_thread = None
        self.carriers_data = []  # List[CarrierInfo]
        
        # Ping相关变量
        self.is_ping_running = False
        self.ping_thread = None
        self.ping_process = None
        
        # 正则表达式模式
        self._init_regex_patterns()
    
    def _init_regex_patterns(self):
        """初始化正则表达式模式"""
        # PhysicalChannel配置解析 - 使用贪婪匹配获取完整块
        self.PHYSICAL_CHANNEL_RE = re.compile(
            r"mPhysicalChannelConfigs=\[(.*?)\]",
            re.DOTALL
        )
        
        self.CHANNEL_CONFIG_RE = re.compile(
            r"\{mConnectionStatus=(?P<conn_status>\w+),"
            r"mCellBandwidthDownlinkKhz=(?P<bw_dl>\d+),"
            r"mCellBandwidthUplinkKhz=(?P<bw_ul>\d+),"
            r"mNetworkType=(?P<rat>\w+),"
            r"mFrequencyRange=(?P<freq_range>\w+),"
            r"mDownlinkChannelNumber=(?P<dl_arfcn>\d+),"
            r"mUplinkChannelNumber=(?P<ul_arfcn>\d+),"
            r"mContextIds=\[.*?\],"
            r"mPhysicalCellId=(?P<pci>\d+),"
            r"mBand=(?P<band>\d+),"
            r"mDownlinkFrequency=(?P<dl_freq>-?\d+),"
            r"mUplinkFrequency=(?P<ul_freq>-?\d+)\}"
        )
        
        # SignalStrength解析
        self.SIGNAL_STRENGTH_RE = re.compile(
            r"mSignalStrength=SignalStrength:\{(.*?)\}",
            re.DOTALL
        )
        
        self.LTE_SIGNAL_RE = re.compile(
            r"mLte=CellSignalStrengthLte:\s*"
            r"rssi=(?P<rssi>-?\d+|%d)\s*"
            r"rsrp=(?P<rsrp>-?\d+|%d)\s*"
            r"rsrq=(?P<rsrq>-?\d+|%d)\s*"
            r"rssnr=(?P<rssnr>-?\d+|%d)\s*"
            r"cqiTableIndex=(?P<cqi_table>-?\d+|%d)\s*"
            r"cqi=(?P<cqi>-?\d+|%d)\s*"
            r"ta=(?P<ta>-?\d+|%d)\s*"
            r"level=(?P<level>-?\d+)"
            % (MAXINT, MAXINT, MAXINT, MAXINT, MAXINT, MAXINT, MAXINT),
            re.DOTALL
        )
        
        self.NR_SIGNAL_RE = re.compile(
            r"mNr=CellSignalStrengthNr:\{.*?"
            r"csiRsrp\s*=\s*(?P<csi_rsrp>-?\d+|%d).*?"
            r"csiRsrq\s*=\s*(?P<csi_rsrq>-?\d+|%d).*?"
            r"csiCqiTableIndex\s*=\s*(?P<csi_cqi_table>-?\d+|%d).*?"
            r"csiCqiReport\s*=\s*\[(?P<csi_cqi_report>[^\]]*)\].*?"
            r"ssRsrp\s*=\s*(?P<ss_rsrp>-?\d+|%d).*?"
            r"ssRsrq\s*=\s*(?P<ss_rsrq>-?\d+|%d).*?"
            r"ssSinr\s*=\s*(?P<ss_sinr>-?\d+|%d).*?"
            r"level\s*=\s*(?P<level>-?\d+).*?"
            r"parametersUseForLevel\s*=\s*(?P<params>-?\d+).*?"
            r"timingAdvance\s*=\s*(?P<timing>-?\d+|%d).*?(?:\}|,primary=)"
            % (MAXINT, MAXINT, MAXINT, MAXINT, MAXINT, MAXINT, MAXINT),
            re.DOTALL
        )
        
        # CellInfo解析 - 使用贪婪匹配获取完整块
        self.CELL_INFO_RE = re.compile(
            r"mCellInfo=\[(.*)\]",
            re.DOTALL
        )
        
        self.CELL_INFO_LTE_RE = re.compile(
            r"CellInfoLte:\{.*?mRegistered=(?P<registered>\w+).*?"
            r"CellIdentityLte:\{.*?"
            r"mCi=(?P<ci>\d+).*?"
            r"mPci=(?P<pci>\d+).*?"
            r"mTac=(?P<tac>\d+).*?"
            r"mEarfcn=(?P<earfcn>\d+).*?"
            r"mBands=\[(?P<bands>[^\]]*)\].*?"
            r"mBandwidth=(?P<bandwidth>-?\d+|%d).*?"
            r"mMcc=(?P<mcc>\d+).*?"
            r"mMnc=(?P<mnc>\d+).*?\}"
            % MAXINT,
            re.DOTALL
        )
        
        self.CELL_INFO_NR_RE = re.compile(
            r"CellInfoNr:\{.*?"
            r"mRegistered=(?P<registered>\w+).*?"
            r"CellIdentityNr:\{.*?"
            r"mPci\s*=\s*(?P<pci>\d+).*?"
            r"mTac\s*=\s*(?P<tac>-?\d+|%d).*?"
            r"mNrArfcn\s*=\s*(?P<nr_arfcn>\d+).*?"
            r"mBands\s*=\s*\[(?P<bands>[^\]]*)\].*?"
            r"mMcc\s*=\s*(?P<mcc>null|\d+).*?"
            r"mMnc\s*=\s*(?P<mnc>null|\d+).*?"
            r"mNci\s*=\s*(?P<nci>\d+).*?\}"
            % MAXINT,
            re.DOTALL
        )
        
        # WiFi正则表达式
        self.WIFI_BLOCK_RES = [
            re.compile(r"mWifiInfo\s*=\s*WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
            re.compile(r"WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
        ]
        
    def _to_int(self, value: Any) -> Optional[int]:
        """转换为整数，处理MAXINT"""
        if value is None:
            return None
        try:
            iv = int(value)
            return None if iv == MAXINT else iv
        except:
            return None
    
    def _val_ok(self, value: Any) -> bool:
        """检查值是否有效"""
        return value is not None and value != MAXINT
    
    def _run_adb(self, cmd: List[str]) -> str:
        """运行ADB命令"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.app.selected_device.get().strip()] + cmd,
                                  capture_output=True, text=True, timeout=10, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            print(f"ADB命令执行失败: {e}")
        return ""
    
    def _parse_physical_channels(self, raw_data: str) -> List[Dict]:
        """解析PhysicalChannel配置 - 支持多块解析，选择最后一个非空块"""
        channels = []
        
        # 手动解析PhysicalChannel块，处理嵌套方括号
        start_pattern = 'mPhysicalChannelConfigs=['
        start_positions = []
        
        # 找到所有开始位置
        pos = 0
        while True:
            pos = raw_data.find(start_pattern, pos)
            if pos == -1:
                break
            start_positions.append(pos)
            pos += len(start_pattern)
        
        if not start_positions:
            return channels
        
        # 解析每个块
        block_contents = []
        for start_pos in start_positions:
            content_start = start_pos + len(start_pattern)
            remaining = raw_data[content_start:]
            
            # 找到匹配的结束位置
            depth = 0
            end_pos = content_start
            for i, char in enumerate(remaining):
                if char == '[':
                    depth += 1
                elif char == ']':
                    if depth == 0:
                        end_pos = content_start + i
                        break
                    depth -= 1
            
            content = raw_data[content_start:end_pos]
            block_contents.append(content)
        
        # 选择最后一个非空块
        chosen = None
        for content in block_contents:
            if not content.strip():
                continue
                
            tmp = []
            for m in self.CHANNEL_CONFIG_RE.finditer(content):
                g = m.groupdict()
                tmp.append({
                    'connection_status': g['conn_status'],
                    'bw_dl_khz': int(g['bw_dl']),
                    'bw_ul_khz': int(g['bw_ul']),
                    'rat': g['rat'],
                    'freq_range': g['freq_range'],
                    'dl_arfcn': int(g['dl_arfcn']),
                    'ul_arfcn': int(g['ul_arfcn']),
                    'pci': int(g['pci']),
                    'band': int(g['band']),
                    'dl_freq': int(g['dl_freq']),
                    'ul_freq': int(g['ul_freq'])
                })
            if tmp:  # 记录最后一个非空块
                chosen = tmp
        
        return chosen or []  # 没有非空块则空列表
    
    def _parse_signal_strength(self, raw_data: str) -> Dict:
        """解析SignalStrength信息"""
        signal_data = {'lte': {}, 'nr': {}}
        
        # 查找所有SignalStrength块
        matches = self.SIGNAL_STRENGTH_RE.finditer(raw_data)
        
        for match in matches:
            signal_text = match.group(1)
            
            # 解析LTE信号
            lte_match = self.LTE_SIGNAL_RE.search(signal_text)
            if lte_match:
                lte_data = lte_match.groupdict()
                # 只使用有效的信号强度数据（不是MAXINT）
                if self._val_ok(self._to_int(lte_data['rsrp'])):
                    signal_data['lte'] = {
                        'rssi': self._to_int(lte_data['rssi']),
                        'rsrp': self._to_int(lte_data['rsrp']),
                        'rsrq': self._to_int(lte_data['rsrq']),
                        'rssnr': self._to_int(lte_data['rssnr']),
                        'cqi_table': self._to_int(lte_data['cqi_table']),
                        'cqi': self._to_int(lte_data['cqi']),
                        'ta': self._to_int(lte_data['ta']),
                        'level': self._to_int(lte_data['level'])
                    }
            
            # 解析NR信号 - 使用简化的方法
            if "mNr=" in signal_text:
                # 提取关键字段
                ss_rsrp_match = re.search(r"ssRsrp\s*=\s*(-?\d+|%d)" % MAXINT, signal_text)
                ss_rsrq_match = re.search(r"ssRsrq\s*=\s*(-?\d+|%d)" % MAXINT, signal_text)
                ss_sinr_match = re.search(r"ssSinr\s*=\s*(-?\d+|%d)" % MAXINT, signal_text)
                csi_cqi_report_match = re.search(r"csiCqiReport\s*=\s*\[([^\]]*)\]", signal_text)
                
                if ss_rsrp_match and self._val_ok(self._to_int(ss_rsrp_match.group(1))):
                    signal_data['nr'] = {
                        'csi_rsrp': None,
                        'csi_rsrq': None,
                        'csi_cqi_table': None,
                        'csi_cqi_report': csi_cqi_report_match.group(1) if csi_cqi_report_match else None,
                        'ss_rsrp': self._to_int(ss_rsrp_match.group(1)),
                        'ss_rsrq': self._to_int(ss_rsrq_match.group(1)) if ss_rsrq_match else None,
                        'ss_sinr': self._to_int(ss_sinr_match.group(1)) if ss_sinr_match else None,
                        'level': None,
                        'timing': None
                    }
        
        return signal_data
    
    def _parse_cell_info(self, raw_data: str) -> List[Dict]:
        """解析CellInfo信息 - 使用简化的字符串搜索方法"""
        cell_infos = []
        
        # 查找CellInfo块
        match = self.CELL_INFO_RE.search(raw_data)
        if not match:
            return cell_infos
        
        cell_info_text = match.group(1)
        
        # 简化的LTE CellInfo解析 - 使用字符串搜索
        if "CellInfoLte:" in cell_info_text:
            # 提取关键字段
            registered_match = re.search(r"mRegistered=(\w+)", cell_info_text)
            pci_match = re.search(r"mPci=(\d+)", cell_info_text)
            earfcn_match = re.search(r"mEarfcn=(\d+)", cell_info_text)
            bands_match = re.search(r"mBands=\[([^\]]*)\]", cell_info_text)
            mcc_match = re.search(r"mMcc=(\d+)", cell_info_text)
            mnc_match = re.search(r"mMnc=(\d+)", cell_info_text)
            
            if pci_match and earfcn_match:
                cell_info = {
                    'type': 'LTE',
                    'registered': registered_match.group(1) == 'YES' if registered_match else False,
                    'ci': 0,  # 简化处理
                    'pci': int(pci_match.group(1)),
                    'tac': 0,  # 简化处理
                    'earfcn': int(earfcn_match.group(1)),
                    'bands': [b.strip() for b in bands_match.group(1).split(',')] if bands_match else [],
                    'bandwidth': None,  # CellInfo中没有带宽信息
                    'mcc': mcc_match.group(1) if mcc_match else None,
                    'mnc': mnc_match.group(1) if mnc_match else None
                }
                cell_infos.append(cell_info)
        
        # 简化的NR CellInfo解析 - 使用字符串搜索
        if "CellInfoNr:" in cell_info_text:
            # 提取关键字段
            registered_match = re.search(r"mRegistered=(\w+)", cell_info_text)
            pci_match = re.search(r"mPci\s*=\s*(\d+)", cell_info_text)
            nr_arfcn_match = re.search(r"mNrArfcn\s*=\s*(\d+)", cell_info_text)
            bands_match = re.search(r"mBands\s*=\s*\[([^\]]*)\]", cell_info_text)
            mcc_match = re.search(r"mMcc\s*=\s*(null|\d+)", cell_info_text)
            mnc_match = re.search(r"mMnc\s*=\s*(null|\d+)", cell_info_text)
            
            if pci_match and nr_arfcn_match:
                cell_info = {
                    'type': 'NR',
                    'registered': registered_match.group(1) == 'YES' if registered_match else False,
                    'pci': int(pci_match.group(1)),
                    'tac': 0,  # 简化处理
                    'nr_arfcn': int(nr_arfcn_match.group(1)),
                    'bands': [b.strip() for b in bands_match.group(1).split(',')] if bands_match else [],
                    'mcc': mcc_match.group(1) if mcc_match and mcc_match.group(1) != 'null' else None,
                    'mnc': mnc_match.group(1) if mnc_match and mnc_match.group(1) != 'null' else None,
                    'nci': 0  # 简化处理
                }
                cell_infos.append(cell_info)
        
        return cell_infos
    
    def _parse_wifi(self, raw_wifi):
        """解析WiFi信息 - 参考backup文件实现更严格的连接状态判断"""
        txt = None
        for pat in self.WIFI_BLOCK_RES:
            m = pat.search(raw_wifi)
            if m:
                txt = m.group("info")
                break
        if not txt:
            txt = raw_wifi

        def first_match(text, pats):
            for p in pats:
                m = p.search(text)
                if m:
                    return m.groupdict()
            return {}

        # 使用backup文件的正则表达式列表
        ssid_re_list = [
            re.compile(r'SSID:\s*"(?P<ssid>[^"]*)"'),
            re.compile(r"SSID:\s*(?P<ssid><unknown ssid>|[^\s,}]+)"),
            re.compile(r"mSSID:\s*SSID\{(?P<ssid>[^}]*)\}"),
        ]
        
        rssi_re_list = [
            re.compile(r"RSSI:\s*(?P<rssi>-?\d+)"), 
            re.compile(r"mRssi=\s*(?P<rssi>-?\d+)")
        ]
        
        bssid_re = re.compile(r"BSSID:\s*(?P<bssid>[0-9a-fA-F:]{11,})")
        linkspd_re = re.compile(r"LinkSpeed:\s*(?P<ls>\d+)\s*Mbps")
        freq_re = re.compile(r"Frequency:\s*(?P<freq>\d+)")
        suppl_re = re.compile(r"Supplicant state:\s*(?P<state>\w+)", re.IGNORECASE)

        ssid_m = first_match(txt, ssid_re_list)
        rssi_m = first_match(txt, rssi_re_list)
        bssid_m = bssid_re.search(txt) or {}
        link_m = linkspd_re.search(txt) or {}
        freq_m = freq_re.search(txt) or {}
        supp_m = suppl_re.search(txt) or {}

        ssid = (ssid_m.get("ssid") if ssid_m else None)
        if ssid == "<unknown ssid>":
            ssid = None

        wifi = {
            "ssid": ssid,
            "rssi": self._to_int((rssi_m.get("rssi") if rssi_m else None)),
            "bssid": (bssid_m.group("bssid") if hasattr(bssid_m, "group") else None),
            "linkMbps": self._to_int((link_m.group("ls") if hasattr(link_m, "group") else None)),
            "freqMHz": self._to_int((freq_m.group("freq") if hasattr(freq_m, "group") else None)),
            "state": (supp_m.group("state") if hasattr(supp_m, "group") else None),
        }
        
        band = None
        if wifi["freqMHz"]:
            f = wifi["freqMHz"]
            if 2400 <= f < 2500:
                band = "2.4GHz"
            elif 4900 <= f < 5900:
                band = "5GHz"
            elif 5925 <= f < 7125:
                band = "6GHz"
        
        wifi["band"] = band
        # 更严格的连接状态判断：需要SSID、RSSI和有效的supplicant状态
        wifi["connected"] = (
            wifi["ssid"] is not None and 
            wifi["rssi"] is not None and 
            wifi["state"] is not None and
            wifi["state"].lower() in ["completed", "associated"]
        )
        return wifi
    
    def _build_carrier_table(self, channels: List[Dict], signal_data: Dict, cell_infos: List[Dict]) -> List[CarrierInfo]:
        """构建载波表格"""
        carriers = []
        
        # 按SIM分组（简化处理，假设第一个SIM）
        sim = "SIM1"
        
        # 分析CA/ENDC配置
        lte_channels = [c for c in channels if c['rat'] == 'LTE']
        nr_channels = [c for c in channels if c['rat'] == 'NR']
        
        # 如果没有PhysicalChannel配置（IDLE情况），尝试从CellInfo构建载波信息
        if not channels and cell_infos:
            return self._build_carrier_from_cellinfo(cell_infos, signal_data)
        
        # 确定主载波
        primary_lte = None
        primary_nr = None
        
        for channel in lte_channels:
            if channel['connection_status'] == 'PrimaryServing':
                primary_lte = channel
                break
        
        for channel in nr_channels:
            if channel['connection_status'] == 'PrimaryServing':
                primary_nr = channel
                break
        
        # 生成CA/ENDC摘要
        ca_endc_summary = self._generate_ca_endc_summary(lte_channels, nr_channels)
        
        # 构建载波信息
        if primary_lte:
            # LTE主载波
            carrier = CarrierInfo()
            carrier.sim = sim
            carrier.cc = "PCC"
            carrier.rat = "LTE"
            carrier.band = f"B{primary_lte['band']}"
            carrier.dl_arfcn = primary_lte['dl_arfcn']
            carrier.ul_arfcn = primary_lte['ul_arfcn']
            carrier.pci = primary_lte['pci']
            carrier.bw_dl = primary_lte['bw_dl_khz'] // 1000
            carrier.bw_ul = primary_lte['bw_ul_khz'] // 1000
            carrier.ca_endc = ca_endc_summary
            
            # 添加信号强度
            if signal_data.get('lte'):
                lte_sig = signal_data['lte']
                carrier.rsrp = lte_sig.get('rsrp')
                carrier.rsrq = lte_sig.get('rsrq')
                carrier.sinr = lte_sig.get('rssnr')
                carrier.rssi = lte_sig.get('rssi')
                carrier.cqi = lte_sig.get('cqi')
            
            carrier.note = "Anchor LTE"
            carriers.append(carrier)
            
            # LTE辅载波
            scc_count = 1
            for channel in lte_channels:
                if channel['connection_status'] == 'SecondaryServing':
                    carrier = CarrierInfo()
                    carrier.sim = ""  # 副载波SIM列留空
                    carrier.cc = f"SCC{scc_count}"
                    carrier.rat = "LTE"
                    carrier.band = f"B{channel['band']}"
                    carrier.dl_arfcn = channel['dl_arfcn']
                    carrier.ul_arfcn = channel['ul_arfcn']
                    carrier.pci = channel['pci']
                    carrier.bw_dl = channel['bw_dl_khz'] // 1000
                    carrier.bw_ul = channel['bw_ul_khz'] // 1000
                    carrier.ca_endc = ca_endc_summary
                    carrier.note = "DL-only" if carrier.ul_arfcn == 0 else ""
                    carriers.append(carrier)
                    scc_count += 1
        
        # NR载波
        if nr_channels:
            # 确定主载波（最大带宽的NR载波）
            primary_nr = max(nr_channels, key=lambda x: x['bw_dl_khz'])
            
            carrier = CarrierInfo()
            carrier.sim = sim
            # 如果有LTE主载波，NR是SpCell；如果没有LTE，NR是PCell
            carrier.cc = "SpCell" if primary_lte else "PCell"
            carrier.rat = "NR"
            carrier.band = f"n{primary_nr['band']}"
            carrier.dl_arfcn = primary_nr['dl_arfcn']
            carrier.ul_arfcn = primary_nr['ul_arfcn']
            carrier.pci = primary_nr['pci']
            carrier.bw_dl = primary_nr['bw_dl_khz'] // 1000
            carrier.bw_ul = primary_nr['bw_ul_khz'] // 1000
            carrier.ca_endc = ca_endc_summary
            
            # 添加信号强度
            if signal_data.get('nr'):
                nr_sig = signal_data['nr']
                carrier.rsrp = nr_sig.get('ss_rsrp')
                carrier.rsrq = nr_sig.get('ss_rsrq')
                carrier.sinr = nr_sig.get('ss_sinr')
                carrier.cqi = nr_sig.get('csi_cqi_report')
            
            carrier.note = "Anchor NR" if not primary_lte else ""
            carriers.append(carrier)
            
            # NR辅载波
            scc_count = 1
            for channel in nr_channels:
                if channel != primary_nr:
                    carrier = CarrierInfo()
                    carrier.sim = ""  # 副载波SIM列留空
                    # 如果有LTE主载波，NR辅载波是SCells；如果没有LTE，NR辅载波是SCC
                    carrier.cc = f"SCells#{scc_count}" if primary_lte else f"SCC{scc_count}"
                    carrier.rat = "NR"
                    carrier.band = f"n{channel['band']}"
                    carrier.dl_arfcn = channel['dl_arfcn']
                    carrier.ul_arfcn = channel['ul_arfcn']
                    carrier.pci = channel['pci']
                    carrier.bw_dl = channel['bw_dl_khz'] // 1000
                    carrier.bw_ul = channel['bw_ul_khz'] // 1000
                    carrier.ca_endc = ca_endc_summary
                    carrier.note = "DL-only" if carrier.ul_arfcn == 0 else ""
                    carriers.append(carrier)
                    scc_count += 1
        
        return carriers
    
    def _build_carrier_from_cellinfo(self, cell_infos: List[Dict], signal_data: Dict) -> List[CarrierInfo]:
        """从CellInfo构建载波信息（用于IDLE情况）"""
        carriers = []
        sim = "SIM1"  # 简化处理
        
        # 按RAT分组
        lte_cells = [c for c in cell_infos if c['type'] == 'LTE']
        nr_cells = [c for c in cell_infos if c['type'] == 'NR']
        
        # 生成CA/ENDC摘要
        ca_endc_summary = self._generate_ca_endc_summary(lte_cells, nr_cells)
        
        # 处理LTE小区
        if lte_cells:
            # 找到已注册的LTE小区
            registered_lte = [c for c in lte_cells if c.get('registered', False)]
            if registered_lte:
                cell = registered_lte[0]  # 取第一个已注册的小区
                carrier = CarrierInfo()
                carrier.sim = sim
                carrier.cc = "PCC"
                carrier.rat = "LTE"
                carrier.band = f"B{cell['bands'][0]}" if cell.get('bands') else ""
                carrier.dl_arfcn = cell.get('earfcn', 0)
                carrier.ul_arfcn = 0  # CellInfo中没有UL信息
                carrier.pci = cell.get('pci', 0)
                carrier.bw_dl = 0  # CellInfo中没有带宽信息
                carrier.bw_ul = 0
                carrier.ca_endc = ca_endc_summary
                carrier.note = "IDLE状态"
                
                # 添加信号强度
                if signal_data.get('lte'):
                    lte_sig = signal_data['lte']
                    carrier.rsrp = lte_sig.get('rsrp')
                    carrier.rsrq = lte_sig.get('rsrq')
                    carrier.sinr = lte_sig.get('rssnr')
                    carrier.rssi = lte_sig.get('rssi')
                    carrier.cqi = lte_sig.get('cqi')
                
                carriers.append(carrier)
        
        # 处理NR小区
        if nr_cells:
            # 找到已注册的NR小区
            registered_nr = [c for c in nr_cells if c.get('registered', False)]
            if registered_nr:
                cell = registered_nr[0]  # 取第一个已注册的小区
                carrier = CarrierInfo()
                carrier.sim = sim
                carrier.cc = "SpCell"
                carrier.rat = "NR"
                carrier.band = f"n{cell['bands'][0]}" if cell.get('bands') else ""
                carrier.dl_arfcn = cell.get('nr_arfcn', 0)
                carrier.ul_arfcn = 0  # CellInfo中没有UL信息
                carrier.pci = cell.get('pci', 0)
                carrier.bw_dl = 0  # CellInfo中没有带宽信息
                carrier.bw_ul = 0
                carrier.ca_endc = ca_endc_summary
                carrier.note = "IDLE状态"
                
                # 添加信号强度
                if signal_data.get('nr'):
                    nr_sig = signal_data['nr']
                    carrier.rsrp = nr_sig.get('ss_rsrp')
                    carrier.rsrq = nr_sig.get('ss_rsrq')
                    carrier.sinr = nr_sig.get('ss_sinr')
                    carrier.cqi = nr_sig.get('csi_cqi_report')
                
                carriers.append(carrier)
        
        return carriers
    
    def _generate_ca_endc_summary(self, lte_channels: List[Dict], nr_channels: List[Dict]) -> str:
        """生成CA/ENDC摘要 - 显示具体的band组合"""
        lte_count = len(lte_channels)
        nr_count = len(nr_channels)
        
        # 如果是CellInfo数据，需要特殊处理
        if lte_count > 0 and isinstance(lte_channels[0], dict) and 'type' in lte_channels[0]:
            # 这是CellInfo数据，不是PhysicalChannel数据
            lte_count = len([c for c in lte_channels if c.get('registered', False)])
            nr_count = len([c for c in nr_channels if c.get('registered', False)])
        
        if lte_count > 0 and nr_count > 0:
            # ENDC情况：LTE + NR
            lte_bands = []
            nr_bands = []
            for c in lte_channels:
                if 'band' in c:
                    lte_bands.append(f"b{c['band']}")
                elif 'bands' in c and c['bands']:
                    lte_bands.extend([f"b{b}" for b in c['bands']])
            for c in nr_channels:
                if 'band' in c:
                    nr_bands.append(f"n{c['band']}")
                elif 'bands' in c and c['bands']:
                    nr_bands.extend([f"n{b}" for b in c['bands']])
            band_str = "_".join(sorted(lte_bands + nr_bands))
            return f"EN_DC_{band_str}"
        elif lte_count > 1:
            # LTE CA情况
            lte_bands = []
            for c in lte_channels:
                if 'band' in c:
                    lte_bands.append(f"b{c['band']}")
                elif 'bands' in c and c['bands']:
                    lte_bands.extend([f"b{b}" for b in c['bands']])
            band_str = "_".join(sorted(lte_bands))
            return f"CA_{band_str}"
        elif lte_count == 1:
            # 单LTE载波
            c = lte_channels[0]
            if 'band' in c:
                lte_band = f"b{c['band']}"
            elif 'bands' in c and c['bands']:
                lte_band = f"b{c['bands'][0]}"
            else:
                lte_band = "b?"
            return f"LTE_{lte_band}"
        elif nr_count > 1:
            # NR CA情况
            nr_bands = []
            for c in nr_channels:
                if 'band' in c:
                    nr_bands.append(f"n{c['band']}")
                elif 'bands' in c and c['bands']:
                    nr_bands.extend([f"n{b}" for b in c['bands']])
            band_str = "_".join(sorted(nr_bands))
            return f"CA_{band_str}"
        elif nr_count == 1:
            # 单NR载波
            c = nr_channels[0]
            if 'band' in c:
                nr_band = f"n{c['band']}"
            elif 'bands' in c and c['bands']:
                nr_band = f"n{c['bands'][0]}"
            else:
                nr_band = "n?"
            return f"NR_{nr_band}"
        else:
            return "No active carriers"
    
    def _get_network_snapshot(self, device: str):
        """获取网络信息快照 - 按照dual_sim_patch_spec.json实现双SIM支持"""
        try:
            # 获取完整的telephony.registry数据
            tel_raw = self._run_adb(["shell", "dumpsys", "telephony.registry"])
            if not tel_raw:
                return
            
            # 1) 尝试现有的phone-id分段
            phone_sections = self._split_by_phone_id(tel_raw)
            
            # 2) 备用方案：如果phone-id分段不够，使用PhysicalChannel块分段
            if len(phone_sections) <= 1:
                phys_blocks = self._split_by_physical_blocks(tel_raw)
                useful = []
                for b in phys_blocks:
                    try:
                        carriers = self._parse_physical_channels(b)
                        if carriers:
                            useful.append(b)
                    except Exception:
                        continue
                # 使用前2个有用的段作为SIM1/SIM2
                phone_sections = useful[:2] if useful else [tel_raw]
            
            # 3) 为每个段构建行，分配SIM标签
            all_carriers = []
            for idx, section in enumerate(phone_sections):
                sim_name = f"SIM{idx + 1}"
                
                # 解析各个组件
                channels = self._parse_physical_channels(section)
                signal_data = self._parse_signal_strength(section)
                cell_infos = self._parse_cell_info(section)
                
                # 构建载波表格
                carriers = self._build_carrier_table(channels, signal_data, cell_infos)
                
                # 更新SIM名称
                for carrier in carriers:
                    carrier.sim = sim_name
                
                all_carriers.extend(carriers)
            
            self.carriers_data = all_carriers
            
            # 获取WiFi信息
            try:
                wifi_raw = self._run_adb(["shell", "dumpsys", "wifi"])
                if wifi_raw:
                    wifi = self._parse_wifi(wifi_raw)
                    # 将WiFi信息添加到载波数据中
                    if wifi.get('connected'):
                        wifi_carrier = CarrierInfo()
                        wifi_carrier.sim = "WIFI"
                        wifi_carrier.cc = "WIFI"
                        wifi_carrier.rat = "WIFI"
                        wifi_carrier.band = wifi.get('band', '')
                        wifi_carrier.dl_arfcn = wifi.get('freqMHz', 0)
                        wifi_carrier.ul_arfcn = 0
                        wifi_carrier.pci = 0
                        wifi_carrier.rsrp = None  # WIFI没有RSRP
                        wifi_carrier.rsrq = None
                        wifi_carrier.sinr = None
                        wifi_carrier.rssi = wifi.get('rssi')  # WIFI只有RSSI
                        wifi_carrier.bw_dl = 0
                        wifi_carrier.bw_ul = 0
                        wifi_carrier.ca_endc = ""  # WIFI不需要CA_ENDC_Comb
                        wifi_carrier.cqi = None
                        wifi_carrier.note = f"SSID: {wifi.get('ssid', '')}"
                        self.carriers_data.append(wifi_carrier)
            except Exception as e:
                print(f"获取WiFi信息失败: {e}")
                        
        except Exception as e:
            print(f"获取网络快照失败: {e}")
    
    def _split_by_phone_id(self, raw_data: str) -> List[str]:
        """按Phone Id分段数据"""
        import re
        
        # 查找所有Phone Id=的位置
        phone_id_pattern = r'Phone Id=(\d+)'
        phone_id_matches = list(re.finditer(phone_id_pattern, raw_data))
        
        if not phone_id_matches:
            return [raw_data]  # 如果没有找到Phone Id，返回整个数据
        
        sections = []
        for i, match in enumerate(phone_id_matches):
            start_pos = match.start()
            # 下一个Phone Id的位置，如果没有就是文件结尾
            end_pos = phone_id_matches[i + 1].start() if i + 1 < len(phone_id_matches) else len(raw_data)
            
            section = raw_data[start_pos:end_pos]
            sections.append(section)
        
        return sections
    
    def _split_by_physical_blocks(self, raw: str) -> List[str]:
        """按PhysicalChannel块分段数据 - 作为Phone Id分段的备用方案"""
        blocks = []
        for m in re.finditer(r"mPhysicalChannelConfigs=\[(.*?)\]", raw, re.DOTALL):
            blocks.append("mPhysicalChannelConfigs=[" + m.group(1) + "]")
        return blocks
    
    def start_network_info(self):
        """开始获取网络信息"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if self.is_running:
            messagebox.showinfo("提示", "网络信息获取已在运行中")
            return
        
        self.is_running = True
        self.app.ui.network_start_button.config(text="停止", state=tk.NORMAL)
        self.app.ui.status_var.set("正在获取网络信息...")
        
        # 启动网络信息获取线程
        self.network_info_thread = threading.Thread(target=self._network_info_worker, daemon=True)
        self.network_info_thread.start()
    
    def stop_network_info(self):
        """停止获取网络信息"""
        self.is_running = False
        self.app.ui.network_start_button.config(text="开始")
        self.app.ui.status_var.set("网络信息获取已停止")
    
    def _network_info_worker(self):
        """网络信息获取工作线程"""
        device = self.app.selected_device.get().strip()
        
        while self.is_running:
            try:
                # 获取网络信息快照
                self._get_network_snapshot(device)
                
                # 更新UI显示
                self.app.root.after(0, self._update_network_display)
                
                # 每2秒更新一次
                time.sleep(2)
                
            except Exception as e:
                print(f"获取网络信息时发生错误: {e}")
                time.sleep(2)
    
    def _update_network_display(self):
        """更新网络信息显示"""
        if not hasattr(self.app.ui, 'network_info_frame'):
            return
        
        try:
            # 如果还没有创建表格，先创建一次
            if not hasattr(self, '_network_table_created'):
                self._create_network_table()
                self._network_table_created = True
            else:
                # 只更新数据，不清空重建
                self._update_network_data()
            
        except Exception as e:
            print(f"更新网络信息显示失败: {e}")
    
    def _create_network_table(self):
        """创建基于Treeview的CA/ENDC表格"""
        # 清空现有内容
        for widget in self.app.ui.network_info_frame.winfo_children():
            widget.destroy()
        
        # 创建主框架
        main_frame = ttk.Frame(self.app.ui.network_info_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 定义列配置（按照spec.json的required_output_columns）
        columns = [
            ('SIM', 50, 'center'),
            ('CC', 80, 'center'),
            ('RAT', 50, 'center'),
            ('BAND', 60, 'center'),
            ('DL_ARFCN', 80, 'center'),
            ('UL_ARFCN', 80, 'center'),
            ('PCI', 50, 'center'),
            ('RSRP', 60, 'center'),
            ('RSRQ', 60, 'center'),
            ('SINR', 60, 'center'),
            ('RSSI', 60, 'center'),
            ('BW_DL', 60, 'center'),
            ('BW_UL', 60, 'center'),
            ('CA_ENDC_Comb', 120, 'center'),
            ('CQI', 60, 'center'),
            ('NOTE', 200, 'w')
        ]
        
        # 创建Treeview
        self.network_tree = ttk.Treeview(main_frame, columns=[col[0] for col in columns], show='headings', height=8)
        
        # 配置列标题和宽度
        for col_id, width, anchor in columns:
            self.network_tree.heading(col_id, text=col_id)
            if col_id == 'NOTE':
                # NOTE列允许拉伸
                self.network_tree.column(col_id, width=width, anchor=anchor, minwidth=width, stretch=tk.YES)
            else:
                self.network_tree.column(col_id, width=width, anchor=anchor, minwidth=width)
        
        # 设置样式
        style = ttk.Style()
        style.configure("Network.Treeview", font=('Arial', 9), rowheight=18)
        style.configure("Network.Treeview.Heading", font=('Arial', 9, 'bold'))
        self.network_tree.configure(style="Network.Treeview")
        
        # 创建滚动条
        v_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.network_tree.yview)
        h_scrollbar = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.network_tree.xview)
        self.network_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.network_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def _update_network_data(self):
        """更新Treeview中的网络数据"""
        try:
            if not hasattr(self, 'network_tree'):
                return
            
            # 清除现有数据
            for item in self.network_tree.get_children():
                self.network_tree.delete(item)
            
            # 插入载波数据
            for carrier in self.carriers_data:
                row_data = [
                    carrier.sim,
                    carrier.cc,
                    carrier.rat,
                    carrier.band,
                    str(carrier.dl_arfcn) if carrier.dl_arfcn else '',
                    str(carrier.ul_arfcn) if carrier.ul_arfcn else '',
                    str(carrier.pci) if carrier.pci else '',
                    str(carrier.rsrp) if carrier.rsrp is not None else '',
                    str(carrier.rsrq) if carrier.rsrq is not None else '',
                    str(carrier.sinr) if carrier.sinr is not None else '',
                    str(carrier.rssi) if carrier.rssi is not None else '',
                    str(carrier.bw_dl) if carrier.bw_dl else '',
                    str(carrier.bw_ul) if carrier.bw_ul else '',
                    carrier.ca_endc,
                    str(carrier.cqi) if carrier.cqi is not None else '',
                    carrier.note
                ]
                self.network_tree.insert('', tk.END, values=row_data)
                    
        except Exception as e:
            print(f"更新网络数据失败: {e}")
    
    def test_with_dump_data(self, dump_file_path: str):
        """使用dump.txt测试数据 - 支持双SIM"""
        try:
            with open(dump_file_path, 'r', encoding='utf-8') as f:
                dump_data = f.read()
            
            # 使用新的双SIM逻辑
            # 1) 尝试现有的phone-id分段
            phone_sections = self._split_by_phone_id(dump_data)
            
            # 2) 备用方案：如果phone-id分段不够，使用PhysicalChannel块分段
            if len(phone_sections) <= 1:
                phys_blocks = self._split_by_physical_blocks(dump_data)
                useful = []
                for b in phys_blocks:
                    try:
                        carriers = self._parse_physical_channels(b)
                        if carriers:
                            useful.append(b)
                    except Exception:
                        continue
                # 使用前2个有用的段作为SIM1/SIM2
                phone_sections = useful[:2] if useful else [dump_data]
            
            print("=== 测试结果 ===")
            print(f"分段数量: {len(phone_sections)}")
            
            # 3) 为每个段构建行，分配SIM标签
            all_carriers = []
            for idx, section in enumerate(phone_sections):
                sim_name = f"SIM{idx + 1}"
                print(f"\n--- {sim_name} ---")
                
                # 解析各个组件
                channels = self._parse_physical_channels(section)
                signal_data = self._parse_signal_strength(section)
                cell_infos = self._parse_cell_info(section)
                
                print(f"PhysicalChannel配置数量: {len(channels)}")
                for i, channel in enumerate(channels):
                    print(f"  载波{i+1}: {channel['rat']} B{channel['band']} PCI={channel['pci']} DL={channel['dl_arfcn']}")
                
                print(f"CellInfo数量: {len(cell_infos)}")
                for cell in cell_infos:
                    print(f"  {cell['type']}: PCI={cell['pci']} Registered={cell['registered']}")
                
                # 构建载波表格
                carriers = self._build_carrier_table(channels, signal_data, cell_infos)
                
                # 更新SIM名称
                for carrier in carriers:
                    carrier.sim = sim_name
                
                all_carriers.extend(carriers)
            
            print(f"\n总载波表格行数: {len(all_carriers)}")
            for carrier in all_carriers:
                print(f"  {carrier.sim} {carrier.cc} {carrier.rat} {carrier.band} PCI={carrier.pci} RSRP={carrier.rsrp}")
            
            return all_carriers
            
        except Exception as e:
            print(f"测试失败: {e}")
            return []
    
    def start_network_ping(self):
        """开始网络Ping测试"""
        try:
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return
            
            if self.is_ping_running:
                messagebox.showwarning("警告", "Ping测试已在运行中")
                return
            
            self.is_ping_running = True
            self.app.ui.network_ping_button.config(text="停止")
            
            # 启动Ping线程
            self.ping_thread = threading.Thread(target=self._ping_worker, args=(device,), daemon=True)
            self.ping_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动Ping测试失败: {str(e)}")
            self.is_ping_running = False
            self.app.ui.network_ping_button.config(text="Ping")
    
    def stop_network_ping(self):
        """停止网络Ping测试"""
        try:
            self.is_ping_running = False
            
            # 终止ping进程
            if self.ping_process:
                try:
                    self.ping_process.terminate()
                    try:
                        self.ping_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.ping_process.kill()
                        self.ping_process.wait()
                except Exception as e:
                    print(f"[DEBUG] 终止ping进程失败: {str(e)}")
                finally:
                    self.ping_process = None
            
            # 更新UI
            self.app.ui.network_ping_button.config(text="Ping")
            
            if hasattr(self.app.ui, 'network_ping_status_label'):
                self.app.ui.network_ping_status_label.config(text="Ping已停止", foreground="gray")
            
        except Exception as e:
            print(f"[DEBUG] 停止Ping测试失败: {str(e)}")
    
    def _ping_worker(self, device):
        """Ping工作线程"""
        try:
            # 执行ping命令 - 使用无限ping，但通过停止标志控制
            cmd = f"adb -s {device} shell ping www.google.com"
            
            # 启动ping进程
            self.ping_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 监控ping进程状态
            while self.is_ping_running and self.ping_process:
                try:
                    if self.ping_process.poll() is not None:
                        # 进程已结束
                        break
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[DEBUG] Ping监控异常: {str(e)}")
                    break
            
            # 启动输出读取线程
            if self.is_ping_running:
                stdout_thread = threading.Thread(target=self._read_ping_stdout, daemon=True)
                stderr_thread = threading.Thread(target=self._read_ping_stderr, daemon=True)
                stdout_thread.start()
                stderr_thread.start()
                
                # 等待线程结束
                stdout_thread.join()
                stderr_thread.join()
                
        except Exception as e:
            print(f"[DEBUG] Ping测试异常: {str(e)}")
            self._update_ping_status("Ping测试失败", "red")
        finally:
            self.is_ping_running = False
            self.ping_process = None
            
            # 更新UI
            if hasattr(self.app.ui, 'network_ping_button'):
                self.app.ui.network_ping_button.config(text="Ping")
    
    def _read_ping_stdout(self):
        """读取ping标准输出"""
        try:
            while self.is_ping_running and self.ping_process:
                line = self.ping_process.stdout.readline()
                if not line:
                    break
                
                line_lower = line.lower().strip()
                
                # 检查成功响应 - 按照backup文件规范
                if "bytes from" in line_lower:
                    # 每次成功响应都更新状态为正常（支持状态切换）
                    self._update_ping_status("网络正常", "green")
                        
        except Exception as e:
            print(f"[DEBUG] 读取ping stdout异常: {str(e)}")
    
    def _read_ping_stderr(self):
        """读取ping错误输出"""
        try:
            while self.is_ping_running and self.ping_process:
                line = self.ping_process.stderr.readline()
                if not line:
                    break
                
                line_lower = line.lower().strip()
                
                # 按照backup文件规范检测各种错误
                if "network is unreachable" in line_lower:
                    self._update_ping_status("网络不可达", "red")
                elif "destination host unreachable" in line_lower:
                    self._update_ping_status("网络不可达", "red")
                elif "unknown host" in line_lower or "name or service not known" in line_lower:
                    self._update_ping_status("DNS解析失败", "red")
                elif "bad address" in line_lower:
                    self._update_ping_status("DNS解析失败", "red")
                elif "time to live exceeded" in line_lower:
                    self._update_ping_status("TTL超限", "orange")
                elif "request timeout" in line_lower or "timeout" in line_lower:
                    self._update_ping_status("请求超时", "orange")
                elif "sendmsg:" in line_lower or "sendto:" in line_lower:
                    # 检测到sendmsg/sendto错误，通常是网络中断
                    if "network is unreachable" in line_lower:
                        self._update_ping_status("网络不可达", "red")
                    else:
                        self._update_ping_status("网络异常", "red")
                        
        except Exception as e:
            print(f"[DEBUG] 读取ping stderr异常: {str(e)}")
    
    def _update_ping_status(self, status_text, color):
        """更新Ping状态显示"""
        try:
            if hasattr(self.app.ui, 'network_ping_status_label'):
                self.app.ui.network_ping_status_label.config(text=status_text, foreground=color)
        except Exception as e:
            print(f"[DEBUG] 更新Ping状态失败: {str(e)}")
