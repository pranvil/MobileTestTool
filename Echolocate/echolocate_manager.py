#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Echolocate管理器
负责TMO Echolocate相关功能的实现和管理
"""

import subprocess
import os
import time
import glob
from datetime import datetime
from tkinter import messagebox, filedialog

class EcholocateManager:
    def __init__(self, app_instance):
        """
        初始化Echolocate管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        self.is_installed = False
        self.is_running = False
        
    def install_echolocate(self):
        """安装Echolocate到设备"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 在当前文件夹查找APK文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            apk_files = glob.glob(os.path.join(current_dir, "*.apk"))
            
            if apk_files:
                # 找到APK文件，安装所有APK
                messagebox.showinfo("安装", f"找到 {len(apk_files)} 个APK文件，开始安装...")
                
                for apk_file in apk_files:
                    try:
                        # 执行adb install命令
                        cmd = f"adb -s {selected_device} install -r \"{apk_file}\""
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            print(f"[DEBUG] APK安装成功: {os.path.basename(apk_file)}")
                        else:
                            print(f"[DEBUG] APK安装失败: {os.path.basename(apk_file)}, 错误: {result.stderr}")
                            messagebox.showerror("错误", f"APK安装失败: {os.path.basename(apk_file)}\n{result.stderr}")
                            return False
                            
                    except subprocess.TimeoutExpired:
                        messagebox.showerror("错误", f"APK安装超时: {os.path.basename(apk_file)}")
                        return False
                    except Exception as e:
                        messagebox.showerror("错误", f"APK安装异常: {os.path.basename(apk_file)}\n{str(e)}")
                        return False
            else:
                # 没有找到APK文件，让用户选择
                apk_file = filedialog.askopenfilename(
                    title="选择Echolocate APK文件",
                    filetypes=[("APK文件", "*.apk"), ("所有文件", "*.*")],
                    parent=self.app.root
                )
                
                if not apk_file:
                    messagebox.showinfo("取消", "用户取消安装")
                    return False
                
                try:
                    # 执行adb install命令
                    cmd = f"adb -s {selected_device} install -r \"{apk_file}\""
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode != 0:
                        messagebox.showerror("错误", f"APK安装失败\n{result.stderr}")
                        return False
                        
                except subprocess.TimeoutExpired:
                    messagebox.showerror("错误", "APK安装超时")
                    return False
                except Exception as e:
                    messagebox.showerror("错误", f"APK安装异常\n{str(e)}")
                    return False
            
            # 安装完成后启动应用
            try:
                cmd = f"adb -s {selected_device} shell am start -n com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.is_installed = True
                    messagebox.showinfo("成功", "Echolocate安装完成并已启动")
                    return True
                else:
                    messagebox.showwarning("警告", "APK安装成功但启动失败，请手动启动应用")
                    self.is_installed = True
                    return True
                    
            except Exception as e:
                messagebox.showwarning("警告", f"APK安装成功但启动失败: {str(e)}")
                self.is_installed = True
                return True
            
        except Exception as e:
            messagebox.showerror("错误", f"安装Echolocate失败: {str(e)}")
            return False
    
    def trigger_echolocate(self):
        """触发Echolocate功能"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 启动Echolocate应用
            try:
                cmd = f"adb -s {selected_device} shell am start -n com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.is_running = True
                    messagebox.showinfo("成功", "Echolocate应用已启动")
                    return True
                else:
                    messagebox.showerror("错误", f"启动Echolocate失败\n{result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror("错误", "启动Echolocate超时")
                return False
            except Exception as e:
                messagebox.showerror("错误", f"启动Echolocate异常\n{str(e)}")
                return False
            
        except Exception as e:
            messagebox.showerror("错误", f"触发Echolocate失败: {str(e)}")
            return False
    
    def pull_echolocate_file(self):
        """拉取Echolocate文件"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 创建目标文件夹
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_dir = f"C:\\log\\echolocate\\diag_debug_{timestamp}"
            
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"创建目标文件夹失败: {str(e)}")
                return False
            
            # 拉取文件
            try:
                cmd = f"adb -s {selected_device} pull /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug \"{target_dir}\""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    messagebox.showinfo("成功", f"Echolocate文件拉取完成\n保存位置: {target_dir}")
                    
                    # 打开文件夹
                    try:
                        os.startfile(target_dir)
                    except Exception as e:
                        print(f"[DEBUG] 打开文件夹失败: {str(e)}")
                        messagebox.showinfo("提示", f"文件已保存到: {target_dir}")
                    
                    return True
                else:
                    messagebox.showerror("错误", f"拉取文件失败\n{result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror("错误", "拉取文件超时")
                return False
            except Exception as e:
                messagebox.showerror("错误", f"拉取文件异常\n{str(e)}")
                return False
            
        except Exception as e:
            messagebox.showerror("错误", f"拉取Echolocate文件失败: {str(e)}")
            return False
    
    def get_filter_keywords(self, filter_type):
        """
        获取指定类型的过滤关键字
        
        Args:
            filter_type: 过滤类型 ('callstate', 'uicallstate', 'allcallstate', 'ims_signalling', 'allcallflow')
        
        Returns:
            str: 对应的过滤关键字
        """
        keywords_map = {
            'callstate': 'CallState',
            'uicallstate': 'UICallState', 
            'allcallstate': 'AllCallState',
            'ims_signalling': 'IMSSignallingMessageLine1',
            'allcallflow': 'AllCallFlow'
        }
        
        return keywords_map.get(filter_type, '')
    
    def apply_filter(self, filter_type):
        """
        应用指定的过滤
        
        Args:
            filter_type: 过滤类型
        """
        try:
            keywords = self.get_filter_keywords(filter_type)
            if not keywords:
                messagebox.showerror("错误", f"未知的过滤类型: {filter_type}")
                return False
            
            # 如果正在过滤中，先停止
            if self.app.is_running:
                self.app.stop_filtering()
            
            # 设置关键字并开始过滤
            self.app.filter_keyword.set(keywords)
            self.app.use_regex.set(True)
            self.app.start_filtering()
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"应用过滤失败: {str(e)}")
            return False
    
    def check_installation_status(self):
        """检查Echolocate安装状态"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                return False
            
            # 这里应该实现具体的检查逻辑
            # 例如：检查应用是否已安装、版本信息等
            return self.is_installed
            
        except Exception as e:
            print(f"[DEBUG] 检查安装状态失败: {str(e)}")
            return False
    
    def get_status_info(self):
        """获取Echolocate状态信息"""
        return {
            'installed': self.is_installed,
            'running': self.is_running,
            'device': self.app.selected_device.get()
        }
    
    def process_file_filter(self, keywords, filter_name, special_logic=None):
        """
        处理文件过滤的通用方法
        
        Args:
            keywords: 过滤关键字列表
            filter_name: 过滤名称，用于生成输出文件名
            special_logic: 特殊逻辑函数，用于处理特殊的过滤规则
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 让用户选择文件
            source_file = filedialog.askopenfilename(
                title=f"选择要过滤的文件 - {filter_name}",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                parent=self.app.root
            )
            
            if not source_file:
                messagebox.showinfo("取消", "用户取消文件选择")
                return False
            
            # 获取文件目录和文件名
            file_dir = os.path.dirname(source_file)
            file_name = os.path.splitext(os.path.basename(source_file))[0]
            
            # 生成输出文件名
            output_file = os.path.join(file_dir, f"{filter_name}.txt")
            
            # 打开源文件和目标文件
            with open(source_file, 'r', encoding='utf-8') as source_f:
                lines = source_f.readlines()
            
            # 查找包含关键字的行
            result_lines = []
            for line_number, line in enumerate(lines, 1):
                # 将行按空格分割成单词
                words = line.strip().split()
                
                # 检查是否匹配
                matched = False
                if special_logic:
                    # 使用特殊逻辑
                    matched = special_logic(words)
                else:
                    # 标准逻辑：检查关键字是否在单词列表中
                    matched = any(keyword in words for keyword in keywords)
                
                if matched:
                    # 移除(java.lang.String)
                    cleaned_line = line.replace('(java.lang.String)', '').strip()
                    result_lines.append(f"Line {line_number}: {cleaned_line}\n")
            
            # 将结果写入新文件
            with open(output_file, 'w', encoding='utf-8') as target_f:
                target_f.writelines(result_lines)
            
            # 打开生成的文件
            try:
                os.startfile(output_file)
                messagebox.showinfo("成功", f"过滤完成！\n找到 {len(result_lines)} 行匹配内容\n文件已保存: {output_file}")
            except Exception as e:
                print(f"[DEBUG] 打开文件失败: {str(e)}")
                messagebox.showinfo("成功", f"过滤完成！\n找到 {len(result_lines)} 行匹配内容\n文件已保存: {output_file}")
            
            return True
            
        except UnicodeDecodeError:
            messagebox.showerror("错误", "文件编码错误，请确保文件是UTF-8编码")
            return False
        except Exception as e:
            messagebox.showerror("错误", f"处理文件过滤失败: {str(e)}")
            return False
    
    def filter_callstate(self):
        """过滤CallState - 查找CallID或CallState ENDED"""
        def callid_logic(words):
            return 'CallID' in words or ('CallState' in words and 'ENDED' in words)
        
        return self.process_file_filter([], 'CallID', callid_logic)
    
    def filter_uicallstate(self):
        """过滤UICallState"""
        keywords = ['UICallState']
        return self.process_file_filter(keywords, 'UICallState')
    
    def filter_allcallstate(self):
        """过滤AllCallState - 查找UICallState或CallState"""
        keywords = ['UICallState', 'CallState']
        return self.process_file_filter(keywords, 'AllCallState')
    
    def filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        keywords = ['IMSSignallingMessageLine1']
        return self.process_file_filter(keywords, 'IMSSignallingMessageLine1')
    
    def filter_allcallflow(self):
        """过滤AllCallFlow - 查找UICallState、CallState或IMSSignallingMessageLine1"""
        keywords = ['UICallState', 'CallState', 'IMSSignallingMessageLine1']
        return self.process_file_filter(keywords, 'AllCallFlow')
