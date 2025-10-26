import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Optional
import re

from SIM_APDU_Parser.app.adapter import load_for_gui, GuiSession

# 颜色
COLOR_PROACTIVE_RX = "#d62728"
COLOR_PROACTIVE_TX = "#1f77b4"
COLOR_ESIM_RX      = "#2ca02c"
COLOR_ESIM_TX      = "#9467bd"
COLOR_SIM_RX       = "#ff7f0e"  # SIM->UE (橙色)
COLOR_SIM_TX       = "#17becf"  # UE->SIM (青色)
COLOR_UNKNOWN      = "#7f7f7f"

def color_for_direction(direction: str) -> str:
    if direction == "UICC=>TERMINAL":   return COLOR_PROACTIVE_RX
    if direction == "TERMINAL=>UICC":   return COLOR_PROACTIVE_TX
    if direction == "ESIM=>LPA":        return COLOR_ESIM_RX
    if direction == "LPA=>ESIM":        return COLOR_ESIM_TX
    if direction == "SIM=>UE":          return COLOR_SIM_RX
    if direction == "UE=>SIM":          return COLOR_SIM_TX
    return COLOR_UNKNOWN

class SearchDialog:
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.dialog = None
        self.search_var = tk.StringVar()
        self.current_index = 0
        self.search_results = []
        self.last_pattern = ""
        
    def show(self):
        """显示搜索对话框"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            self.entry_search.focus_set()
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("搜索")
        self.dialog.geometry("400x100")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        
        # 设置窗口属性，确保可以通过Alt+Tab和任务栏访问
        self.dialog.wm_attributes("-topmost", False)  # 不强制置顶
        self.dialog.wm_attributes("-toolwindow", False)  # 确保显示在任务栏
        
        # 使用非模态对话框，避免grab_set()导致的问题
        # self.dialog.grab_set()  # 注释掉这行，避免模态对话框问题
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # 创建界面
        self._build_ui()
        
        # 绑定事件
        self.dialog.bind("<Return>", lambda e: self.search_next())
        self.dialog.bind("<Shift-Return>", lambda e: self.search_prev())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        
        # 聚焦到搜索框
        self.entry_search.focus_set()
        
        # 如果搜索框有内容，自动执行搜索
        if self.search_var.get().strip():
            self.perform_search()
        
    def _build_ui(self):
        """构建搜索对话框界面"""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 搜索框
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.entry_search = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.entry_search.pack(side=tk.LEFT, padx=(5, 10))
        self.entry_search.bind("<KeyRelease>", self.on_search_text_changed)
        

        
        # 按钮
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.btn_prev = tk.Button(button_frame, text="上一个", command=self.search_prev, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_next = tk.Button(button_frame, text="下一个", command=self.search_next, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_close = tk.Button(button_frame, text="关闭", command=self.dialog.destroy)
        self.btn_close.pack(side=tk.RIGHT)
        
        # 状态标签
        self.status_label = tk.Label(main_frame, text="", fg="gray")
        self.status_label.pack(anchor=tk.W)
        
    def on_search_text_changed(self, event=None):
        """搜索文本改变时的处理"""
        pattern = self.search_var.get().strip()
        if pattern != self.last_pattern:
            self.last_pattern = pattern
            self.perform_search()
            
    def perform_search(self):
        """执行搜索"""
        pattern = self.search_var.get().strip()
        if not pattern:
            self.search_results = []
            self.current_index = 0
            self.update_buttons()
            self.status_label.config(text="")
            return
            
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            self.status_label.config(text="无效的正则表达式", fg="red")
            return
            
        self.search_results = []
        
        for idx, event in enumerate(self.app.events):
            # 搜索标题
            if regex.search(event.get("title", "")):
                self.search_results.append(idx)
                continue
                
            # 搜索详情内容（默认启用）
            if self.app._session:
                raw = event["raw"]
                detail_text = self.app._detail_cache.get(raw)
                if detail_text is None:
                    # 生成详情文本
                    tree = self.app._session.get_tree_by_raw(raw)
                    parts = []
                    def walk(node):
                        text = node.get("text")
                        hint = node.get("hint")
                        if text: parts.append(text)
                        if hint: parts.append(hint)
                        for child in node.get("children", []):
                            walk(child)
                    walk(tree)
                    detail_text = "\n".join(parts)
                    self.app._detail_cache[raw] = detail_text
                    
                if regex.search(detail_text):
                    self.search_results.append(idx)
                    
        self.current_index = 0
        self.update_buttons()
        self.update_status()
        
    def update_buttons(self):
        """更新按钮状态"""
        has_results = len(self.search_results) > 0
        self.btn_prev.config(state=tk.NORMAL if has_results else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if has_results else tk.DISABLED)
        
    def update_status(self):
        """更新状态显示"""
        if not self.search_var.get().strip():
            self.status_label.config(text="")
        elif not self.search_results:
            self.status_label.config(text="未找到匹配项", fg="red")
        else:
            self.status_label.config(
                text=f"找到 {len(self.search_results)} 个匹配项 (第 {self.current_index + 1} 个)",
                fg="blue"
            )
            
    def search_next(self):
        """搜索下一个"""
        if not self.search_results:
            return
            
        self.current_index = (self.current_index + 1) % len(self.search_results)
        self.highlight_result()
        self.update_status()
        
    def search_prev(self):
        """搜索上一个"""
        if not self.search_results:
            return
            
        self.current_index = (self.current_index - 1) % len(self.search_results)
        self.highlight_result()
        self.update_status()
        
    def highlight_result(self):
        """高亮显示搜索结果"""
        if not self.search_results:
            return
            
        target_idx = self.search_results[self.current_index]
        
        # 滚动到目标项
        self.app.tree_events.selection_set(str(target_idx))
        self.app.tree_events.see(str(target_idx))
        
        # 触发选择事件以显示详情
        self.app.tree_events.event_generate("<<TreeviewSelect>>")

class ApduDialog:
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.dialog = None
        self.apdu_var = tk.StringVar()
        
    def show(self):
        """显示APDU解析对话框"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("APDU 解析器")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        
        # 设置窗口属性，确保可以通过Alt+Tab和任务栏访问
        self.dialog.wm_attributes("-topmost", False)  # 不强制置顶
        self.dialog.wm_attributes("-toolwindow", False)  # 确保显示在任务栏
        
        # 使用非模态对话框，避免grab_set()导致的问题
        # self.dialog.grab_set()  # 注释掉这行，避免模态对话框问题
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # 创建界面
        self._build_ui()
        
        # 绑定事件
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        
        # 聚焦到输入框
        self.text_apdu.focus_set()
        
    def _build_ui(self):
        """构建APDU解析对话框界面"""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上半部分：输入区域
        input_frame = tk.LabelFrame(main_frame, text="APDU 输入", font=("Arial", 10, "bold"))
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 提示标签
        hint_label = tk.Label(input_frame, 
                             text="请输入标准的APDU格式（十六进制，支持空格分隔）\n例如：81 E2 91 00 03 BF 22 00",
                             font=("Arial", 9),
                             fg="gray")
        hint_label.pack(anchor=tk.W, pady=(5, 5))
        
        # APDU输入文本框
        text_frame = tk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.text_apdu = tk.Text(text_frame, height=4, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.text_apdu.yview)
        self.text_apdu.configure(yscrollcommand=scrollbar.set)
        
        self.text_apdu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮区域
        button_frame = tk.Frame(input_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.btn_parse = tk.Button(button_frame, text="解析", command=self.parse_apdu, 
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_parse.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_clear = tk.Button(button_frame, text="清除", command=self.clear_input,
                                  bg="#f44336", fg="white", font=("Arial", 10, "bold"))
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_close = tk.Button(button_frame, text="关闭", command=self.dialog.destroy,
                                  font=("Arial", 10))
        self.btn_close.pack(side=tk.RIGHT)
        
        # 下半部分：解析结果显示区域
        result_frame = tk.LabelFrame(main_frame, text="解析结果", font=("Arial", 10, "bold"))
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条框架
        scroll_frame = tk.Frame(result_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 垂直滚动条
        yscroll = ttk.Scrollbar(scroll_frame, orient="vertical")
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        xscroll = ttk.Scrollbar(scroll_frame, orient="horizontal")
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 树形视图显示解析结果
        self.tree_result = ttk.Treeview(scroll_frame, show="tree", 
                                       yscrollcommand=yscroll.set, 
                                       xscrollcommand=xscroll.set)
        self.tree_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        yscroll.config(command=self.tree_result.yview)
        xscroll.config(command=self.tree_result.xview)
        
        # RAW显示区域
        raw_frame = tk.Frame(result_frame)
        raw_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        tk.Label(raw_frame, text="RAW:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.txt_raw_result = tk.Text(raw_frame, height=3, wrap="none", font=("Consolas", 9))
        self.txt_raw_result.pack(fill=tk.X)
        
    def clear_input(self):
        """清除输入的APDU消息"""
        self.text_apdu.delete("1.0", tk.END)
        self.tree_result.delete(*self.tree_result.get_children())
        self.txt_raw_result.delete("1.0", tk.END)
        
    def parse_apdu(self):
        """解析APDU消息"""
        apdu_text = self.text_apdu.get("1.0", tk.END).strip()
        if not apdu_text:
            messagebox.showwarning("警告", "请输入APDU消息")
            return
            
        try:
            # 预处理：移除空格并转换为大写
            apdu_hex = apdu_text.replace(" ", "").replace("\n", "").upper()
            
            # 验证是否为有效的十六进制
            if not all(c in "0123456789ABCDEF" for c in apdu_hex):
                messagebox.showerror("错误", "APDU格式无效，请确保只包含十六进制字符")
                return
                
            if len(apdu_hex) % 2 != 0:
                messagebox.showerror("错误", "APDU长度必须为偶数")
                return
                
            # 创建Message对象
            from SIM_APDU_Parser.core.models import Message
            message = Message(raw=apdu_hex, direction="tx", meta={"source": "manual_input"})
            
            # 使用现有的解析管道
            from SIM_APDU_Parser.pipeline import Pipeline
            pipeline = Pipeline(prefer_mtk=False, show_normal_sim=True)
            results = pipeline._run_messages([message])
            
            if not results:
                messagebox.showwarning("警告", "无法解析此APDU消息")
                return
                
            # 显示解析结果
            self._display_result(results[0])
            
        except Exception as e:
            messagebox.showerror("错误", f"解析失败：\n{str(e)}")
            
    def _display_result(self, result):
        """显示解析结果"""
        # 清除之前的结果
        self.tree_result.delete(*self.tree_result.get_children())
        self.txt_raw_result.delete("1.0", tk.END)
        
        # 显示RAW数据
        self.txt_raw_result.insert(tk.END, result.message.raw)
        
        # 显示解析树
        if result.root:
            self._populate_result_tree(result.root)
        else:
            self.tree_result.insert("", "end", text="(无解析结果)")
            
        # 默认展开所有节点
        def expand_all(item=""):
            for child in self.tree_result.get_children(item):
                self.tree_result.item(child, open=True)
                expand_all(child)
        expand_all()
        
    def _populate_result_tree(self, node):
        """填充解析结果树"""
        def add_node(parent, node_data, node_id=""):
            text = node_data.name
            if node_data.value is not None:
                text += f": {node_data.value}"
            if node_data.hint:
                text += f" ({node_data.hint})"
                
            item_id = self.tree_result.insert(parent, "end", text=text)
            
            for child in node_data.children:
                add_node(item_id, child)
                
        add_node("", node)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SIM APDU Viewer V2.2")
        self.geometry("1200x760")

        self._session: GuiSession | None = None
        self.events_all: List[Dict] = []
        self.events: List[Dict] = []
        self._detail_cache: dict[str, str] = {}
        self._search_dialog: Optional[SearchDialog] = None
        self._apdu_dialog: Optional[ApduDialog] = None

        self._build_widgets()
        self._bind_shortcuts()

    # ---------- UI ----------
    def _build_widgets(self):
        top = tk.Frame(self); top.pack(fill=tk.X, padx=8, pady=6)
        tk.Button(top, text="加载 MTK APDU文本日志", command=self.on_load_mtk).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="加载 高通APDU文本日志", command=self.on_load_qualcomm).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="加载 标准APDU格式文本", command=self.on_load_apdu).pack(side=tk.LEFT, padx=4)


        # 多选下拉菜单：筛选类别
        self.var_filter_proactive = tk.BooleanVar(value=True)
        self.var_filter_esim = tk.BooleanVar(value=True)
        self.var_filter_normal = tk.BooleanVar(value=False)

        self.menu_btn = tk.Menubutton(top, text="筛选类别 ▾", relief=tk.RAISED)
        self.menu = tk.Menu(self.menu_btn, tearoff=0)
        self.menu_btn.configure(menu=self.menu)
        self.menu.add_checkbutton(label="CAT APDU", variable=self.var_filter_proactive, command=self.on_filter_changed)
        self.menu.add_checkbutton(label="eSIM APDU", variable=self.var_filter_esim, command=self.on_filter_changed)
        self.menu.add_checkbutton(label="Generic APDU", variable=self.var_filter_normal, command=self.on_filter_changed)
        self.menu_btn.pack(side=tk.LEFT, padx=8)

        tk.Label(top, text="搜索:").pack(side=tk.LEFT, padx=(16, 4))
        self.search_var = tk.StringVar(value="")
        self.entry_search = tk.Entry(top, textvariable=self.search_var, width=36)
        self.entry_search.pack(side=tk.LEFT)
        self.entry_search.bind("<Return>", lambda e: self.apply_search())
        tk.Button(top, text="Search", command=self.apply_search).pack(side=tk.LEFT, padx=6)
        tk.Button(top, text="清除筛选", command=self.clear_filters).pack(side=tk.LEFT, padx=4)

        self.var_search_detail = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="搜索右侧详情", variable=self.var_search_detail,
                       command=self.apply_search).pack(side=tk.LEFT, padx=8)

        self.status = tk.StringVar(value="就绪")
        tk.Label(top, textvariable=self.status).pack(side=tk.RIGHT)
        tk.Button(top, text="解析单条 APDU", command=self.show_apdu_dialog).pack(side=tk.RIGHT, padx=4)

        main = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 左侧列表
        left_frame = tk.Frame(main)
        
        # 创建滚动条框架
        scroll_frame = tk.Frame(left_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        # 垂直滚动条
        yscroll = ttk.Scrollbar(scroll_frame, orient="vertical")
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        xscroll = ttk.Scrollbar(scroll_frame, orient="horizontal")
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 树形视图
        self.tree_events = ttk.Treeview(scroll_frame, show="tree", 
                                       yscrollcommand=yscroll.set, 
                                       xscrollcommand=xscroll.set)
        self.tree_events.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        yscroll.config(command=self.tree_events.yview)
        xscroll.config(command=self.tree_events.xview)
        
        # 绑定事件
        self.tree_events.bind("<<TreeviewSelect>>", self.on_select_event)
        
        # 配置列
        self.tree_events.column("#0", anchor="w", stretch=True, width=800, minwidth=300)
        self.tree_events.heading("#0", text="")
        self.tree_events.bind("<Configure>", lambda e: self.tree_events.column("#0", width=max(self.tree_events.winfo_width()-4, 200)))
        
        main.add(left_frame, width=520)

        # 右侧详情 + RAW
        right_frame = tk.Frame(main)
        
        # 详情显示区域
        detail_frame = tk.Frame(right_frame)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条框架
        detail_scroll_frame = tk.Frame(detail_frame)
        detail_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        # 垂直滚动条
        detail_yscroll = ttk.Scrollbar(detail_scroll_frame, orient="vertical")
        detail_yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        detail_xscroll = ttk.Scrollbar(detail_scroll_frame, orient="horizontal")
        detail_xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 树形视图显示详情
        self.tree_detail = ttk.Treeview(detail_scroll_frame, show="tree",
                                       yscrollcommand=detail_yscroll.set,
                                       xscrollcommand=detail_xscroll.set)
        self.tree_detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        detail_yscroll.config(command=self.tree_detail.yview)
        detail_xscroll.config(command=self.tree_detail.xview)
        
        # RAW显示区域
        tk.Label(right_frame, text="RAW:").pack(anchor="w")
        self.txt_raw = tk.Text(right_frame, height=6, wrap="none")
        self.txt_raw.pack(fill=tk.X, expand=False)
        main.add(right_frame)

        # ---------- 复制功能：右键菜单 & 快捷键 ----------
        # 左侧菜单
        self.menu_left = tk.Menu(self, tearoff=0)
        self.menu_left.add_command(label="复制此行", command=self.copy_left_line)
        self.menu_left.add_command(label="复制 RAW", command=self.copy_left_raw)
        self.menu_left.add_separator()
        self.menu_left.add_command(label="复制右侧详情（全部）", command=self.copy_detail_all_from_left)
        self.tree_events.bind("<Button-3>", self._popup_left)

        # 右侧详情菜单
        self.menu_detail = tk.Menu(self, tearoff=0)
        self.menu_detail.add_command(label="复制所选节点", command=self.copy_detail_node)
        self.menu_detail.add_command(label="复制所选子树", command=self.copy_detail_subtree)
        self.menu_detail.add_separator()
        self.menu_detail.add_command(label="复制全部详情", command=self.copy_detail_all)
        self.tree_detail.bind("<Button-3>", self._popup_detail)

        # RAW 菜单
        self.menu_raw = tk.Menu(self, tearoff=0)
        self.menu_raw.add_command(label="复制选中", command=lambda: self._to_clip(self.txt_raw.get("sel.first", "sel.last")) if self.txt_raw.tag_ranges("sel") else None)
        self.menu_raw.add_command(label="复制全部", command=lambda: self._to_clip(self.txt_raw.get("1.0", "end-1c")))
        self.txt_raw.bind("<Button-3>", lambda e: self.menu_raw.tk_popup(e.x_root, e.y_root))
        self.txt_raw.bind("<Control-a>", lambda e: (self.txt_raw.tag_add("sel", "1.0", "end-1c"), "break"))

        # Ctrl+C 快捷键
        self.tree_events.bind("<Control-c>", lambda e: (self.copy_left_line(), "break"))
        self.tree_detail.bind("<Control-c>", lambda e: (self.copy_detail_node(), "break"))

    def _bind_shortcuts(self):
        """绑定全局快捷键"""
        # Ctrl+F 搜索 - 使用更强制的方式绑定
        self.bind("<Control-f>", lambda e: self.show_search_dialog())
        self.bind_all("<Control-F>", lambda e: self.show_search_dialog())  # 大写F
        self.bind_all("<Control-f>", lambda e: self.show_search_dialog())  # 小写f
        
        # 为主要的Treeview控件单独绑定
        if hasattr(self, 'tree_events'):
            self.tree_events.bind("<Control-f>", lambda e: self.show_search_dialog())
        if hasattr(self, 'tree_detail'):
            self.tree_detail.bind("<Control-f>", lambda e: self.show_search_dialog())
        
    def show_search_dialog(self):
        """显示搜索对话框"""
        print("Ctrl+F pressed - showing search dialog")  # 调试信息
        if not self._search_dialog:
            self._search_dialog = SearchDialog(self, self)
        self._search_dialog.show()
        
    def show_apdu_dialog(self):
        """显示APDU解析对话框"""
        if not self._apdu_dialog:
            self._apdu_dialog = ApduDialog(self, self)
        self._apdu_dialog.show()

    # ---------- 文件加载 ----------
    def on_load_mtk(self):
        fp = filedialog.askopenfilename(title="选择 MTK 文本日志",
                                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not fp: return
        try:
            self._session = load_for_gui(fp, prefer_mtk=True, show_normal=self.var_filter_normal.get())
            # 初始化筛选
            kinds = []
            if self.var_filter_proactive.get(): kinds.append('proactive')
            if self.var_filter_esim.get(): kinds.append('esim')
            if self.var_filter_normal.get(): kinds.append('normal_sim')
            self._session.set_allowed_types(kinds)
            self.events_all = self._session.events[:]
            self._detail_cache.clear()
            self.status.set(f"加载完成：{len(self.events_all)} 条")
            self.apply_search()
        except Exception as ex:
            messagebox.showerror("错误", f"解析失败：\n{ex}")

    def on_load_apdu(self):
        fp = filedialog.askopenfilename(title="选择 标准APDU文本",
                                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not fp: return
        try:
            self._session = load_for_gui(fp, prefer_mtk=False, show_normal=self.var_filter_normal.get())
            # 初始化筛选
            kinds = []
            if self.var_filter_proactive.get(): kinds.append('proactive')
            if self.var_filter_esim.get(): kinds.append('esim')
            if self.var_filter_normal.get(): kinds.append('normal_sim')
            self._session.set_allowed_types(kinds)
            self.events_all = self._session.events[:]
            self._detail_cache.clear()
            self.status.set(f"加载完成：{len(self.events_all)} 条")
            self.apply_search()
        except Exception as ex:
            messagebox.showerror("错误", f"解析失败：\n{ex}")

    def on_load_qualcomm(self):
        fp = filedialog.askopenfilename(title="选择 高通APDU文本日志",
                                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not fp: return
        try:
            self._session = load_for_gui(fp, prefer_mtk=False, show_normal=self.var_filter_normal.get(), use_qualcomm=True)
            # 初始化筛选
            kinds = []
            if self.var_filter_proactive.get(): kinds.append('proactive')
            if self.var_filter_esim.get(): kinds.append('esim')
            if self.var_filter_normal.get(): kinds.append('normal_sim')
            self._session.set_allowed_types(kinds)
            self.events_all = self._session.events[:]
            self._detail_cache.clear()
            self.status.set(f"加载完成：{len(self.events_all)} 条")
            self.apply_search()
        except Exception as ex:
            messagebox.showerror("错误", f"解析失败：\n{ex}")

    def on_filter_changed(self):
        kinds = []
        if self.var_filter_proactive.get(): kinds.append('proactive')
        if self.var_filter_esim.get(): kinds.append('esim')
        if self.var_filter_normal.get(): kinds.append('normal_sim')
        if self._session:
            self._session.set_allowed_types(kinds)
            self.events_all = self._session.events[:]
            self._detail_cache.clear()
            self.apply_search()

    def clear_filters(self):
        """清除所有筛选条件"""
        # 清除搜索框
        self.search_var.set("")
        # 重置类别筛选为默认状态
        self.var_filter_proactive.set(True)
        self.var_filter_esim.set(True)
        self.var_filter_normal.set(False)
        # 重置搜索详情选项
        self.var_search_detail.set(False)
        # 应用更改
        self.on_filter_changed()

    # ---------- 搜索 ----------
    def apply_search(self):
        if not self._session: return
        pattern = (self.search_var.get() or "").strip()
        include_detail = self.var_search_detail.get()

        if not pattern:
            self.events = self.events_all[:]
            self.status.set(f"共 {len(self.events_all)} 条")
        else:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                messagebox.showerror("Regex Error", f"无效的正则表达式: {e}")
                return

            out = []
            for e in self.events_all:
                if regex.search(e.get("title", "")):
                    out.append(e); continue
                if include_detail:
                    raw = e["raw"]
                    buf = self._detail_cache.get(raw)
                    if buf is None:
                        nd = self._session.get_tree_by_raw(raw)
                        parts = []
                        def walk(n):
                            t = n.get("text"); h = n.get("hint")
                            if t: parts.append(t)
                            if h: parts.append(h)
                            for c in n.get("children", []): walk(c)
                        walk(nd)
                        buf = "\n".join(parts)
                        self._detail_cache[raw] = buf
                    if regex.search(buf): out.append(e)
            self.events = out
            self.status.set(f"匹配 {len(self.events)} / {len(self.events_all)} 条")

        self._refresh_event_list()

    # ---------- 列表渲染 ----------
    def _refresh_event_list(self):
        self.tree_events.delete(*self.tree_events.get_children())
        for idx, e in enumerate(self.events):
            text = e.get('title') or ''
            iid = self.tree_events.insert("", "end", iid=str(idx), text=text)
            color = color_for_direction(e["direction"])
            self.tree_events.item(iid, tags=(e["direction"],))
            self.tree_events.tag_configure(e["direction"], foreground=color)

        self.tree_detail.delete(*self.tree_detail.get_children())
        self.txt_raw.delete("1.0", tk.END)

        if self.events:
            self.tree_events.selection_set("0")
            self.tree_events.event_generate("<<TreeviewSelect>>")
        else:
            self.status.set("无匹配结果")

    # ---------- 选择 / 详情 ----------
    def on_select_event(self, evt=None):
        if not self._session: return
        sel = self.tree_events.selection()
        if not sel: return
        idx = int(sel[0])
        e = self.events[idx]
        raw = e["raw"]

        self.txt_raw.configure(state=tk.NORMAL)
        self.txt_raw.delete("1.0", tk.END)
        self.txt_raw.insert(tk.END, raw)
        self.txt_raw.configure(state=tk.NORMAL)

        tree = self._session.get_tree_by_raw(raw)
        self._populate_detail_tree(tree)

    def _populate_detail_tree(self, node_dict):
        self.tree_detail.delete(*self.tree_detail.get_children())
        def add(parent, nd):
            text = nd.get("text") or ""
            iid = self.tree_detail.insert(parent, "end", text=text)
            for ch in nd.get("children", []): add(iid, ch)
        add("", node_dict)
        # 默认展开所有节点
        def expand_all(item=""):
            for child in self.tree_detail.get_children(item):
                self.tree_detail.item(child, open=True)
                expand_all(child)
        expand_all()

    # ---------- 右键菜单 / 复制 ----------
    def _popup_left(self, e):
        try:
            iid = self.tree_events.identify_row(e.y)
            if iid: self.tree_events.selection_set(iid)
            self.menu_left.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu_left.grab_release()

    def _popup_detail(self, e):
        try:
            iid = self.tree_detail.identify_row(e.y)
            if iid: self.tree_detail.selection_set(iid)
            self.menu_detail.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu_detail.grab_release()

    def _to_clip(self, text: str | None):
        if not text: return
        self.clipboard_clear()
        self.clipboard_append(text)
        try: self.update()
        except Exception: pass

    def copy_left_line(self):
        sel = self.tree_events.selection()
        if not sel: return
        self._to_clip(self.tree_events.item(sel[0], "text"))

    def copy_left_raw(self):
        sel = self.tree_events.selection()
        if not sel: return
        idx = int(sel[0])
        self._to_clip(self.events[idx]["raw"])

    def copy_detail_node(self):
        sel = self.tree_detail.selection()
        if not sel: return
        iid = sel[0]
        self._to_clip(self.tree_detail.item(iid, "text"))

    def copy_detail_subtree(self):
        sel = self.tree_detail.selection()
        if not sel: return
        iid = sel[0]
        lines = []
        def walk(node, depth=0):
            lines.append("  "*depth + (self.tree_detail.item(node, "text") or ""))
            for c in self.tree_detail.get_children(node):
                walk(c, depth+1)
        walk(iid)
        self._to_clip("\n".join(lines))

    def copy_detail_all(self):
        lines = []
        def walk(node, depth=0):
            lines.append("  "*depth + (self.tree_detail.item(node, "text") or ""))
            for c in self.tree_detail.get_children(node): walk(c, depth+1)
        for r in self.tree_detail.get_children(""):
            walk(r, 0)
        self._to_clip("\n".join(lines))

    def copy_detail_all_from_left(self):
        # 从左侧当前项直接取解析树，避免右侧未展开/滚动影响
        sel = self.tree_events.selection()
        if not sel or not self._session: return
        idx = int(sel[0]); raw = self.events[idx]["raw"]
        nd = self._session.get_tree_by_raw(raw)
        lines = []
        def walk(n, d=0):
            lines.append("  "*d + (n.get("text") or ""))
            for c in n.get("children", []):
                walk(c, d+1)
        walk(nd)
        self._to_clip("\n".join(lines))

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
