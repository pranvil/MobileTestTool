#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一管理对话框
整合Tab管理和按钮管理功能，并提供配置导出/导入功能
"""

import os
import json
import datetime
from PySide6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QMessageBox, QFileDialog,
                             QListWidget, QListWidgetItem, QCheckBox, QScrollArea, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QFormLayout, QLineEdit, QTextEdit, QComboBox,
                             QLabel, QSplitter, QFrame, QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# 延迟导入，支持 PyInstaller 环境，以及 SIM Reader 对话框可能修改 sys.path/sys.modules 的情况
#
# 背景：项目中存在多个同名包 `core`（项目根目录、sim_reader/core、SIM_APDU_Parser/core），
# 如果某个功能临时把 sys.path 调整为优先命中其它 core，会导致后续 `from core.debug_logger` 概率性失败。
def _load_app_logger():
    """确保导入到的是项目自身的 core.debug_logger（而不是 sim_reader/core 等同名包）。"""
    try:
        from core.debug_logger import logger as _logger
        return _logger
    except ModuleNotFoundError:
        import sys
        import os
        import importlib

        # 计算项目根目录（开发环境）或 PyInstaller base_path（打包环境）
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            project_root = sys._MEIPASS
        else:
            current_file = os.path.abspath(__file__)
            # ui/unified_manager_dialog.py -> ui -> 项目根目录
            project_root = os.path.dirname(os.path.dirname(current_file))

        normalized_project_root = os.path.normpath(os.path.abspath(project_root))
        sim_reader_path = os.path.normpath(os.path.abspath(os.path.join(project_root, "sim_reader")))

        # 修复 sys.path：确保项目根目录（或 _MEIPASS）在最前面
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        else:
            # 置顶，避免被其它路径抢先命中同名包
            try:
                sys.path.remove(project_root)
            except ValueError:
                pass
            sys.path.insert(0, project_root)

        def _module_file(mod):
            return getattr(mod, "__file__", None) or ""

        def _is_wrong_core_module(mod) -> bool:
            mod_file = _module_file(mod)
            if not mod_file:
                # 没有 __file__ 的 core 很可能是命名空间包/脏状态，宁可清掉重来
                return True
            normalized_mod_file = os.path.normpath(os.path.abspath(mod_file))
            # 来自 sim_reader 的 core，一律视为冲突
            if sim_reader_path in normalized_mod_file:
                return True
            # 不在项目根目录内，也视为冲突（例如被其它子工程的 core 覆盖）
            if normalized_project_root not in normalized_mod_file:
                return True
            # 文件不存在，也视为脏缓存
            if not os.path.exists(mod_file):
                return True
            return False

        # 关键修复：如果 core 包本身已经被错误来源占用，必须先删掉 core 及其所有子模块缓存
        core_pkg = sys.modules.get("core")
        if core_pkg is not None and _is_wrong_core_module(core_pkg):
            for name in list(sys.modules.keys()):
                if name == "core" or name.startswith("core."):
                    sys.modules.pop(name, None)

        # 同理：即使 core 包没在 sys.modules，core.debug_logger 也可能有残留缓存
        if "core.debug_logger" in sys.modules:
            mod = sys.modules["core.debug_logger"]
            if _is_wrong_core_module(mod):
                sys.modules.pop("core.debug_logger", None)

        importlib.invalidate_caches()
        imported = importlib.import_module("core.debug_logger")
        return imported.logger


logger = _load_app_logger()
from ui.widgets.drag_drop_table import DragDropButtonTable
from ui.widgets.shadow_utils import add_card_shadow


class UnifiedManagerDialog(QDialog):
    """统一管理对话框"""
    
    def __init__(self, tab_config_manager, custom_button_manager, parent=None):
        super().__init__(parent)
        self.tab_config_manager = tab_config_manager
        self.custom_button_manager = custom_button_manager
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("自定义界面管理"))
        self.setModal(True)
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)  # 设置最小尺寸，允许调整高度和宽度
        
        # 存储控件引用
        self.tab_list_widget = None
        self.custom_card_list = None
        self.button_table = None
        self.current_selected_tab_id = None
        self.is_selected_custom_tab = False
        self.current_selected_card_name = None  # 当前选中的card名称
        self.current_selected_card_is_preset = False  # 当前选中的card是否为预置card
        self.all_buttons_data = []  # 存储所有按钮数据用于搜索
        self.search_filter_mode = 0  # 0=全局搜索, 1-7=按列搜索
        self.column_filters = []  # 列级过滤器控件列表 (combo, col_idx, label_text) 元组
        
        self.setup_ui()
        self.load_all_configs()

        self.custom_button_manager.buttons_updated.connect(self.load_buttons)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        self.main_splitter = splitter
        splitter.setObjectName("unified_manager_splitter")
        splitter.setHandleWidth(12)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(
            "QSplitter#unified_manager_splitter::handle {"
            "    background-color: rgba(255, 255, 255, 20);"
            "}"
            "QSplitter#unified_manager_splitter::handle:hover {"
            "    background-color: rgba(74, 163, 255, 120);"
            "}"
        )
        layout.addWidget(splitter)
        
        # 左侧：Tab管理
        left_widget = self.create_tab_management_widget()
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(left_widget)
        
        # 右侧：按钮管理
        right_widget = self.create_button_management_widget()
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(right_widget)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        # 设置分割器比例
        splitter.setSizes([400, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        handle = splitter.handle(1)
        if handle:
            handle.setCursor(Qt.SplitHCursor)
        splitter.splitterMoved.connect(self._on_splitter_moved)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📥 " + self.tr("导入配置"))
        self.import_btn.clicked.connect(self.import_config)
        self.import_btn.setAutoDefault(False)
        self.import_btn.setDefault(False)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 " + self.tr("导出配置"))
        self.export_btn.clicked.connect(self.export_config)
        self.export_btn.setAutoDefault(False)
        self.export_btn.setDefault(False)
        button_layout.addWidget(self.export_btn)
        
        self.refresh_btn = QPushButton("🔄 " + self.tr("刷新"))
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        self.refresh_btn.setAutoDefault(False)
        self.refresh_btn.setDefault(False)
        button_layout.addWidget(self.refresh_btn)
        
        self.reset_btn = QPushButton("🔄 " + self.tr("重置为默认"))
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.reset_btn.setAutoDefault(False)
        self.reset_btn.setDefault(False)
        self.reset_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        self.add_btn = QPushButton("➕ " + self.tr("添加"))
        self.add_btn.clicked.connect(self.add_button)
        self.add_btn.setAutoDefault(False)
        self.add_btn.setDefault(False)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ " + self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_button)
        self.edit_btn.setAutoDefault(False)
        self.edit_btn.setDefault(False)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ " + self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_button)
        self.delete_btn.setAutoDefault(False)
        self.delete_btn.setDefault(False)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
    
    def create_tab_management_widget(self):
        """创建Tab管理控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Tab管理组（使用与Tab界面一致的样式：QLabel + QFrame）
        tab_container = QWidget()
        tab_container_layout = QVBoxLayout(tab_container)
        tab_container_layout.setContentsMargins(0, 0, 0, 0)
        tab_container_layout.setSpacing(4)  # 与Tab界面一致的紧凑间距
        
        # 标题
        tab_title = QLabel(self.tr("Tab管理"))
        tab_title.setProperty("class", "section-title")
        tab_container_layout.addWidget(tab_title)
        
        # 卡片容器
        tab_card = QFrame()
        tab_card.setObjectName("card")
        add_card_shadow(tab_card)
        tab_layout = QVBoxLayout(tab_card)
        tab_layout.setContentsMargins(10, 1, 10, 1)
        tab_layout.setSpacing(8)

        self.tab_list_widget = QListWidget()
        self.tab_list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.tab_list_widget.itemSelectionChanged.connect(self.on_tab_selection_changed)
        self.tab_list_widget.setFocusPolicy(Qt.NoFocus)
        self.tab_list_widget.setStyleSheet("""
            QListWidget::item {
                padding: 4px;
                border: none;
            }
            QListWidget::item:selected {
                padding: 4px;
                border: none;
                background: rgba(74, 163, 255, 45%);
            }
        """)

        tab_content_layout = QHBoxLayout()
        tab_content_layout.addWidget(self.tab_list_widget)

        tab_button_widget = QWidget()
        tab_button_widget.setMinimumWidth(140)
        tab_button_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        tab_button_layout = QVBoxLayout(tab_button_widget)
        tab_button_layout.setContentsMargins(12, 0, 0, 0)
        tab_button_layout.setSpacing(10)
        tab_button_layout.setAlignment(Qt.AlignTop)

        self.add_tab_btn = QPushButton("➕ " + self.tr("添加Tab"))
        self.add_tab_btn.clicked.connect(self.show_add_tab_dialog)
        self.add_tab_btn.setAutoDefault(False)
        self.add_tab_btn.setDefault(False)
        self.add_tab_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tab_button_layout.addWidget(self.add_tab_btn)

        self.edit_tab_btn = QPushButton("✏️ " + self.tr("编辑Tab"))
        self.edit_tab_btn.clicked.connect(self.edit_custom_tab)
        self.edit_tab_btn.setAutoDefault(False)
        self.edit_tab_btn.setDefault(False)
        self.edit_tab_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tab_button_layout.addWidget(self.edit_tab_btn)

        self.delete_tab_btn = QPushButton("🗑️ " + self.tr("删除Tab"))
        self.delete_tab_btn.clicked.connect(self.delete_custom_tab)
        self.delete_tab_btn.setAutoDefault(False)
        self.delete_tab_btn.setDefault(False)
        self.delete_tab_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tab_button_layout.addWidget(self.delete_tab_btn)

        self.apply_btn = QPushButton("✅ " + self.tr("应用"))
        self.apply_btn.clicked.connect(self.apply_tab_visibility)
        self.apply_btn.setAutoDefault(False)
        self.apply_btn.setDefault(False)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.apply_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tab_button_layout.addWidget(self.apply_btn)
        tab_button_layout.addStretch()

        tab_content_layout.addWidget(tab_button_widget)
        tab_layout.addLayout(tab_content_layout)
        tab_container_layout.addWidget(tab_card)
        layout.addWidget(tab_container)

        # 自定义Card管理（使用与Tab界面一致的样式：QLabel + QFrame）
        custom_card_container = QWidget()
        custom_card_container_layout = QVBoxLayout(custom_card_container)
        custom_card_container_layout.setContentsMargins(0, 0, 0, 0)
        custom_card_container_layout.setSpacing(4)  # 与Tab界面一致的紧凑间距
        
        # 标题
        custom_card_title = QLabel(self.tr("自定义Card管理"))
        custom_card_title.setProperty("class", "section-title")
        custom_card_container_layout.addWidget(custom_card_title)
        
        # 卡片容器
        custom_card_group = QFrame()
        custom_card_group.setObjectName("card")
        add_card_shadow(custom_card_group)
        custom_card_main_layout = QHBoxLayout(custom_card_group)
        custom_card_main_layout.setContentsMargins(10, 1, 10, 1)
        custom_card_main_layout.setSpacing(8)
        
        # 左侧：Card列表区域
        card_left_layout = QVBoxLayout()
        
        self.custom_card_list = QListWidget()
        self.custom_card_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.custom_card_list.itemSelectionChanged.connect(self.on_card_selection_changed)
        card_left_layout.addWidget(self.custom_card_list)
        
        custom_card_main_layout.addLayout(card_left_layout)
        
        # 右侧：Card按钮（垂直排列）
        custom_card_btn_layout = QVBoxLayout()
        self.add_card_btn = QPushButton("➕ " + self.tr("添加Card"))
        self.add_card_btn.clicked.connect(self.show_add_card_dialog)
        self.add_card_btn.setAutoDefault(False)
        self.add_card_btn.setDefault(False)
        custom_card_btn_layout.addWidget(self.add_card_btn)
        
        self.edit_card_btn = QPushButton("✏️ " + self.tr("编辑Card"))
        self.edit_card_btn.clicked.connect(self.edit_custom_card)
        self.edit_card_btn.setAutoDefault(False)
        self.edit_card_btn.setDefault(False)
        custom_card_btn_layout.addWidget(self.edit_card_btn)
        
        self.delete_card_btn = QPushButton("🗑️ " + self.tr("删除Card"))
        self.delete_card_btn.clicked.connect(self.delete_custom_card)
        self.delete_card_btn.setAutoDefault(False)
        self.delete_card_btn.setDefault(False)
        custom_card_btn_layout.addWidget(self.delete_card_btn)

        self.card_up_btn = QPushButton("⬆️ " + self.tr("上移"))
        self.card_up_btn.clicked.connect(lambda: self.move_custom_card(-1))
        self.card_up_btn.setAutoDefault(False)
        self.card_up_btn.setDefault(False)
        custom_card_btn_layout.addWidget(self.card_up_btn)

        self.card_down_btn = QPushButton("⬇️ " + self.tr("下移"))
        self.card_down_btn.clicked.connect(lambda: self.move_custom_card(1))
        self.card_down_btn.setAutoDefault(False)
        self.card_down_btn.setDefault(False)
        custom_card_btn_layout.addWidget(self.card_down_btn)
        
        custom_card_main_layout.addLayout(custom_card_btn_layout)
        custom_card_container_layout.addWidget(custom_card_group, 1)  # 设置拉伸因子为1，使其能够扩展
        layout.addWidget(custom_card_container, 1)  # 设置拉伸因子为1，让自定义Card容器占据更多空间
        
        return widget
    
    def create_button_management_widget(self):
        """创建按钮管理控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 搜索栏（移到顶部）
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 " + self.tr("搜索:"))
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("输入关键词进行搜索..."))
        self.search_input.setMinimumWidth(150)
        self.search_input.returnPressed.connect(self.search_buttons)  # 按回车键搜索
        search_layout.addWidget(self.search_input)
        
        self.search_scope_combo = QComboBox()
        self.search_scope_combo.setObjectName("search_scope_combo")
        self.search_scope_combo.setStyleSheet("QComboBox#search_scope_combo { min-width: 50px; }")
        self.search_scope_combo.addItems([
            self.tr("整个表格"),
            self.tr("名称"),
            self.tr("类型"),
            self.tr("命令"),
            self.tr("所在Tab"),
            self.tr("所在卡片"),
            self.tr("启用"),
            self.tr("描述")
        ])
        search_layout.addWidget(self.search_scope_combo)
        
        self.search_btn = QPushButton("🔍 " + self.tr("搜索"))
        self.search_btn.clicked.connect(self.search_buttons)
        self.search_btn.setAutoDefault(False)
        self.search_btn.setDefault(False)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("❌ " + self.tr("清除"))
        self.clear_search_btn.clicked.connect(self.clear_all_filters)
        self.clear_search_btn.setAutoDefault(False)
        self.clear_search_btn.setDefault(False)
        search_layout.addWidget(self.clear_search_btn)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # 按钮列表表格
        self.button_table = DragDropButtonTable()
        self.button_table.setColumnCount(7)
        self.button_table.setHorizontalHeaderLabels([
            self.tr('名称'), self.tr('类型'), self.tr('命令'), 
            self.tr('所在Tab'), self.tr('所在卡片'), self.tr('启用'), self.tr('描述')
        ])
        
        # 设置列宽
        header = self.button_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(True)
        header.setHighlightSections(False)
        header.setMinimumSectionSize(40)
        default_widths = [100, 80, 100, 80, 70, 50, 110]
        for column, width in enumerate(default_widths):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            self.button_table.setColumnWidth(column, width)
        
        self.button_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.button_table.setSelectionMode(QTableWidget.SingleSelection)
        self.button_table.setWordWrap(False)
        self.button_table.setTextElideMode(Qt.ElideRight)
        self.button_table.setMinimumWidth(360)
        self.button_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.button_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.button_table.rows_reordered.connect(self.on_button_rows_reordered)
        self.button_table.itemDoubleClicked.connect(self.on_button_table_item_double_clicked)
        layout.addWidget(self.button_table)
        
        # 列级过滤器
        filter_row_layout = QHBoxLayout()
        filter_row_layout.addWidget(QLabel("🔽 " + self.tr("列过滤:")))
        self.column_filters = []
        
        # 只创建4个过滤器：类型、Tab、卡片、启用
        filter_configs = [
            (1, self.tr("类型")),
            (3, self.tr("Tab")),
            (4, self.tr("卡片")),
            (5, self.tr("启用"))
        ]
        
        for col_idx, label_text in filter_configs:
            # 组合框
            combo = QComboBox()
            combo.addItem(f"{self.tr('全部')}-{label_text}")  # 第一项显示"全部-类型"等
            combo.setObjectName(f"column_filter_{col_idx}")
            combo.setStyleSheet("QComboBox { max-width: 120px; }")
            combo.currentIndexChanged.connect(lambda idx, c=col_idx: self.on_column_filter_changed(c))
            self.column_filters.append((combo, col_idx, label_text))  # 存储组合框、列索引和列名称的对应关系
            filter_row_layout.addWidget(combo)
        
        filter_row_layout.addStretch()
        layout.addLayout(filter_row_layout)
        
        return widget
    
    
    def load_all_configs(self):
        """加载所有配置"""
        self.load_tab_config()
        self.load_custom_cards()
        self.load_buttons()
        self.update_tab_buttons_state()
    
    def update_tab_buttons_state(self):
        """根据选择状态更新Tab相关按钮"""
        has_custom_selection = self.is_selected_custom_tab and self.current_selected_tab_id is not None
        if hasattr(self, 'edit_tab_btn') and self.edit_tab_btn:
            self.edit_tab_btn.setEnabled(has_custom_selection)
        if hasattr(self, 'delete_tab_btn') and self.delete_tab_btn:
            self.delete_tab_btn.setEnabled(has_custom_selection)

    def load_tab_config(self):
        """加载Tab配置"""
        try:
            preserve_tab_id = self.current_selected_tab_id
            logger.debug(f"加载Tab配置: preserve_tab_id={preserve_tab_id}, is_selected_custom_tab={self.is_selected_custom_tab}")
            if self.tab_list_widget:
                self.tab_list_widget.blockSignals(True)
                self.tab_list_widget.clear()

            all_tabs = self.tab_config_manager.get_all_tabs()
            found_preserved = False

            for tab in all_tabs:
                item = QListWidgetItem()
                data = {
                    'id': tab['id'],
                    'name': tab['name'],
                    'custom': tab.get('custom', False)
                }
                item.setData(Qt.UserRole, data)
                widget = self._create_tab_item_widget(tab)
                item.setSizeHint(widget.sizeHint())
                self.tab_list_widget.addItem(item)
                self.tab_list_widget.setItemWidget(item, widget)

                if preserve_tab_id and tab['id'] == preserve_tab_id:
                    item.setSelected(True)
                    found_preserved = True

            if self.tab_list_widget:
                if not found_preserved:
                    self.tab_list_widget.clearSelection()
                    self.current_selected_tab_id = None
                    self.is_selected_custom_tab = False
                self.tab_list_widget.blockSignals(False)

            self.on_tab_selection_changed()
            logger.debug(f"加载Tab配置完成: current_selected_tab_id={self.current_selected_tab_id}, is_selected_custom_tab={self.is_selected_custom_tab}")

        except Exception as e:
            logger.exception(f"{self.tr('加载Tab配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('加载Tab配置失败:')} {str(e)}")
    
    def _create_tab_item_widget(self, tab_info):
        """为Tab列表创建条目控件"""
        tab_id = tab_info['id']
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setChecked(tab_info.get('visible', True))
        checkbox.setEnabled(self.tab_config_manager.can_hide_tab(tab_id))
        if not checkbox.isEnabled():
            checkbox.setToolTip(self.tr("此Tab不能隐藏"))
        checkbox.setFixedSize(20, 20)
        layout.addWidget(checkbox)

        label = QLabel(tab_info['name'])
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if tab_info.get('custom'):
            label.setStyleSheet("color: #ffd166;")
        label.setMinimumWidth(140)
        layout.addWidget(label)
        layout.addStretch()

        container.checkbox = checkbox
        container.tab_id = tab_id

        return container

    def on_tab_selection_changed(self):
        """Tab列表选择变化处理"""
        if not self.tab_list_widget:
            return

        item = self.tab_list_widget.currentItem()
        if item is None:
            self.current_selected_tab_id = None
            self.is_selected_custom_tab = False
        else:
            data = item.data(Qt.UserRole) or {}
            self.current_selected_tab_id = data.get('id')
            self.is_selected_custom_tab = data.get('custom', False)

        self.update_tab_buttons_state()
        self.load_custom_cards()
        # 清除Card选择，因为Tab变化了
        if self.custom_card_list:
            self.custom_card_list.clearSelection()
            self.current_selected_card_name = None
            self.current_selected_card_is_preset = False
            # 启用所有编辑操作按钮
            if hasattr(self, 'edit_card_btn') and self.edit_card_btn:
                self.edit_card_btn.setEnabled(True)
            if hasattr(self, 'delete_card_btn') and self.delete_card_btn:
                self.delete_card_btn.setEnabled(True)
            if hasattr(self, 'card_up_btn') and self.card_up_btn:
                self.card_up_btn.setEnabled(True)
            if hasattr(self, 'card_down_btn') and self.card_down_btn:
                self.card_down_btn.setEnabled(True)
        # 重新应用过滤器，显示该Tab下的所有自定义按钮
        self.apply_filters()
        logger.debug(f"Tab选择变化: current_selected_tab_id={self.current_selected_tab_id}, is_selected_custom_tab={self.is_selected_custom_tab}")

    def _on_splitter_moved(self, pos, index):
        logger.debug(f"分割线移动: pos={pos}, index={index}")

    def on_card_selection_changed(self):
        """Card列表选择变化处理"""
        if not self.custom_card_list:
            return
        
        current_item = self.custom_card_list.currentItem()
        if current_item:
            # 获取card名称（从显示文本中提取，或者从数据中获取）
            item_text = current_item.text()
            # 如果显示文本包含Tab名称，需要提取card名称
            # 例如："网页 (MYTAB)" -> "网页"
            if ' (' in item_text:
                card_name = item_text.split(' (')[0]
            else:
                card_name = item_text
            
            # 检查是否为预置Card
            self.current_selected_card_is_preset = current_item.data(Qt.UserRole + 1) == True
            
            # 获取完整的card信息以验证
            card_id = current_item.data(Qt.UserRole)
            card = next((c for c in self.tab_config_manager.custom_cards if c.get('id') == card_id), None)
            if card:
                self.current_selected_card_name = card.get('name', card_name)
            else:
                self.current_selected_card_name = card_name
        else:
            self.current_selected_card_name = None
            self.current_selected_card_is_preset = False
        
        # 根据Card类型启用/禁用编辑操作按钮
        is_preset = self.current_selected_card_is_preset
        if hasattr(self, 'edit_card_btn') and self.edit_card_btn:
            self.edit_card_btn.setEnabled(not is_preset)
        if hasattr(self, 'delete_card_btn') and self.delete_card_btn:
            self.delete_card_btn.setEnabled(not is_preset)
        if hasattr(self, 'card_up_btn') and self.card_up_btn:
            self.card_up_btn.setEnabled(not is_preset)
        if hasattr(self, 'card_down_btn') and self.card_down_btn:
            self.card_down_btn.setEnabled(not is_preset)
        
        logger.debug(f"Card选择变化: current_selected_card_name={self.current_selected_card_name}, is_preset={self.current_selected_card_is_preset}")
        # 重新应用过滤器，更新按钮显示
        self.apply_filters()
    
    def load_custom_cards(self):
        """加载Card列表（包括自定义Card和预置Card）"""
        try:
            if self.custom_card_list is None:
                return
            
            # 保存当前选择（如果有）- 只有在Tab和Card都有效时才保存
            selected_card_name = None
            selected_card_is_preset = None
            # 只有在Tab已选中且Card选择状态有效时才尝试恢复Card选择
            if self.current_selected_tab_id is not None and self.current_selected_card_name is not None:
                current_item = self.custom_card_list.currentItem()
                if current_item:
                    selected_card_name = current_item.text().split(' (')[0] if ' (' in current_item.text() else current_item.text()
                    # 检查是否为预置Card（通过UserRole+1数据）
                    selected_card_is_preset = current_item.data(Qt.UserRole + 1) == True
                # 如果current_item不存在，但current_selected_card_name存在，使用它
                elif self.current_selected_card_name:
                    selected_card_name = self.current_selected_card_name
                    selected_card_is_preset = self.current_selected_card_is_preset
            
            self.custom_card_list.clear()
            # 注意：不清除current_selected_card_name，因为可能需要在load_custom_cards中恢复选择
            # 但如果Tab被清除，则应该清除Card选择状态
            if self.current_selected_tab_id is None:
                self.current_selected_card_name = None  # 清除选择状态
                self.current_selected_card_is_preset = False  # 清除预置Card标识

            # 获取所有自定义Card的名称集合，用于区分预置Card和自定义Card
            custom_card_names = set()
            for card in self.tab_config_manager.custom_cards:
                custom_card_names.add(card.get('name', ''))

            cards_to_display = []  # 存储要显示的Card信息列表

            if self.current_selected_tab_id is None:
                # 未选中Tab，显示所有自定义Card
                for card in self.tab_config_manager.custom_cards:
                    cards_to_display.append({
                        'name': card['name'],
                        'id': card.get('id'),
                        'is_preset': False,
                        'tab_name': None
                    })
            elif self.is_selected_custom_tab and self.current_selected_tab_id:
                # 选中自定义Tab，显示该Tab下的自定义Card
                for card in self.tab_config_manager.custom_cards:
                    if card.get('tab_id') == self.current_selected_tab_id:
                        associated_tab = next((tab for tab in self.tab_config_manager.custom_tabs if tab['id'] == self.current_selected_tab_id), None)
                        tab_name = associated_tab['name'] if associated_tab else ''
                        cards_to_display.append({
                            'name': card['name'],
                            'id': card.get('id'),
                            'is_preset': False,
                            'tab_name': tab_name
                        })
            else:
                # 选中预置Tab，显示该Tab下的所有Card（包括预置Card和自定义Card）
                # 获取Tab名称
                all_tabs = self.tab_config_manager.get_all_tabs()
                selected_tab = next((tab for tab in all_tabs if tab['id'] == self.current_selected_tab_id), None)
                if selected_tab:
                    tab_name = selected_tab['name']
                    # 从custom_button_manager获取该Tab下的所有Card
                    available_cards = self.custom_button_manager.get_available_cards(tab_name)
                    
                    for card_name in available_cards:
                        is_preset = card_name not in custom_card_names
                        # 如果是自定义Card，获取其ID
                        card_id = None
                        if not is_preset:
                            card = next((c for c in self.tab_config_manager.custom_cards if c.get('name') == card_name), None)
                            if card:
                                card_id = card.get('id')
                        
                        cards_to_display.append({
                            'name': card_name,
                            'id': card_id,
                            'is_preset': is_preset,
                            'tab_name': tab_name
                        })

            # 尝试恢复之前的选择
            selected_item = None
            for card_info in cards_to_display:
                # 构建显示文本
                if self.is_selected_custom_tab and self.current_selected_tab_id:
                    item_text = card_info['name']
                else:
                    tab_name_display = card_info['tab_name'] if card_info['tab_name'] else ''
                    item_text = f"{card_info['name']} ({tab_name_display})" if tab_name_display else card_info['name']

                item = QListWidgetItem(item_text)
                # 如果是自定义Card，存储其ID；如果是预置Card，存储None或特殊标识
                if card_info['id']:
                    item.setData(Qt.UserRole, card_info['id'])
                else:
                    item.setData(Qt.UserRole, None)
                # 存储是否为预置Card的标识
                item.setData(Qt.UserRole + 1, card_info['is_preset'])
                self.custom_card_list.addItem(item)
                
                # 如果这是之前选中的card，标记它
                if (selected_card_name and card_info['name'] == selected_card_name and 
                    selected_card_is_preset is not None and card_info['is_preset'] == selected_card_is_preset):
                    selected_item = item
            
            # 恢复选择（但不触发过滤，因为已经在最后会调用apply_filters）
            if selected_item:
                self.custom_card_list.blockSignals(True)
                selected_item.setSelected(True)
                self.custom_card_list.setCurrentItem(selected_item)
                # 从item中获取card信息
                self.current_selected_card_name = selected_item.text().split(' (')[0] if ' (' in selected_item.text() else selected_item.text()
                self.current_selected_card_is_preset = selected_item.data(Qt.UserRole + 1) == True
                self.custom_card_list.blockSignals(False)
        except Exception as e:
            logger.exception(f"{self.tr('加载Card失败:')} {e}")
    
    def load_buttons(self):
        """加载按钮到表格"""
        try:
            # 保存当前的过滤状态（在清空之前）
            saved_filter_states = {}
            if hasattr(self, 'column_filters') and self.column_filters:
                for combo, col_idx, _ in self.column_filters:
                    saved_filter_states[col_idx] = {
                        'current_index': combo.currentIndex(),
                        'current_text': combo.currentText() if combo.currentIndex() >= 0 else ''
                    }
            
            # 保存搜索状态
            saved_search_keyword = self.search_input.text() if hasattr(self, 'search_input') else ''
            saved_search_scope = self.search_scope_combo.currentIndex() if hasattr(self, 'search_scope_combo') else 0
            
            self.button_table.setSortingEnabled(False)
            self.button_table.setRowCount(0)
            buttons = self.custom_button_manager.get_all_buttons()
            
            # 保存原始按钮数据
            self.all_buttons_data = buttons
            
            for btn in buttons:
                row = self.button_table.rowCount()
                self.button_table.insertRow(row)
                
                # 获取按钮类型显示名称
                button_type = btn.get('type', 'adb')
                type_map = {
                    'adb': self.tr('ADB命令'),
                    'python': self.tr('Python脚本'),
                    'file': self.tr('打开文件'),
                    'program': self.tr('运行程序'),
                    'system': self.tr('系统命令'),
                    'url': self.tr('打开网页')
                }
                type_display = type_map.get(button_type, self.tr('ADB命令'))
                
                self.button_table.setItem(row, 0, QTableWidgetItem(btn.get('name', '')))
                self.button_table.setItem(row, 1, QTableWidgetItem(type_display))
                self.button_table.setItem(row, 2, QTableWidgetItem(btn.get('command', '')))
                self.button_table.setItem(row, 3, QTableWidgetItem(btn.get('tab', '')))
                self.button_table.setItem(row, 4, QTableWidgetItem(btn.get('card', '')))
                self.button_table.setItem(row, 5, QTableWidgetItem('✓' if btn.get('enabled', True) else '✗'))
                self.button_table.setItem(row, 6, QTableWidgetItem(btn.get('description', '')))
                
                # 存储按钮ID
                self.button_table.item(row, 0).setData(Qt.UserRole, btn.get('id'))

            self.button_table.resizeRowsToContents()
            
            # 填充列过滤器（会清空并重新填充）
            self.populate_column_filters()
            
            # 恢复过滤状态（阻止信号，避免触发apply_filters）
            if saved_filter_states and hasattr(self, 'column_filters') and self.column_filters:
                for combo, col_idx, _ in self.column_filters:
                    combo.blockSignals(True)  # 阻止信号
                    if col_idx in saved_filter_states:
                        saved_state = saved_filter_states[col_idx]
                        saved_text = saved_state['current_text']
                        # 尝试找到相同的文本
                        found = False
                        for i in range(combo.count()):
                            if combo.itemText(i) == saved_text:
                                combo.setCurrentIndex(i)
                                found = True
                                break
                        if not found:
                            # 如果找不到，使用保存的索引（如果有效）
                            saved_index = saved_state['current_index']
                            if 0 <= saved_index < combo.count():
                                combo.setCurrentIndex(saved_index)
                    combo.blockSignals(False)  # 恢复信号
            
            # 恢复搜索状态（阻止信号）
            if hasattr(self, 'search_input'):
                self.search_input.blockSignals(True)
                if saved_search_keyword:
                    self.search_input.setText(saved_search_keyword)
                self.search_input.blockSignals(False)
            if hasattr(self, 'search_scope_combo'):
                self.search_scope_combo.blockSignals(True)
                if 0 <= saved_search_scope < self.search_scope_combo.count():
                    self.search_scope_combo.setCurrentIndex(saved_search_scope)
                self.search_scope_combo.blockSignals(False)
                    
        except Exception as e:
            logger.exception(f"{self.tr('加载按钮失败:')} {e}")
    
    def populate_column_filters(self):
        """填充列过滤器的唯一值"""
        try:
            if not self.column_filters:
                return
            
            # 收集每列的唯一值
            for combo, col_idx, label_text in self.column_filters:
                # 先清空（保留"全部"选项）
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(f"{self.tr('全部')}-{label_text}")
                
                # 收集唯一值
                unique_values = set()
                for btn in self.all_buttons_data:
                    value = ""
                    if col_idx == 1:  # 类型
                        button_type = btn.get('type', 'adb')
                        type_map = {
                            'adb': self.tr('ADB命令'),
                            'python': self.tr('Python脚本'),
                            'file': self.tr('打开文件'),
                            'program': self.tr('运行程序'),
                            'system': self.tr('系统命令'),
                            'url': self.tr('打开网页')
                        }
                        value = type_map.get(button_type, self.tr('ADB命令'))
                    elif col_idx == 3:  # Tab
                        value = btn.get('tab', '')
                    elif col_idx == 4:  # 卡片
                        value = btn.get('card', '')
                    elif col_idx == 5:  # 启用
                        value = '✓' if btn.get('enabled', True) else '✗'
                    
                    if value:
                        unique_values.add(value)
                
                # 排序并添加到组合框
                sorted_values = sorted(unique_values, key=lambda x: str(x))
                for value in sorted_values:
                    combo.addItem(str(value))
                
                combo.blockSignals(False)
        except Exception as e:
            logger.exception(f"{self.tr('填充列过滤器失败:')} {e}")
    
    def search_buttons(self):
        """搜索按钮"""
        try:
            logger.debug("search_buttons被调用")
            self.apply_filters()  # 统一使用apply_filters
        except Exception as e:
            logger.exception(f"{self.tr('搜索失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('搜索失败:')} {str(e)}")
    
    def on_column_filter_changed(self, column_idx):
        """列过滤器改变事件"""
        try:
            logger.debug(f"列过滤器改变: column_idx={column_idx}")
            self.apply_filters()
        except Exception as e:
            logger.exception(f"{self.tr('列过滤器改变失败:')} {e}")
    
    def apply_filters(self):
        """应用所有过滤器（搜索 + 列过滤）"""
        try:
            keyword = self.search_input.text().strip()
            scope_index = self.search_scope_combo.currentIndex()
            
            # 清空表格
            self.button_table.setRowCount(0)
            
            # 筛选按钮
            filtered_buttons = []
            for btn in self.all_buttons_data:
                match = True
                
                # 先应用列过滤器（AND逻辑）
                for combo, col_idx, _ in self.column_filters:
                    if combo.currentIndex() == 0:  # "(全部)"选项
                        continue
                    
                    selected_value = combo.currentText()
                    value = ""
                    if col_idx == 1:  # 类型
                        button_type = btn.get('type', 'adb')
                        type_map = {
                            'adb': self.tr('ADB命令'),
                            'python': self.tr('Python脚本'),
                            'file': self.tr('打开文件'),
                            'program': self.tr('运行程序'),
                            'system': self.tr('系统命令'),
                            'url': self.tr('打开网页')
                        }
                        value = type_map.get(button_type, self.tr('ADB命令'))
                    elif col_idx == 3:  # Tab
                        value = btn.get('tab', '')
                    elif col_idx == 4:  # 卡片
                        value = btn.get('card', '')
                    elif col_idx == 5:  # 启用
                        value = '✓' if btn.get('enabled', True) else '✗'
                    
                    if str(value) != selected_value:
                        match = False
                        break
                
                if not match:
                    continue
                
                # 应用Tab选择过滤器（如果选中了Tab）
                if self.current_selected_tab_id:
                    # 获取Tab名称
                    all_tabs = self.tab_config_manager.get_all_tabs()
                    selected_tab = next((tab for tab in all_tabs if tab['id'] == self.current_selected_tab_id), None)
                    if selected_tab:
                        tab_name = selected_tab['name']
                        btn_tab = btn.get('tab', '')
                        if btn_tab != tab_name:
                            match = False
                            continue
                
                # 应用Card选择过滤器（如果选中了Card）
                if self.current_selected_card_name:
                    btn_card = btn.get('card', '')
                    # 规范化card名称进行比较（去除多余空格）
                    normalized_btn_card = ' '.join(btn_card.split()) if btn_card else ''
                    normalized_selected_card = ' '.join(self.current_selected_card_name.split()) if self.current_selected_card_name else ''
                    if normalized_btn_card != normalized_selected_card:
                        match = False
                        continue
                    
                    # 如果选中的是预置Card，只显示自定义按钮
                    # 注意：self.all_buttons_data已经只包含自定义按钮（从custom_button_manager.get_all_buttons()获取）
                    # 所以当选中预置Card时，只显示匹配该Card的自定义按钮，预置按钮不会显示
                    # 这个逻辑已经通过使用self.all_buttons_data自动实现
                
                # 再应用搜索过滤器（如果有搜索关键词）
                if keyword:
                    search_match = False
                    
                    if scope_index == 0:  # 整个表格
                        search_texts = [
                            btn.get('name', ''),
                            btn.get('command', ''),
                            btn.get('tab', ''),
                            btn.get('card', ''),
                            btn.get('description', ''),
                            '✓' if btn.get('enabled', True) else '✗'
                        ]
                        button_type = btn.get('type', 'adb')
                        type_map = {
                            'adb': self.tr('ADB命令'),
                            'python': self.tr('Python脚本'),
                            'file': self.tr('打开文件'),
                            'program': self.tr('运行程序'),
                            'system': self.tr('系统命令'),
                            'url': self.tr('打开网页')
                        }
                        search_texts.append(type_map.get(button_type, ''))
                        
                        for text in search_texts:
                            if keyword.lower() in str(text).lower():
                                search_match = True
                                break
                    else:
                        # 按列搜索
                        if scope_index == 1:  # 名称
                            search_text = btn.get('name', '')
                        elif scope_index == 2:  # 类型
                            button_type = btn.get('type', 'adb')
                            type_map = {
                                'adb': self.tr('ADB命令'),
                                'python': self.tr('Python脚本'),
                                'file': self.tr('打开文件'),
                                'program': self.tr('运行程序'),
                                'system': self.tr('系统命令'),
                                'url': self.tr('打开网页')
                            }
                            search_text = type_map.get(button_type, '')
                        elif scope_index == 3:  # 命令
                            search_text = btn.get('command', '')
                        elif scope_index == 4:  # 所在Tab
                            search_text = btn.get('tab', '')
                        elif scope_index == 5:  # 所在卡片
                            search_text = btn.get('card', '')
                        elif scope_index == 6:  # 启用
                            search_text = '✓' if btn.get('enabled', True) else '✗'
                        elif scope_index == 7:  # 描述
                            search_text = btn.get('description', '')
                        else:
                            search_text = ''
                        
                        if keyword.lower() in str(search_text).lower():
                            search_match = True
                    
                    match = search_match
                
                if match:
                    filtered_buttons.append(btn)
            
            # 显示筛选结果
            for btn in filtered_buttons:
                row = self.button_table.rowCount()
                self.button_table.insertRow(row)
                
                button_type = btn.get('type', 'adb')
                type_map = {
                    'adb': self.tr('ADB命令'),
                    'python': self.tr('Python脚本'),
                    'file': self.tr('打开文件'),
                    'program': self.tr('运行程序'),
                    'system': self.tr('系统命令'),
                    'url': self.tr('打开网页')
                }
                type_display = type_map.get(button_type, self.tr('ADB命令'))
                
                self.button_table.setItem(row, 0, QTableWidgetItem(btn.get('name', '')))
                self.button_table.setItem(row, 1, QTableWidgetItem(type_display))
                self.button_table.setItem(row, 2, QTableWidgetItem(btn.get('command', '')))
                self.button_table.setItem(row, 3, QTableWidgetItem(btn.get('tab', '')))
                self.button_table.setItem(row, 4, QTableWidgetItem(btn.get('card', '')))
                self.button_table.setItem(row, 5, QTableWidgetItem('✓' if btn.get('enabled', True) else '✗'))
                self.button_table.setItem(row, 6, QTableWidgetItem(btn.get('description', '')))
                
                self.button_table.item(row, 0).setData(Qt.UserRole, btn.get('id'))
            
            self.button_table.resizeRowsToContents()
            
            if len(filtered_buttons) == 0 and (keyword or any(combo.currentIndex() > 0 for combo, _, _ in self.column_filters)):
                # 只有在有过滤条件时才提示
                pass  # 不显示提示，让用户自己知道过滤结果
                
        except Exception as e:
            logger.exception(f"{self.tr('应用过滤器失败:')} {e}")
    
    def clear_all_filters(self):
        """清除所有过滤条件（包括Tab/Card选择和搜索/过滤条件），恢复显示所有按钮"""
        try:
            # 清除Tab选择
            if self.tab_list_widget:
                self.tab_list_widget.blockSignals(True)  # 阻止信号，避免触发on_tab_selection_changed
                self.tab_list_widget.clearSelection()
                self.tab_list_widget.blockSignals(False)
                self.current_selected_tab_id = None
                self.is_selected_custom_tab = False
                # 更新Tab按钮状态
                self.update_tab_buttons_state()
            
            # 清除Card选择
            if self.custom_card_list:
                self.custom_card_list.blockSignals(True)  # 阻止信号，避免触发on_card_selection_changed
                self.custom_card_list.clearSelection()
                self.custom_card_list.blockSignals(False)
            # 清除Card选择状态变量
            self.current_selected_card_name = None
            self.current_selected_card_is_preset = False
            # 启用所有编辑操作按钮
            if hasattr(self, 'edit_card_btn') and self.edit_card_btn:
                self.edit_card_btn.setEnabled(True)
            if hasattr(self, 'delete_card_btn') and self.delete_card_btn:
                self.delete_card_btn.setEnabled(True)
            if hasattr(self, 'card_up_btn') and self.card_up_btn:
                self.card_up_btn.setEnabled(True)
            if hasattr(self, 'card_down_btn') and self.card_down_btn:
                self.card_down_btn.setEnabled(True)
            
            # 清除搜索条件
            self.search_input.clear()
            self.search_scope_combo.setCurrentIndex(0)
            # 重置所有列过滤器
            for combo, _, _ in self.column_filters:
                combo.setCurrentIndex(0)
            
            # 重新加载Card列表（显示所有自定义Card）
            self.load_custom_cards()
            
            # 重新加载所有按钮
            self.load_buttons()
            
            logger.debug("所有过滤条件已清除")
        except Exception as e:
            logger.exception(f"{self.tr('清除所有过滤条件失败:')} {e}")
    
    def clear_search(self):
        """清除搜索，恢复显示所有按钮（保留此方法以兼容其他代码）"""
        self.clear_all_filters()
    
    def on_refresh_clicked(self):
        """刷新按钮点击，保持过滤条件但重新加载数据"""
        try:
            # 重新加载数据，但保持当前的搜索和过滤条件
            self.load_buttons()
            # 重新应用当前过滤条件
            self.apply_filters()
        except Exception as e:
            logger.exception(f"{self.tr('刷新失败:')} {e}")
    
    def apply_tab_visibility(self):
        """应用Tab显示设置"""
        try:
            # 保存Tab可见性配置
            self.save_config()
            
            # 通知父窗口重新加载Tab
            if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                self.parent().reload_tabs()
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab显示设置已应用"))
            else:
                QMessageBox.warning(self, self.tr("警告"), self.tr("无法通知主窗口更新Tab"))
                
        except Exception as e:
            logger.exception(f"{self.tr('应用Tab显示设置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('应用Tab显示设置失败:')} {str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            if self.tab_list_widget:
                for index in range(self.tab_list_widget.count()):
                    item = self.tab_list_widget.item(index)
                    widget = self.tab_list_widget.itemWidget(item)
                    if not widget:
                        continue
                    tab_id = getattr(widget, 'tab_id', None)
                    checkbox = getattr(widget, 'checkbox', None)
                    if tab_id is None or checkbox is None:
                        continue
                    self.tab_config_manager.tab_visibility[tab_id] = checkbox.isChecked()
            
            self.tab_config_manager.save_config()
            
        except Exception as e:
            logger.exception(f"{self.tr('保存配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存失败:')} {str(e)}")
    
    def export_config(self):
        """导出配置"""
        try:
            # 选择导出文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                self.tr("导出配置"), 
                f"MobileTestTool_Config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json)"
            )
            
            if file_path:
                # 收集所有配置
                config_data = {
                    'export_time': datetime.datetime.now().isoformat(),
                    'version': '1.0',
                    'tab_config': {
                        'tab_order': self.tab_config_manager.tab_order,
                        'tab_visibility': self.tab_config_manager.tab_visibility,
                        'custom_tabs': self.tab_config_manager.custom_tabs,
                        'custom_cards': self.tab_config_manager.custom_cards
                    },
                    'button_config': {
                        'custom_buttons': self.custom_button_manager.get_all_buttons()
                    }
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, self.tr("成功"), f"{self.tr('配置已导出到:')} {file_path}")
                logger.info(f"{self.tr('配置已导出到:')} {file_path}")
                
        except Exception as e:
            logger.exception(f"{self.tr('导出配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导出配置失败:')} {str(e)}")
    
    def import_config(self):
        """导入配置"""
        try:
            # 选择导入文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                self.tr("导入配置"), 
                "", 
                "JSON文件 (*.json)"
            )
            
            if file_path:
                # 确认导入
                reply = QMessageBox.question(
                    self,
                    self.tr("确认导入配置"),
                    (self.tr("⚠️ 导入配置将完全覆盖当前所有设置！\n\n") +
                     self.tr("• 所有自定义Tab将被替换\n") +
                     self.tr("• 所有自定义Card将被替换\n") +
                     self.tr("• 所有自定义Button将被替换\n") +
                     self.tr("• 当前配置将永久丢失\n\n") +
                     self.tr("确定要继续导入吗？")),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 读取配置文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # 验证配置格式
                    if 'tab_config' not in config_data or 'button_config' not in config_data:
                        QMessageBox.warning(self, self.tr("错误"), self.tr("配置文件格式不正确"))
                        return
                    
                    # 导入Tab配置
                    tab_config = config_data['tab_config']
                    self.tab_config_manager.tab_visibility = tab_config.get('tab_visibility', {})
                    self.tab_config_manager.custom_tabs = tab_config.get('custom_tabs', [])
                    self.tab_config_manager.custom_cards = tab_config.get('custom_cards', [])
                    
                    # 处理tab_order，如果配置文件中没有则使用默认顺序
                    if 'tab_order' in tab_config:
                        self.tab_config_manager.tab_order = tab_config['tab_order']
                    else:
                        # 如果没有tab_order，创建默认顺序（包含自定义tab）
                        default_order = [tab['id'] for tab in self.tab_config_manager.default_tabs]
                        custom_tab_ids = [tab['id'] for tab in self.tab_config_manager.custom_tabs]
                        self.tab_config_manager.tab_order = default_order + custom_tab_ids
                    
                    # 修复tab_order，确保包含所有默认tab和自定义tab
                    # 这样可以避免因为配置不完整导致tab无法显示的问题
                    self.tab_config_manager._fix_tab_order()
                    
                    self.tab_config_manager.save_config()
                    
                    # 导入按钮配置
                    button_config = config_data['button_config']
                    imported_buttons = button_config.get('custom_buttons', [])
                    
                    # 验证并过滤按钮，只保留有效的按钮
                    valid_buttons, invalid_buttons = self._validate_and_filter_buttons(imported_buttons)
                    
                    if invalid_buttons:
                        # 有无效按钮，询问用户是否继续
                        invalid_count = len(invalid_buttons)
                        invalid_details = "\n".join(f"• {invalid['reason']}" for invalid in invalid_buttons[:5])  # 最多显示5个
                        if invalid_count > 5:
                            invalid_details += f"\n  ... 还有 {invalid_count - 5} 个无效按钮"
                        
                        reply = QMessageBox.question(
                            self,
                            self.tr("发现无效按钮"),
                            (self.tr(f"发现 {invalid_count} 个无效按钮，将跳过这些按钮：\n\n") +
                             invalid_details +
                             f"\n\n{self.tr('是否继续导入其他有效按钮？')}"),
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.Yes
                        )
                        
                        if reply == QMessageBox.StandardButton.No:
                            QMessageBox.information(self, self.tr("已取消"), self.tr("导入已取消"))
                            return
                        
                        logger.warning(f"{self.tr('跳过')} {invalid_count} {self.tr('个无效按钮')}")
                    
                    if valid_buttons:
                        # 保存有效的按钮
                        self.custom_button_manager.buttons = valid_buttons
                        self.custom_button_manager.save_buttons()
                        logger.info(f"{self.tr('导入')} {len(valid_buttons)} {self.tr('个有效按钮')}")
                        if invalid_buttons:
                            logger.warning(f"{self.tr('跳过')} {len(invalid_buttons)} {self.tr('个无效按钮')}")
                    else:
                        # 所有按钮都无效
                        error_msg = self.tr("❌ 所有按钮都无效！\n\n") + self.tr("发现以下问题：\n\n")
                        error_msg += "\n".join(f"• {invalid['reason']}" for invalid in invalid_buttons[:10])  # 最多显示10个
                        if len(invalid_buttons) > 10:
                            error_msg += f"\n  ... 还有 {len(invalid_buttons) - 10} 个无效按钮"
                        error_msg += f"\n\n{self.tr('请检查配置文件中的Tab和Card名称是否正确。')}"
                        QMessageBox.critical(self, self.tr("导入失败"), error_msg)
                        logger.error(f"{self.tr('配置导入失败，所有按钮都无效')}")
                        return
                    
                    # 重新加载所有配置
                    self.load_all_configs()
                    
                    # 通知主窗口重新加载Tab
                    if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                        self.parent().reload_tabs()
                        logger.info(self.tr("已通知主窗口重新加载Tab"))
                    
                    # 确保按钮正确显示 - 触发按钮更新信号
                    self.custom_button_manager.buttons_updated.emit()
                    
                    # 统计导入的内容
                    tab_count = len(self.tab_config_manager.custom_tabs)
                    card_count = len(self.tab_config_manager.custom_cards)
                    button_count = len(self.custom_button_manager.buttons)
                    
                    success_msg = (self.tr("✅ 配置导入成功！\n\n") +
                                 f"{self.tr('导入内容:')}\n" +
                                 f"• {self.tr('自定义Tab')}: {tab_count} {self.tr('个')}\n" +
                                 f"• {self.tr('自定义Card')}: {card_count} {self.tr('个')}\n" +
                                 f"• {self.tr('自定义Button')}: {button_count} {self.tr('个')}\n\n" +
                                 f"{self.tr('文件来源:')} {file_path}")
                    
                    QMessageBox.information(self, self.tr("导入成功"), success_msg)
                    logger.info(f"{self.tr('配置已从文件导入:')} {file_path}")
                    
        except Exception as e:
            logger.exception(f"{self.tr('导入配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导入配置失败:')} {str(e)}")
    
    def _validate_button_references(self):
        """验证Button的Tab和Card引用，返回错误列表（保留此方法以兼容其他代码）"""
        errors = []
        try:
            valid_buttons, invalid_buttons = self._validate_and_filter_buttons(self.custom_button_manager.buttons)
            for invalid in invalid_buttons:
                errors.append(invalid['reason'])
        except Exception as e:
            logger.exception(f"{self.tr('验证Button引用失败:')} {e}")
            errors.append(f"{self.tr('验证过程出错:')} {str(e)}")
        return errors
    
    def _validate_and_filter_buttons(self, buttons):
        """验证并过滤按钮，返回有效按钮列表和无效按钮列表"""
        valid_buttons = []
        invalid_buttons = []
        
        try:
            # 获取所有有效的Tab名称
            valid_tab_names = set()
            
            # 添加默认Tab名称
            for tab in self.tab_config_manager.default_tabs:
                valid_tab_names.add(tab['name'])
            
            # 添加自定义Tab名称
            for tab in self.tab_config_manager.custom_tabs:
                valid_tab_names.add(tab['name'])
            
            # 验证每个按钮的Tab和Card引用
            for button in buttons:
                button_name = button.get('name', '未知按钮')
                button_tab = button.get('tab', '')
                button_card = button.get('card', '')
                is_valid = True
                reason = None
                
                # 验证Tab是否存在
                if button_tab:
                    if button_tab not in valid_tab_names:
                        is_valid = False
                        reason = f"{self.tr('按钮')} '{button_name}' {self.tr('引用的Tab不存在:')} '{button_tab}'"
                    else:
                        # 验证Card是否存在（允许空格变体匹配）
                        if button_card:
                            # 获取该Tab下所有可用的Card
                            available_cards = self.custom_button_manager.get_available_cards(button_tab)
                            # 规范化card名称进行比较（去除多余空格）
                            normalized_button_card = ' '.join(button_card.split())
                            card_matched = False
                            for available_card in available_cards:
                                normalized_available_card = ' '.join(available_card.split())
                                if normalized_button_card == normalized_available_card:
                                    card_matched = True
                                    # 如果存在空格差异，规范化按钮的card名称
                                    if button_card != available_card:
                                        button['card'] = available_card
                                        logger.info(f"{self.tr('规范化按钮card名称:')} '{button_card}' -> '{available_card}'")
                                    break
                            
                            if not card_matched:
                                is_valid = False
                                reason = f"{self.tr('按钮')} '{button_name}' {self.tr('引用的Card不存在:')} Tab='{button_tab}', Card='{button_card}'"
                else:
                    # Tab为空也可能是个问题，但这里不报错，因为可能是未配置的按钮
                    pass
                
                if is_valid:
                    valid_buttons.append(button)
                else:
                    invalid_buttons.append({
                        'button': button,
                        'reason': reason
                    })
                
        except Exception as e:
            logger.exception(f"{self.tr('验证Button引用失败:')} {e}")
            # 如果验证过程出错，将所有按钮都标记为无效
            invalid_buttons = [{
                'button': btn,
                'reason': f"{self.tr('验证过程出错:')} {str(e)}"
            } for btn in buttons]
            valid_buttons = []
        
        return valid_buttons, invalid_buttons
    
    def _validate_and_fix_button_tab_references(self):
        """验证并修复Button的Tab名称引用（保留此方法以兼容旧代码）"""
        # 先验证，如果有错误就记录警告
        errors = self._validate_button_references()
        if errors:
            for error in errors:
                logger.warning(error)
    
    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self,
            self.tr("确认重置"),
            self.tr("确定要重置为默认配置吗？这将删除所有自定义Tab、Card和按钮。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 重置Tab配置
                self.tab_config_manager.reset_to_default()
                
                # 重置按钮配置
                self.custom_button_manager.buttons = self.custom_button_manager._create_default_buttons()
                self.custom_button_manager.save_buttons()
                
                # 重新加载所有配置
                self.load_all_configs()
                
                # 通知主窗口重新加载Tab
                if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                    self.parent().reload_tabs()
                    logger.info(self.tr("已通知主窗口重新加载Tab"))
                
                QMessageBox.information(self, self.tr("成功"), self.tr("已重置为默认配置"))
                logger.info(self.tr("配置已重置为默认"))
                
            except Exception as e:
                logger.exception(f"{self.tr('重置配置失败:')} {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('重置配置失败:')} {str(e)}")
    
    # Tab管理相关方法
    def show_add_tab_dialog(self):
        """显示添加Tab对话框"""
        from ui.tab_manager_dialog import CustomTabDialog
        dialog = CustomTabDialog(self.tab_config_manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_tab_config()
            self.load_custom_cards()
    
    def edit_custom_tab(self):
        """编辑自定义Tab"""
        if not self.is_selected_custom_tab or not self.current_selected_tab_id:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要编辑的自定义Tab"))
            return
        
        tab_id = self.current_selected_tab_id
        from ui.tab_manager_dialog import CustomTabDialog
        dialog = CustomTabDialog(self.tab_config_manager, tab_id=tab_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_tab_config()
    
    def delete_custom_tab(self):
        """删除自定义Tab"""
        if not self.is_selected_custom_tab or not self.current_selected_tab_id:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的自定义Tab"))
            return
        
        current_item = self.tab_list_widget.currentItem()
        tab_data = current_item.data(Qt.UserRole) if current_item else {}
        tab_name = tab_data.get('name', '')
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除Tab')} '{tab_name}' {self.tr('吗？这将同时删除该Tab下的所有Card。')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            tab_id = self.current_selected_tab_id
            if self.tab_config_manager.delete_custom_tab(tab_id):
                self.current_selected_tab_id = None
                self.is_selected_custom_tab = False
                self.load_custom_cards()
                self.load_tab_config()
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab已删除"))
    
    def show_add_card_dialog(self):
        """显示添加Card对话框"""
        # 检查是否有自定义Tab
        if not self.tab_config_manager.custom_tabs:
            QMessageBox.information(
                self, 
                self.tr("提示"), 
                self.tr("请先创建自定义Tab，Card只能添加到自定义Tab中")
            )
            return
        
        # 获取预设的tab_id（如果选中了自定义tab）
        preset_tab_id = None
        if self.current_selected_tab_id and self.is_selected_custom_tab:
            preset_tab_id = self.current_selected_tab_id
        
        from ui.tab_manager_dialog import CustomCardDialog
        dialog = CustomCardDialog(self.tab_config_manager, preset_tab_id=preset_tab_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_custom_cards()
    
    def edit_custom_card(self):
        """编辑自定义Card"""
        current_item = self.custom_card_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要编辑的Card"))
            return
        
        # 检查是否为预置Card
        is_preset = current_item.data(Qt.UserRole + 1) == True
        if is_preset:
            QMessageBox.warning(self, self.tr("警告"), self.tr("预置Card不能编辑"))
            return
        
        card_id = current_item.data(Qt.UserRole)
        if not card_id:
            QMessageBox.warning(self, self.tr("警告"), self.tr("无法获取Card ID"))
            return
        
        from ui.tab_manager_dialog import CustomCardDialog
        dialog = CustomCardDialog(self.tab_config_manager, card_id=card_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_custom_cards()
    
    def delete_custom_card(self):
        """删除自定义Card"""
        current_item = self.custom_card_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的Card"))
            return
        
        # 检查是否为预置Card
        is_preset = current_item.data(Qt.UserRole + 1) == True
        if is_preset:
            QMessageBox.warning(self, self.tr("警告"), self.tr("预置Card不能删除"))
            return
        
        card_id = current_item.data(Qt.UserRole)
        if not card_id:
            QMessageBox.warning(self, self.tr("警告"), self.tr("无法获取Card ID"))
            return
        
        card_name = current_item.text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除Card')} '{card_name}' {self.tr('吗？')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.tab_config_manager.delete_custom_card(card_id):
                self.load_custom_cards()
                QMessageBox.information(self, self.tr("成功"), self.tr("Card已删除"))

    def move_custom_card(self, step):
        """调整自定义Card的顺序"""
        count = self.custom_card_list.count()
        if count == 0:
            return

        current_row = self.custom_card_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要移动的Card"))
            return

        current_item = self.custom_card_list.item(current_row)
        # 检查是否为预置Card
        is_preset = current_item.data(Qt.UserRole + 1) == True
        if is_preset:
            QMessageBox.warning(self, self.tr("警告"), self.tr("预置Card不能移动"))
            return

        new_row = current_row + step
        if new_row < 0 or new_row >= count:
            return

        # 检查目标位置是否为预置Card
        target_item = self.custom_card_list.item(new_row)
        if target_item and target_item.data(Qt.UserRole + 1) == True:
            QMessageBox.warning(self, self.tr("警告"), self.tr("不能移动到预置Card的位置"))
            return

        item = self.custom_card_list.takeItem(current_row)
        self.custom_card_list.insertItem(new_row, item)
        self.custom_card_list.setCurrentRow(new_row)

        # 只收集自定义Card的ID（排除预置Card）
        ordered_ids = []
        for idx in range(self.custom_card_list.count()):
            item = self.custom_card_list.item(idx)
            card_id = item.data(Qt.UserRole)
            is_preset = item.data(Qt.UserRole + 1) == True
            if card_id and not is_preset:
                ordered_ids.append(card_id)

        if not self.tab_config_manager.reorder_custom_cards(ordered_ids):
            QMessageBox.warning(self, self.tr("失败"), self.tr("Card排序保存失败，请检查日志"))
        else:
            logger.info(self.tr("自定义Card顺序已更新"))
    
    # 按钮管理相关方法
    def add_button(self):
        """添加按钮"""
        # 获取预设的tab和card名称
        preset_tab_name = None
        preset_card_name = None
        
        if self.current_selected_card_name:
            # 如果选中了card，使用card的tab和card名称
            preset_card_name = self.current_selected_card_name
            preset_tab_name = self._get_selected_card_tab_name()
        elif self.current_selected_tab_id:
            # 如果只选了tab，没有选card，使用tab名称，card选择第一个
            all_tabs = self.tab_config_manager.get_all_tabs()
            selected_tab = next((tab for tab in all_tabs if tab['id'] == self.current_selected_tab_id), None)
            if selected_tab:
                preset_tab_name = selected_tab['name']
                # 获取该tab下的第一个card
                available_cards = self.custom_button_manager.get_available_cards(preset_tab_name)
                if available_cards:
                    preset_card_name = available_cards[0]
        
        from ui.custom_button_dialog import ButtonEditDialog
        dialog = ButtonEditDialog(
            self.custom_button_manager,
            preset_tab_name=preset_tab_name,
            preset_card_name=preset_card_name,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            button_data = dialog.get_button_data()
            if self.custom_button_manager.add_button(button_data):
                # 重新加载数据，但保持当前的搜索和过滤条件
                self.load_buttons()
                # 重新应用当前过滤条件
                self.apply_filters()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮添加成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮添加失败，请检查日志"))
    
    def on_button_table_item_double_clicked(self, item):
        """处理按钮表格项双击事件"""
        if item:
            self.edit_button()
    
    def edit_button(self):
        """编辑按钮"""
        current_row = self.button_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的按钮"))
            return
        
        button_id = self.button_table.item(current_row, 0).data(Qt.UserRole)
        buttons = self.custom_button_manager.get_all_buttons()
        button_data = next((btn for btn in buttons if btn['id'] == button_id), None)
        
        if button_data:
            from ui.custom_button_dialog import ButtonEditDialog
            dialog = ButtonEditDialog(self.custom_button_manager, button_data=button_data, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_data = dialog.get_button_data()
                if self.custom_button_manager.update_button(button_id, updated_data):
                    # 重新加载数据，但保持当前的搜索和过滤条件
                    self.load_buttons()
                    # 重新应用当前过滤条件
                    self.apply_filters()
                    QMessageBox.information(self, self.tr("成功"), self.tr("按钮更新成功！"))
                else:
                    QMessageBox.warning(self, self.tr("失败"), self.tr("按钮更新失败，请检查日志"))
    
    def delete_button(self):
        """删除按钮"""
        current_row = self.button_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的按钮"))
            return
        
        button_name = self.button_table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除按钮')} '{button_name}' {self.tr('吗？')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            button_id = self.button_table.item(current_row, 0).data(Qt.UserRole)
            if self.custom_button_manager.delete_button(button_id):
                # 重新加载数据，但保持当前的搜索和过滤条件
                self.load_buttons()
                # 重新应用当前过滤条件
                self.apply_filters()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮删除成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮删除失败，请检查日志"))
    
    def on_button_rows_reordered(self, ordered_ids):
        """处理按钮拖拽排序"""
        if not ordered_ids:
            return

        if not self.custom_button_manager.reorder_buttons(ordered_ids):
            QMessageBox.warning(self, self.tr("失败"), self.tr("按钮排序保存失败，请检查日志"))
        else:
            # 重新加载数据，但保持当前的搜索和过滤条件
            self.load_buttons()
            # 重新应用当前过滤条件
            self.apply_filters()

    def _get_selected_card_tab_name(self):
        """获取选中card所属的tab名称"""
        if not self.current_selected_card_name:
            return None
        
        # 如果是预置card，使用current_selected_tab_id
        if self.current_selected_card_is_preset:
            if self.current_selected_tab_id:
                all_tabs = self.tab_config_manager.get_all_tabs()
                selected_tab = next((tab for tab in all_tabs if tab['id'] == self.current_selected_tab_id), None)
                return selected_tab['name'] if selected_tab else None
            return None
        
        # 如果是自定义card，从custom_cards中查找
        card = next(
            (c for c in self.tab_config_manager.custom_cards 
             if c.get('name') == self.current_selected_card_name), 
            None
        )
        if card:
            tab_id = card.get('tab_id')
            if tab_id:
                # 从custom_tabs中查找
                custom_tab = next(
                    (tab for tab in self.tab_config_manager.custom_tabs 
                     if tab['id'] == tab_id), 
                    None
                )
                return custom_tab['name'] if custom_tab else None
        
        return None
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            logger.debug(
                f"UnifiedManagerDialog关闭: current_selected_tab_id={self.current_selected_tab_id}, "
                f"is_selected_custom_tab={self.is_selected_custom_tab}"
            )
            # 保存当前配置
            self.save_config()
            event.accept()
        except Exception as e:
            logger.exception(f"{self.tr('保存配置失败:')} {e}")
            event.accept()
