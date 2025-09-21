#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络信息管理模块
负责获取和显示设备网络信息
"""

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
from datetime import datetime

MAXINT = 2147483647

class NetworkInfoManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_running = False
        self.network_info_thread = None
        self.is_ping_running = False
        self.ping_thread = None
        self.ping_process = None
        self.network_info_data = {
            'SIM1': {
                'LTE': {
                    'Band': '',
                    'arfcn': '',
                    'PCI': '',
                    'rssi': '',
                    'rsrp': '',
                    'rsrq': '',
                    'rssnr': ''
                },
                'NR': {
                    'Band': '',
                    'arfcn': '',
                    'PCI': '',
                    'ssRsrp': '',
                    'ssRsrq': '',
                    'ssSinr': '',
                    'rssnr': ''
                }
            },
            'SIM2': {
                'LTE': {
                    'Band': '',
                    'arfcn': '',
                    'PCI': '',
                    'rssi': '',
                    'rsrp': '',
                    'rsrq': '',
                    'rssnr': ''
                },
                'NR': {
                    'Band': '',
                    'arfcn': '',
                    'PCI': '',
                    'ssRsrp': '',
                    'ssRsrq': '',
                    'ssSinr': '',
                    'rssnr': ''
                }
            },
            'WIFI': {
                'SSID': '',
                'BSSID': '',
                'RSSI': '',
                'Freq': '',
                'State': ''
            }
        }
        
        # 正则表达式模式
        self.SIG_BLOCK_RE = re.compile(r"mSignalStrength=SignalStrength:\{", re.DOTALL)
        self.PRIMARY_RE = re.compile(r"primary=(?P<primary>\w+)")
        
        self.LTE_SIG_RE = re.compile(
            r"CellSignalStrengthLte:.*?rssi=(?P<rssi>-?\d+|%d).*?rsrp=(?P<rsrp>-?\d+|%d).*?rsrq=(?P<rsrq>-?\d+|%d).*?rssnr=(?P<rssnr>-?\d+|%d).*?ta=(?P<ta>-?\d+|%d).*?level=(?P<level>-?\d+)"
            % (MAXINT, MAXINT, MAXINT, MAXINT, MAXINT),
            re.DOTALL,
        )
        
        self.NR_SIG_RE = re.compile(
            r"CellSignalStrengthNr:\{.*?ssRsrp\s*=\s*(?P<ssrsrp>-?\d+|%d).*?ssRsrq\s*=\s*(?P<ssrsrq>-?\d+|%d).*?ssSinr\s*=\s*(?P<sssinr>-?\d+|%d).*?level\s*=\s*(?P<level>-?\d+)"
            % (MAXINT, MAXINT, MAXINT),
            re.DOTALL,
        )
        
        self.LTE_ID_RE = re.compile(
            r"CellIdentityLte:\{.*?mPci=(?P<pci>\d+).*?mTac=(?P<tac>\d+).*?mEarfcn=(?P<earfcn>\d+).*?mBands=\[(?P<bands>[^\]]*)\].*?mMcc=(?P<mcc>\d+).*?mMnc=(?P<mnc>\d+)",
            re.DOTALL,
        )
        
        self.NR_ID_RE = re.compile(
            r"CellIdentityNr:\{.*?mPci\s*=\s*(?P<pci>\d+).*?mTac\s*=\s*(?P<tac>\d+).*?mNrArfcn\s*=\s*(?P<nrarfcn>\d+).*?mBands\s*=\s*\[(?P<bands>[^\]]*)\].*?mMcc\s*=\s*(?P<mcc>null|\d+).*?mMnc\s*=\s*(?P<mnc>null|\d+).*?mNci\s*=\s*(?P<nci>\d+)",
            re.DOTALL,
        )
        
        self.REG_FLAG_RE = re.compile(r"mRegistered=(?P<yesno>YES|NO)")
        
        # WiFi正则表达式
        self.WIFI_BLOCK_RES = [
            re.compile(r"mWifiInfo\s*=\s*WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
            re.compile(r"WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
        ]
        
        self.SSID_RE_LIST = [
            re.compile(r'SSID:\s*"(?P<ssid>[^"]*)"'),
            re.compile(r"SSID:\s*(?P<ssid><unknown ssid>|[^\s,}]+)"),
            re.compile(r"mSSID:\s*SSID\{(?P<ssid>[^}]*)\}"),
        ]
        
        self.RSSI_RE_LIST = [
            re.compile(r"RSSI:\s*(?P<rssi>-?\d+)"), 
            re.compile(r"mRssi=\s*(?P<rssi>-?\d+)")
        ]
        
        self.BSSID_RE = re.compile(r"BSSID:\s*(?P<bssid>[0-9a-fA-F:]{11,})")
        self.LINKSPD_RE = re.compile(r"LinkSpeed:\s*(?P<ls>\d+)\s*Mbps")
        self.FREQ_RE = re.compile(r"Frequency:\s*(?P<freq>\d+)")
        self.SUPPL_RE = re.compile(r"Supplicant state:\s*(?P<state>\w+)", re.IGNORECASE)
    
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
                time.sleep(1)
                
            except Exception as e:
                print(f"获取网络信息时发生错误: {e}")
                time.sleep(2)
    
    def _run_adb(self, cmd):
        """运行ADB命令"""
        try:
            result = subprocess.run(["adb", "-s", self.app.selected_device.get().strip(), "shell"] + cmd, 
                                  capture_output=True, text=True, timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            print(f"ADB命令执行失败: {e}")
        return ""
    
    def _to_int(self, v):
        """转换为整数，处理MAXINT"""
        if v is None:
            return None
        try:
            iv = int(v)
            return None if iv == MAXINT else iv
        except:
            return None
    
    def _val_ok(self, v):
        """检查值是否有效"""
        return v is not None
    
    def _split_segments(self, raw):
        """按每个 mSignalStrength 起点分段"""
        starts = [m.start() for m in self.SIG_BLOCK_RE.finditer(raw)]
        if not starts:
            return []
        bounds = []
        for i, s in enumerate(starts):
            e = starts[i+1] if i+1 < len(starts) else len(raw)
            bounds.append(raw[s:e])
        return bounds
    
    def _parse_signal_from_segment(self, seg):
        """从段内解析 mSignalStrength 的 LTE/NR 数值 + primary"""
        primary = None
        mpri = self.PRIMARY_RE.search(seg)
        if mpri:
            primary = mpri.group("primary")

        lte = nr = None
        ml = self.LTE_SIG_RE.search(seg)
        if ml:
            lte = {k: self._to_int(ml.group(k)) for k in ("rssi", "rsrp", "rsrq", "rssnr", "ta", "level")}
            if not any(self._val_ok(v) for v in lte.values()):
                lte = None

        mn = self.NR_SIG_RE.search(seg)
        if mn:
            nr = {
                "ssRsrp": self._to_int(mn.group("ssrsrp")),
                "ssRsrq": self._to_int(mn.group("ssrsrq")),
                "ssSinr": self._to_int(mn.group("sssinr")),
                "level": self._to_int(mn.group("level"))
            }
            if not any(self._val_ok(v) for v in (nr["ssRsrp"], nr["ssRsrq"], nr["ssSinr"])):
                nr = None

        return {"primary": primary, "lte": lte, "nr": nr}
    
    def _iter_cellinfo_chunks(self, seg, kind="NR"):
        """粗切片：从 'CellInfoNr:{' 或 'CellInfoLte:{' 到下一个 CellInfo/Signal/Carrier 标记"""
        start_tag = "CellInfoNr:{" if kind == "NR" else "CellInfoLte:{"
        i = 0
        while True:
            s = seg.find(start_tag, i)
            if s < 0:
                break
            # 下一个边界
            nexts = []
            for tag in ("CellInfoNr:{", "CellInfoLte:{", "mCarrierRoaming", "mSignalStrength=", "mPhysicalChannelConfigs="):
                p = seg.find(tag, s+1)
                if p != -1:
                    nexts.append(p)
            e = min(nexts) if nexts else len(seg)
            yield seg[s:e]
            i = s + 1
    
    def _parse_cellinfo_from_segment(self, seg):
        """返回 (best_nr, best_lte)，优先 registered=YES；否则按 RSRP 最大"""
        nrs, ltes = [], []

        for chunk in self._iter_cellinfo_chunks(seg, "NR"):
            reg = self.REG_FLAG_RE.search(chunk)
            idm = self.NR_ID_RE.search(chunk)
            sgm = self.NR_SIG_RE.search(chunk)
            entry = {
                "type": "NR",
                "registered": (reg and reg.group("yesno") == "YES"),
                "pci": self._to_int(idm.group("pci")) if idm else None,
                "tac": self._to_int(idm.group("tac")) if idm else None,
                "nrarfcn": self._to_int(idm.group("nrarfcn")) if idm else None,
                "bands": [b.strip() for b in (idm.group("bands") if idm else "").split(",")] if idm else [],
                "mcc": None if not idm or idm.group("mcc") in (None, "null") else idm.group("mcc"),
                "mnc": None if not idm or idm.group("mnc") in (None, "null") else idm.group("mnc"),
                "nci": self._to_int(idm.group("nci")) if idm else None,
                "ssRsrp": self._to_int(sgm.group("ssrsrp")) if sgm else None,
                "ssRsrq": self._to_int(sgm.group("ssrsrq")) if sgm else None,
                "ssSinr": self._to_int(sgm.group("sssinr")) if sgm else None,
                "level": self._to_int(sgm.group("level")) if sgm else None,
            }
            if any(self._val_ok(entry[k]) for k in ("ssRsrp", "ssRsrq", "ssSinr")):
                nrs.append(entry)

        for chunk in self._iter_cellinfo_chunks(seg, "LTE"):
            reg = self.REG_FLAG_RE.search(chunk)
            idm = self.LTE_ID_RE.search(chunk)
            sgm = self.LTE_SIG_RE.search(chunk)
            entry = {
                "type": "LTE",
                "registered": (reg and reg.group("yesno") == "YES"),
                "pci": self._to_int(idm.group("pci")) if idm else None,
                "tac": self._to_int(idm.group("tac")) if idm else None,
                "earfcn": self._to_int(idm.group("earfcn")) if idm else None,
                "bands": [b.strip() for b in (idm.group("bands") if idm else "").split(",")] if idm else [],
                "mcc": idm.group("mcc") if idm else None,
                "mnc": idm.group("mnc") if idm else None,
                "rssi": self._to_int(sgm.group("rssi")) if sgm else None,
                "rsrp": self._to_int(sgm.group("rsrp")) if sgm else None,
                "rsrq": self._to_int(sgm.group("rsrq")) if sgm else None,
                "rssnr": self._to_int(sgm.group("rssnr")) if sgm else None,
                "ta": self._to_int(sgm.group("ta")) if sgm else None,
                "level": self._to_int(sgm.group("level")) if sgm else None,
            }
            if any(self._val_ok(entry[k]) for k in ("rsrp", "rsrq", "rssnr", "rssi")):
                ltes.append(entry)

        def pick_best(items, is_nr):
            regs = [x for x in items if x.get("registered")]
            if regs:
                return regs[0]
            key = (lambda x: x.get("ssRsrp")) if is_nr else (lambda x: x.get("rsrp"))
            cand = [x for x in items if self._val_ok(key(x))]
            if cand:
                return sorted(cand, key=key, reverse=True)[0]
            return items[0] if items else None

        return pick_best(nrs, True), pick_best(ltes, False)
    
    def _parse_wifi(self, raw_wifi):
        """解析WiFi信息"""
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

        ssid_m = first_match(txt, self.SSID_RE_LIST)
        rssi_m = first_match(txt, self.RSSI_RE_LIST)
        bssid_m = self.BSSID_RE.search(txt) or {}
        link_m = self.LINKSPD_RE.search(txt) or {}
        freq_m = self.FREQ_RE.search(txt) or {}
        supp_m = self.SUPPL_RE.search(txt) or {}

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
        wifi["connected"] = (wifi["ssid"] is not None) and (wifi["rssi"] is not None)
        return wifi
    
    def _get_network_snapshot(self, device):
        """获取网络信息快照"""
        try:
            # 重置所有数据
            for sim in ['SIM1', 'SIM2']:
                for tech in ['LTE', 'NR']:
                    for key in self.network_info_data[sim][tech]:
                        self.network_info_data[sim][tech][key] = ''
            
            for key in self.network_info_data['WIFI']:
                self.network_info_data['WIFI'][key] = ''
            
            # 获取telephony信息
            tel = self._run_adb(["dumpsys", "telephony.registry"])
            if not tel:
                return
            
            # 获取WiFi信息
            wifi_raw = self._run_adb(["dumpsys", "wifi"])
            wifi = self._parse_wifi(wifi_raw)
            
            # 更新WiFi信息
            self.network_info_data['WIFI']['SSID'] = str(wifi.get('ssid', ''))
            self.network_info_data['WIFI']['BSSID'] = str(wifi.get('bssid', ''))
            self.network_info_data['WIFI']['RSSI'] = str(wifi.get('rssi', ''))
            self.network_info_data['WIFI']['Freq'] = str(wifi.get('freqMHz', ''))
            self.network_info_data['WIFI']['State'] = str(wifi.get('state', ''))
            
            # 分段处理SIM信息
            segments = self._split_segments(tel)
            for i, seg in enumerate(segments[:2]):  # 最多处理2个SIM
                sim_key = f'SIM{i+1}'
                
                sig = self._parse_signal_from_segment(seg)
                best_nr, best_lte = self._parse_cellinfo_from_segment(seg)
                
                # 更新LTE信息
                if best_lte:
                    self.network_info_data[sim_key]['LTE']['PCI'] = str(best_lte.get('pci', '')) if best_lte.get('pci') else ''
                    self.network_info_data[sim_key]['LTE']['arfcn'] = str(best_lte.get('earfcn', '')) if best_lte.get('earfcn') else ''
                    self.network_info_data[sim_key]['LTE']['rssi'] = str(best_lte.get('rssi', '')) if best_lte.get('rssi') else ''
                    self.network_info_data[sim_key]['LTE']['rsrp'] = str(best_lte.get('rsrp', '')) if best_lte.get('rsrp') else ''
                    self.network_info_data[sim_key]['LTE']['rsrq'] = str(best_lte.get('rsrq', '')) if best_lte.get('rsrq') else ''
                    self.network_info_data[sim_key]['LTE']['rssnr'] = str(best_lte.get('rssnr', '')) if best_lte.get('rssnr') else ''
                    self.network_info_data[sim_key]['LTE']['registered'] = best_lte.get('registered', None)
                    
                    if best_lte.get('bands'):
                        self.network_info_data[sim_key]['LTE']['Band'] = str(best_lte['bands'][0])
                    else:
                        self.network_info_data[sim_key]['LTE']['Band'] = ''
                
                # 更新NR信息
                if best_nr:
                    self.network_info_data[sim_key]['NR']['PCI'] = str(best_nr.get('pci', '')) if best_nr.get('pci') else ''
                    self.network_info_data[sim_key]['NR']['arfcn'] = str(best_nr.get('nrarfcn', '')) if best_nr.get('nrarfcn') else ''
                    self.network_info_data[sim_key]['NR']['ssRsrp'] = str(best_nr.get('ssRsrp', '')) if best_nr.get('ssRsrp') else ''
                    self.network_info_data[sim_key]['NR']['ssRsrq'] = str(best_nr.get('ssRsrq', '')) if best_nr.get('ssRsrq') else ''
                    self.network_info_data[sim_key]['NR']['ssSinr'] = str(best_nr.get('ssSinr', '')) if best_nr.get('ssSinr') else ''
                    self.network_info_data[sim_key]['NR']['rssnr'] = str(best_nr.get('level', '')) if best_nr.get('level') else ''
                    self.network_info_data[sim_key]['NR']['registered'] = best_nr.get('registered', None)
                    
                    if best_nr.get('bands'):
                        self.network_info_data[sim_key]['NR']['Band'] = str(best_nr['bands'][0])
                    else:
                        self.network_info_data[sim_key]['NR']['Band'] = ''
                
                # 如果信号强度信息可用，优先使用
                if sig.get('lte'):
                    lte_sig = sig['lte']
                    if self._val_ok(lte_sig.get('rssi')):
                        self.network_info_data[sim_key]['LTE']['rssi'] = str(lte_sig['rssi'])
                    if self._val_ok(lte_sig.get('rsrp')):
                        self.network_info_data[sim_key]['LTE']['rsrp'] = str(lte_sig['rsrp'])
                    if self._val_ok(lte_sig.get('rsrq')):
                        self.network_info_data[sim_key]['LTE']['rsrq'] = str(lte_sig['rsrq'])
                    if self._val_ok(lte_sig.get('rssnr')):
                        self.network_info_data[sim_key]['LTE']['rssnr'] = str(lte_sig['rssnr'])
                
                if sig.get('nr'):
                    nr_sig = sig['nr']
                    if self._val_ok(nr_sig.get('ssRsrp')):
                        self.network_info_data[sim_key]['NR']['ssRsrp'] = str(nr_sig['ssRsrp'])
                    if self._val_ok(nr_sig.get('ssRsrq')):
                        self.network_info_data[sim_key]['NR']['ssRsrq'] = str(nr_sig['ssRsrq'])
                    if self._val_ok(nr_sig.get('ssSinr')):
                        self.network_info_data[sim_key]['NR']['ssSinr'] = str(nr_sig['ssSinr'])
                    if self._val_ok(nr_sig.get('level')):
                        self.network_info_data[sim_key]['NR']['rssnr'] = str(nr_sig['level'])
                        
        except Exception as e:
            print(f"获取网络快照失败: {e}")
    
    
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
        """创建基于Treeview的紧凑网络信息表格"""
        # 清空现有内容
        for widget in self.app.ui.network_info_frame.winfo_children():
            widget.destroy()
        
        # 创建主框架
        main_frame = ttk.Frame(self.app.ui.network_info_frame)
        main_frame.pack(fill=tk.X, expand=False, padx=2, pady=2)
        main_frame.columnconfigure(0, weight=1)
        
        # 定义列配置（按照spec.json）
        columns = [
            ('SIM', 42, 'center'),
            ('RAT', 42, 'center'),
            ('Band', 50, 'center'),
            ('CH', 64, 'center'),
            ('PCI', 50, 'center'),
            ('RSRP', 64, 'e'),
            ('RSRQ', 64, 'e'),
            ('SINR', 58, 'e'),
            ('RSSI', 58, 'e'),
            ('CA', 40, 'e'),
            ('NOTE', 160, 'w')
        ]
        
        # 创建Treeview
        self.network_tree = ttk.Treeview(main_frame, columns=[col[0] for col in columns], show='headings', height=5)
        
        # 配置列标题和宽度
        for col_id, width, anchor in columns:
            self.network_tree.heading(col_id, text=col_id)
            if col_id == 'NOTE':
                # NOTE列允许拉伸
                self.network_tree.column(col_id, width=width, anchor=anchor, minwidth=width, stretch=tk.YES)
            else:
                self.network_tree.column(col_id, width=width, anchor=anchor, minwidth=width)
        
        # 设置紧凑样式
        style = ttk.Style()
        style.configure("Compact.Treeview", font=('Arial', 9), rowheight=16)
        style.configure("Compact.Treeview.Heading", font=('Arial', 9, 'bold'))
        self.network_tree.configure(style="Compact.Treeview")
        
        # 创建垂直滚动条
        v_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.network_tree.yview)
        self.network_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 创建水平滚动条
        h_scrollbar = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.network_tree.xview)
        self.network_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局 - 不使用垂直拉伸
        self.network_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 初始化行ID存储
        self.network_row_ids = {}
    
    def _update_network_data(self):
        """更新Treeview中的网络数据"""
        try:
            if not hasattr(self, 'network_tree'):
                return
            
            # 清除现有数据
            for item in self.network_tree.get_children():
                self.network_tree.delete(item)
            
            # 准备所有行数据
            rows_data = []
            
            # SIM1 LTE
            sim1_lte = self.network_info_data['SIM1']['LTE']
            if any(sim1_lte[key] for key in ['Band', 'arfcn', 'PCI', 'rssi', 'rsrp', 'rsrq', 'rssnr']):
                # 检查是否已注册
                if sim1_lte.get('registered') == False:
                    # 未注册，显示为缓存状态
                    note = self._generate_cellular_note('SIM1', 'LTE', sim1_lte) + " (缓存)"
                    rows_data.append([
                        'SIM1', 'LTE', 
                        '-', '-', '-', '-', '-', '-', '-', '-', note
                    ])
                else:
                    # 已注册或状态未知，显示实际数据
                    note = self._generate_cellular_note('SIM1', 'LTE', sim1_lte)
                    rows_data.append([
                        'SIM1', 'LTE', 
                        sim1_lte.get('Band', ''),
                        sim1_lte.get('arfcn', ''),
                        sim1_lte.get('PCI', ''),
                        sim1_lte.get('rsrp', ''),
                        sim1_lte.get('rsrq', ''),
                        sim1_lte.get('rssnr', ''),  # SINR for LTE
                        sim1_lte.get('rssi', ''),
                        '',  # TA for LTE (not implemented yet)
                        note
                    ])
            
            # SIM1 NR
            sim1_nr = self.network_info_data['SIM1']['NR']
            if any(sim1_nr[key] for key in ['Band', 'arfcn', 'PCI', 'ssRsrp', 'ssRsrq', 'ssSinr', 'rssnr']):
                # 检查是否已注册
                if sim1_nr.get('registered') == False:
                    # 未注册，显示为缓存状态
                    note = self._generate_cellular_note('SIM1', 'NR', sim1_nr) + " (缓存)"
                    rows_data.append([
                        'SIM1', 'NR',
                        '-', '-', '-', '-', '-', '-', '-', '-', note
                    ])
                else:
                    # 已注册或状态未知，显示实际数据
                    note = self._generate_cellular_note('SIM1', 'NR', sim1_nr)
                    rows_data.append([
                        'SIM1', 'NR',
                        sim1_nr.get('Band', ''),
                        sim1_nr.get('arfcn', ''),
                        sim1_nr.get('PCI', ''),
                        sim1_nr.get('ssRsrp', ''),
                        sim1_nr.get('ssRsrq', ''),
                        sim1_nr.get('ssSinr', ''),  # SINR for NR
                        '',  # RSSI not available for NR
                        '',  # TA not available for NR
                        note
                    ])
            
            # SIM2 LTE
            sim2_lte = self.network_info_data['SIM2']['LTE']
            if any(sim2_lte[key] for key in ['Band', 'arfcn', 'PCI', 'rssi', 'rsrp', 'rsrq', 'rssnr']):
                # 检查是否已注册
                if sim2_lte.get('registered') == False:
                    # 未注册，显示为缓存状态
                    note = self._generate_cellular_note('SIM2', 'LTE', sim2_lte) + " (缓存)"
                    rows_data.append([
                        'SIM2', 'LTE',
                        '-', '-', '-', '-', '-', '-', '-', '-', note
                    ])
                else:
                    # 已注册或状态未知，显示实际数据
                    note = self._generate_cellular_note('SIM2', 'LTE', sim2_lte)
                    rows_data.append([
                        'SIM2', 'LTE',
                        sim2_lte.get('Band', ''),
                        sim2_lte.get('arfcn', ''),
                        sim2_lte.get('PCI', ''),
                        sim2_lte.get('rsrp', ''),
                        sim2_lte.get('rsrq', ''),
                        sim2_lte.get('rssnr', ''),  # SINR for LTE
                        sim2_lte.get('rssi', ''),
                        '',  # TA for LTE (not implemented yet)
                        note
                    ])
            
            # SIM2 NR
            sim2_nr = self.network_info_data['SIM2']['NR']
            if any(sim2_nr[key] for key in ['Band', 'arfcn', 'PCI', 'ssRsrp', 'ssRsrq', 'ssSinr', 'rssnr']):
                # 检查是否已注册
                if sim2_nr.get('registered') == False:
                    # 未注册，显示为缓存状态
                    note = self._generate_cellular_note('SIM2', 'NR', sim2_nr) + " (缓存)"
                    rows_data.append([
                        'SIM2', 'NR',
                        '-', '-', '-', '-', '-', '-', '-', '-', note
                    ])
                else:
                    # 已注册或状态未知，显示实际数据
                    note = self._generate_cellular_note('SIM2', 'NR', sim2_nr)
                    rows_data.append([
                        'SIM2', 'NR',
                        sim2_nr.get('Band', ''),
                        sim2_nr.get('arfcn', ''),
                        sim2_nr.get('PCI', ''),
                        sim2_nr.get('ssRsrp', ''),
                        sim2_nr.get('ssRsrq', ''),
                        sim2_nr.get('ssSinr', ''),  # SINR for NR
                        '',  # RSSI not available for NR
                        '',  # TA not available for NR
                        note
                    ])
            
            # WiFi
            wifi = self.network_info_data['WIFI']
            if wifi.get('SSID') or wifi.get('RSSI'):
                note = self._generate_wifi_note(wifi)
                rows_data.append([
                    'Wi-Fi', 'WLAN',
                    '',  # Band
                    '',  # CH
                    '',  # PCI
                    '',  # RSRP
                    '',  # RSRQ
                    '',  # SINR
                    wifi.get('RSSI', ''),
                    '',  # CA
                    note
                ])
            
            # 插入数据到Treeview
            for row_data in rows_data:
                self.network_tree.insert('', tk.END, values=row_data)
                    
        except Exception as e:
            print(f"更新网络数据失败: {e}")
    
    def _generate_cellular_note(self, sim, rat, data):
        """生成蜂窝网络备注信息"""
        note_parts = []
        
        # 如果有PLMN信息，可以在这里添加
        # if data.get('mcc') and data.get('mnc'):
        #     note_parts.append(f"PLMN={data['mcc']}{data['mnc']}")
        
        # 如果有频段信息，添加频段标签
        if data.get('Band'):
            band_label = f"B{data['Band']}" if rat == 'LTE' else f"n{data['Band']}"
            note_parts.append(band_label)
        
        # 如果有带宽信息，可以在这里添加CA信息
        # if data.get('dl_bw_khz'):
        #     note_parts.append(f"DL={data['dl_bw_khz']/1000:.0f}MHz")
        
        return '; '.join(note_parts) if note_parts else ''
    
    def _generate_wifi_note(self, wifi_data):
        """生成WiFi备注信息"""
        note_parts = []
        
        if wifi_data.get('SSID'):
            ssid = wifi_data['SSID']
            if len(ssid) > 15:
                ssid = ssid[:15] + '…'
            note_parts.append(f"SSID={ssid}")
        
        if wifi_data.get('Freq'):
            freq = wifi_data['Freq']
            if freq:
                note_parts.append(f"Freq={freq}MHz")
        
        return '; '.join(note_parts) if note_parts else ''
    
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
            # 设置停止标志
            self.is_ping_running = False
            
            # 终止ping进程
            if self.ping_process:
                try:
                    # 先尝试优雅终止
                    self.ping_process.terminate()
                    
                    # 等待进程结束，最多等待2秒
                    try:
                        self.ping_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # 如果进程没有在2秒内结束，强制杀死
                        self.ping_process.kill()
                        self.ping_process.wait()
                    
                    self.ping_process = None
                except Exception as e:
                    print(f"[DEBUG] 终止ping进程失败: {str(e)}")
                    # 即使终止失败，也要清理引用
                    self.ping_process = None
            
            # 更新UI
            self.app.ui.network_ping_button.config(text="Ping")
            
            # 更新状态显示
            if hasattr(self.app.ui, 'network_ping_status_label'):
                self.app.ui.network_ping_status_label.config(text="Ping已停止", foreground="gray")
            
        except Exception as e:
            print(f"[DEBUG] 停止Ping测试失败: {str(e)}")
    
    def _ping_worker(self, device):
        """Ping工作线程 - 按照network_ping_monitor_spec.json规范实现"""
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
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 启动两个独立的线程来监控stdout和stderr
            stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 主线程等待进程结束或停止标志
            while self.is_ping_running and self.ping_process:
                try:
                    # 检查进程是否还在运行
                    if self.ping_process.poll() is not None:
                        # 进程已结束
                        break
                    
                    # 短暂休眠，避免CPU占用过高
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"[DEBUG] Ping监控异常: {str(e)}")
                    break
            
            # 等待子线程结束
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
                
        except Exception as e:
            print(f"[DEBUG] Ping测试异常: {str(e)}")
            self._update_ping_status("Ping测试失败", "red")
        finally:
            # 清理状态
            self.is_ping_running = False
            self.ping_process = None
            
            # 更新UI
            if hasattr(self.app.ui, 'network_ping_button'):
                self.app.ui.network_ping_button.config(text="Ping")
    
    def _read_stdout(self):
        """读取stdout输出 - 检测成功响应"""
        try:
            while self.is_ping_running and self.ping_process:
                line = self.ping_process.stdout.readline()
                if not line:
                    break
                
                line_lower = line.lower().strip()
                
                # 检查成功响应 - 按照spec.json规范
                if "bytes from" in line_lower:
                    # 每次成功响应都更新状态为正常（支持状态切换）
                    self._update_ping_status("网络正常", "green")
                        
        except Exception as e:
            print(f"[DEBUG] 读取stdout异常: {str(e)}")
    
    def _read_stderr(self):
        """读取stderr输出 - 检测网络错误"""
        try:
            while self.is_ping_running and self.ping_process:
                line = self.ping_process.stderr.readline()
                if not line:
                    break
                
                line_lower = line.lower().strip()
                
                # 按照spec.json规范检测各种错误
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
            print(f"[DEBUG] 读取stderr异常: {str(e)}")
    
    def _update_ping_status(self, status_text, color):
        """更新Ping状态显示"""
        try:
            if hasattr(self.app.ui, 'network_ping_status_label'):
                self.app.ui.network_ping_status_label.config(text=status_text, foreground=color)
        except Exception as e:
            print(f"[DEBUG] 更新Ping状态失败: {str(e)}")
