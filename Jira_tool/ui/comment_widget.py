"""
查询评论功能界面
"""
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTextBrowser, QMessageBox, QFileDialog, QCheckBox, QApplication,
    QStackedLayout
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QPalette
from pathlib import Path
from Jira_tool.modules.comment_fetcher import fetch_comments_to_html
from core.debug_logger import logger

try:
    # 可选：安装 PySide6-WebEngine 后，HTML 渲染效果接近浏览器
    from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
    _HAS_WEBENGINE = True
except Exception:
    QWebEngineView = None  # type: ignore
    _HAS_WEBENGINE = False


class CommentFetchThread(QThread):
    """评论获取线程"""
    finished = Signal(bool, str, str)  # success, message, file_path
    
    def __init__(self, issue_key: str, download_images: bool):
        super().__init__()
        self.issue_key = issue_key
        self.download_images = download_images
    
    def run(self):
        """执行获取评论"""
        try:
            success, message, file_path = fetch_comments_to_html(
                self.issue_key,
                download_images=self.download_images
            )
            self.finished.emit(success, message, file_path)
        except Exception as e:
            logger.exception(f"获取评论线程异常: {e}")
            self.finished.emit(False, f"发生错误: {str(e)}", "")


class CommentWidget(QWidget):
    """查询评论界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fetch_thread = None
        self.current_file_path = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("查询Issue评论")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_label = QLabel("Issue Key:")
        input_label.setMinimumWidth(100)
        self.issue_input = QLineEdit()
        self.issue_input.setPlaceholderText("例如: GF65DISH-1347")
        self.issue_input.returnPressed.connect(self.fetch_comments)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.issue_input)
        layout.addLayout(input_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.fetch_button = QPushButton("查询")
        self.fetch_button.clicked.connect(self.fetch_comments)
        button_layout.addWidget(self.fetch_button)

        self.preview_checkbox = QCheckBox("在GUI预览")
        self.preview_checkbox.setChecked(True)
        button_layout.addWidget(self.preview_checkbox)

        self.download_images_checkbox = QCheckBox("显示图片")
        self.download_images_checkbox.setChecked(True)
        button_layout.addWidget(self.download_images_checkbox)
        
        self.open_file_button = QPushButton("打开文件")
        self.open_file_button.clicked.connect(self.open_file)
        self.open_file_button.setEnabled(False)
        button_layout.addWidget(self.open_file_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 结果显示区域
        result_label = QLabel("结果:")
        layout.addWidget(result_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        # 结果区默认高度降低 2/3（原 150 -> 50）
        self.result_text.setMaximumHeight(50)
        layout.addWidget(self.result_text)

        # GUI 预览区域（HTML渲染）
        preview_label = QLabel("预览(HTML):")
        layout.addWidget(preview_label)

        # 预览控件：
        # - 有 WebEngine：用 “暗色占位层(QTextBrowser) + WebEngine” 的 stacked 结构，避免切换/首次渲染闪白
        # - 无 WebEngine：直接 QTextBrowser
        if _HAS_WEBENGINE:
            self.preview_container = QWidget()
            self.preview_stack = QStackedLayout(self.preview_container)
            self.preview_stack.setContentsMargins(0, 0, 0, 0)
            # 关键：使用 StackAll + 手动 raise/lower，避免切换导致子控件/窗口 Hide/Show 链路
            try:
                self.preview_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)  # type: ignore[attr-defined]
            except Exception:
                pass

            self.preview_placeholder = QTextBrowser()
            self.preview_placeholder.setOpenExternalLinks(True)
            self.preview_placeholder.setObjectName("jiraCommentPreview")

            self.preview_browser = QWebEngineView()
            self.preview_browser.setObjectName("jiraCommentPreview")
            try:
                self.preview_browser.loadFinished.connect(self._on_web_load_finished)  # type: ignore[attr-defined]
            except Exception:
                pass

            self.preview_stack.addWidget(self.preview_placeholder)
            self.preview_stack.addWidget(self.preview_browser)
            try:
                self.preview_browser.lower()  # type: ignore[attr-defined]
                self.preview_placeholder.raise_()  # type: ignore[attr-defined]
            except Exception:
                self.preview_stack.setCurrentWidget(self.preview_placeholder)

            self._apply_preview_background()

            # 为避免显示/隐藏导致主窗口布局重排闪烁，这里保持容器始终可见，用内容占位来表达状态
            self.preview_container.setVisible(True)
            self.preview_container.setMinimumHeight(300)
            layout.addWidget(self.preview_container)
        else:
            self.preview_browser = QTextBrowser()
            self.preview_browser.setOpenExternalLinks(True)
            # 统一交给全局 QSS 主题控制（避免亮色主题下仍黑底）
            self.preview_browser.setObjectName("jiraCommentPreview")
            self._apply_preview_background()

            # 为避免显示/隐藏导致主窗口布局重排闪烁，这里保持预览控件始终可见，用内容占位来表达状态
            self.preview_browser.setVisible(True)
            self.preview_browser.setMinimumHeight(300)
            layout.addWidget(self.preview_browser)

        self._set_preview_placeholder("尚未加载评论。点击“查询”后将显示预览。")
        
        # 让预览区域占满剩余空间，避免底部出现额外空白
        if _HAS_WEBENGINE:
            layout.setStretchFactor(self.preview_container, 1)
        else:
            layout.setStretchFactor(self.preview_browser, 1)
        self.setLayout(layout)

    def _clear_preview(self):
        """清空预览内容（兼容 QTextBrowser / QWebEngineView）"""
        if _HAS_WEBENGINE:
            # 关键：不要对 QWebEngineView 做 setHtml("") 清空。
            # 实测这可能触发 WebEngine 重载/合成，导致“整窗闪一下”。
            # 我们只切回占位层即可，旧页面留在后台，等新页面 loadFinished 再切换显示。
            try:
                # StackAll: 只抬升占位层，不切换 currentWidget
                try:
                    self.preview_browser.lower()  # type: ignore[attr-defined]
                    self.preview_placeholder.raise_()  # type: ignore[attr-defined]
                except Exception:
                    self.preview_stack.setCurrentWidget(self.preview_placeholder)  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            self.preview_browser.clear()

    def _get_theme(self) -> str:
        theme = "dark"
        try:
            app = QApplication.instance()
            if app:
                theme = app.property("currentTheme") or "dark"
        except Exception:
            theme = "dark"
        return str(theme).lower()

    def _get_preview_colors(self) -> tuple[str, str, str]:
        theme = self._get_theme()
        if theme == "light":
            return "#ffffff", "#333333", "#d0d0d0"
        return "#1A1A1A", "#cccccc", "#454545"

    def _apply_preview_background(self):
        """
        解决初次渲染闪白：在控件创建/每次 setHtml 前，给预览控件设置与主题一致的背景色。
        - QTextBrowser：用 palette 兜底（不抢占全局 QSS 优先级）
        - QWebEngineView：用 page backgroundColor 兜底（避免空白页白底闪烁）
        """
        bg, fg, _border = self._get_preview_colors()
        try:
            if _HAS_WEBENGINE:
                # 占位层（QTextBrowser）先用 palette 兜底，确保切页时不闪白
                try:
                    pal2 = self.preview_placeholder.palette()  # type: ignore[attr-defined]
                    pal2.setColor(QPalette.ColorRole.Base, QColor(bg))
                    pal2.setColor(QPalette.ColorRole.Text, QColor(fg))
                    self.preview_placeholder.setAutoFillBackground(True)  # type: ignore[attr-defined]
                    self.preview_placeholder.setPalette(pal2)  # type: ignore[attr-defined]
                except Exception:
                    pass

                # WebEngine：页面背景兜底（渲染前仍可能白帧，所以需要占位层遮挡）
                page = getattr(self.preview_browser, "page", None)  # type: ignore[attr-defined]
                if callable(page):
                    self.preview_browser.page().setBackgroundColor(QColor(bg))  # type: ignore[attr-defined]
            else:
                pal = self.preview_browser.palette()
                pal.setColor(QPalette.ColorRole.Base, QColor(bg))
                pal.setColor(QPalette.ColorRole.Text, QColor(fg))
                self.preview_browser.setAutoFillBackground(True)
                self.preview_browser.setPalette(pal)
        except Exception:
            # 兜底：不阻塞 UI
            pass

    def _set_preview_placeholder(self, text: str):
        """设置预览区占位内容"""
        self._apply_preview_background()
        bg, fg, border = self._get_preview_colors()

        html = f"""
        <html>
          <head><meta charset="UTF-8"></head>
          <body style="font-family: Arial, sans-serif; color: {fg}; padding: 12px; background-color: {bg}; border: 1px solid {border};">
            {text}
          </body>
        </html>
        """
        if _HAS_WEBENGINE:
            try:
                # StackAll: 只抬升占位层，不切换 currentWidget
                try:
                    self.preview_browser.lower()  # type: ignore[attr-defined]
                    self.preview_placeholder.raise_()  # type: ignore[attr-defined]
                except Exception:
                    self.preview_stack.setCurrentWidget(self.preview_placeholder)  # type: ignore[attr-defined]
            except Exception:
                pass
            self.preview_placeholder.setHtml(html)  # type: ignore[attr-defined]
        else:
            self.preview_browser.setHtml(html)

    def showEvent(self, event):
        try:
            self._apply_preview_background()
        except Exception:
            pass
        return super().showEvent(event)

    def _on_web_load_finished(self, ok: bool):
        if not _HAS_WEBENGINE:
            return
        try:
            if ok:
                # StackAll: 只把 WebEngine 抬到最上层
                try:
                    self.preview_placeholder.lower()  # type: ignore[attr-defined]
                    self.preview_browser.raise_()  # type: ignore[attr-defined]
                except Exception:
                    self.preview_stack.setCurrentWidget(self.preview_browser)  # type: ignore[attr-defined]
            else:
                self._set_preview_placeholder("预览加载失败，可点击“打开文件”使用浏览器查看。")
        except Exception:
            pass
    
    def fetch_comments(self):
        """获取评论"""
        issue_key = self.issue_input.text().strip()
        
        if not issue_key:
            QMessageBox.warning(self, "警告", "请输入Issue Key")
            return
        
        # 禁用按钮
        self.fetch_button.setEnabled(False)
        self.result_text.clear()
        self.result_text.append("正在查询...")
        self._clear_preview()
        self._set_preview_placeholder("正在加载评论预览…")
        
        # 创建并启动线程
        download_images = self.download_images_checkbox.isChecked()
        self.fetch_thread = CommentFetchThread(issue_key, download_images=download_images)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.start()
    
    def on_fetch_finished(self, success: bool, message: str, file_path: str):
        """获取完成回调"""
        self.fetch_button.setEnabled(True)
        
        if success:
            self.result_text.clear()
            self.result_text.append(f"✅ {message}")
            if file_path:
                self.current_file_path = file_path
                self.open_file_button.setEnabled(True)
                self.result_text.append(f"文件路径: {file_path}")

                if self.preview_checkbox.isChecked():
                    try:
                        base = QUrl.fromLocalFile(str(Path(file_path).parent) + "/")
                        self._apply_preview_background()

                        # 优先使用 WebEngine 渲染（更接近浏览器效果）
                        if _HAS_WEBENGINE:
                            # 先显示占位层遮挡 WebEngine 渲染前白帧
                            self._set_preview_placeholder("正在渲染预览…")
                            # 使用 setUrl 加载本地文件，避免 setHtml 可能触发的同步重排/闪烁
                            self.preview_browser.setUrl(QUrl.fromLocalFile(str(file_path)))  # type: ignore[attr-defined]
                        else:
                            # QTextBrowser：支持部分 CSS，效果可能不如浏览器
                            self.preview_browser.document().setBaseUrl(base)
                            html = Path(file_path).read_text(encoding="utf-8")
                            self.preview_browser.setHtml(html)
                    except Exception as e:
                        logger.warning(f"GUI预览加载失败: {e}")
                        self._set_preview_placeholder("预览加载失败，可点击“打开文件”使用浏览器查看。")
                else:
                    self._set_preview_placeholder("已关闭GUI预览。可点击“打开文件”使用浏览器查看。")
        else:
            self.result_text.clear()
            self.result_text.append(f"❌ {message}")
            self.open_file_button.setEnabled(False)
            QMessageBox.critical(self, "错误", message)
    
    def open_file(self):
        """打开生成的HTML文件"""
        if self.current_file_path:
            file_url = QUrl.fromLocalFile(self.current_file_path)
            QDesktopServices.openUrl(file_url)
        else:
            QMessageBox.warning(self, "警告", "没有可打开的文件")

