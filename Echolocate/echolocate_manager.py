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
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk

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
            
            # 显示重命名对话框
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"diag_debug_{timestamp}"
            
            # 创建重命名对话框
            rename_dialog = tk.Toplevel(self.app.root)
            rename_dialog.title("重命名文件")
            rename_dialog.geometry("400x200")
            rename_dialog.resizable(False, False)
            rename_dialog.transient(self.app.root)
            rename_dialog.grab_set()
            
            # 居中显示
            rename_dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 200) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(rename_dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="重命名Echolocate文件", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 文件名输入
            ttk.Label(main_frame, text="文件夹名称:").pack(anchor=tk.W)
            name_var = tk.StringVar()
            name_var.set(default_name)
            name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
            name_entry.pack(pady=(5, 15))
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            result = [None]
            
            def on_confirm():
                folder_name = name_var.get().strip()
                if folder_name:
                    # 创建目标文件夹 - 使用统一的路径格式 c:\log\yyyymmdd
                    date_str = datetime.now().strftime("%Y%m%d")
                    target_dir = f"C:\\log\\{date_str}\\{folder_name}"
                    result[0] = target_dir
                    rename_dialog.destroy()
                else:
                    messagebox.showwarning("输入错误", "请输入文件夹名称")
            
            def on_cancel():
                rename_dialog.destroy()
            
            ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
            
            # 绑定回车键
            name_entry.bind('<Return>', lambda e: on_confirm())
            name_entry.focus()
            name_entry.select_range(0, tk.END)
            
            # 等待对话框关闭
            rename_dialog.wait_window()
            
            if not result[0]:
                messagebox.showinfo("取消", "用户取消操作")
                return False
            
            target_dir = result[0]
            
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
    
    def process_file_filter(self, keywords, filter_name, special_logic=None, source_file=None):
        """
        处理文件过滤的通用方法
        
        Args:
            keywords: 过滤关键字列表
            filter_name: 过滤名称，用于生成输出文件名
            special_logic: 特殊逻辑函数，用于处理特殊的过滤规则
            source_file: 源文件路径，如果为None则弹出文件选择对话框
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 如果没有提供源文件路径，则让用户选择文件
            if source_file is None:
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
                # messagebox.showinfo("成功", f"过滤完成！\n找到 {len(result_lines)} 行匹配内容\n文件已保存: {output_file}")
            except Exception as e:
                print(f"[DEBUG] 打开文件失败: {str(e)}")
                # messagebox.showinfo("成功", f"过滤完成！\n找到 {len(result_lines)} 行匹配内容\n文件已保存: {output_file}")
            
            return True
            
        except UnicodeDecodeError:
            messagebox.showerror("错误", "文件编码错误，请确保文件是UTF-8编码")
            return False
        except Exception as e:
            messagebox.showerror("错误", f"处理文件过滤失败: {str(e)}")
            return False
    def delete_echolocate_file(self):
        """删除手机上的Echolocate文件"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            
            # 执行删除命令
            try:
                cmd = f"adb -s {selected_device} shell rm -rf /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/*"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    messagebox.showinfo("成功", "Echolocate文件删除完成")
                    return True
                else:
                    messagebox.showerror("错误", f"删除文件失败\n{result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror("错误", "删除文件超时")
                return False
            except Exception as e:
                messagebox.showerror("错误", f"删除文件异常\n{str(e)}")
                return False
            
        except Exception as e:
            messagebox.showerror("错误", f"删除Echolocate文件失败: {str(e)}")
            return False
    def filter_callid(self, source_file=None):
        """过滤CallID"""
        keywords = ['CallID']
        return self.process_file_filter(keywords, 'CallID', source_file=source_file)
    
    def filter_callstate(self, source_file=None):
        """过滤CallState"""
        keywords = ['CallState']
        return self.process_file_filter(keywords, 'CallState', source_file=source_file)
    
    def filter_uicallstate(self, source_file=None):
        """过滤UICallState"""
        keywords = ['UICallState']
        return self.process_file_filter(keywords, 'UICallState', source_file=source_file)
    
    def filter_allcallstate(self, source_file=None):
        """过滤AllCallState - 查找UICallState或CallState"""
        keywords = ['UICallState', 'CallState']
        return self.process_file_filter(keywords, 'AllCallState', source_file=source_file)
    
    def filter_ims_signalling(self, source_file=None):
        """过滤IMSSignallingMessageLine1"""
        keywords = ['IMSSignallingMessageLine1']
        return self.process_file_filter(keywords, 'IMSSignallingMessageLine1', source_file=source_file)
    
    def filter_allcallflow(self):
        """过滤AllCallFlow - 查找UICallState、CallState或IMSSignallingMessageLine1"""
        keywords = ['UICallState', 'CallState', 'IMSSignallingMessageLine1']
        
        # 先让用户选择源文件
        source_file = filedialog.askopenfilename(
            title="选择要过滤的文件 - AllCallFlow",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            parent=self.app.root
        )
        
        if not source_file:
            messagebox.showinfo("取消", "用户取消文件选择")
            return False
        
        # 先执行主要的AllCallFlow过滤
        result = self.process_file_filter(keywords, 'AllCallFlow', source_file=source_file)
        
        # 额外调用其他过滤函数，传递相同的源文件路径
        try:
            self.filter_ims_signalling(source_file)
            self.filter_uicallstate(source_file)
            self.filter_callstate(source_file)
            self.filter_callid(source_file)
        except Exception as e:
            print(f"[DEBUG] 额外过滤函数调用失败: {str(e)}")
        
        return result

    def filter_voice_intent_classification(self):
        """voice_intent测试功能"""
        try:
            # 创建选择对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("Voice Intent测试选项")
            dialog.geometry("400x200")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            dialog.grab_set()
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 200) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="选择Voice Intent测试模式", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # 选项框架
            options_frame = ttk.Frame(main_frame)
            options_frame.pack(pady=(0, 20))
            
            # 按钮
            btn1 = ttk.Button(options_frame, text="开始测试",
                            command=lambda: self.start_voice_intent_test(dialog))
            btn1.pack(side=tk.LEFT, padx=10)
            
            btn2 = ttk.Button(options_frame, text="提取指定intent",
                            command=lambda: self.extract_voice_intent(dialog))
            btn2.pack(side=tk.LEFT, padx=10)
            
            # 取消按钮
            ttk.Button(main_frame, text="取消", command=dialog.destroy).pack(pady=(10, 0))
            
        except Exception as e:
            messagebox.showerror("错误", f"创建voice_intent测试对话框失败: {str(e)}")
    
    def start_voice_intent_test(self, dialog):
        """开始voice_intent测试"""
        try:
            dialog.destroy()  # 关闭选择对话框
            
            # 获取选中的设备
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 获取测试用例ID
            test_case_id = simpledialog.askstring(
                "输入测试用例ID",
                "请输入测试用例ID:",
                parent=self.app.root
            )
            
            if not test_case_id:
                messagebox.showinfo("取消", "用户取消测试")
                return False
            
            # 定义后台工作函数
            def voice_intent_test_worker(progress_var, status_label, progress_dialog):
                return self._execute_voice_intent_test_worker(device, test_case_id, progress_var, status_label, progress_dialog)
            
            # 定义完成回调
            def on_test_done(result):
                if result and result.get('success', False):
                    test_folder = result.get('test_folder', '')
                    messagebox.showinfo("测试完成", 
                        f"Voice Intent测试完成！\n\n"
                        f"测试文件夹: {test_folder}\n"
                        f"文件已自动打开。")
                else:
                    error_msg = result.get('error', '未知错误') if result else '测试失败'
                    messagebox.showerror("测试失败", f"Voice Intent测试失败: {error_msg}")
            
            # 定义错误回调
            def on_test_error(error):
                messagebox.showerror("错误", f"执行Voice Intent测试时发生错误: {str(error)}")
            
            # 使用模态执行器
            self.app.ui.run_with_modal(
                title="Voice Intent测试",
                worker_fn=voice_intent_test_worker,
                on_done=on_test_done,
                on_error=on_test_error
            )
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"开始voice_intent测试失败: {str(e)}")
            return False
    
    def extract_voice_intent(self, dialog):
        """提取指定voice_intent"""
        try:
            dialog.destroy()  # 关闭选择对话框
            
            # 让用户选择txt文件
            source_file = filedialog.askopenfilename(
                title="选择要提取intent的文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                parent=self.app.root
            )
            
            if not source_file:
                messagebox.showinfo("取消", "用户取消文件选择")
                return False
            
            # 显示intent类型选择对话框
            intent_types = [
                "diagandroid.phone.detailedCallState",
                "diagandroid.phone.UICallState", 
                "diagandroid.phone.imsSignallingMessage",
                "diagandroid.phone.AppTriggeredCall",
                "diagandroid.phone.CallSetting message",
                "diagandroid.phone.emergencyCallTimerState",
                "diagandroid.phone.carrierConfig",
                "diagandroid.phone.RTPDLStat",
                "diagandroid.phone.VoiceRadioBearerHandoverState"
            ]
            
            # 创建intent选择对话框
            intent_dialog = tk.Toplevel(self.app.root)
            intent_dialog.title("选择Intent类型")
            intent_dialog.geometry("500x400")
            intent_dialog.resizable(False, False)
            intent_dialog.transient(self.app.root)
            intent_dialog.grab_set()
            
            # 居中显示
            intent_dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 400) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(intent_dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="选择要提取的Intent类型", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 列表框架
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # 创建列表框
            listbox = tk.Listbox(list_frame, height=10)
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            for i, intent_type in enumerate(intent_types):
                listbox.insert(tk.END, f"{i+1}. {intent_type}")
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            result = [None]
            
            def on_extract():
                selection = listbox.curselection()
                if selection:
                    selected_intent = intent_types[selection[0]]
                    result[0] = selected_intent
                    intent_dialog.destroy()
                    
                    # 执行提取
                    self._execute_intent_extraction(source_file, selected_intent)
                else:
                    messagebox.showwarning("选择错误", "请选择一个Intent类型")
            
            ttk.Button(button_frame, text="提取", command=on_extract).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=intent_dialog.destroy).pack(side=tk.RIGHT)
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"提取voice_intent失败: {str(e)}")
            return False
    
    def _execute_voice_intent_test_worker(self, device, test_case_id, progress_var, status_label, progress_dialog):
        """执行voice_intent测试的后台工作函数"""
        try:
            import datetime
            import time
            
            # 更新进度
            status_label.config(text="清理旧文件...")
            progress_var.set(10)
            progress_dialog.update()
            
            # 删除旧文件
            cmd = f"adb -s {device} shell rm /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/*"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            # 更新进度
            status_label.config(text="请手动执行测试...")
            progress_var.set(20)
            progress_dialog.update()
            
            # 生成时间戳文件名
            now = datetime.datetime.now()
            filename = now.strftime("%Y%m%d_%H%M%S")
            
            # 更新进度对话框，添加确认按钮
            self.app.root.after(0, lambda: self._update_progress_dialog_for_confirmation(
                progress_dialog, status_label, progress_var, test_case_id
            ))
            
            # 等待用户确认（通过检查确认按钮是否被点击）
            max_wait_time = 3600  # 最多等待1小时
            wait_start_time = time.time()
            user_confirmed = False
            
            while time.time() - wait_start_time < max_wait_time:
                # 检查是否用户已确认
                if hasattr(progress_dialog, '_user_confirmed') and progress_dialog._user_confirmed:
                    user_confirmed = True
                    break
                time.sleep(1)
            
            if not user_confirmed:
                return {
                    'success': False,
                    'error': '等待用户确认超时，请重新开始测试。'
                }
            
            # 更新进度
            status_label.config(text="检查测试结果...")
            progress_var.set(50)
            progress_dialog.update()
            
            # 检查是否存在log_voice_intents文件
            # 首先列出目录中的所有文件
            list_cmd = f"adb -s {device} shell ls -l /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug/"
            list_result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            print(f"[DEBUG] 目录列表结果: {list_result.stdout}")
            print(f"[DEBUG] 目录列表错误: {list_result.stderr}")
            
            if list_result.returncode != 0:
                return {
                    'success': False,
                    'error': f'无法访问目录，错误: {list_result.stderr}'
                }
            
            # 检查是否包含log_voice_intents文件（支持多种可能的文件名）
            file_found = False
            possible_names = ['log_voice_intents', 'voice_intents', 'voice_intent']
            
            for name in possible_names:
                if name in list_result.stdout:
                    file_found = True
                    print(f"[DEBUG] 找到文件: {name}")
                    break
            
            if not file_found:
                return {
                    'success': False,
                    'error': f'未找到voice_intents相关文件。目录内容:\n{list_result.stdout}\n\n请确认测试已完成并生成了正确的日志文件。'
                }
            
            # 更新进度
            status_label.config(text="拉取日志文件...")
            progress_var.set(60)
            progress_dialog.update()
            
            # 创建目标文件夹 - 使用统一的路径格式 c:\log\yyyymmdd
            date_str = now.strftime("%Y%m%d")
            target_folder = f"C:\\log\\{date_str}\\{test_case_id}_{filename}"
            os.makedirs(target_folder, exist_ok=True)
            
            # 拉取echolocate文件
            pull_cmd1 = f"adb -s {device} pull /sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug \"{target_folder}\""
            pull_result1 = subprocess.run(pull_cmd1, shell=True, capture_output=True, text=True, timeout=120)
            
            # 更新进度
            status_label.config(text="拉取debuglogger文件...")
            progress_var.set(80)
            progress_dialog.update()
            
            # 拉取debuglogger文件
            pull_cmd2 = f"adb -s {device} pull /data/debuglogger \"{target_folder}\""
            pull_result2 = subprocess.run(pull_cmd2, shell=True, capture_output=True, text=True, timeout=120)
            
            # 更新进度
            status_label.config(text="测试完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            # 打开文件夹
            try:
                os.startfile(target_folder)
            except Exception as e:
                print(f"[DEBUG] 打开文件夹失败: {str(e)}")
            
            return {
                'success': True,
                'test_folder': target_folder
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '操作超时，请检查设备连接'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"执行voice_intent测试失败: {str(e)}"
            }
    
    def _execute_intent_extraction(self, source_file, intent_type):
        """执行intent提取"""
        try:
            # 获取文件目录和文件名
            file_dir = os.path.dirname(source_file)
            file_name = os.path.splitext(os.path.basename(source_file))[0]
            
            # 生成输出文件名
            output_file = os.path.join(file_dir, f"{intent_type.replace('.', '_').replace(' ', '_')}.txt")
            
            # 读取源文件
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 提取指定intent的内容
            result_lines = []
            found = False
            start_token = f"Action: {intent_type}"
            end_token = "--INTENT--"
            
            for line in lines:
                line = line.strip()
                
                if found:
                    result_lines.append(line + '\n')
                    if line == end_token:
                        found = False
                        result_lines.append('\n')
                
                if line == start_token:
                    found = True
                    result_lines.append(line + '\n')
            
            # 写入结果文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.writelines(result_lines)
            
            # 打开结果文件
            try:
                os.startfile(output_file)
                messagebox.showinfo("提取完成", 
                    f"Intent提取完成！\n\n"
                    f"找到 {len(result_lines)} 行匹配内容\n"
                    f"文件已保存: {output_file}\n"
                    f"文件已自动打开。")
            except Exception as e:
                print(f"[DEBUG] 打开文件失败: {str(e)}")
                messagebox.showinfo("提取完成", 
                    f"Intent提取完成！\n\n"
                    f"找到 {len(result_lines)} 行匹配内容\n"
                    f"文件已保存: {output_file}")
            
            return True
            
        except UnicodeDecodeError:
            messagebox.showerror("错误", "文件编码错误，请确保文件是UTF-8编码")
            return False
        except Exception as e:
            messagebox.showerror("错误", f"执行intent提取失败: {str(e)}")
            return False
    
    def _update_progress_dialog_for_confirmation(self, progress_dialog, status_label, progress_var, test_case_id):
        """更新进度对话框，添加确认按钮"""
        try:
            if not progress_dialog.winfo_exists():
                return
            
            # 初始化确认标志
            progress_dialog._user_confirmed = False
            
            # 更新状态文本
            status_label.config(text=f"测试用例 {test_case_id} - 请在完成测试后点击确认按钮")
            
            # 查找确认按钮（如果存在就更新，否则创建）
            if hasattr(progress_dialog, '_confirm_button'):
                # 按钮已存在，启用它
                progress_dialog._confirm_button.config(state=tk.NORMAL)
            else:
                # 创建确认按钮
                button_frame = None
                # 查找按钮框架
                for child in progress_dialog.winfo_children():
                    if isinstance(child, ttk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Frame):
                                button_frame = grandchild
                                break
                        if button_frame:
                            break
                
                if button_frame:
                    confirm_button = ttk.Button(
                        button_frame, 
                        text="测试已完成，确认",
                        command=lambda: self._confirm_test_completion(progress_dialog)
                    )
                    confirm_button.pack(side=tk.LEFT, padx=(0, 5))
                    progress_dialog._confirm_button = confirm_button
            
            progress_dialog.update()
            
        except Exception as e:
            print(f"[DEBUG] 更新确认对话框失败: {str(e)}")
    
    def _confirm_test_completion(self, progress_dialog):
        """确认测试完成"""
        try:
            # 设置确认标志
            progress_dialog._user_confirmed = True
            
            # 禁用确认按钮
            if hasattr(progress_dialog, '_confirm_button'):
                progress_dialog._confirm_button.config(state=tk.DISABLED, text="已确认，正在处理...")
            
            print(f"[DEBUG] 用户确认测试完成")
            
        except Exception as e:
            print(f"[DEBUG] 确认测试完成失败: {str(e)}")