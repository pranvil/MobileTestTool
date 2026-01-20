"""
创建Confluence页面功能界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTextEdit, QMessageBox, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QDateEdit,
    QProgressBar, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QRadioButton, QButtonGroup, QCheckBox,
    QSizePolicy, QTabWidget
)
from Jira_tool.ui.chapter_editor import ChapterEditor
from PySide6.QtCore import Qt, QThread, Signal, QDate, QUrl
from PySide6.QtGui import QDesktopServices
from datetime import datetime
import html as html_utils
import re
from typing import Dict, List, Any, Optional
from Jira_tool.confluence_client import (
    get_page_content, get_page_by_id, create_page, ConfluenceAPIError, reset_client
)
from Jira_tool.modules.confluence_template import (
    get_template_list, load_template_from_confluence, replace_variables,
    get_template_fields
)
from Jira_tool.modules.confluence_page_tree import (
    load_page_tree, load_children, load_all_pages,
    should_auto_load_page_tree, mark_auto_loaded,
    clear_page_tree_cache
)
from core.jira_config_manager import (
    get_default_confluence_space, set_default_confluence_space,
    get_confluence_url,
)
from core.debug_logger import logger


class LoadTemplateThread(QThread):
    """加载模板线程"""
    finished = Signal(bool, str, list)  # success, content, fields
    error = Signal(str)  # error_message
    
    def __init__(self, page_id: str):
        super().__init__()
        self.page_id = page_id
    
    def run(self):
        """执行加载模板"""
        try:
            content = load_template_from_confluence(self.page_id)
            fields = get_template_fields(self.page_id)  # 使用JSON配置
            self.finished.emit(True, content, fields)
        except Exception as e:
            logger.exception(f"加载模板线程异常: {e}")
            self.error.emit(str(e))


class LoadPagesThread(QThread):
    """加载页面树线程"""
    finished = Signal(bool, str, list)  # success, homepage_id, pages
    error = Signal(str)  # error_message
    
    def __init__(self, space_key: str, force_reload: bool = False, load_all: bool = False):
        super().__init__()
        self.space_key = space_key
        self.force_reload = force_reload
        self.load_all = load_all
    
    def run(self):
        """执行加载页面树"""
        try:
            homepage_id, pages = load_page_tree(self.space_key, force_reload=self.force_reload)
            
            # 如果手动刷新，加载所有目录
            if self.load_all and homepage_id:
                logger.info(f"开始加载所有目录: {self.space_key}")
                load_all_pages(self.space_key, homepage_id)
                # 重新获取一级目录（确保是最新的）
                homepage_id, pages = load_page_tree(self.space_key, force_reload=True)
            
            self.finished.emit(True, homepage_id or "", pages)
        except Exception as e:
            logger.exception(f"加载页面树线程异常: {e}")
            self.error.emit(str(e))


class LoadChildrenThread(QThread):
    """加载子页面线程"""
    finished = Signal(str, list)  # page_id, children
    error = Signal(str, str)  # page_id, error_message
    
    def __init__(self, page_id: str, space_key: str):
        super().__init__()
        self.page_id = page_id
        self.space_key = space_key
    
    def run(self):
        """执行加载子页面"""
        try:
            children = load_children(self.page_id, self.space_key)
            self.finished.emit(self.page_id, children)
        except Exception as e:
            logger.exception(f"加载子页面线程异常: {e}")
            self.error.emit(self.page_id, str(e))


class LoadPageContentThread(QThread):
    """按需加载页面内容线程"""
    finished = Signal(str, str, int)  # page_id, html, version
    error = Signal(str, str)  # page_id, error_message
    
    def __init__(self, page_id: str):
        super().__init__()
        self.page_id = page_id
    
    def run(self):
        """执行加载页面内容"""
        try:
            page_data = get_page_by_id(self.page_id, expand="body.view,version")
            body = page_data.get("body", {}) if isinstance(page_data, dict) else {}
            view = body.get("view", {}) if isinstance(body, dict) else {}
            html = view.get("value", "") if isinstance(view, dict) else ""
            
            if not html:
                page_data = get_page_by_id(self.page_id, expand="body.storage,version")
                body = page_data.get("body", {}) if isinstance(page_data, dict) else {}
                storage = body.get("storage", {}) if isinstance(body, dict) else {}
                html = storage.get("value", "") if isinstance(storage, dict) else ""
            
            version = 0
            if isinstance(page_data, dict):
                version_value = (page_data.get("version") or {}).get("number")
                if isinstance(version_value, int):
                    version = version_value
            
            if not html:
                html = "<p>该页面无正文或无法加载。</p>"
            
            self.finished.emit(self.page_id, html, version)
        except Exception as e:
            logger.exception(f"加载页面内容线程异常: {e}")
            self.error.emit(self.page_id, str(e))


class CreatePageThread(QThread):
    """创建页面线程"""
    finished = Signal(bool, dict)  # success, result
    error = Signal(str)  # error_message
    
    def __init__(self, title: str, content: str, space_key: str, parent_id: Optional[str], image_files: List[str] = None):
        super().__init__()
        self.title = title
        self.content = content
        self.space_key = space_key
        self.parent_id = parent_id
        self.image_files = image_files or []
    
    def run(self):
        """执行创建页面"""
        try:
            # 先创建页面
            result = create_page(self.title, self.content, self.space_key, self.parent_id)
            page_id = result.get('id', '')
            
            if not page_id:
                raise Exception("创建页面失败：未获取到页面ID")
            
            # 上传所有图片附件
            if self.image_files:
                from Jira_tool.confluence_client import upload_attachment
                from pathlib import Path
                
                logger.info(f"开始上传 {len(self.image_files)} 个图片附件到页面 {page_id}")
                for image_file in self.image_files:
                    if image_file and Path(image_file).exists():
                        try:
                            upload_attachment(page_id, image_file)
                            logger.info(f"成功上传图片: {Path(image_file).name}")
                        except Exception as e:
                            logger.warning(f"上传图片失败 {Path(image_file).name}: {e}")
                            # 继续上传其他图片，不因单个失败而中断
            
            self.finished.emit(True, result)
        except Exception as e:
            logger.exception(f"创建页面线程异常: {e}")
            self.error.emit(str(e))


class ConfluenceCreateWidget(QWidget):
    """创建Confluence页面界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_template_content = ""
        self.current_template_fields: List[Dict] = []
        self.current_template_page_id = ""
        self.current_space_key = get_default_confluence_space()
        self.current_homepage_id = ""
        self.selected_parent_id = ""
        self.field_widgets: Dict[str, Any] = {}  # {field_name: widget}
        self.load_template_thread = None
        self.load_pages_thread = None
        self.load_children_threads: List[LoadChildrenThread] = []  # 保存所有子页面加载线程
        self.load_page_content_thread = None
        self.create_page_thread = None
        self.page_preview_cache: Dict[str, Dict[str, Any]] = {}
        self._last_preview_page_id = ""
        self.init_ui()
        # 不在这里加载，由主窗口在启动时自动加载
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("创建Confluence页面")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(title)
        
        # 创建主分割器（左右分割）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ========== 左侧：树形结构（25%） ==========
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        tree_group = QGroupBox("选择创建位置")
        tree_layout = QVBoxLayout()
        self.page_tree = QTreeWidget()
        self.page_tree.setIndentation(12) 
        self.page_tree.setHeaderLabel("页面目录")
        self.page_tree.itemExpanded.connect(self.on_item_expanded)
        self.page_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        tree_layout.addWidget(self.page_tree)
        self.selected_location_label = QLabel("未选择位置")
        self.selected_location_label.setStyleSheet("color: gray; padding: 5px;")
        tree_layout.addWidget(self.selected_location_label)
        tree_group.setLayout(tree_layout)
        left_layout.addWidget(tree_group)
        
        left_widget.setLayout(left_layout)
        main_splitter.addWidget(left_widget)
        
        # ========== 右侧：主要内容区域（75%） ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 第一行：空间配置和模板选择（合并为一行）
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(10)
        
        # 空间配置
        space_input_layout = QHBoxLayout()
        space_input_layout.addWidget(QLabel("空间Key:"))
        self.space_input = QLineEdit()
        self.space_input.setText(self.current_space_key)
        self.space_input.setPlaceholderText("例如: USVAL")
        # 设置输入框固定大小，不自动缩放（宽度为原来的一半）
        self.space_input.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.space_input.setMaximumWidth(150)  # 设置最大宽度
        space_input_layout.addWidget(self.space_input)
        
        # 刷新目录按钮放在输入框后面
        self.refresh_space_button = QPushButton("刷新目录")
        self.refresh_space_button.clicked.connect(lambda: self.refresh_page_tree(force_reload=True, show_loading=True, load_all=True))
        space_input_layout.addWidget(self.refresh_space_button)
        space_input_layout.addStretch()
        top_row_layout.addLayout(space_input_layout)
        
        # 模板选择
        template_select_layout = QHBoxLayout()
        template_label = QLabel("选择模板:")
        # 设置label宽度固定，不随窗口大小调整
        template_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        template_select_layout.addWidget(template_label)
        self.template_combo = QComboBox()
        templates = get_template_list()
        for template in templates:
            self.template_combo.addItem(template['name'], template['page_id'])
        self.template_combo.currentIndexChanged.connect(self.on_template_changed)
        template_select_layout.addWidget(self.template_combo)
        self.load_template_button = QPushButton("加载模板")
        self.load_template_button.clicked.connect(self.load_template)
        template_select_layout.addWidget(self.load_template_button)
        template_select_layout.addStretch()
        top_row_layout.addLayout(template_select_layout)
        
        right_layout.addLayout(top_row_layout)
        
        # 页面信息区域（占据剩余空间）
        self.form_group = QGroupBox("页面信息")
        form_container_layout = QVBoxLayout()
        form_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 页面标题输入（在表单顶部）
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("页面标题:"))
        self.page_title_input = QLineEdit()
        self.page_title_input.setPlaceholderText("请输入页面标题（必填）")
        self.page_title_input.textChanged.connect(self.update_create_button_state)
        title_layout.addWidget(self.page_title_input)
        form_container_layout.addLayout(title_layout)
        
        # 使用滚动区域
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.form_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.form_widget = QWidget()
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_widget.setLayout(self.form_layout)
        self.form_scroll.setWidget(self.form_widget)
        
        form_container_layout.addWidget(self.form_scroll)
        self.form_group.setLayout(form_container_layout)
        
        # 页面预览区域（轻量）
        self.preview_group = QGroupBox("页面预览（轻量）")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(6, 6, 6, 6)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("选择左侧页面后自动加载预览内容")
        self.preview_text.setMinimumHeight(180)
        preview_layout.addWidget(self.preview_text)
        self.preview_group.setLayout(preview_layout)
        
        # Tab切换（页面信息/页面预览）
        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self.form_group, "页面信息")
        self.right_tabs.addTab(self.preview_group, "页面预览")
        right_layout.addWidget(self.right_tabs, stretch=1)
        
        # 操作按钮区域（在页面信息下方）
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)
        
        self.preview_button = QPushButton("预览")
        self.preview_button.clicked.connect(self.preview_content)
        self.preview_button.setEnabled(False)
        button_layout.addWidget(self.preview_button)
        
        self.create_button = QPushButton("创建页面")
        self.create_button.clicked.connect(self.start_create)
        self.create_button.setEnabled(False)
        button_layout.addWidget(self.create_button)
        
        button_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)
        
        button_container.setLayout(button_layout)
        right_layout.addWidget(button_container)
        
        right_widget.setLayout(right_layout)
        main_splitter.addWidget(right_widget)
        
        # 设置主分割器比例（25%-75%）
        main_splitter.setSizes([1, 3])
        main_layout.addWidget(main_splitter, stretch=1)
        
        self.setLayout(main_layout)
    
    def load_initial_data(self, auto_load: bool = False):
        """
        加载初始数据
        
        Args:
            auto_load: 是否为自动加载（如果是，检查24小时限制）
        """
        space_key = self.space_input.text().strip() or self.current_space_key
        if not space_key:
            return
        
        # 如果是自动加载，检查是否需要加载
        if auto_load:
            if not should_auto_load_page_tree(space_key):
                logger.debug(f"空间 {space_key} 在24小时内已自动加载过，跳过")
                # 尝试从缓存加载
                self.load_from_cache(space_key)
                return
        
        # 加载页面树
        self.refresh_page_tree(force_reload=False, show_loading=False)
        
        # 标记已自动加载
        if auto_load:
            mark_auto_loaded(space_key)
    
    def load_from_cache(self, space_key: str):
        """从缓存加载页面树"""
        try:
            homepage_id, pages = load_page_tree(space_key, force_reload=False)
            if homepage_id and pages:
                self.current_space_key = space_key
                self.current_homepage_id = homepage_id
                self.populate_tree(homepage_id, pages)
        except Exception as e:
            logger.warning(f"从缓存加载失败: {e}")
    
    def refresh_page_tree(self, force_reload: bool = True, show_loading: bool = True, load_all: bool = False):
        """
        刷新页面树
        
        Args:
            force_reload: 是否强制重新加载
            show_loading: 是否显示加载状态
            load_all: 是否加载所有目录（手动刷新时）
        """
        space_key = self.space_input.text().strip()
        if not space_key:
            QMessageBox.warning(self, "警告", "请输入空间Key")
            return
        
        self.current_space_key = space_key
        set_default_confluence_space(space_key)
        
        # 如果是手动刷新（load_all=True），清空缓存数据
        # 因为手动刷新只刷新2层目录，其他更深的会使用缓存，可能是错的
        if load_all:
            clear_page_tree_cache(space_key)
        
        # 清空树
        self.page_tree.clear()
        self.selected_parent_id = ""
        self.selected_location_label.setText("未选择位置")
        
        if show_loading:
            # 显示加载状态
            loading_item = QTreeWidgetItem(self.page_tree)
            loading_text = "正在加载所有目录..." if load_all else "正在加载..."
            loading_item.setText(0, loading_text)
            self.page_tree.setEnabled(False)
        
        # 启动加载线程
        if self.load_pages_thread and self.load_pages_thread.isRunning():
            # 如果线程正在运行，等待它完成
            self.load_pages_thread.wait()
        
        self.load_pages_thread = LoadPagesThread(space_key, force_reload, load_all)
        self.load_pages_thread.finished.connect(self.on_pages_loaded)
        self.load_pages_thread.error.connect(self.on_pages_load_error)
        self.load_pages_thread.start()
    
    def populate_tree(self, homepage_id: str, pages: List[Dict]):
        """填充树形控件"""
        self.page_tree.clear()
        self.current_homepage_id = homepage_id
        
        # 添加根节点（空间首页）
        root_item = QTreeWidgetItem(self.page_tree)
        root_item.setText(0, "空间首页")
        root_item.setData(0, Qt.ItemDataRole.UserRole, homepage_id)
        
        # 添加一级目录
        for page in pages:
            item = self._create_tree_item(page, root_item)
            # 检查是否有子页面
            children = page.get('children', {})
            if children:
                page_children = children.get('page', {})
                if page_children and page_children.get('size', 0) > 0:
                    # 添加占位符，实现懒加载
                    placeholder = QTreeWidgetItem(item)
                    placeholder.setText(0, "加载中...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
        
        # 默认展开第一层级（根节点）
        root_item.setExpanded(True)
    
    def on_pages_loaded(self, success: bool, homepage_id: str, pages: List[Dict]):
        """页面树加载完成"""
        self.page_tree.setEnabled(True)
        
        if not success or not pages:
            if self.page_tree.topLevelItemCount() == 0:
                QMessageBox.warning(self, "提示", "未找到页面或空间不存在")
            return
        
        self.populate_tree(homepage_id, pages)
    
    def _create_tree_item(self, page: Dict, parent: QTreeWidgetItem) -> QTreeWidgetItem:
        """创建树节点"""
        item = QTreeWidgetItem(parent)
        item.setText(0, page.get('title', 'N/A'))
        item.setData(0, Qt.ItemDataRole.UserRole, page.get('id'))
        return item
    
    def on_pages_load_error(self, error_msg: str):
        """页面树加载错误"""
        self.page_tree.clear()
        self.page_tree.setEnabled(True)
        QMessageBox.critical(self, "错误", f"加载页面树失败:\n{error_msg}")
    
    def on_item_expanded(self, item: QTreeWidgetItem):
        """树节点展开事件（懒加载）"""
        page_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not page_id or page_id == "placeholder":
            return
        
        # 检查是否已加载
        if item.childCount() > 0:
            first_child = item.child(0)
            if first_child.data(0, Qt.ItemDataRole.UserRole) == "placeholder":
                # 移除占位符
                item.removeChild(first_child)
                # 加载子页面
                self.load_children_for_item(item, page_id)
    
    def load_children_for_item(self, parent_item: QTreeWidgetItem, page_id: str):
        """为树节点加载子页面"""
        # 检查是否已有线程在加载
        for thread in self.load_children_threads:
            if thread.page_id == page_id and thread.isRunning():
                logger.debug(f"页面 {page_id} 正在加载中，跳过")
                return
        
        thread = LoadChildrenThread(page_id, self.current_space_key)
        self.load_children_threads.append(thread)
        
        # 使用局部变量避免闭包问题
        def on_finished(pid, children):
            self.on_children_loaded(parent_item, children)
            if thread in self.load_children_threads:
                self.load_children_threads.remove(thread)
        
        def on_error(pid, error):
            self.on_children_load_error(parent_item, error)
            if thread in self.load_children_threads:
                self.load_children_threads.remove(thread)
        
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        thread.start()
    
    def on_children_loaded(self, parent_item: QTreeWidgetItem, children: List[Dict]):
        """子页面加载完成"""
        for page in children:
            item = self._create_tree_item(page, parent_item)
            # 检查是否有子页面
            page_children = page.get('children', {})
            if page_children:
                page_children_obj = page_children.get('page', {})
                if page_children_obj and page_children_obj.get('size', 0) > 0:
                    placeholder = QTreeWidgetItem(item)
                    placeholder.setText(0, "加载中...")
                    placeholder.setData(0, Qt.ItemDataRole.UserRole, "placeholder")
    
    def on_children_load_error(self, parent_item: QTreeWidgetItem, error_msg: str):
        """子页面加载错误"""
        logger.warning(f"加载子页面失败: {error_msg}")
        # 不显示错误对话框，避免干扰用户
    
    def on_tree_selection_changed(self):
        """树选择改变"""
        selected_items = self.page_tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            page_id = item.data(0, Qt.ItemDataRole.UserRole)
            if page_id and page_id != "placeholder":
                self.selected_parent_id = page_id
                page_title = item.text(0)
                self.selected_location_label.setText(f"创建位置: {page_title}")
                self.update_create_button_state()
                self.load_page_preview(page_id, page_title)
            else:
                self.selected_parent_id = ""
                self.selected_location_label.setText("未选择位置")
                self.set_preview_status("请选择页面以预览内容")
        else:
            self.selected_parent_id = ""
            self.selected_location_label.setText("未选择位置")
            self.set_preview_status("请选择页面以预览内容")

    def set_preview_status(self, message: str):
        """设置预览区状态文本"""
        html = f"<p style='color:#666;'>{message}</p>"
        self.preview_text.setHtml(html)
    
    def load_page_preview(self, page_id: str, page_title: str):
        """按需加载页面预览内容"""
        self._last_preview_page_id = page_id
        cached = self.page_preview_cache.get(page_id)
        if cached and cached.get("html"):
            self.show_page_preview(cached.get("html", ""), page_title)
            return
        
        self.set_preview_status("正在加载页面内容...")
        if self.load_page_content_thread and self.load_page_content_thread.isRunning():
            # 允许多个请求并发，但只展示最后一次选择的页面
            pass
        
        thread = LoadPageContentThread(page_id)
        self.load_page_content_thread = thread
        
        def on_finished(pid: str, html: str, version: int):
            if pid != self._last_preview_page_id:
                return
            self.page_preview_cache[pid] = {"html": html, "version": version}
            self.show_page_preview(html, page_title)
        
        def on_error(pid: str, error_msg: str):
            if pid != self._last_preview_page_id:
                return
            logger.warning(f"页面预览加载失败: {error_msg}")
            self.set_preview_status("预览失败，可点击创建结果中的链接在浏览器打开。")
        
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        thread.start()
    
    def show_page_preview(self, html: str, page_title: str):
        """展示预览内容（轻量HTML）"""
        base_url = get_confluence_url().rstrip("/")
        safe_html = self._sanitize_preview_html(html)
        if len(safe_html) > 400_000:
            plain = self._html_to_plain_text(safe_html)
            self.preview_text.setPlainText(plain)
            return
        
        styled_content = f"""
        <html>
        <head>
        <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 12px;
            line-height: 1.5;
        }}
        h1, h2, h3 {{
            color: #333;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 6px 10px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        </style>
        </head>
        <body>
        <h3 style="margin-top:0;">{page_title}</h3>
        {safe_html}
        </body>
        </html>
        """
        self.preview_text.document().setBaseUrl(QUrl(base_url))
        self.preview_text.setHtml(styled_content)

    def _sanitize_preview_html(self, html: str) -> str:
        """清理可能导致预览崩溃的HTML片段"""
        if not html:
            return ""
        safe = html
        # 移除可能引发渲染问题的标签
        safe = re.sub(r'<!DOCTYPE[^>]*>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'<\?xml[^>]*\?>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'</?html[^>]*>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'</?head[^>]*>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'</?body[^>]*>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'<meta[^>]*>', '', safe, flags=re.IGNORECASE)
        safe = re.sub(r'<style[^>]*>.*?</style>', '', safe, flags=re.IGNORECASE | re.DOTALL)
        safe = re.sub(r'<script[^>]*>.*?</script>', '', safe, flags=re.IGNORECASE | re.DOTALL)
        # 将内联黑色替换为暗色主题文本色，避免黑底黑字
        dark_text_color = "#EAEAEA"
        safe = re.sub(
            r'color\s*:\s*(?:black|#000000|#000|rgb\(\s*0\s*,\s*0\s*,\s*0\s*\)|rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*1\s*\))',
            f"color: {dark_text_color}",
            safe,
            flags=re.IGNORECASE,
        )
        # Confluence 宏整体替换为占位文本
        safe = re.sub(r'<ac:structured-macro[^>]*>.*?</ac:structured-macro>', '<p>[宏内容已省略]</p>', safe, flags=re.IGNORECASE | re.DOTALL)
        return safe.strip()
    
    def _html_to_plain_text(self, html: str) -> str:
        """HTML转纯文本（极端情况下的兜底）"""
        text = re.sub(r'<[^>]+>', '', html or '')
        return html_utils.unescape(text).strip()
    
    def on_template_changed(self, index: int):
        """模板选择改变"""
        # 清空表单
        self.clear_form()
        self.current_template_content = ""
        self.current_template_fields = []
        self.current_template_page_id = ""
    
    def load_template(self):
        """加载模板"""
        index = self.template_combo.currentIndex()
        if index < 0:
            QMessageBox.warning(self, "警告", "请选择模板")
            return
        
        page_id = self.template_combo.currentData()
        template_name = self.template_combo.currentText()
        
        self.load_template_button.setEnabled(False)
        self.clear_form()
        
        # 启动加载线程
        self.load_template_thread = LoadTemplateThread(page_id)
        self.load_template_thread.finished.connect(self.on_template_loaded)
        self.load_template_thread.error.connect(self.on_template_load_error)
        self.load_template_thread.start()
    
    def on_template_loaded(self, success: bool, content: str, fields: List[Dict]):
        """模板加载完成"""
        self.load_template_button.setEnabled(True)
        
        if not success:
            return
        
        self.current_template_content = content
        self.current_template_fields = fields
        self.current_template_page_id = self.template_combo.currentData()
        
        # 生成表单
        self.generate_form(fields)
        self.update_create_button_state()
    
    def on_template_load_error(self, error_msg: str):
        """模板加载错误"""
        self.load_template_button.setEnabled(True)
        QMessageBox.critical(self, "错误", f"加载模板失败:\n{error_msg}")
    
    def generate_form(self, fields: List[Dict]):
        """根据字段生成表单（支持多列布局）"""
        self.clear_form()
        self.field_widgets.clear()
        
        # 按row_group分组字段
        row_groups = {}
        standalone_fields = []
        
        for field in fields:
            field_name = field.get('field_name', '')
            if not field_name:
                continue
            
            row_group = field.get('row_group')
            if row_group:
                if row_group not in row_groups:
                    row_groups[row_group] = []
                row_groups[row_group].append(field)
            else:
                standalone_fields.append(field)
        
        # 处理分组字段（同一组放在一行）
        for group_name, group_fields in row_groups.items():
            self._add_row_group(group_fields)
        
        # 处理独立字段（每个字段一行）
        for field in standalone_fields:
            self._add_single_field(field)
    
    def _add_single_field(self, field: Dict):
        """添加单个字段到表单"""
        field_name = field.get('field_name', '')
        field_label = field.get('name', '')
        field_type = field.get('type', 'text')
        required = field.get('required', False)
        
        # 创建标签
        label_text = field_label
        if required:
            label_text += " *"
        label = QLabel(label_text)
        
        # 创建控件
        widget = self._create_field_widget(field)
        
        # 添加到表单
        self.form_layout.addRow(label, widget)
        self.field_widgets[field_name] = {
            'widget': widget,
            'field': field
        }
    
    def _add_row_group(self, fields: List[Dict]):
        """将多个字段添加到同一行"""
        # 创建容器widget
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)
        
        widgets = []
        for field in fields:
            field_name = field.get('field_name', '')
            field_label = field.get('name', '')
            required = field.get('required', False)
            
            # 创建字段容器（标签+输入）
            field_container = QWidget()
            field_layout = QVBoxLayout()
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(2)
            
            # 标签
            label_text = field_label
            if required:
                label_text += " *"
            label = QLabel(label_text)
            label.setStyleSheet("font-size: 11px;")
            field_layout.addWidget(label)
            
            # 输入控件
            widget = self._create_field_widget(field)
            field_layout.addWidget(widget)
            
            field_container.setLayout(field_layout)
            container_layout.addWidget(field_container)
            
            widgets.append({
                'widget': widget,
                'field': field,
                'field_name': field_name
            })
        
        container_layout.addStretch()
        container.setLayout(container_layout)
        
        # 添加到表单（使用一个标签占位）
        group_label = QLabel("")  # 空标签作为占位
        self.form_layout.addRow(group_label, container)
        
        # 保存所有字段的widget
        for item in widgets:
            self.field_widgets[item['field_name']] = {
                'widget': item['widget'],
                'field': item['field']
            }
    
    def _create_field_widget(self, field: Dict) -> QWidget:
        """创建字段控件"""
        field_type = field.get('type', 'text')
        default_value = field.get('default', '')
        
        if field_type == "table":
            return self._create_table_widget(field)
        elif field_type == "chapters":
            # 章节编辑器
            editor = ChapterEditor()
            editor.setMinimumHeight(400)
            return editor
        elif field_type == "date":
            widget = QDateEdit()
            widget.setDate(QDate.currentDate())
            widget.setCalendarPopup(True)
            return widget
        elif field_type == "textarea":
            # 会议纪要模板：参加人员只需要单行输入（节省空间）
            if self.current_template_page_id == "310457377" and field.get("field_name") == "participants":
                widget = QLineEdit()
                if default_value:
                    widget.setText(str(default_value))
                return widget
            widget = QTextEdit()
            widget.setMaximumHeight(100)
            if default_value:
                widget.setPlainText(str(default_value))
            return widget
        elif field_type == "richtext":
            # 富文本编辑器
            widget = QTextEdit()
            widget.setAcceptRichText(True)
            widget.setMinimumHeight(200)
            widget.setMaximumHeight(400)
            if default_value:
                widget.setHtml(str(default_value))
            return widget
        elif field_type == "richtext_advanced":
            # 高级富文本编辑器（支持图片和表格）
            from Jira_tool.ui.richtext_editor import RichTextEditor
            editor = RichTextEditor()
            # 让“测试说明”等富文本区域默认更高，并且不再被最大高度限制
            editor.setMinimumHeight(700)
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            if default_value:
                editor.set_content(str(default_value))
            return editor
        elif field_type == "radio":
            return self._create_radio_group(field)
        elif field_type == "checkbox":
            widget = QCheckBox()
            default = field.get('default', False)
            widget.setChecked(default)
            return widget
        else:
            widget = QLineEdit()
            if default_value:
                widget.setText(str(default_value))
            placeholder = field.get('placeholder', '')
            if placeholder:
                widget.setPlaceholderText(placeholder)
            return widget
    
    def _create_table_widget(self, field: Dict) -> QWidget:
        """
        创建表格控件（支持动态添加/删除行）
        
        Args:
            field: 字段定义
        
        Returns:
            包含表格和操作按钮的QWidget
        """
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建表格
        table = QTableWidget()
        columns = field.get('columns', [])
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([col.get('name', '') for col in columns])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # 默认表格高度（多数表格较短）
        table.setMinimumHeight(150)
        table.setMaximumHeight(300)

        # 三类模板的“问题列表/问题记录”需要更大的编辑区域：至少700px，且不限制最大高度
        issue_table_fields = {"issue_records", "issue_list"}
        issue_table_templates = {"221989592", "310457377", "521081686"}  # 测试用例评审/会议纪要/通用评审
        if (
            str(self.current_template_page_id) in issue_table_templates
            and str(field.get("field_name", "")) in issue_table_fields
        ):
            table.setMinimumHeight(500)
            table.setMaximumHeight(16777215)  # Qt默认最大值，等同于不限制
        
        # 存储列配置到表格属性中
        table.setProperty('columns', columns)
        
        # 检查是否为只读单行模式
        readonly = field.get('readonly', False)
        single_row = field.get('single_row', False)
        
        # 在表格上设置属性，用于后续检查
        table.setProperty('single_row', single_row)
        table.setProperty('readonly', readonly)
        
        if not readonly:
            # 操作按钮
            button_layout = QHBoxLayout()
            add_button = QPushButton("添加行")
            add_button.clicked.connect(lambda: self._add_table_row(table))
            delete_button = QPushButton("删除选中行")
            delete_button.clicked.connect(lambda: self._delete_table_row(table))
            button_layout.addWidget(add_button)
            button_layout.addWidget(delete_button)
            button_layout.addStretch()
            layout.addLayout(button_layout)
        
        layout.addWidget(table)
        container.setLayout(layout)
        
        # 初始添加一行（如果是单行模式，只添加一行；否则添加一行作为默认）
        if single_row:
            self._add_table_row(table)
            # 单行模式：如果只读，禁用编辑；否则允许编辑但限制只能有一行
            if readonly:
                table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        else:
            self._add_table_row(table)
        
        return container
    
    def _add_table_row(self, table: QTableWidget):
        """添加表格行"""
        # 检查是否为单行模式
        single_row = table.property('single_row')
        if single_row and table.rowCount() >= 1:
            # 单行模式，不允许添加更多行
            return
        
        columns = table.property('columns')
        if columns is None:
            columns = []
        
        row = table.rowCount()
        table.insertRow(row)
        
        for col_idx, col in enumerate(columns):
            default_value = col.get('default', '')
            item = QTableWidgetItem(str(default_value) if default_value else "")
            table.setItem(row, col_idx, item)
    
    def _delete_table_row(self, table: QTableWidget):
        """删除选中的表格行"""
        # 检查是否为单行模式
        single_row = table.property('single_row')
        if single_row:
            QMessageBox.information(self, "提示", "单行模式不允许删除行")
            return
        
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
        else:
            QMessageBox.information(self, "提示", "请先选择要删除的行")
    
    def _create_radio_group(self, field: Dict) -> QWidget:
        """
        创建单选按钮组
        
        Args:
            field: 字段定义
        
        Returns:
            包含单选按钮的QWidget
        """
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建按钮组
        button_group = QButtonGroup(container)
        options = field.get('options', [])
        default = field.get('default', '')
        
        for option in options:
            radio = QRadioButton(option)
            if option == default:
                radio.setChecked(True)
            button_group.addButton(radio)
            layout.addWidget(radio)
        
        layout.addStretch()
        container.setLayout(layout)
        
        # 存储按钮组到容器属性中
        container.setProperty('button_group', button_group)
        
        return container
    
    def clear_form(self):
        """清空表单"""
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self.field_widgets.clear()
    
    def _collect_image_files_from_chapters(self, chapters: List[Dict]) -> List[str]:
        """从章节数据中收集所有图片文件路径"""
        image_files = []
        
        def collect_from_chapter(chapter: Dict):
            # 收集当前章节的图片
            for image in chapter.get("images", []):
                filepath = image.get("filepath", "")
                if filepath:
                    image_files.append(filepath)
            # 递归收集子章节的图片
            for subchapter in chapter.get("sections", []):
                collect_from_chapter(subchapter)
        
        for chapter in chapters:
            collect_from_chapter(chapter)
        
        return image_files
    
    def get_form_values(self) -> Dict[str, Any]:
        """获取表单值（支持表格数据和章节数据）"""
        values = {}
        for field_name, field_data in self.field_widgets.items():
            widget = field_data['widget']
            field = field_data['field']
            field_type = field.get('type', 'text')
            
            if field_type == "chapters":
                # 章节数据：从章节编辑器获取
                if isinstance(widget, ChapterEditor):
                    chapters = widget.get_chapters()
                    # 生成章节 HTML 和目录
                    from Jira_tool.modules.local_templates import generate_summary_doc_chapters
                    toc_html, chapters_html = generate_summary_doc_chapters(chapters, generate_toc=True)
                    values[field_name] = chapters_html
                    values["table_of_contents"] = toc_html  # 添加目录
            elif field_type == "table":
                # 表格数据：返回列表
                table = self._get_table_from_widget(widget)
                if table:
                    table_data = self._get_table_data(table)
                    # 如果是单行模式，只返回第一行
                    if field.get('single_row', False):
                        table_data = table_data[:1] if table_data else [{}]
                    values[field_name] = table_data
            elif field_type == "radio":
                # 单选按钮组：获取选中的按钮文本
                button_group = widget.property('button_group')
                if button_group:
                    checked_button = button_group.checkedButton()
                    value = checked_button.text() if checked_button else ""
                else:
                    # 尝试从容器中查找按钮组
                    button_groups = widget.findChildren(QButtonGroup)
                    if button_groups:
                        checked_button = button_groups[0].checkedButton()
                        value = checked_button.text() if checked_button else ""
                    else:
                        value = ""
                values[field_name] = value
            elif field_type == "checkbox":
                # 复选框：返回是否选中
                value = "是" if widget.isChecked() else "否"
                values[field_name] = value
            elif isinstance(widget, QDateEdit):
                value = widget.date().toString("yyyy-MM-dd")
                values[field_name] = value
            elif isinstance(widget, QTextEdit):
                if field_type == "richtext":
                    # 富文本：获取HTML内容
                    value = widget.toHtml()
                else:
                    # 普通文本：获取纯文本
                    value = widget.toPlainText()
                values[field_name] = value
            elif field_type == "richtext_advanced":
                # 高级富文本编辑器：获取内容
                from Jira_tool.ui.richtext_editor import RichTextEditor
                if isinstance(widget, RichTextEditor):
                    value = widget.get_content()
                    values[field_name] = value
            else:
                value = widget.text()
                values[field_name] = value
            
            # 同时使用字段名和显示名称作为key
            field_label = field.get('name', '')
            if field_label and field_type != "table":
                values[field_label] = values.get(field_name, "")
        
        # 如果是测试指导模板，也生成浮动目录（即使没有chapters字段）
        if self.current_template_page_id == "TEST_GUIDE" and "table_of_contents" not in values:
            from Jira_tool.modules.local_templates import generate_table_of_contents
            # 生成浮动目录（会自动扫描页面中的标题）
            toc_html = generate_table_of_contents([], None)
            values["table_of_contents"] = toc_html
        
        return values
    
    def _get_table_from_widget(self, widget: QWidget) -> Optional[QTableWidget]:
        """从容器widget中获取QTableWidget"""
        if isinstance(widget, QTableWidget):
            return widget
        # 如果是容器，查找其中的QTableWidget
        for child in widget.findChildren(QTableWidget):
            return child
        return None
    
    def _get_table_data(self, table: QTableWidget) -> List[Dict[str, str]]:
        """获取表格数据"""
        rows = []
        # property() 只接受一个参数，需要单独处理默认值
        columns = table.property('columns') if table.property('columns') is not None else []
        
        if not columns:
            return rows
        
        for row in range(table.rowCount()):
            row_data = {}
            for col_idx, col in enumerate(columns):
                col_field = col.get('field_name', '')
                item = table.item(row, col_idx)
                value = item.text() if item else ""
                row_data[col_field] = value
            # 添加所有行（包括空行），让预览能显示表格结构
            rows.append(row_data)
        
        return rows
    
    def validate_form(self) -> tuple[bool, str]:
        """验证表单（包括表格字段）"""
        for field_name, field_data in self.field_widgets.items():
            field = field_data['field']
            field_type = field.get('type', 'text')
            
            if not field.get('required', False):
                continue
            
            widget = field_data['widget']
            
            if field_type == "radio":
                # 单选按钮：检查是否有选中项
                button_group = widget.property('button_group')
                if not button_group:
                    # 尝试从容器中查找按钮组
                    button_groups = widget.findChildren(QButtonGroup)
                    if button_groups:
                        button_group = button_groups[0]
                
                if button_group:
                    checked_button = button_group.checkedButton()
                    if not checked_button:
                        field_label = field.get('name', field_name)
                        return False, f"请选择必填字段: {field_label}"
            elif field_type == "checkbox":
                # 复选框：必填时检查是否选中
                if not widget.isChecked():
                    field_label = field.get('name', field_name)
                    return False, f"请勾选必填字段: {field_label}"
            elif field_type == "table":
                # 验证表格：至少有一行数据
                table = self._get_table_from_widget(widget)
                if table:
                    table_data = self._get_table_data(table)
                    if not table_data:
                        field_label = field.get('name', field_name)
                        return False, f"请填写必填字段: {field_label}"
                    
                    # 验证表格中必填列
                    columns = field.get('columns', [])
                    for row_idx, row_data in enumerate(table_data):
                        for col in columns:
                            if col.get('required', False):
                                col_field = col.get('field_name', '')
                                if not row_data.get(col_field, '').strip():
                                    col_name = col.get('name', '')
                                    field_label = field.get('name', field_name)
                                    return False, f"请填写必填字段: {field_label} 的第 {row_idx + 1} 行的 {col_name}"
            else:
                value = ""
                if isinstance(widget, QTextEdit):
                    value = widget.toPlainText().strip()
                elif isinstance(widget, QDateEdit):
                    value = widget.date().toString("yyyy-MM-dd")
                else:
                    value = widget.text().strip()
                
                if not value:
                    field_label = field.get('name', field_name)
                    return False, f"请填写必填字段: {field_label}"
        
        return True, ""
    
    def preview_content(self):
        """预览内容"""
        if not self.current_template_content:
            QMessageBox.warning(self, "警告", "请先加载模板")
            return
        
        values = self.get_form_values()
        content = replace_variables(self.current_template_content, values, self.current_template_page_id)
        
        # 添加整体样式，改善预览格式
        styled_content = f"""
        <html>
        <head>
        <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            line-height: 1.6;
        }}
        h1, h2, h3 {{
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        p {{
            margin: 8px 0;
        }}
        </style>
        </head>
        <body>
        {content}
        </body>
        </html>
        """
        
        # 显示预览对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        dialog = QDialog(self)
        dialog.setWindowTitle("内容预览")
        dialog.resize(900, 700)
        layout = QVBoxLayout()
        
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setHtml(styled_content)
        layout.addWidget(preview_text)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def update_create_button_state(self):
        """更新创建按钮状态"""
        has_template = bool(self.current_template_content)
        has_location = bool(self.selected_parent_id)
        has_title = bool(self.page_title_input.text().strip())
        
        # 调试信息
        if not (has_template and has_location and has_title):
            logger.debug(
                f"按钮状态检查: 模板={has_template}, 位置={has_location} "
                f"(parent_id={self.selected_parent_id}), 标题={has_title} "
                f"(title='{self.page_title_input.text().strip()}')"
            )
        
        self.create_button.setEnabled(has_template and has_location and has_title)
        self.preview_button.setEnabled(has_template)
    
    def start_create(self):
        """开始创建页面"""
        # 验证表单
        is_valid, error_msg = self.validate_form()
        if not is_valid:
            QMessageBox.warning(self, "警告", error_msg)
            return
        
        # 获取页面标题（从专门的输入框获取）
        title = self.page_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "警告", "请输入页面标题")
            return
        
        # 获取表单值并替换变量（传递page_id以支持模糊匹配）
        values = self.get_form_values()
        content = replace_variables(self.current_template_content, values, self.current_template_page_id)
        
        # 收集所有需要上传的图片文件
        image_files = []
        for field_name, field_data in self.field_widgets.items():
            widget = field_data['widget']
            field = field_data['field']
            if field.get('type') == "chapters" and isinstance(widget, ChapterEditor):
                chapters = widget.get_chapters()
                image_files.extend(self._collect_image_files_from_chapters(chapters))
            elif field.get('type') == "richtext_advanced":
                from Jira_tool.ui.richtext_editor import RichTextEditor
                if isinstance(widget, RichTextEditor):
                    image_files.extend(widget.get_image_files())
        
        # 确认对话框
        image_info = f"\n包含 {len(image_files)} 个图片附件" if image_files else ""
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要创建页面吗？\n"
            f"标题: {title}\n"
            f"位置: {self.selected_location_label.text()}\n"
            f"空间: {self.current_space_key}{image_info}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮
        self.create_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 启动创建线程（传递图片文件列表）
        self.create_page_thread = CreatePageThread(
            title, content, self.current_space_key, self.selected_parent_id, image_files
        )
        self.create_page_thread.finished.connect(self.on_create_finished)
        self.create_page_thread.error.connect(self.on_create_error)
        self.create_page_thread.start()
    
    def on_create_finished(self, success: bool, result: Dict):
        """创建完成"""
        self.create_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            page_id = result.get('id', '')
            page_title = result.get('title', '')
            _links = result.get('_links', {})
            webui = _links.get('webui', '')
            
            base_url = get_confluence_url().rstrip('/')
            if webui:
                page_url = f"{base_url}{webui}"
            else:
                page_url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
            
            # 使用弹框显示创建结果
            result_text = f"✅ 页面创建成功！\n\n"
            result_text += f"标题: {page_title}\n"
            result_text += f"页面ID: {page_id}\n"
            result_text += f"链接: {page_url}"
            
            # 询问是否打开页面
            reply = QMessageBox.question(
                self,
                "创建成功",
                f"{result_text}\n\n是否在浏览器中打开？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(page_url))
        else:
            QMessageBox.critical(self, "创建失败", "页面创建失败，请检查错误信息。")
    
    def on_create_error(self, error_msg: str):
        """创建错误"""
        self.create_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"创建页面失败:\n{error_msg}")
    
    def closeEvent(self, event):
        """窗口关闭事件，确保线程正确退出"""
        self._is_destroying = True
        
        # 等待所有线程完成
        if self.load_pages_thread and self.load_pages_thread.isRunning():
            self.load_pages_thread.wait(3000)  # 最多等待3秒
        
        if self.load_template_thread and self.load_template_thread.isRunning():
            self.load_template_thread.wait(3000)
        
        if self.load_page_content_thread and self.load_page_content_thread.isRunning():
            self.load_page_content_thread.wait(3000)
        
        if self.create_page_thread and self.create_page_thread.isRunning():
            self.create_page_thread.wait(3000)
        
        # 等待所有子页面加载线程
        for thread in self.load_children_threads[:]:  # 使用切片复制列表
            if thread.isRunning():
                thread.wait(1000)  # 每个线程最多等待1秒
        
        event.accept()