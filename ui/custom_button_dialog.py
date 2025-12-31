#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义按钮编辑对话框
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QMessageBox, QLabel, QLineEdit, QComboBox,
                             QTextEdit, QCheckBox, QFileDialog,
                             QFormLayout, QScrollArea, QWidget, QTextBrowser,
                             QSizePolicy, QFrame)
from PySide6.QtCore import Qt
from core.debug_logger import logger
from ui.widgets.shadow_utils import add_card_shadow


class ButtonEditDialog(QDialog):
    """按钮编辑对话框"""
    
    def __init__(self, button_manager, button_data=None, preset_tab_name=None, preset_card_name=None, parent=None):
        super().__init__(parent)
        self.button_manager = button_manager
        self.button_data = button_data or {}
        self.is_edit = button_data is not None
        self.preset_tab_name = preset_tab_name
        self.preset_card_name = preset_card_name
        
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("编辑按钮") if self.is_edit else self.tr("添加按钮"))
        self.setModal(True)
        self.resize(700, 600)  # 增加宽度和高度
        
        # 设置窗口标志，显示帮助按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_data()
        elif self.preset_tab_name or self.preset_card_name:
            # 如果有预设值，在UI设置完成后设置
            self._apply_preset_values()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def event(self, event):
        """处理事件，包括帮助按钮点击"""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.EnterWhatsThisMode:
            # 点击帮助按钮时显示帮助对话框
            self.show_help_dialog()
            return True
        return super().event(event)
    
    def show_help_dialog(self):
        """显示帮助对话框"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("📖 " + self.tr("自定义按钮使用帮助"))
        help_dialog.resize(800, 600)
        
        layout = QVBoxLayout(help_dialog)
        
        # 创建文本浏览器
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        
        # 帮助文档内容
        help_text = """
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 20px; }
                h3 { 
                    color: #3498db; 
                    background-color: #2c3e50; 
                    margin-top: 15px; 
                    margin-bottom: 10px;
                    padding: 8px 15px; 
                    border-radius: 5px; 
                    font-weight: bold;
                    font-size: 1.1em;
                }
                .type-section { 
                    background: #ecf0f1; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }
                .example { 
                    background: #f8f9fa; 
                    color: #2c3e50;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border: 1px solid #dee2e6;
                    font-family: "Consolas", monospace;
                    font-weight: normal;
                }
                .warning { 
                    background: #f8d7da; 
                    color: #721c24;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #dc3545;
                }
                .tip { 
                    background: #d1ecf1; 
                    color: #0c5460;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #17a2b8;
                }
                ul { margin-left: 20px; }
                li { margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>🔧 自定义按钮使用指南</h1>
            
            <div class="tip">
                <strong>💡 提示：</strong>自定义按钮功能允许您创建各种类型的快捷操作按钮，支持ADB命令、Python脚本、打开文件等多种功能。
            </div>
            
            <h2>📋 按钮类型说明</h2>
            
            <div class="type-section">
                <h3>① ADB命令</h3>
                <p><strong>用途：</strong>执行ADB命令来操作Android设备</p>
                <p><strong>输入格式：</strong>直接输入ADB命令内容，<strong>不需要</strong>加 "adb -s {device}" 前缀</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    命令/路径: adb reboot<br>
                    说明: 重启设备<br><br>
                    
                    命令/路径: shell dumpsys battery<br>
                    说明: 查看电池信息<br><br>
                    
                    命令/路径: logcat -c<br>
                    说明: 清除logcat缓存
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>某些危险命令（如 push、pull、install、uninstall）被禁止使用，以确保系统安全。
                </div>
            </div>
            
            <div class="type-section">
                <h3>② Python脚本</h3>
                <p><strong>用途：</strong>执行自定义Python代码片段</p>
                <p><strong>输入格式：</strong></p>
                <ul>
                    <li><strong>命令/路径：</strong>可选，用于描述脚本功能</li>
                    <li><strong>Python脚本区域：</strong>必填，输入要执行的Python代码</li>
                </ul>
                <p><strong>可用模块：</strong>datetime、platform、os、json、math、random、time、subprocess</p>
                <p><strong>可用变量和函数：</strong></p>
                <ul>
                    <li><code>DEVICE_ID</code> - 当前连接的设备ID</li>
                    <li><code>adb_shell(cmd_list)</code> - 执行ADB shell命令，例如：<code>result = adb_shell(["shell", "getprop"])</code></li>
                </ul>
                <p><strong>示例：</strong></p>
                <div class="example">
                    # 执行ADB命令<br>
                    import subprocess as sp<br>
                    result = adb_shell(["shell", "getprop", "ro.product.model"])<br>
                    print(f"设备型号: {result.stdout}")<br><br>
                    
                    # 获取设备ID<br>
                    print(f"当前设备: {DEVICE_ID}")<br><br>
                    
                    # 获取当前时间<br>
                    import datetime<br>
                    print(f"当前时间: {datetime.datetime.now()}")
                </div>
                <div class="tip">
                    <strong>💡 提示：</strong>Python脚本在沙箱环境中执行，输出会显示在日志区域。使用 <code>adb_shell()</code> 函数可以执行ADB命令，会自动添加设备参数。
                </div>
            </div>
            
            <div class="type-section">
                <h3>③ 打开文件</h3>
                <p><strong>用途：</strong>使用默认程序打开指定文件或文件夹</p>
                <p><strong>输入格式：</strong>输入完整的文件路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Users\\用户名\\Desktop\\测试报告.docx<br>
                    C:\\Users\\用户名\\Documents\\项目文档.pdf<br>
                    D:\\工作文件夹
                </div>
            </div>
            
            <div class="type-section">
                <h3>④ 运行程序</h3>
                <p><strong>用途：</strong>启动指定的可执行程序或Python脚本</p>
                <p><strong>输入格式：</strong>输入完整的程序路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>Python脚本支持：</strong>如果运行.py文件，系统会自动传递设备ID作为命令行参数</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Program Files\\Notepad++\\notepad++.exe<br>
                    C:\\Windows\\System32\\calc.exe<br>
                    D:\\Tools\\script.py  ← Python脚本会自动收到设备ID参数
                </div>
                <div class="tip">
                    <strong>💡 提示：</strong>Python脚本可以通过 <code>sys.argv[1]</code> 获取设备ID，例如：<br>
                    <code>import sys<br>device_id = sys.argv[1] if len(sys.argv) > 1 else None</code>
                </div>
            </div>
            
            <div class="type-section">
                <h3>⑤ 系统命令</h3>
                <p><strong>用途：</strong>执行Windows/Linux/Mac系统命令</p>
                <p><strong>输入格式：</strong>直接输入系统命令</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    ipconfig /all<br>
                    dir C:\\<br>
                    ping 8.8.8.8 -n 4
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>系统命令会在30秒后超时，请避免使用长时间运行的命令。
                </div>
            </div>
            
            <div class="type-section">
                <h3>⑥ 打开网页</h3>
                <p><strong>用途：</strong>在默认浏览器中打开指定的网页地址</p>
                <p><strong>输入格式：</strong>输入网页地址（URL），支持http://或https://前缀，也可以省略前缀（会自动添加https://）</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    https://www.example.com<br>
                    http://www.google.com<br>
                    www.example.com  ← 会自动添加https://前缀<br>
                    github.com  ← 会自动添加https://前缀
                </div>
                <div class="tip">
                    <strong>💡 提示：</strong>如果输入的地址没有http://或https://前缀，系统会自动添加https://前缀。网页会在系统默认浏览器中打开。
                </div>
            </div>
            
            <h2>🎯 按钮配置说明</h2>
            
            <ul>
                <li><strong>按钮名称：</strong>显示在界面上的按钮文字（必填）</li>
                <li><strong>按钮类型：</strong>选择按钮执行的操作类型（必选）</li>
                <li><strong>命令/路径：</strong>根据按钮类型填写相应内容（部分类型必填）</li>
                <li><strong>描述：</strong>按钮的详细说明，鼠标悬停时显示（可选）</li>
                <li><strong>所在Tab：</strong>按钮将显示在哪个选项卡（必选）</li>
                <li><strong>所在卡片：</strong>按钮将显示在哪个功能卡片中（必选）</li>
                <li><strong>启用此按钮：</strong>是否立即启用该按钮（可选）</li>
            </ul>
            
            <h2>✨ 使用技巧</h2>
            
            <ul>
                <li>为按钮起一个简洁明了的名称，方便快速识别</li>
                <li>合理使用描述字段，提供更多操作说明</li>
                <li>将相关功能的按钮放在同一个卡片中，便于管理</li>
                <li>对于常用操作，可以创建多个快捷按钮</li>
                <li>使用self.tr("导出")功能可以备份您的按钮配置</li>
                <li>使用self.tr("导入")功能可以在不同设备间共享配置</li>
            </ul>
            
            <div class="tip">
                <strong>💡 小贴士：</strong>如果不确定按钮是否正确配置，可以先测试一次，查看日志区域的输出结果。
            </div>
            
        </body>
        </html>
        """
        
        browser.setHtml(help_text)
        layout.addWidget(browser)
        
        # 关闭按钮
        close_btn = QPushButton(self.tr("关闭"))
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)
        
        help_dialog.exec()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建滚动内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        # 避免内容不足时把“基本信息”区域拉伸得过高：整体顶对齐，剩余空间留在底部
        scroll_layout.setAlignment(Qt.AlignTop)
        
        # 基本信息组（使用与Tab界面一致的样式：QLabel + QFrame）
        basic_container = QWidget()
        basic_layout = QVBoxLayout(basic_container)
        basic_layout.setContentsMargins(0, 0, 0, 0)
        basic_layout.setSpacing(4)  # 与Tab界面一致的紧凑间距
        
        # 标题
        basic_title = QLabel(self.tr("基本信息"))
        basic_title.setProperty("class", "section-title")
        basic_layout.addWidget(basic_title)
        
        # 卡片容器
        basic_card = QFrame()
        basic_card.setObjectName("card")
        add_card_shadow(basic_card)
        basic_card_layout = QVBoxLayout(basic_card)
        basic_card_layout.setContentsMargins(10, 1, 10, 1)
        basic_card_layout.setSpacing(8)
        
        # 统一标签宽度，确保对齐
        label_width = 85
        
        # 统一输入框和下拉框的固定宽度（像素值，不受对话框缩放影响）
        input_width = 200  # 固定宽度200像素
        
        # 第一行：按钮名称和按钮类型
        row1_layout = QHBoxLayout()
        name_label = QLabel(self.tr("按钮名称*:"))
        name_label.setFixedWidth(label_width)
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("例如：重启设备"))
        # 使用固定宽度，不会随对话框缩放而变化
        self.name_edit.setFixedWidth(input_width)
        # 设置大小策略为Fixed，确保宽度不会随窗口缩放改变
        self.name_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row1_layout.addWidget(name_label)
        row1_layout.addWidget(self.name_edit)
        row1_layout.addSpacing(20)  # 添加间距
        
        type_label = QLabel(self.tr("按钮类型*:"))
        type_label.setFixedWidth(label_width)
        type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        # 按钮类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            self.tr("ADB命令"), 
            self.tr("Python脚本"), 
            self.tr("打开文件"), 
            self.tr("运行程序"), 
            self.tr("系统命令"),
            self.tr("打开网页")
        ])
        self.type_combo.setCurrentIndex(0)  # 默认选择ADB命令
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        # 统一QComboBox和QLineEdit的高度和宽度（固定宽度）
        self.type_combo.setFixedHeight(self.name_edit.sizeHint().height())
        self.type_combo.setFixedWidth(input_width)
        # 设置大小策略为Fixed，确保宽度不会随窗口缩放改变
        self.type_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row1_layout.addWidget(type_label)
        row1_layout.addWidget(self.type_combo)
        basic_card_layout.addLayout(row1_layout)
        
        # 第二行：所在Tab和所在卡片
        row2_layout = QHBoxLayout()
        tab_label = QLabel(self.tr("所在Tab*:"))
        tab_label.setFixedWidth(label_width)
        tab_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.tab_combo = QComboBox()
        self.tab_combo.currentTextChanged.connect(self.on_tab_changed)
        # 统一高度和宽度（固定宽度）
        self.tab_combo.setFixedHeight(self.name_edit.sizeHint().height())
        self.tab_combo.setFixedWidth(input_width)
        # 设置大小策略为Fixed，确保宽度不会随窗口缩放改变
        self.tab_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row2_layout.addWidget(tab_label)
        row2_layout.addWidget(self.tab_combo)
        row2_layout.addSpacing(20)  # 添加间距
        
        card_label = QLabel(self.tr("所在卡片*:"))
        card_label.setFixedWidth(label_width)
        card_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.card_combo = QComboBox()
        # 统一高度和宽度（固定宽度）
        self.card_combo.setFixedHeight(self.name_edit.sizeHint().height())
        self.card_combo.setFixedWidth(input_width)
        # 设置大小策略为Fixed，确保宽度不会随窗口缩放改变
        self.card_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row2_layout.addWidget(card_label)
        row2_layout.addWidget(self.card_combo)
        basic_card_layout.addLayout(row2_layout)
        
        # 在card_combo创建之后刷新Tab列表
        self.refresh_tab_list()
        
        # 启用此按钮
        self.enabled_check = QCheckBox(self.tr("启用此按钮"))
        self.enabled_check.setChecked(True)
        basic_card_layout.addWidget(self.enabled_check)
        
        # 描述
        description_label = QLabel(self.tr("描述:"))
        # 固定标签高度，防止布局变化时被拉伸
        label_height = description_label.sizeHint().height()
        description_label.setFixedHeight(label_height)
        description_label.setMaximumHeight(label_height)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(self.tr("描述按钮的功能..."))
        self.description_edit.setMaximumHeight(52)
        basic_card_layout.addWidget(description_label)
        basic_card_layout.addWidget(self.description_edit)
        
        basic_layout.addWidget(basic_card)
        scroll_layout.addWidget(basic_container)
        
        # 高级设置组（用于脚本/命令输入或文件选择）（使用与Tab界面一致的样式）
        advanced_container = QWidget()
        advanced_layout = QVBoxLayout(advanced_container)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(4)  # 与Tab界面一致的紧凑间距
        
        # 标题（保存引用以便动态修改）
        self.advanced_title = QLabel(self.tr("高级设置"))
        self.advanced_title.setProperty("class", "section-title")
        advanced_layout.addWidget(self.advanced_title)
        
        # 卡片容器
        self.advanced_card = QFrame()
        self.advanced_card.setObjectName("card")
        add_card_shadow(self.advanced_card)
        advanced_card_layout = QVBoxLayout(self.advanced_card)
        advanced_card_layout.setContentsMargins(10, 1, 10, 1)
        advanced_card_layout.setSpacing(8)
        
        # 脚本/命令输入区域（用于ADB命令、系统命令、Python脚本）
        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText(self.tr("输入Python脚本代码..."))
        self.script_edit.setMaximumHeight(300)
        self.script_edit.setVisible(False)
        advanced_card_layout.addWidget(self.script_edit)
        
        # 文件路径输入区域（用于打开文件和运行程序）
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(self.tr("输入文件路径或点击浏览按钮选择..."))
        self.path_edit.setVisible(False)
        path_layout.addWidget(self.path_edit)
        
        self.file_browse_btn = QPushButton(self.tr("浏览文件"))
        self.file_browse_btn.clicked.connect(self.browse_file)
        self.file_browse_btn.setVisible(False)
        path_layout.addWidget(self.file_browse_btn)
        
        self.folder_browse_btn = QPushButton(self.tr("浏览文件夹"))
        self.folder_browse_btn.clicked.connect(self.browse_folder)
        self.folder_browse_btn.setVisible(False)
        path_layout.addWidget(self.folder_browse_btn)
        
        advanced_card_layout.addLayout(path_layout)
        advanced_layout.addWidget(self.advanced_card)
        scroll_layout.addWidget(advanced_container)
        # 让多余高度留在底部，保持各类型界面高度风格一致
        scroll_layout.addStretch(1)
        
        # 保存advanced_card引用，用于控制可见性
        self.advanced_group = advanced_container
        
        # 设置滚动区域的内容
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton(self.tr("保存"))
        self.save_btn.clicked.connect(self.save)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 初始化Card列表（在card_combo创建之后）
        self.on_tab_changed(self.tab_combo.currentText())
        
        # 初始化类型相关的UI（默认不选择类型，所以高级设置区域应该是隐藏的）
        self.on_type_changed(self.type_combo.currentText())
    
    def _apply_preset_values(self):
        """应用预设的tab和card值"""
        try:
            if self.preset_tab_name:
                # 设置tab
                index = self.tab_combo.findText(self.preset_tab_name)
                if index >= 0:
                    self.tab_combo.setCurrentIndex(index)
                    # 触发tab改变事件，更新card列表
                    self.on_tab_changed(self.preset_tab_name)
                    
                    # 设置card（需要在tab改变后）
                    if self.preset_card_name:
                        index = self.card_combo.findText(self.preset_card_name)
                        if index >= 0:
                            self.card_combo.setCurrentIndex(index)
        except Exception as e:
            from core.debug_logger import logger
            logger.exception(f"{self.tr('应用预设值失败:')} {e}")
    
    def refresh_tab_list(self):
        """刷新Tab列表"""
        self.tab_combo.clear()
        tabs = self.button_manager.get_available_tabs()
        self.tab_combo.addItems(tabs)
        
        # 如果有选中的Tab，触发Card列表更新
        if tabs:
            self.on_tab_changed(tabs[0])
    
    def on_tab_changed(self, tab_name):
        """Tab改变时更新Card列表"""
        self.card_combo.clear()
        cards = self.button_manager.get_available_cards(tab_name)
        self.card_combo.addItems(cards)
    
    def on_type_changed(self, type_text):
        """按钮类型改变时的处理"""
        # 如果未选择类型（空字符串），隐藏高级设置区域
        if not type_text or type_text.strip() == "":
            self.script_edit.setVisible(False)
            self.path_edit.setVisible(False)
            self.file_browse_btn.setVisible(False)
            self.folder_browse_btn.setVisible(False)
            self.advanced_group.setVisible(False)  # advanced_group现在是容器
            return
        
        type_map = {
            self.tr("ADB命令"): "adb",
            self.tr("Python脚本"): "python", 
            self.tr("打开文件"): "file",
            self.tr("运行程序"): "program",
            self.tr("系统命令"): "system",
            self.tr("打开网页"): "url"
        }
        
        button_type = type_map.get(type_text, None)
        if not button_type:
            # 如果不是已知的类型，隐藏高级设置
            self.script_edit.setVisible(False)
            self.path_edit.setVisible(False)
            self.file_browse_btn.setVisible(False)
            self.folder_browse_btn.setVisible(False)
            self.advanced_group.setVisible(False)
            return
        
        # file/program：使用“路径 + 浏览”，不再让用户手动输入多行路径
        if button_type in ["file", "program"]:
            self.script_edit.setVisible(False)
            self.path_edit.setVisible(True)
            self.file_browse_btn.setVisible(True)
            self.folder_browse_btn.setVisible(button_type == "file")
            self.advanced_title.setText(self.tr("路径"))
            self.advanced_group.setVisible(True)
            if button_type == "file":
                self.path_edit.setPlaceholderText(self.tr("点击右侧按钮选择文件或文件夹..."))
            else:
                self.path_edit.setPlaceholderText(self.tr("点击右侧按钮选择要运行的程序（支持 .exe / .py / .bat / .cmd）..."))
            return

        # 其它类型仍使用脚本/命令输入区域
        if button_type in ["adb", "system", "python", "url"]:
            self.script_edit.setVisible(True)
            self.script_edit.setMaximumHeight(300)
            self.path_edit.setVisible(False)
            self.file_browse_btn.setVisible(False)
            self.folder_browse_btn.setVisible(False)
            self.advanced_title.setText(self.tr("脚本\\命令"))
            self.advanced_group.setVisible(True)

            if button_type == "adb":
                self.script_edit.setPlaceholderText(self.tr("输入ADB命令（多行支持，不需要加 'adb -s {device}'）...\n例如：reboot\n例如：shell dumpsys battery"))
            elif button_type == "system":
                self.script_edit.setPlaceholderText(self.tr("输入系统命令（多行支持）...\n例如：dir\n例如：ipconfig /all"))
            elif button_type == "python":
                self.script_edit.setPlaceholderText(self.tr("输入Python脚本代码..."))
            elif button_type == "url":
                self.script_edit.setPlaceholderText(self.tr("输入网页地址（多行支持）...\n例如：https://www.example.com\n例如：www.google.com"))
        else:
            self.script_edit.setVisible(False)
            self.path_edit.setVisible(False)
            self.file_browse_btn.setVisible(False)
            self.folder_browse_btn.setVisible(False)
            self.advanced_group.setVisible(False)
    
    def browse_file(self):
        """浏览文件"""
        from PySide6.QtWidgets import QFileDialog
        
        type_text = self.type_combo.currentText()
        
        if type_text == self.tr("打开文件"):
            # 选择文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择要打开的文件"), "",
                self.tr("所有文件 (*.*)")
            )
            if file_path:
                self.path_edit.setText(file_path)
        elif type_text == self.tr("运行程序"):
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择要运行的程序"), "",
                self.tr("可执行文件/脚本 (*.exe *.py *.bat *.cmd);;可执行文件 (*.exe);;脚本 (*.py *.bat *.cmd)")
            )
            if file_path:
                self.path_edit.setText(file_path)
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择文件"), "",
                self.tr("所有文件 (*.*)")
            )
            if file_path:
                self.path_edit.setText(file_path)
    
    def browse_folder(self):
        """浏览文件夹"""
        from PySide6.QtWidgets import QFileDialog
        
        folder_path = QFileDialog.getExistingDirectory(
            self, self.tr("选择要打开的文件夹"), ""
        )
        if folder_path:
            self.path_edit.setText(folder_path)
    
    def load_data(self):
        """加载按钮数据"""
        self.name_edit.setText(self.button_data.get('name', ''))
        self.description_edit.setPlainText(self.button_data.get('description', ''))
        
        # 加载按钮类型
        button_type = self.button_data.get('type', 'adb')
        type_map = {
            'adb': self.tr('ADB命令'),
            'python': self.tr('Python脚本'),
            'file': self.tr('打开文件'),
            'program': self.tr('运行程序'),
            'system': self.tr('系统命令'),
            'url': self.tr('打开网页')
        }
        type_text = type_map.get(button_type, self.tr('ADB命令'))
        # 在ComboBox中查找，注意第一个选项是空字符串
        index = self.type_combo.findText(type_text)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # 根据类型加载内容
        command = self.button_data.get('command', '')
        if button_type in ['file', 'program']:
            # 文件/程序：加载到路径输入框
            self.path_edit.setText(command)
        elif button_type in ['adb', 'system', 'url']:
            # ADB命令、系统命令、打开网页：加载到script_edit
            self.script_edit.setPlainText(command)
        elif button_type == 'python':
            # Python脚本：加载script字段到script_edit
            script = self.button_data.get('script', '')
            self.script_edit.setPlainText(script)
        
        tab = self.button_data.get('tab', '')
        if tab:
            index = self.tab_combo.findText(tab)
            if index >= 0:
                self.tab_combo.setCurrentIndex(index)
                # 触发tab改变事件，更新card列表
                self.on_tab_changed(tab)
        
        card = self.button_data.get('card', '')
        if card:
            index = self.card_combo.findText(card)
            if index >= 0:
                self.card_combo.setCurrentIndex(index)
        
        self.enabled_check.setChecked(self.button_data.get('enabled', True))
    
    def save(self):
        """保存按钮"""
        name = self.name_edit.text().strip()
        button_type = self.type_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, self.tr("验证失败"), "请输入按钮名称")
            return
        
        # 检查是否选择了按钮类型
        if not button_type or button_type.strip() == "":
            QMessageBox.warning(self, self.tr("验证失败"), "请选择按钮类型")
            return
        
        # 根据按钮类型进行不同的验证
        if button_type == self.tr("ADB命令"):
            # 验证ADB命令
            command = self.script_edit.toPlainText().strip()
            if not command:
                QMessageBox.warning(self, self.tr("验证失败"), "请输入ADB命令")
                return
            if not self.button_manager.validate_command(command):
                reason = self.button_manager.get_blocked_reason(command)
                QMessageBox.warning(
                    self, self.tr("验证失败"),
                    f"{self.tr('ADB命令验证失败')}\n{reason if reason else self.tr('请检查命令是否正确')}"
                )
                return
        elif button_type == self.tr("Python脚本"):
            # 验证Python脚本
            script = self.script_edit.toPlainText().strip()
            if not script:
                QMessageBox.warning(self, self.tr("验证失败"), "请输入Python脚本代码")
                return
        elif button_type == self.tr("系统命令"):
            # 验证系统命令
            command = self.script_edit.toPlainText().strip()
            if not command:
                QMessageBox.warning(self, self.tr("验证失败"), "请输入系统命令")
                return
        elif button_type == self.tr("打开文件"):
            path = self.path_edit.text().strip()
            if not path:
                QMessageBox.warning(self, self.tr("验证失败"), self.tr("请选择要打开的文件或文件夹"))
                return
            import os
            if not os.path.exists(path):
                QMessageBox.warning(self, self.tr("验证失败"), f"{self.tr('文件/文件夹不存在:')}\n{path}")
                return
        elif button_type == self.tr("运行程序"):
            path = self.path_edit.text().strip()
            if not path:
                QMessageBox.warning(self, self.tr("验证失败"), self.tr("请选择要运行的程序"))
                return
            import os
            if not os.path.exists(path):
                QMessageBox.warning(self, self.tr("验证失败"), f"{self.tr('程序不存在:')}\n{path}")
                return
            lower = path.lower()
            if not (lower.endswith('.exe') or lower.endswith('.py') or lower.endswith('.bat') or lower.endswith('.cmd')):
                QMessageBox.warning(self, self.tr("验证失败"), self.tr("仅支持选择 .exe / .py / .bat / .cmd 文件"))
                return
        elif button_type == self.tr("打开网页"):
            # 验证网页地址
            url = self.script_edit.toPlainText().strip()
            if not url:
                QMessageBox.warning(self, self.tr("验证失败"), "请输入网页地址")
                return
        
        self.accept()
    
    def get_button_data(self):
        """获取按钮数据"""
        # 获取按钮类型
        current_text = self.type_combo.currentText()
        type_map = {
            self.tr("ADB命令"): "adb",
            self.tr("Python脚本"): "python", 
            self.tr("打开文件"): "file",
            self.tr("运行程序"): "program",
            self.tr("系统命令"): "system",
            self.tr("打开网页"): "url"
        }
        button_type = type_map.get(current_text, "adb")
        
        # 根据类型获取command字段
        if button_type in ['file', 'program']:
            command = self.path_edit.text().strip()
        elif button_type in ['adb', 'system', 'url']:
            command = self.script_edit.toPlainText().strip()
        elif button_type == 'python':
            # Python脚本：command可以为空，使用script字段
            command = ''
        else:
            command = ''
        
        data = {
            'name': self.name_edit.text().strip(),
            'type': button_type,
            'command': command,
            'tab': self.tab_combo.currentText(),
            'card': self.card_combo.currentText(),
            'enabled': self.enabled_check.isChecked(),
            'description': self.description_edit.toPlainText().strip()
        }
        
        # 如果是Python脚本，添加脚本内容
        if button_type == 'python':
            data['script'] = self.script_edit.toPlainText().strip()
        
        return data

