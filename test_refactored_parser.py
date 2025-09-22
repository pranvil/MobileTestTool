#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重构后的解析器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Network_info.telephony_parser import compute_rows_for_registry, COLS
from Network_info.network_info_manager import NetworkInfoManager

class MockApp:
    """模拟应用实例"""
    def __init__(self):
        self.selected_device = MockDevice()
        self.device_manager = MockDeviceManager()
        self.ui = MockUI()
        self.root = MockRoot()

class MockDevice:
    def get(self):
        return "test_device"

class MockDeviceManager:
    def validate_device_selection(self):
        return "test_device"

class MockUI:
    def __init__(self):
        self.network_info_frame = MockFrame()
        self.network_start_button = MockButton()
        self.network_ping_button = MockButton()
        self.network_ping_status_label = MockLabel()
        self.status_var = MockVar()

class MockFrame:
    def winfo_children(self):
        return []
    def destroy(self):
        pass

class MockButton:
    def config(self, **kwargs):
        pass

class MockLabel:
    def config(self, **kwargs):
        pass

class MockVar:
    def set(self, value):
        pass

class MockRoot:
    def after(self, delay, func):
        func()

def test_telephony_parser():
    """测试telephony_parser模块"""
    print("=== 测试 telephony_parser ===")
    
    # 测试COLS常量
    print(f"COLS: {COLS}")
    print(f"列数: {len(COLS)}")
    
    # 测试空数据
    empty_result = compute_rows_for_registry("")
    print(f"空数据结果: {len(empty_result)} 行")
    
    # 测试简单数据
    simple_data = """
    Phone Id=0
    mPhysicalChannelConfigs=[{mConnectionStatus=PrimaryServing,mCellBandwidthDownlinkKhz=20000,mCellBandwidthUplinkKhz=20000,mNetworkType=LTE,mFrequencyRange=LOW,mDownlinkChannelNumber=66500,mUplinkChannelNumber=66500,mContextIds=[],mPhysicalCellId=96,mBand=66,mDownlinkFrequency=2140,mUplinkFrequency=1950}]
    mSignalStrength=SignalStrength:{mLte=CellSignalStrengthLte: rssi=-65 rsrp=-98 rsrq=-12 rssnr=15 cqiTableIndex=1 cqi=15 ta=0 level=4}
    """
    
    result = compute_rows_for_registry(simple_data)
    print(f"简单数据结果: {len(result)} 行")
    
    for i, row in enumerate(result):
        print(f"  行{i+1}: {row}")
    
    return result

def test_network_manager():
    """测试NetworkInfoManager"""
    print("\n=== 测试 NetworkInfoManager ===")
    
    app = MockApp()
    manager = NetworkInfoManager(app)
    
    print(f"管理器初始化成功")
    print(f"Ping管理器: {manager.ping_manager}")
    print(f"WiFi解析器: {manager.wifi_parser}")
    
    # 测试test_with_dump_data方法
    test_data = """
    Phone Id=0
    mPhysicalChannelConfigs=[{mConnectionStatus=PrimaryServing,mCellBandwidthDownlinkKhz=20000,mCellBandwidthUplinkKhz=20000,mNetworkType=LTE,mFrequencyRange=LOW,mDownlinkChannelNumber=66500,mUplinkChannelNumber=66500,mContextIds=[],mPhysicalCellId=96,mBand=66,mDownlinkFrequency=2140,mUplinkFrequency=1950}]
    mSignalStrength=SignalStrength:{mLte=CellSignalStrengthLte: rssi=-65 rsrp=-98 rsrq=-12 rssnr=15 cqiTableIndex=1 cqi=15 ta=0 level=4}
    """
    
    # 创建临时测试文件
    with open("test_dump.txt", "w", encoding="utf-8") as f:
        f.write(test_data)
    
    try:
        result = manager.test_with_dump_data("test_dump.txt")
        print(f"测试结果: {len(result)} 行")
        
        for i, row in enumerate(result):
            print(f"  行{i+1}: {row}")
            
    finally:
        # 清理测试文件
        if os.path.exists("test_dump.txt"):
            os.remove("test_dump.txt")

def test_line_count():
    """检查代码行数"""
    print("\n=== 代码行数检查 ===")
    
    files_to_check = [
        "Network_info/telephony_parser.py",
        "Network_info/network_info_manager.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                non_empty_lines = [line for line in lines if line.strip()]
                print(f"{file_path}: {len(lines)} 行 (总行数), {len(non_empty_lines)} 行 (非空行)")
        else:
            print(f"{file_path}: 文件不存在")

if __name__ == "__main__":
    print("开始测试重构后的解析器...")
    
    try:
        # 测试telephony_parser
        test_telephony_parser()
        
        # 测试NetworkInfoManager
        test_network_manager()
        
        # 检查代码行数
        test_line_count()
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
