#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络信息管理模块 - 重构版本
按照 min_parser_refactor.json 规范重构
只负责IO+UI，调用telephony_parser进行纯解析
"""

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Dict, List, Optional, Any

# 导入解析模块
from .telephony_parser import compute_rows_for_registry, COLS
from .utilities_ping import PingManager
from .utilities_wifi_info import WifiInfoParser

class NetworkInfoManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_running = False
        self.network_info_thread = None
        self.rows_data = []  # List[Dict] - 解析后的行数据
        
        # 初始化工具模块
        self.ping_manager = PingManager(app_instance)
        self.wifi_parser = WifiInfoParser()
    
    
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
    
    def _get_network_snapshot(self, device: str):
        """获取网络信息快照 - 调用telephony_parser进行纯解析"""
        try:
            # 获取telephony.registry数据
            tel_raw = self._run_adb(["shell", "dumpsys", "telephony.registry"])
            if not tel_raw:
                return
            
            # 调用纯解析器
            self.rows_data = compute_rows_for_registry(tel_raw)
            
            # 获取WiFi信息
            try:
                wifi_raw = self._run_adb(["shell", "dumpsys", "wifi"])
                if wifi_raw:
                    wifi = self.wifi_parser.parse_wifi(wifi_raw)
                    # 将WiFi信息添加到行数据中
                    if wifi.get('connected'):
                        wifi_row = {
                            'SIM': 'WIFI',
                            'CC': 'WIFI',
                            'RAT': 'WIFI',
                            'BAND': wifi.get('band', ''),
                            'DL_ARFCN': wifi.get('freqMHz', 0),
                            'UL_ARFCN': 0,
                            'PCI': 0,
                            'RSRP': None,  # WIFI没有RSRP
                            'RSRQ': None,
                            'SINR': None,
                            'RSSI': wifi.get('rssi'),  # WIFI只有RSSI
                            'BW_DL': 0,
                            'BW_UL': 0,
                            'CA_ENDC': '',  # WIFI不需要CA_ENDC_Comb
                            'CQI': None,
                            'NOTE': f"SSID: {wifi.get('ssid', '')}"
                        }
                        self.rows_data.append(wifi_row)
            except Exception as e:
                print(f"获取WiFi信息失败: {e}")
                        
        except Exception as e:
            print(f"获取网络快照失败: {e}")
    
    
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
        
        # 定义列配置（使用COLS常量）
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
            ('CA_ENDC', 120, 'center'),
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
            
            # 插入行数据
            for row in self.rows_data:
                row_data = [
                    row.get('SIM', ''),
                    row.get('CC', ''),
                    row.get('RAT', ''),
                    row.get('BAND', ''),
                    str(row.get('DL_ARFCN', '')) if row.get('DL_ARFCN') else '',
                    str(row.get('UL_ARFCN', '')) if row.get('UL_ARFCN') else '',
                    str(row.get('PCI', '')) if row.get('PCI') else '',
                    str(row.get('RSRP', '')) if row.get('RSRP') is not None else '',
                    str(row.get('RSRQ', '')) if row.get('RSRQ') is not None else '',
                    str(row.get('SINR', '')) if row.get('SINR') is not None else '',
                    str(row.get('RSSI', '')) if row.get('RSSI') is not None else '',
                    str(row.get('BW_DL', '')) if row.get('BW_DL') else '',
                    str(row.get('BW_UL', '')) if row.get('BW_UL') else '',
                    row.get('CA_ENDC', ''),
                    str(row.get('CQI', '')) if row.get('CQI') is not None else '',
                    row.get('NOTE', '')
                ]
                self.network_tree.insert('', tk.END, values=row_data)
                    
        except Exception as e:
            print(f"更新网络数据失败: {e}")
    
    def test_with_dump_data(self, dump_file_path: str):
        """使用dump.txt测试数据 - 调用telephony_parser"""
        try:
            with open(dump_file_path, 'r', encoding='utf-8') as f:
                dump_data = f.read()
            
            # 调用纯解析器
            rows = compute_rows_for_registry(dump_data)
            
            print("=== 测试结果 ===")
            print(f"总行数: {len(rows)}")
            
            for i, row in enumerate(rows):
                rsrp = row.get('RSRP', 'None')
                print(f"  行{i+1}: {row['SIM']} {row['CC']} {row['RAT']} {row['BAND']} PCI={row['PCI']} RSRP={rsrp}")
            
            return rows
            
        except Exception as e:
            print(f"测试失败: {e}")
            return []
    
    # Ping相关方法 - 委托给PingManager
    def start_network_ping(self):
        """开始网络Ping测试"""
        self.ping_manager.start_network_ping()
    
    def stop_network_ping(self):
        """停止网络Ping测试"""
        self.ping_manager.stop_network_ping()
    
    @property
    def is_ping_running(self):
        """获取ping运行状态"""
        return self.ping_manager.is_ping_running
