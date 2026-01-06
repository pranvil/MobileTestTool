"""
设置对话框
用于配置JIRA URL和API Token，以及Confluence URL和API Token
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from core.jira_config_manager import (
    get_jira_url, get_token, set_jira_url, set_token,
    get_confluence_url, get_confluence_token, set_confluence_url, set_confluence_token
)
from Jira_tool.jira_client import JiraClient, reset_client
from core.debug_logger import logger
from Jira_tool.core.exceptions import JiraAPIError


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 350)
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # JIRA URL
        url_layout = QHBoxLayout()
        url_label = QLabel("JIRA URL:")
        url_label.setMinimumWidth(100)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://jira.tcl.com")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # API Token
        token_layout = QHBoxLayout()
        token_label = QLabel("API Token:")
        token_label.setMinimumWidth(100)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("请输入您的API Token")
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)
        
        # 分隔线
        separator = QLabel("─" * 50)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)
        
        # Confluence URL
        confluence_url_layout = QHBoxLayout()
        confluence_url_label = QLabel("Confluence URL:")
        confluence_url_label.setMinimumWidth(100)
        self.confluence_url_input = QLineEdit()
        self.confluence_url_input.setPlaceholderText("https://confluence.tclking.com/")
        confluence_url_layout.addWidget(confluence_url_label)
        confluence_url_layout.addWidget(self.confluence_url_input)
        layout.addLayout(confluence_url_layout)
        
        # Confluence API Token
        confluence_token_layout = QHBoxLayout()
        confluence_token_label = QLabel("Confluence Token:")
        confluence_token_label.setMinimumWidth(100)
        self.confluence_token_input = QLineEdit()
        self.confluence_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confluence_token_input.setPlaceholderText("请输入您的Confluence API Token")
        confluence_token_layout.addWidget(confluence_token_label)
        confluence_token_layout.addWidget(self.confluence_token_input)
        layout.addLayout(confluence_token_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("验证JIRA Token")
        self.test_button.clicked.connect(self.test_token)
        button_layout.addWidget(self.test_button)
        
        self.test_confluence_button = QPushButton("验证Confluence Token")
        self.test_confluence_button.clicked.connect(self.test_confluence_token)
        button_layout.addWidget(self.test_confluence_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_settings(self):
        """加载设置"""
        self.url_input.setText(get_jira_url())
        self.token_input.setText(get_token())
        self.confluence_url_input.setText(get_confluence_url())
        self.confluence_token_input.setText(get_confluence_token())
    
    def test_token(self):
        """测试Token是否有效"""
        url = self.url_input.text().strip()
        token = self.token_input.text().strip()
        
        if not url or not token:
            QMessageBox.warning(self, "警告", "请先填写JIRA URL和API Token")
            return
        
        # 临时更新配置以测试
        old_url = get_jira_url()
        old_token = get_token()
        set_jira_url(url)
        set_token(token)
        
        try:
            # 使用临时配置创建客户端进行测试
            client = JiraClient(base_url=url, token=token)
            user_info = client.get_myself()
            display_name = user_info.get('displayName', '未知')
            QMessageBox.information(
                self,
                "验证成功",
                f"Token验证成功！\n当前用户: {display_name}"
            )
        except JiraAPIError as e:
            QMessageBox.critical(
                self,
                "验证失败",
                f"Token验证失败:\n{str(e)}"
            )
            # 恢复旧配置
            set_jira_url(old_url)
            set_token(old_token)
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"验证过程中发生错误:\n{str(e)}"
            )
            # 恢复旧配置
            set_jira_url(old_url)
            set_token(old_token)
    
    def test_confluence_token(self):
        """测试Confluence Token是否有效"""
        url = self.confluence_url_input.text().strip()
        token = self.confluence_token_input.text().strip()
        
        if not url or not token:
            QMessageBox.warning(self, "警告", "请先填写Confluence URL和API Token")
            return
        
        # 临时更新配置以测试
        old_url = get_confluence_url()
        old_token = get_confluence_token()
        set_confluence_url(url)
        set_confluence_token(token)
        
        try:
            # 使用Confluence API测试连通性
            import requests
            import urllib3
            import ssl
            from requests.adapters import HTTPAdapter
            
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 支持旧式SSL重新协商的适配器
            class LegacySSLAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    # 创建SSL上下文，允许旧式重新协商
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    # 允许旧式SSL重新协商 (OP_LEGACY_SERVER_CONNECT = 0x4)
                    try:
                        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                        else:
                            ctx.options |= 0x4
                    except Exception:
                        pass
                    kwargs['ssl_context'] = ctx
                    return super().init_poolmanager(*args, **kwargs)
            
            # 确保URL以/结尾
            base_url = url.rstrip('/')
            test_url = f"{base_url}/rest/api/user/current"
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            session = requests.Session()
            session.verify = False  # 跳过SSL验证
            session.mount('https://', LegacySSLAdapter())
            
            response = session.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                display_name = user_info.get('displayName', user_info.get('username', '未知'))
                QMessageBox.information(
                    self,
                    "验证成功",
                    f"Confluence Token验证成功！\n当前用户: {display_name}"
                )
            else:
                error_msg = f"Confluence API错误: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {response.text[:200]}"
                QMessageBox.critical(
                    self,
                    "验证失败",
                    f"Token验证失败:\n{error_msg}"
                )
                # 恢复旧配置
                set_confluence_url(old_url)
                set_confluence_token(old_token)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(
                self,
                "验证失败",
                f"网络请求失败:\n{str(e)}"
            )
            # 恢复旧配置
            set_confluence_url(old_url)
            set_confluence_token(old_token)
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"验证过程中发生错误:\n{str(e)}"
            )
            # 恢复旧配置
            set_confluence_url(old_url)
            set_confluence_token(old_token)
    
    def save_settings(self):
        """保存设置"""
        url = self.url_input.text().strip()
        token = self.token_input.text().strip()
        confluence_url = self.confluence_url_input.text().strip()
        confluence_token = self.confluence_token_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "警告", "JIRA URL不能为空")
            return
        
        if not token:
            QMessageBox.warning(self, "警告", "JIRA API Token不能为空")
            return
        
        try:
            set_jira_url(url)
            set_token(token)
            set_confluence_url(confluence_url)
            set_confluence_token(confluence_token)
            # 重置客户端以使用新配置
            reset_client()
            QMessageBox.information(self, "成功", "设置已保存")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败:\n{str(e)}")

