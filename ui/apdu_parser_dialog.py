#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APDU 解析器对话框 - 集成 SIM_APDU_Parser 核心功能
"""

import os
import sys
import re
from typing import List, Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QTextEdit, QTreeWidget, QTreeWidgetItem,
                           QFileDialog, QMessageBox, QSplitter,
                           QProgressBar, QComboBox, QCheckBox, QLineEdit,
                           QSizePolicy, QApplication, QWidget, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette
from ui.widgets.shadow_utils import add_card_shadow

# 延迟导入 SIM_APDU_Parser 核心模块
APDU_PARSER_AVAILABLE = False
ParseResult = None
Message = None
Apdu = None
Pipeline = None
load_text = None
MTKExtractor = None
GenericExtractor = None
classify_message = None
CatParser = None
EsimParser = None
NormalSimParser = None

def _import_sim_parser_modules():
    """延迟导入SIM_APDU_Parser模块"""
    global APDU_PARSER_AVAILABLE, ParseResult, Message, Apdu, Pipeline
    global load_text, MTKExtractor, GenericExtractor, classify_message
    global CatParser, EsimParser, NormalSimParser
    
    if APDU_PARSER_AVAILABLE:
        return True
    
    # 添加详细的调试信息
    print("[DEBUG] ===== Starting SIM_APDU_Parser module import =====")
    print(f"[DEBUG] Current sys.path: {sys.path[:3]}...")  # 只显示前3个路径
    
    # 在PyInstaller打包环境中，使用sys._MEIPASS获取资源路径
    # 在开发环境中，使用__file__计算路径
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller打包环境：SIM_APDU_Parser在sys._MEIPASS中
        # 在打包环境中，SIM_APDU_Parser目录本身就在sys._MEIPASS中，所以将sys._MEIPASS添加到sys.path
        base_path = sys._MEIPASS
        sim_parser_parent_path = base_path  # 父目录就是sys._MEIPASS
        sim_parser_path = os.path.join(base_path, 'SIM_APDU_Parser')
        print(f"[DEBUG] PyInstaller environment detected, using sys._MEIPASS: {base_path}")
    else:
        # 开发环境：使用__file__计算路径
        # 需要将SIM_APDU_Parser的父目录添加到sys.path，而不是SIM_APDU_Parser本身
        sim_parser_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'SIM_APDU_Parser')
        sim_parser_parent_path = os.path.dirname(sim_parser_path)  # 父目录
        print(f"[DEBUG] Development environment, using __file__: {sim_parser_path}")
        print(f"[DEBUG] Parent path (to add to sys.path): {sim_parser_parent_path}")
    
    print(f"[DEBUG] SIM_APDU_Parser path: {sim_parser_path}")
    print(f"[DEBUG] SIM_APDU_Parser path exists: {os.path.exists(sim_parser_path)}")
    print(f"[DEBUG] core directory exists: {os.path.exists(os.path.join(sim_parser_path, 'core'))}")
    print(f"[DEBUG] models.py exists: {os.path.exists(os.path.join(sim_parser_path, 'core', 'models.py'))}")
    print(f"[DEBUG] pipeline.py exists: {os.path.exists(os.path.join(sim_parser_path, 'pipeline.py'))}")
    
    # 检查Python路径：需要将SIM_APDU_Parser的父目录添加到sys.path，而不是SIM_APDU_Parser本身
    # 这样才能使用 from SIM_APDU_Parser.pipeline import Pipeline
    if sim_parser_parent_path not in sys.path:
        print(f"[DEBUG] Adding SIM_APDU_Parser parent path to sys.path: {sim_parser_parent_path}")
        sys.path.insert(0, sim_parser_parent_path)
    else:
        print(f"[DEBUG] SIM_APDU_Parser parent path already in sys.path: {sim_parser_parent_path}")
    
    print(f"[DEBUG] Updated sys.path: {sys.path[:3]}...")
        
    try:
        print("[DEBUG] Trying to import SIM_APDU_Parser modules with absolute imports...")
        
        # 使用绝对导入
        print("[DEBUG] Step 1: Importing SIM_APDU_Parser.pipeline...")
        from SIM_APDU_Parser.pipeline import Pipeline
        print("[DEBUG] SIM_APDU_Parser.pipeline import successful")
        
        print("[DEBUG] Step 2: Importing SIM_APDU_Parser.core.models...")
        from SIM_APDU_Parser.core.models import ParseResult, Message, Apdu
        print("[DEBUG] SIM_APDU_Parser.core.models import successful")
        
        print("[DEBUG] Step 3: Importing SIM_APDU_Parser.data_io.loaders...")
        from SIM_APDU_Parser.data_io.loaders import load_text
        print("[DEBUG] SIM_APDU_Parser.data_io.loaders import successful")
        
        print("[DEBUG] Step 4: Importing SIM_APDU_Parser.data_io.extractors...")
        from SIM_APDU_Parser.data_io.extractors.mtk import MTKExtractor
        from SIM_APDU_Parser.data_io.extractors.generic import GenericExtractor
        print("[DEBUG] SIM_APDU_Parser.data_io.extractors import successful")
        
        print("[DEBUG] Step 5: Importing SIM_APDU_Parser.classify.rules...")
        from SIM_APDU_Parser.classify.rules import classify_message
        print("[DEBUG] SIM_APDU_Parser.classify.rules import successful")
        
        print("[DEBUG] Step 6: Importing SIM_APDU_Parser.parsers.base...")
        from SIM_APDU_Parser.parsers.base import CatParser, EsimParser, NormalSimParser
        print("[DEBUG] SIM_APDU_Parser.parsers.base import successful")
        
        APDU_PARSER_AVAILABLE = True
        print("[DEBUG] ===== SIM_APDU_Parser module import successful! =====")
        return True
    except ImportError as e:
        print(f"[DEBUG] SIM_APDU_Parser module import failed: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        import traceback
        print(f"[DEBUG] Detailed error info:")
        traceback.print_exc()
        APDU_PARSER_AVAILABLE = False
        return False

class ApduParseWorker(QThread):
    """APDU解析工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, file_path: str, prefer_mtk: bool = True, use_qualcomm: bool = False):
        super().__init__()
        self.file_path = file_path
        self.prefer_mtk = prefer_mtk
        self.use_qualcomm = use_qualcomm
    
    def run(self):
        try:
            print("[DEBUG] ApduParseWorker.run() started")
            print(f"[DEBUG] File path: {self.file_path}")
            print(f"[DEBUG] Prefer MTK: {self.prefer_mtk}")
            print(f"[DEBUG] Use Qualcomm: {self.use_qualcomm}")
            
            # 延迟导入模块
            print("[DEBUG] Calling _import_sim_parser_modules() in worker thread...")
            import_result = _import_sim_parser_modules()
            print(f"[DEBUG] _import_sim_parser_modules() returned: {import_result}")
            
            if not import_result:
                print("[DEBUG] Module import failed in worker thread")
                self.error.emit("SIM_APDU_Parser 模块不可用")
                return
            
            print("[DEBUG] Module import successful in worker thread")
            self.progress.emit(10)
            
            # 创建解析管道
            print("[DEBUG] Creating Pipeline instance...")
            print(f"[DEBUG] Pipeline parameters: prefer_mtk={self.prefer_mtk}, use_qualcomm={self.use_qualcomm}")
            pipeline = Pipeline(prefer_mtk=self.prefer_mtk, use_qualcomm=self.use_qualcomm)
            print("[DEBUG] Pipeline created successfully")
            self.progress.emit(30)
            
            # 解析文件
            print(f"[DEBUG] Starting file parsing: {self.file_path}")
            print("[DEBUG] Calling pipeline.run_from_file()...")
            results = pipeline.run_from_file(self.file_path)
            print(f"[DEBUG] File parsing completed, found {len(results)} results")
            self.progress.emit(80)
            
            self.progress.emit(100)
            print("[DEBUG] Emitting finished signal with results")
            self.finished.emit(results)
            
        except Exception as e:
            print(f"[DEBUG] Exception in ApduParseWorker.run(): {e}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            print("[DEBUG] Full traceback:")
            traceback.print_exc()
            self.error.emit(f"解析失败: {str(e)}")

class ApduParserDialog(QDialog):
    """APDU解析器对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.parse_results = []
        
        # 设置窗口标志，允许最小化和最大化
        # 使用 Qt.Dialog 但添加 WindowMinMaxButtonsHint 以支持最大化按钮
        self.setWindowFlags(Qt.Dialog | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("APDU 解析器")
        self.setMinimumSize(800, 600)
        self.setGeometry(100, 100, 1200, 800)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)  # 移除垂直间距
        main_layout.setContentsMargins(5, 5, 5, 5)  # 设置较小的边距
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)  # 设置较小的水平间距
        toolbar_layout.setContentsMargins(0, 0, 0, 0)  # 移除工具栏边距
        
        # 文件选择
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("font-weight: bold; color: #666;")
        toolbar_layout.addWidget(self.file_label)
        
        self.load_btn = QPushButton("加载文件")
        self.load_btn.clicked.connect(self.load_file)
        toolbar_layout.addWidget(self.load_btn)
        
        # 解析选项
        toolbar_layout.addWidget(QLabel("解析器:"))
        self.parser_combo = QComboBox()
        self.parser_combo.addItems(["MTK", "通用", "Qualcomm"])
        toolbar_layout.addWidget(self.parser_combo)
        
        # 解析按钮
        self.parse_btn = QPushButton("开始解析")
        self.parse_btn.clicked.connect(self.start_parse)
        self.parse_btn.setEnabled(False)
        toolbar_layout.addWidget(self.parse_btn)
        
        # 筛选类别下拉菜单
        toolbar_layout.addWidget(QLabel("筛选类别:"))
        self.filter_btn = QPushButton("全部")
        self.filter_btn.setCheckable(False)
        toolbar_layout.addWidget(self.filter_btn)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # 搜索和筛选工具栏
        search_toolbar_layout = QHBoxLayout()
        search_toolbar_layout.setSpacing(5)  # 设置较小的水平间距
        search_toolbar_layout.setContentsMargins(0, 0, 0, 0)  # 移除工具栏边距
        
        # 搜索框
        search_toolbar_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_apdu_list)
        search_toolbar_layout.addWidget(self.search_edit)
        
        # 搜索按钮
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.filter_apdu_list)
        search_toolbar_layout.addWidget(self.search_btn)
        
        # 清除筛选按钮
        self.clear_filter_btn = QPushButton("清除筛选")
        self.clear_filter_btn.clicked.connect(self.clear_filters)
        search_toolbar_layout.addWidget(self.clear_filter_btn)
        
        # 搜索右侧详情复选框
        self.search_details_checkbox = QCheckBox("搜索右侧详情")
        self.search_details_checkbox.stateChanged.connect(self.filter_apdu_list)
        search_toolbar_layout.addWidget(self.search_details_checkbox)
        
        # 使用正则表达式复选框
        self.use_regex_checkbox = QCheckBox("使用正则表达式")
        self.use_regex_checkbox.stateChanged.connect(self.filter_apdu_list)
        search_toolbar_layout.addWidget(self.use_regex_checkbox)
        
        # 解析单条APDU按钮
        self.parse_single_btn = QPushButton("解析单条 APDU")
        self.parse_single_btn.clicked.connect(self.parse_single_apdu)
        self.parse_single_btn.setEnabled(True)  # 默认启用，允许手动输入APDU
        search_toolbar_layout.addWidget(self.parse_single_btn)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        search_toolbar_layout.addWidget(self.status_label)
        
        search_toolbar_layout.addStretch()
        main_layout.addLayout(search_toolbar_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 主内容区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：APDU列表（使用与Tab界面一致的样式：QLabel + QFrame）
        left_container = QWidget()
        left_container_layout = QVBoxLayout(left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(4)
        
        left_title = QLabel("APDU 事件列表")
        left_title.setProperty("class", "section-title")
        left_container_layout.addWidget(left_title)
        
        left_card = QFrame()
        left_card.setObjectName("card")
        add_card_shadow(left_card)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(10, 1, 10, 1)
        left_layout.setSpacing(8)
        
        self.apdu_tree = QTreeWidget()
        self.apdu_tree.setHeaderLabels(["序号", "方向", "标题"])
        self.apdu_tree.itemClicked.connect(self.on_apdu_selected)
        # 设置APDU树的大小策略，让它占据所有可用空间
        self.apdu_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 启用上下文菜单
        self.apdu_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.apdu_tree.customContextMenuRequested.connect(self.show_apdu_context_menu)
        left_layout.addWidget(self.apdu_tree, 1)  # 伸缩因子设为1
        
        left_container_layout.addWidget(left_card)
        splitter.addWidget(left_container)
        
        # 右侧：详细信息（使用与Tab界面一致的样式：QLabel + QFrame）
        right_container = QWidget()
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setContentsMargins(0, 0, 0, 0)
        right_container_layout.setSpacing(4)
        
        right_title = QLabel("APDU 详细信息")
        right_title.setProperty("class", "section-title")
        right_container_layout.addWidget(right_title)
        
        right_card = QFrame()
        right_card.setObjectName("card")
        add_card_shadow(right_card)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(10, 1, 10, 1)
        right_layout.setSpacing(8)
        
        # 解析结果树（移到上面）
        self.parse_tree = QTreeWidget()
        self.parse_tree.setHeaderLabels(["字段", "说明"])
        # 设置解析结果树的大小策略
        self.parse_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 设置列宽度 - 根据内容自动调整
        self.parse_tree.header().setStretchLastSection(True)  # 说明列自动拉伸填充剩余空间
        # 启用上下文菜单
        self.parse_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parse_tree.customContextMenuRequested.connect(self.show_parse_context_menu)
        # 注意：resizeColumnToContents() 需要在有内容后调用，所以我们在填充数据后调用
        right_layout.addWidget(QLabel("解析结果:"))
        right_layout.addWidget(self.parse_tree, 1)  # 伸缩因子设为1，占据大部分空间
        
        # APDU原始数据（移到下面）
        self.apdu_raw_text = QTextEdit()
        self.apdu_raw_text.setMaximumHeight(30)  # 调整为一行高度
        self.apdu_raw_text.setPlaceholderText("APDU 原始数据")
        right_layout.addWidget(QLabel("原始数据:"))
        right_layout.addWidget(self.apdu_raw_text, 0)  # 伸缩因子设为0，保持固定高度
        
        right_container_layout.addWidget(right_card)
        splitter.addWidget(right_container)
        
        # 设置分割比例
        splitter.setSizes([400, 800])
        # 设置分割器的大小策略，让它占据剩余空间
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(splitter, 1)  # 伸缩因子设为1，占据剩余空间
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # 初始化可复选下拉菜单
        self.setup_filter_combo()
        
    def setup_filter_combo(self):
        """设置可复选的下拉菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        
        # 创建菜单
        self.filter_menu = QMenu(self.filter_btn)
        
        # 创建复选框动作
        self.filter_cat_action = QAction("CAT APDU", self.filter_menu)
        self.filter_cat_action.setCheckable(True)
        self.filter_cat_action.setChecked(True)
        self.filter_cat_action.triggered.connect(self.on_filter_changed)
        
        self.filter_esim_action = QAction("eSIM APDU", self.filter_menu)
        self.filter_esim_action.setCheckable(True)
        self.filter_esim_action.setChecked(True)
        self.filter_esim_action.triggered.connect(self.on_filter_changed)
        
        self.filter_generic_action = QAction("Generic APDU", self.filter_menu)
        self.filter_generic_action.setCheckable(True)
        self.filter_generic_action.setChecked(False)
        self.filter_generic_action.triggered.connect(self.on_filter_changed)
        
        # 添加动作到菜单
        self.filter_menu.addAction(self.filter_cat_action)
        self.filter_menu.addAction(self.filter_esim_action)
        self.filter_menu.addAction(self.filter_generic_action)
        
        # 设置按钮菜单
        self.filter_btn.setMenu(self.filter_menu)
        
        # 更新显示文本
        self.update_filter_combo_text()
        
    def update_filter_combo_text(self):
        """更新下拉菜单的显示文本"""
        selected = []
        if self.filter_cat_action.isChecked():
            selected.append("CAT APDU")
        if self.filter_esim_action.isChecked():
            selected.append("eSIM APDU")
        if self.filter_generic_action.isChecked():
            selected.append("Generic APDU")
        
        if not selected:
            self.filter_btn.setText("无筛选")
        elif len(selected) == 3:
            self.filter_btn.setText("全部")
        else:
            self.filter_btn.setText(", ".join(selected))
    
    def on_filter_changed(self):
        """筛选选项改变时的回调"""
        self.update_filter_combo_text()
        self.filter_apdu_list()
        
    def load_file(self):
        """加载文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择APDU日志文件", "", 
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(f"文件: {os.path.basename(file_path)}")
            self.parse_btn.setEnabled(True)
            self.parse_single_btn.setEnabled(True)  # 保持启用状态
            self.status_label.setText("文件已加载，准备解析")
            self.apdu_tree.clear()
            self.parse_tree.clear()
            self.apdu_raw_text.clear()
            self.clear_filters()
    
    def start_parse(self):
        """开始解析"""
        
        
        if not self.current_file:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return
        
        print("[DEBUG] Calling _import_sim_parser_modules()...")
        # 延迟导入模块
        import_result = _import_sim_parser_modules()
        print(f"[DEBUG] _import_sim_parser_modules() returned: {import_result}")
        
        if not import_result:
            print("[DEBUG] Module import failed, showing error dialog")
            # 显示详细的错误信息
            QMessageBox.critical(self, "错误", f"SIM_APDU_Parser 模块不可用\n导入结果: {import_result}\n请检查控制台输出获取详细信息")
            return
        
        print("[DEBUG] Module import successful, continuing with parsing...")
        
        # 获取解析选项
        parser_type = self.parser_combo.currentText()
        prefer_mtk = parser_type == "MTK"
        use_qualcomm = parser_type == "Qualcomm"
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.parse_btn.setEnabled(False)
        self.parse_single_btn.setEnabled(False)
        self.status_label.setText("正在解析...")
        
        # 启动解析线程
        self.parse_worker = ApduParseWorker(self.current_file, prefer_mtk, use_qualcomm)
        self.parse_worker.progress.connect(self.progress_bar.setValue)
        self.parse_worker.finished.connect(self.on_parse_finished)
        self.parse_worker.error.connect(self.on_parse_error)
        self.parse_worker.start()
    
    def on_parse_finished(self, results: List):
        """解析完成"""
        self.parse_results = results
        self.populate_apdu_list()
        
        self.progress_bar.setVisible(False)
        self.parse_btn.setEnabled(True)
        self.parse_single_btn.setEnabled(True)  # 始终启用，允许手动输入APDU
        self.status_label.setText(f"解析完成 - {len(results)} 个事件")
        
        QMessageBox.information(self, "完成", f"解析完成，共找到 {len(results)} 个APDU事件")
    
    def on_parse_error(self, error_msg: str):
        """解析错误"""
        self.progress_bar.setVisible(False)
        self.parse_btn.setEnabled(True)
        self.parse_single_btn.setEnabled(True)  # 保持启用，允许手动输入APDU
        self.status_label.setText("解析失败")
        
        QMessageBox.critical(self, "解析错误", error_msg)
    
    def populate_apdu_list(self):
        """填充APDU列表"""
        self.apdu_tree.clear()
        
        for i, result in enumerate(self.parse_results):
            # 创建树项
            item = QTreeWidgetItem()
            item.setText(0, f"{i+1}")  # 序号
            item.setText(1, result.direction_hint)  # 方向
            item.setText(2, result.title)  # 标题
            
            # 设置颜色
            color = self.get_direction_color(result.direction_hint)
            item.setForeground(1, QColor(color))
            
            # 存储结果数据
            item.setData(0, Qt.UserRole, result)
            
            self.apdu_tree.addTopLevelItem(item)
    
    def get_direction_color(self, direction: str) -> str:
        """获取方向颜色"""
        color_map = {
            "UICC=>TERMINAL": "#d62728",  # 红色
            "TERMINAL=>UICC": "#1f77b4",  # 蓝色
            "ESIM=>LPA": "#2ca02c",       # 绿色
            "LPA=>ESIM": "#9467bd",       # 紫色
            "SIM=>UE": "#ff7f0e",         # 橙色
            "UE=>SIM": "#17becf",         # 青色
        }
        return color_map.get(direction, "#7f7f7f")
    
    def on_apdu_selected(self, item: QTreeWidgetItem):
        """APDU项被选中"""
        result = item.data(0, Qt.UserRole)
        if not result:
            return
        
        # 显示原始数据
        self.apdu_raw_text.setText(result.message.raw)
        
        # 显示解析结果
        self.populate_parse_tree(result)
    
    def populate_parse_tree(self, result):
        """填充解析结果树"""
        self.parse_tree.clear()
        
        if not result.root:
            return
        
        # 递归添加解析节点
        self.add_parse_node(self.parse_tree, result.root)
        
        # 默认展开解析结果树
        self.parse_tree.expandAll()
        
        # 根据内容自动调整列宽度
        self.parse_tree.resizeColumnToContents(0)  # 字段列根据内容调整
        self.parse_tree.resizeColumnToContents(1)  # 说明列根据内容调整
    
    def add_parse_node(self, parent: QTreeWidgetItem, node, level: int = 0):
        """递归添加解析节点"""
        item = QTreeWidgetItem(parent)
        item.setText(0, "  " * level + node.name)
        item.setText(1, node.value or "")  # 将值放到"说明"列中
        
        # 默认展开所有节点
        item.setExpanded(True)
        
        for child in node.children:
            self.add_parse_node(item, child, level + 1)
    
    def filter_apdu_list(self):
        """过滤APDU列表"""
        filter_text = self.search_edit.text()
        search_details = self.search_details_checkbox.isChecked()
        use_regex = self.use_regex_checkbox.isChecked()
        
        # 获取选中的筛选类别
        filter_cat = self.filter_cat_action.isChecked()
        filter_esim = self.filter_esim_action.isChecked()
        filter_generic = self.filter_generic_action.isChecked()
        
        # 如果使用正则表达式，编译正则表达式
        regex_pattern = None
        if use_regex and filter_text:
            try:
                regex_pattern = re.compile(filter_text, re.IGNORECASE)
            except re.error as e:
                # 正则表达式错误，显示错误信息但不阻止搜索
                QMessageBox.warning(self, "正则表达式错误", f"无效的正则表达式: {e}\n将使用普通文本搜索。")
                use_regex = False
                regex_pattern = None
        
        for i in range(self.apdu_tree.topLevelItemCount()):
            item = self.apdu_tree.topLevelItem(i)
            result = item.data(0, Qt.UserRole)
            
            # 类别筛选 - 根据消息类型筛选
            category_match = True
            if result and hasattr(result, 'msg_type'):
                msg_type = result.msg_type
                
                if msg_type == 'proactive' and not filter_cat:
                    category_match = False
                elif msg_type == 'esim' and not filter_esim:
                    category_match = False
                elif msg_type == 'normal_sim' and not filter_generic:
                    category_match = False
            
            # 文本搜索
            text_match = True
            if filter_text:
                # 搜索标题
                search_text = item.text(2)
                
                # 如果启用搜索右侧详情，也搜索解析结果
                if search_details and result and result.root:
                    search_text += " " + self.get_parse_tree_text(result.root)
                
                # 根据是否使用正则表达式进行匹配
                if use_regex and regex_pattern:
                    # 使用正则表达式搜索（不区分大小写）
                    text_match = bool(regex_pattern.search(search_text))
                else:
                    # 使用普通文本搜索（不区分大小写）
                    text_match = filter_text.lower() in search_text.lower()
            
            # 综合筛选
            item.setHidden(not (category_match and text_match))
    
    def get_parse_tree_text(self, node) -> str:
        """递归获取解析树的所有文本"""
        text = f"{node.name} {node.value or ''} {node.hint or ''}"
        for child in node.children:
            text += " " + self.get_parse_tree_text(child)
        return text
    
    def clear_filters(self):
        """清除所有筛选"""
        # 重置复选框为默认状态
        self.filter_cat_action.setChecked(True)
        self.filter_esim_action.setChecked(True)
        self.filter_generic_action.setChecked(False)
        
        # 更新显示文本
        self.update_filter_combo_text()
        
        # 清除搜索框
        self.search_edit.clear()
        
        # 重置搜索详情选项
        self.search_details_checkbox.setChecked(False)
        self.use_regex_checkbox.setChecked(False)
        
        # 应用筛选
        self.filter_apdu_list()
    
    def parse_single_apdu(self):
        """解析单条APDU"""
        # 显示单条APDU解析对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("单条APDU解析")
        dialog.setGeometry(200, 200, 700, 600)
        
        layout = QVBoxLayout(dialog)
        
        # APDU输入区域
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("APDU数据:"))
        apdu_input = QLineEdit()
        apdu_input.setPlaceholderText("请输入APDU数据，如: 00A40004023F0000")
        input_layout.addWidget(apdu_input)
        
        parse_btn = QPushButton("解析")
        input_layout.addWidget(parse_btn)
        layout.addLayout(input_layout)
        
        # 解析结果显示区域
        layout.addWidget(QLabel("解析结果:"))
        parse_text = QTextEdit()
        parse_text.setReadOnly(True)
        parse_text.setPlaceholderText("解析结果将显示在这里...")
        layout.addWidget(parse_text)
        
        # 解析函数
        def do_parse():
            apdu_data = apdu_input.text().strip()
            if not apdu_data:
                QMessageBox.warning(dialog, "警告", "请输入APDU数据")
                return
            
            try:
                # 延迟导入模块
                import_result = _import_sim_parser_modules()
                if not import_result:
                    QMessageBox.critical(dialog, "错误", "SIM_APDU_Parser 模块不可用")
                    return
                
                # 创建临时Message对象用于分类
                from SIM_APDU_Parser.core.models import Message
                temp_message = Message(raw=apdu_data, direction="unknown")
                
                # 分类消息
                from SIM_APDU_Parser.classify.rules import classify_message
                msg_type, direction, tag, title = classify_message(temp_message)
                
                # 使用正确的direction创建最终的Message对象
                message = Message(raw=apdu_data, direction=direction)
                
                # 选择解析器
                from SIM_APDU_Parser.parsers.base import CatParser, EsimParser, NormalSimParser
                
                if msg_type.name == "CAT":
                    parser = CatParser()
                elif msg_type.name == "ESIM":
                    parser = EsimParser()
                else:
                    parser = NormalSimParser()
                
                # 解析
                result = parser.parse(message)
                
                # 显示结果
                result_text = f"标题: {title}\n"
                result_text += f"方向: {direction}\n"
                result_text += f"类型: {msg_type.name}\n"
                result_text += f"原始数据: {apdu_data}\n\n"
                result_text += "解析结果:\n"
                
                if result and result.root:
                    result_text += self.format_parse_tree(result.root)
                else:
                    result_text += "无解析结果"
                
                parse_text.setText(result_text)
                
            except Exception as e:
                parse_text.setText(f"解析失败: {str(e)}")
                import traceback
                traceback.print_exc()
        
        parse_btn.clicked.connect(do_parse)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(lambda: (apdu_input.clear(), parse_text.clear()))
        button_layout.addWidget(clear_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def format_parse_tree(self, node, level: int = 0) -> str:
        """格式化解析树为文本"""
        indent = "  " * level
        text = f"{indent}{node.name}: {node.value or ''}"
        if node.hint:
            text += f" ({node.hint})"
        text += "\n"
        
        for child in node.children:
            text += self.format_parse_tree(child, level + 1)
        
        return text
    
    def show_apdu_context_menu(self, position):
        """显示APDU事件列表的上下文菜单"""
        item = self.apdu_tree.itemAt(position)
        if not item:
            return
        
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self.apdu_tree)
        
        # 复制选中行
        copy_action = QAction("复制选中行", self.apdu_tree)
        copy_action.triggered.connect(lambda: self.copy_apdu_item(item))
        menu.addAction(copy_action)
        
        # 复制所有内容
        copy_all_action = QAction("复制所有APDU", self.apdu_tree)
        copy_all_action.triggered.connect(self.copy_all_apdu_items)
        menu.addAction(copy_all_action)
        
        menu.exec_(self.apdu_tree.mapToGlobal(position))
    
    def show_parse_context_menu(self, position):
        """显示解析结果的上下文菜单"""
        item = self.parse_tree.itemAt(position)
        if not item:
            return
        
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self.parse_tree)
        
        # 复制选中项
        copy_action = QAction("复制选中项", self.parse_tree)
        copy_action.triggered.connect(lambda: self.copy_parse_item(item))
        menu.addAction(copy_action)
        
        # 复制所有解析结果
        copy_all_action = QAction("复制所有解析结果", self.parse_tree)
        copy_all_action.triggered.connect(self.copy_all_parse_items)
        menu.addAction(copy_all_action)
        
        menu.exec_(self.parse_tree.mapToGlobal(position))
    
    def copy_apdu_item(self, item):
        """复制APDU事件列表的选中行"""
        if not item:
            return
        
        # 获取行的所有列内容
        row_data = []
        for col in range(self.apdu_tree.columnCount()):
            row_data.append(item.text(col))
        
        # 用制表符分隔
        text = "\t".join(row_data)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def copy_all_apdu_items(self):
        """复制所有APDU事件"""
        if self.apdu_tree.topLevelItemCount() == 0:
            return
        
        lines = []
        for i in range(self.apdu_tree.topLevelItemCount()):
            item = self.apdu_tree.topLevelItem(i)
            row_data = []
            for col in range(self.apdu_tree.columnCount()):
                row_data.append(item.text(col))
            lines.append("\t".join(row_data))
        
        text = "\n".join(lines)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def copy_parse_item(self, item):
        """复制解析结果的选中项"""
        if not item:
            return
        
        # 获取项的所有列内容
        row_data = []
        for col in range(self.parse_tree.columnCount()):
            row_data.append(item.text(col))
        
        # 用制表符分隔
        text = "\t".join(row_data)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def copy_all_parse_items(self):
        """复制所有解析结果"""
        if self.parse_tree.topLevelItemCount() == 0:
            return
        
        lines = []
        self._collect_parse_items(self.parse_tree.invisibleRootItem(), lines)
        
        text = "\n".join(lines)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def _collect_parse_items(self, parent_item, lines, level=0):
        """递归收集解析结果项"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            row_data = []
            for col in range(self.parse_tree.columnCount()):
                row_data.append(item.text(col))
            
            # 添加缩进表示层级
            indent = "  " * level
            lines.append(indent + "\t".join(row_data))
            
            # 递归处理子项
            if item.childCount() > 0:
                self._collect_parse_items(item, lines, level + 1)
