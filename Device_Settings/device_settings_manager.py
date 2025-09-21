#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备设置管理器
负责设置灭屏时间、合并MTKlog、MTKlog提取pcap等功能
"""

import subprocess
import os
import shutil
import zipfile
import glob
from datetime import datetime
from tkinter import messagebox, filedialog, simpledialog

class DeviceSettingsManager:
    def __init__(self, app_instance):
        """
        初始化设备设置管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        
    def set_screen_timeout(self):
        """设置灭屏时间"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 获取用户输入的灭屏时间（秒）
            timeout_seconds = simpledialog.askinteger(
                "设置灭屏时间",
                "请输入灭屏时间（秒）:\n"
                "0 = 永不灭屏",
                parent=self.app.root,
                minvalue=0,
                maxvalue=86400  # 最大24小时
            )
            
            if timeout_seconds is None:
                messagebox.showinfo("取消", "用户取消设置")
                return False
            
            # 转换为毫秒，如果输入0则设置为永不灭屏的值
            if timeout_seconds == 0:
                timeout_ms = 2147483647  # 32位有符号整数最大值，表示永不灭屏
            else:
                timeout_ms = timeout_seconds * 1000
            
            try:
                # 设置屏幕超时时间
                cmd = f"adb -s {selected_device} shell settings put system screen_off_timeout {timeout_ms}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    if timeout_seconds == 0:
                        messagebox.showinfo("成功", "屏幕超时已设置为永不灭屏")
                    else:
                        # 转换为更友好的显示格式
                        if timeout_seconds < 60:
                            display_text = f"{timeout_seconds} 秒"
                        elif timeout_seconds < 3600:
                            minutes = timeout_seconds // 60
                            seconds = timeout_seconds % 60
                            if seconds > 0:
                                display_text = f"{minutes} 分钟 {seconds} 秒"
                            else:
                                display_text = f"{minutes} 分钟"
                        else:
                            hours = timeout_seconds // 3600
                            minutes = (timeout_seconds % 3600) // 60
                            if minutes > 0:
                                display_text = f"{hours} 小时 {minutes} 分钟"
                            else:
                                display_text = f"{hours} 小时"
                        
                        messagebox.showinfo("成功", f"屏幕超时已设置为 {display_text}")
                    return True
                else:
                    messagebox.showerror("错误", f"设置屏幕超时失败: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror("错误", "设置屏幕超时超时")
                return False
            except Exception as e:
                messagebox.showerror("错误", f"设置屏幕超时异常: {str(e)}")
                return False
            
        except Exception as e:
            messagebox.showerror("错误", f"设置灭屏时间失败: {str(e)}")
            return False
    
    def merge_mtklog(self):
        """合并MTKlog文件 - 占位函数"""
        messagebox.showinfo("功能开发中", "合并MTKlog功能正在开发中，敬请期待！")
        return True
    
    def extract_pcap_from_mtklog(self):
        """从MTKlog中提取pcap文件 - 占位函数"""
        messagebox.showinfo("功能开发中", "MTKlog提取pcap功能正在开发中，敬请期待！")
        return True
    
    def _find_mtklog_files(self, directory):
        """查找MTKlog文件"""
        mtklog_files = []
        
        # 查找常见的MTKlog文件模式
        patterns = [
            "*.txt",
            "*mtklog*",
            "*log*",
            "*.log"
        ]
        
        for pattern in patterns:
            files = glob.glob(os.path.join(directory, pattern))
            mtklog_files.extend(files)
        
        # 去重并排序
        mtklog_files = sorted(list(set(mtklog_files)))
        
        # 过滤掉太小的文件（可能是空文件）
        mtklog_files = [f for f in mtklog_files if os.path.getsize(f) > 100]
        
        return mtklog_files
    
    def _extract_pcap_data(self, mtklog_file, output_dir):
        """从MTKlog中提取pcap数据"""
        pcap_files = []
        
        try:
            with open(mtklog_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 查找包含网络数据包信息的行
            packet_lines = []
            for line_num, line in enumerate(lines):
                # 查找包含IP地址、端口等网络信息的行
                if any(keyword in line.lower() for keyword in ['ip', 'tcp', 'udp', 'packet', 'frame']):
                    packet_lines.append((line_num, line.strip()))
            
            if not packet_lines:
                return []
            
            # 创建pcap文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pcap_file = os.path.join(output_dir, f"extracted_packets_{timestamp}.pcap")
            
            # 这里应该实现真正的pcap格式写入
            # 由于pcap格式比较复杂，这里先创建一个包含网络数据的文本文件
            with open(pcap_file.replace('.pcap', '.txt'), 'w', encoding='utf-8') as f:
                f.write("=== 从MTKlog提取的网络数据包信息 ===\n\n")
                f.write(f"源文件: {mtklog_file}\n")
                f.write(f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"找到的网络数据包行数: {len(packet_lines)}\n\n")
                
                for line_num, line in packet_lines[:100]:  # 显示前100条
                    f.write(f"行 {line_num}: {line}\n")
            
            pcap_files.append(pcap_file.replace('.pcap', '.txt'))
            
            # 如果有更多数据，可以创建多个文件
            if len(packet_lines) > 100:
                batch_size = 100
                for i in range(100, len(packet_lines), batch_size):
                    batch_num = i // batch_size + 1
                    batch_file = os.path.join(output_dir, f"extracted_packets_{timestamp}_batch{batch_num}.txt")
                    
                    with open(batch_file, 'w', encoding='utf-8') as f:
                        f.write(f"=== 网络数据包批次 {batch_num} ===\n\n")
                        for line_num, line in packet_lines[i:i+batch_size]:
                            f.write(f"行 {line_num}: {line}\n")
                    
                    pcap_files.append(batch_file)
            
            return pcap_files
            
        except Exception as e:
            print(f"[DEBUG] 提取pcap数据失败: {str(e)}")
            return []
    
    def merge_pcap(self):
        """合并PCAP文件 - 占位函数"""
        messagebox.showinfo("功能开发中", "合并PCAP功能正在开发中，敬请期待！")
        return True
    
    def extract_pcap_from_qualcomm_log(self):
        """从高通log提取pcap文件 - 占位函数"""
        messagebox.showinfo("功能开发中", "高通log提取pcap功能正在开发中，敬请期待！")
        return True
    
    def delete_bugreport(self):
        """删除bugreport文件 - 占位函数"""
        messagebox.showinfo("功能开发中", "删除bugreport功能正在开发中，敬请期待！")
        return True
