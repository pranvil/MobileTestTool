#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android ADB Logcat 关键字过滤工具 v2.0
支持正则表达式、大小写敏感、彩色显示和保存功能
重构版本 - 模块化设计
"""

import tkinter as tk
from tkinter import ttk

# 导入自定义模块
from ui_manager import UIManager
from Device_Control import DeviceManager, MTKLogManager, ScreenshotManager, VideoManager
from Device_Control.network_info_manager import NetworkInfoManager
from Device_Control.enable_telephony import TelephonyManager
from Log_Filter import LogProcessor, SearchManager, ADBLogManager
from Log_Filter.google_log import GoogleLogManager
from TMO_CC import PullCCManager, PushCCManager, ServerManager
from Echolocate.echolocate_manager import EcholocateManager

class LogcatFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手机测试辅助工具 v2.1")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 默认最大化窗口，确保用户能看到所有按钮
        try:
            self.root.state('zoomed')  # Windows上最大化窗口
        except:
            # 如果zoomed不支持，使用其他方法
            self.root.attributes('-zoomed', True)
        
        # 变量
        self.filter_keyword = tk.StringVar()
        self.use_regex = tk.BooleanVar()
        self.case_sensitive = tk.BooleanVar()
        self.color_highlight = tk.BooleanVar()
        self.is_running = False
        
        # 设备选择相关变量
        self.selected_device = tk.StringVar()
        self.available_devices = []
        
        # 设置默认值
        self.use_regex.set(True)
        self.case_sensitive.set(False)
        self.color_highlight.set(True)
        
        # 初始化各个管理器
        self.ui = UIManager(self.root, self)
        self.device_manager = DeviceManager(self)
        self.mtklog_manager = MTKLogManager(self)
        self.adblog_manager = ADBLogManager(self)
        self.google_log_manager = GoogleLogManager(self)
        self.network_info_manager = NetworkInfoManager(self)
        self.log_processor = LogProcessor(self)
        self.search_manager = SearchManager(self)
        self.screenshot_manager = ScreenshotManager(self)
        self.video_manager = VideoManager(self)
        self.tmo_cc_manager = PullCCManager(self)
        self.push_cc_manager = PushCCManager(self)
        self.server_manager = ServerManager(self)
        self.telephony_manager = TelephonyManager(self)
        self.echolocate_manager = EcholocateManager(self)
        
        # 初始化设备列表
        self.device_manager.refresh_devices()
        
        # 设置录制按钮引用
        self.video_manager.set_recording_button(self.ui.record_button)
    
    # 设备管理相关方法
    def refresh_devices(self):
        """刷新设备列表"""
        self.device_manager.refresh_devices()
    
    # MTKLOG相关方法
    def start_mtklog(self):
        """开启MTKLOG"""
        self.mtklog_manager.start_mtklog()
    
    def stop_and_export_mtklog(self):
        """停止并导出MTKLOG"""
        self.mtklog_manager.stop_and_export_mtklog()
    
    def delete_mtklog(self):
        """删除MTKLOG"""
        self.mtklog_manager.delete_mtklog()
    
    def set_sd_mode(self):
        """设置SD模式"""
        self.mtklog_manager.set_sd_mode()
    
    def set_usb_mode(self):
        """设置USB模式"""
        self.mtklog_manager.set_usb_mode()
    
    def install_mtklogger(self):
        """安装MTKLOGGER"""
        self.mtklog_manager.install_mtklogger()
    
    # ADBLOG相关方法
    def start_adblog(self):
        """开启adb log"""
        self.adblog_manager.start_adblog()
    
    def export_adblog(self):
        """停止adb log并导出"""
        self.adblog_manager.export_adblog()
    
    # 日志处理相关方法
    def start_filtering(self):
        """开始过滤日志"""
        self.log_processor.start_filtering()
    
    def stop_filtering(self):
        """停止过滤"""
        self.log_processor.stop_filtering()
    
    def clear_logs(self):
        """清空日志"""
        self.log_processor.clear_logs()
    
    def save_logs(self):
        """保存日志到文件"""
        self.log_processor.save_logs()
    
    def clear_device_logs(self):
        """清除设备日志缓存"""
        self.log_processor.clear_device_logs()
    
    def show_display_lines_dialog(self):
        """显示设置最大显示行数的对话框"""
        self.log_processor.show_display_lines_dialog()
    
    # 搜索相关方法
    def show_search_dialog(self, event=None):
        """显示搜索对话框"""
        self.search_manager.show_search_dialog(event)
    
    def find_next(self, event=None):
        """查找下一个匹配项"""
        self.search_manager.find_next(event)
    
    def find_previous(self, event=None):
        """查找上一个匹配项"""
        self.search_manager.find_previous(event)
    
    def take_screenshot(self):
        """截图"""
        self.screenshot_manager.take_screenshot()
    
    def toggle_recording(self):
        """切换录制状态"""
        self.video_manager.toggle_recording()
    
    def enable_telephony(self):
        """启用Telephony日志"""
        self.telephony_manager.enable_telephony_logs()

def main():
    """主函数"""
    root = tk.Tk()
    app = LogcatFilterApp(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_running:
            app.stop_filtering()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
