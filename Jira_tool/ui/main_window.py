"""
主窗口
使用侧边栏导航布局
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QStackedWidget, QLabel, QPushButton, QMenuBar, QStatusBar, QToolBar
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QAction
from pathlib import Path
from Jira_tool.ui.settings_dialog import SettingsDialog
from Jira_tool.ui.comment_widget import CommentWidget
from Jira_tool.ui.create_widget import CreateWidget
from Jira_tool.ui.confluence_create_widget import ConfluenceCreateWidget
from Jira_tool.ui.issue_export_widget import IssueExportWidget
from Jira_tool.core.paths import get_log_path
from core.debug_logger import logger
from core.jira_config_manager import get_confluence_url, get_confluence_token, get_default_confluence_space
from Jira_tool.confluence_client import get_space, ConfluenceAPIError
from Jira_tool.modules.confluence_page_tree import should_auto_load_page_tree


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JIRA 自动化工具")
        self.resize(1000, 700)
        
        self.init_ui()
        logger.info("主窗口初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 先创建状态栏，避免 sidebar.setCurrentRow 触发回调时 status_bar 未初始化
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 主布局（水平布局：侧边栏 + 内容区）
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("jiraSidebar")
        self.sidebar.setMaximumWidth(200)
        
        # 添加菜单项
        self.sidebar.addItem("查询评论")
        self.sidebar.addItem("创建Test Progress")
        self.sidebar.addItem("创建Confluence页面")
        self.sidebar.addItem("Issue Export")
        
        # 内容区（堆叠窗口）
        self.stacked_widget = QStackedWidget()
        
        # 创建各个功能页面
        self.comment_widget = CommentWidget()
        self.create_widget = CreateWidget()
        self.confluence_create_widget = ConfluenceCreateWidget()
        self.issue_export_widget = IssueExportWidget()
        
        self.stacked_widget.addWidget(self.comment_widget)
        self.stacked_widget.addWidget(self.create_widget)
        self.stacked_widget.addWidget(self.confluence_create_widget)
        self.stacked_widget.addWidget(self.issue_export_widget)
        
        # 连接信号（必须在创建stacked_widget之后）
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        self.sidebar.setCurrentRow(0)  # 默认选择第一项
        
        # 添加到主布局
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget, 1)  # 内容区占据剩余空间
        
        central_widget.setLayout(main_layout)
        
        # 移除菜单栏和工具栏
        # self.create_menu_bar()
        # self.create_toolbar()
        
        # 状态栏已在上方初始化
        
        # 启动时自动加载Confluence目录树
        self.auto_load_confluence_tree()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 移除设置菜单项（配置将在主程序中管理）
        # settings_action = QAction("设置", self)
        # settings_action.setShortcut("Ctrl+S")
        # settings_action.triggered.connect(self.open_settings)
        # file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        open_logs_action = QAction("打开日志", self)
        open_logs_action.triggered.connect(self.open_logs)
        help_menu.addAction(open_logs_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 打开日志按钮
        open_logs_action = QAction("打开日志", self)
        open_logs_action.triggered.connect(self.open_logs)
        toolbar.addAction(open_logs_action)
        
        toolbar.addSeparator()
        
        # 移除设置按钮（配置将在主程序中管理）
        # settings_action = QAction("设置", self)
        # settings_action.triggered.connect(self.open_settings)
        # toolbar.addAction(settings_action)
    
    def on_sidebar_changed(self, index: int):
        """侧边栏选择改变"""
        self.stacked_widget.setCurrentIndex(index)
        
        # 更新状态栏
        if index == 0:
            self.status_bar.showMessage("查询Issue评论")
        elif index == 1:
            self.status_bar.showMessage("批量创建Test Progress")
        elif index == 2:
            self.status_bar.showMessage("创建Confluence页面")
        elif index == 3:
            self.status_bar.showMessage("Issue Export（导出Excel）")

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            # 设置已保存，可能需要重新初始化客户端
            logger.info("设置已更新")
            self.status_bar.showMessage("设置已保存")
    
    def open_logs(self):
        """打开日志文件"""
        log_path = get_log_path()
        if log_path.exists():
            file_url = QUrl.fromLocalFile(str(log_path))
            QDesktopServices.openUrl(file_url)
            self.status_bar.showMessage(f"已打开日志文件: {log_path}")
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "警告",
                f"日志文件不存在:\n{log_path}"
            )
    
    def auto_load_confluence_tree(self):
        """自动加载Confluence目录树（如果连接正常且24小时内未加载过）"""
        try:
            # 检查配置
            url = get_confluence_url()
            token = get_confluence_token()
            space_key = get_default_confluence_space()
            
            if not url or not token or not space_key:
                logger.debug("Confluence未配置，跳过自动加载")
                return
            
            # 检查是否需要自动加载
            if not should_auto_load_page_tree(space_key):
                logger.debug(f"空间 {space_key} 在24小时内已自动加载过，跳过")
                # 仍然尝试加载目录树（优先走磁盘/内存缓存，不会强制请求网络）
                if hasattr(self, 'confluence_create_widget'):
                    self.confluence_create_widget.load_initial_data(auto_load=False)
                return
            
            # 测试连接
            try:
                get_space(space_key)
                logger.info(f"Confluence连接正常，开始自动加载目录树: {space_key}")
            except ConfluenceAPIError as e:
                logger.warning(f"Confluence连接失败，跳过自动加载: {e}")
                return
            
            # 后台加载目录树
            if hasattr(self, 'confluence_create_widget'):
                self.confluence_create_widget.load_initial_data(auto_load=True)
        except Exception as e:
            logger.exception(f"自动加载Confluence目录树失败: {e}")

