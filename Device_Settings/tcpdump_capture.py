import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import threading
import time
from datetime import datetime

class TCPDumpManager:
    def __init__(self, app_instance):
        """
        初始化TCPDUMP管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        
        # 状态变量
        self.is_running = False
        self.tcpdump_process = None
        self.system_ready = False  # 系统是否就绪（Root权限和TCPDUMP支持）
        self.dialog = None
    
    def show_tcpdump_dialog(self):
        """显示TCPDUMP抓包对话框"""
        try:
            # 检查设备连接
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 创建对话框
            self.dialog = tk.Toplevel(self.app.root)
            self.dialog.title("Android TCPDUMP 抓包工具")
            self.dialog.geometry("500x400")
            self.dialog.resizable(False, False)
            self.dialog.transient(self.app.root)
            self.dialog.grab_set()  # 模态对话框
            
            # 居中显示
            self.dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 400) // 2
            ))
            
            # 创建UI界面
            self.create_ui()
            
            # 初始化检查
            self.check_initial_status()
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"打开TCPDUMP工具失败: {str(e)}")
            return False
    
    def create_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="🔧 Android TCPDUMP 抓包工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 设备类型变量（不再显示在UI中）
        self.device_type = tk.StringVar(value="android")
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, height=8, width=50, wrap=tk.WORD, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置文本颜色标签
        self.status_text.tag_configure("success", foreground="#28a745")  # 绿色
        self.status_text.tag_configure("error", foreground="#dc3545")    # 红色
        self.status_text.tag_configure("warning", foreground="#ffc107")  # 黄色
        self.status_text.tag_configure("info", foreground="#17a2b8")    # 蓝色
        
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        self.start_stop_btn = ttk.Button(button_frame, text="▶️ 开始", command=self.toggle_capture)
        self.start_stop_btn.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(button_frame, text="🗑️ 清空日志", command=self.clear_log).grid(row=0, column=1, padx=(0, 10))
        
        # 关闭按钮
        ttk.Button(button_frame, text="❌ 关闭", command=self.close_dialog).grid(row=0, column=2)
        
        # 配置网格权重
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
    
    def log_message(self, message, level="info"):
        """添加日志消息到状态显示区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据消息类型添加颜色标记
        if "✅" in message or "成功" in message:
            color_tag = "success"
        elif "❌" in message or "失败" in message or "错误" in message:
            color_tag = "error"
        elif "⚠️" in message or "警告" in message:
            color_tag = "warning"
        else:
            color_tag = "info"
        
        # 插入消息
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # 应用颜色标记
        start_line = self.status_text.index(tk.END + "-2l")
        end_line = self.status_text.index(tk.END + "-1l")
        self.status_text.tag_add(color_tag, start_line, end_line)
        
        self.status_text.see(tk.END)
        if self.dialog:
            self.dialog.update()
    
    def clear_log(self):
        """清空日志显示"""
        self.status_text.delete(1.0, tk.END)
    
    def close_dialog(self):
        """关闭对话框"""
        if self.is_running:
            if messagebox.askyesno("确认关闭", "TCPDUMP正在运行中，关闭对话框将停止抓包。是否继续？"):
                self.stop_capture()
                self.dialog.destroy()
        else:
            self.dialog.destroy()
    
    def run_adb_command(self, command, timeout=10):
        """运行ADB命令并返回结果"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "命令执行超时"
        except Exception as e:
            return False, "", str(e)
    
    def check_root_permission(self):
        """检查Root权限"""
        self.log_message("正在检查Root权限...")
        success, stdout, stderr = self.run_adb_command("adb root")
        
        if not success:
            self.log_message(f"ADB命令执行失败: {stderr}")
            return False
        
        if "adbd cannot run as root in production builds" in stderr:
            self.log_message("❌ 设备不支持Root权限")
            return False
        else:
            # 只要不是production builds错误，都认为有root权限
            self.log_message("✅ Root权限检查通过")
            return True
    
    def check_tcpdump_support(self):
        """检查TCPDUMP支持"""
        self.log_message("正在检查TCPDUMP支持...")
        success, stdout, stderr = self.run_adb_command("adb shell tcpdump --version")
        
        if not success or "inaccessible or not found" in stderr:
            self.log_message("❌ 设备不支持TCPDUMP命令")
            return False
        else:
            self.log_message("✅ TCPDUMP支持检查通过")
            return True
    
    def check_initial_status(self):
        """初始化状态检查"""
        self.log_message("开始初始化检查...")
        
        # 检查ADB连接
        success, stdout, stderr = self.run_adb_command("adb devices")
        if not success:
            self.log_message("❌ ADB连接失败，请确保设备已连接并开启USB调试")
            return
        
        if "device" not in stdout:
            self.log_message("❌ 未检测到连接的设备")
            return
        
        self.log_message("✅ 设备连接正常")
        
        # 检查Root权限
        if not self.check_root_permission():
            self.log_message("❌ 设备不支持Root权限")
            return
        
        # 检查TCPDUMP支持
        if not self.check_tcpdump_support():
            self.log_message("❌ 设备不支持TCPDUMP")
            return
        
        self.log_message("✅ 所有检查通过，可以开始抓包")
    
    def get_log_path(self):
        """根据设备类型获取日志路径"""
        if self.device_type.get() == "kaios":
            return "/data/media/music/netlog.pcap"
        else:
            return "/sdcard/netlog.pcap"
    
    def get_log_directory(self):
        """根据设备类型获取日志目录"""
        if self.device_type.get() == "kaios":
            return "/data/media/music"
        else:
            return "/sdcard"
    
    def check_path_and_start(self):
        """检查路径并启动抓包"""
        log_dir = self.get_log_directory()
        log_path = self.get_log_path()
        
        self.log_message(f"检查设备路径: {log_dir}")
        
        # 检查路径是否存在
        success, stdout, stderr = self.run_adb_command(f"adb shell ls -d '{log_dir}'")
        
        if not success or "No such file or directory" in stderr:
            self.log_message(f"❌ 路径不存在: {log_dir}")
            self.log_message("正在尝试创建目录...")
            
            # 尝试创建目录
            success2, stdout2, stderr2 = self.run_adb_command(f"adb shell mkdir -p '{log_dir}'")
            
            if success2:
                self.log_message(f"✅ 目录创建成功: {log_dir}")
            else:
                self.log_message(f"❌ 目录创建失败: {stderr2}")
                self.log_message("❌ 程序停止：无法创建必要的目录")
                return
        else:
            self.log_message(f"✅ 路径存在: {log_dir}")
        
        # 在新线程中启动抓包，避免UI阻塞
        threading.Thread(target=self.start_capture, daemon=True).start()
    
    def start_capture(self):
        """开始抓包"""
        log_path = self.get_log_path()
        self.log_message(f"开始抓包，日志保存到: {log_path}")
        
        # 构建tcpdump命令
        tcpdump_cmd = f'adb shell "nohup tcpdump -i any -s 0 -w {log_path} >/dev/null 2>&1 &"'
        
        success, stdout, stderr = self.run_adb_command(tcpdump_cmd)
        
        if success:
            self.is_running = True
            self.start_stop_btn.config(text="⏹️ 停止")
            self.log_message("✅ TCPDUMP进程启动成功")
            
            # 等待进程启动
            self.log_message("⏳ 等待TCPDUMP进程启动...")
            time.sleep(1)
            
            # 验证进程是否真的在运行（重试检查）
            self.verify_tcpdump_process()
        else:
            self.log_message(f"❌ TCPDUMP启动失败: {stderr}")
    
    def stop_capture(self):
        """停止抓包并拉取日志"""
        self.log_message("正在停止抓包...")
        
        # 停止tcpdump进程
        success, stdout, stderr = self.run_adb_command("adb shell pkill tcpdump")
        if success:
            self.log_message("✅ TCPDUMP进程已停止")
        else:
            self.log_message(f"⚠️ 停止进程时出现警告: {stderr}")
        
        # 等待进程完全停止
        time.sleep(2)
        
        # 拉取日志文件
        self.pull_log_file()
        
        # 更新UI状态
        self.is_running = False
        self.start_stop_btn.config(text="▶️ 开始")
    
    def pull_log_file(self):
        """拉取日志文件到本地"""
        log_path = self.get_log_path()
        self.log_message(f"正在拉取日志文件: {log_path}")
        
        # 创建本地日志目录
        local_log_dir = "C:\\log"
        if not os.path.exists(local_log_dir):
            try:
                os.makedirs(local_log_dir)
                self.log_message(f"✅ 创建日志目录: {local_log_dir}")
            except Exception as e:
                self.log_message(f"⚠️ 无法创建C:\\log目录，将保存到当前目录: {e}")
                local_log_dir = "."
        
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_type = self.device_type.get()
        local_file = os.path.join(local_log_dir, f"netlog_{device_type}_{timestamp}.pcap")
        
        # 拉取文件
        pull_cmd = f'adb pull "{log_path}" "{local_file}"'
        success, stdout, stderr = self.run_adb_command(pull_cmd, timeout=30)
        
        if success and os.path.exists(local_file):
            file_size = os.path.getsize(local_file)
            self.log_message(f"✅ 日志文件拉取成功")
            self.log_message(f"📁 文件路径: {os.path.abspath(local_file)}")
            self.log_message(f"📊 文件大小: {file_size} 字节")
            
            # 打开文件夹
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(os.path.dirname(os.path.abspath(local_file)))
                else:  # macOS/Linux
                    subprocess.run(['open', os.path.dirname(os.path.abspath(local_file))])
                self.log_message("✅ 已打开日志文件夹")
            except Exception as e:
                self.log_message(f"⚠️ 无法自动打开文件夹: {e}")
        else:
            self.log_message(f"❌ 日志文件拉取失败: {stderr}")
            self.log_message("请检查设备存储空间和文件权限")
    
    def check_system_requirements(self):
        """检查系统要求"""
        self.log_message("检查系统要求...")
        
        # 检查ADB连接
        success, stdout, stderr = self.run_adb_command("adb devices")
        if not success:
            self.log_message("❌ ADB连接失败，请确保设备已连接并开启USB调试")
            return False
        
        if "device" not in stdout:
            self.log_message("❌ 未检测到连接的设备")
            return False
        
        # 检查Root权限
        if not self.check_root_permission():
            self.log_message("❌ 设备不支持Root权限，程序终止")
            return False
        
        # 检查TCPDUMP支持
        if not self.check_tcpdump_support():
            self.log_message("❌ 设备不支持TCPDUMP，程序终止")
            return False
        
        return True
    
    def verify_tcpdump_process(self):
        """验证TCPDUMP进程是否正在运行"""
        max_retries = 2
        for attempt in range(max_retries):
            # 使用 ps -A 命令检查所有进程，在Windows上使用findstr
            command = "adb shell ps -A | findstr tcpdump"
            success, stdout, stderr = self.run_adb_command(command)
            
            if success and stdout.strip() and "tcpdump" in stdout:
                # 提取进程信息
                lines = stdout.strip().split('\n')
                for line in lines:
                    if "tcpdump" in line and "findstr" not in line:
                        self.log_message("✅ 确认TCPDUMP进程正在运行")
                        return True
            
            # 如果未找到，等待后重试
            if attempt < max_retries - 1:
                self.log_message("⏳ 等待进程启动...")
                time.sleep(1)
            else:
                # 检查日志文件是否存在
                log_path = self.get_log_path()
                success2, stdout2, stderr2 = self.run_adb_command(f"adb shell ls -la '{log_path}'")
                if success2 and log_path.split('/')[-1] in stdout2:
                    self.log_message("✅ 日志文件存在，TCPDUMP可能正在后台运行")
                    return True
                else:
                    self.log_message("❌ TCPDUMP进程不存在，程序终止")
                    self.log_message("请检查设备权限和TCPDUMP安装状态")
                    # 恢复按钮状态
                    self.is_running = False
                    self.start_stop_btn.config(text="▶️ 开始")
                    return False
        return False
    
    def show_device_selection_dialog(self):
        """显示设备类型选择对话框"""
        device_dialog = tk.Toplevel(self.dialog)
        device_dialog.title("选择设备类型")
        device_dialog.geometry("300x200")
        device_dialog.resizable(False, False)
        
        # 居中显示对话框
        device_dialog.transient(self.dialog)
        device_dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(device_dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="请选择设备类型", font=("Arial", 12, "bold")).pack(pady=(0, 15))
        
        # 设备类型选择
        device_type = tk.StringVar(value="android")
        ttk.Radiobutton(main_frame, text="Android", variable=device_type, value="android").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(main_frame, text="KaiOS", variable=device_type, value="kaios").pack(anchor=tk.W, pady=2)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(30, 0))
        
        def on_ok():
            self.device_type.set(device_type.get())
            device_dialog.destroy()
            # 检查路径并启动抓包
            self.check_path_and_start()
        
        def on_cancel():
            device_dialog.destroy()
        
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
        
        # 绑定回车键
        device_dialog.bind('<Return>', lambda e: on_ok())
        device_dialog.bind('<Escape>', lambda e: on_cancel())
        
        # 设置焦点
        device_dialog.focus_set()
    
    def toggle_capture(self):
        """切换抓包状态"""
        if self.is_running:
            self.stop_capture()
        else:
            # 先检查系统要求
            if not self.check_system_requirements():
                self.log_message("❌ 系统检查失败，无法开始抓包")
                return
            
            # 显示设备选择对话框
            self.show_device_selection_dialog()
