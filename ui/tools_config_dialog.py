#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具配置对话框
"""

import os
import glob
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QGroupBox, QCheckBox,
                             QMessageBox, QFileDialog, QSpinBox, QScrollArea,
                             QWidget)


class ToolsConfigDialog(QDialog):
    """工具配置对话框"""
    
    def __init__(self, tool_config, parent=None):
        super().__init__(parent)
        self.tool_config = tool_config
        self.temp_config = tool_config.copy()
        self.temp_config.setdefault("update_feed_url", "")
        self.temp_config.setdefault("update_download_dir", "")
        self.temp_config.setdefault("update_auto_launch_installer", True)
        self.temp_config.setdefault("update_timeout", 15)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(self.tr("工具路径配置"))
        self.setModal(True)
        self.setMinimumSize(600, 600)
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(10, 10, 10, 10)

        scroll_area.setWidget(content_widget)

        main_layout.addWidget(scroll_area)
        
        # 标题
        title_label = QLabel(self.tr("工具配置"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        content_layout.addWidget(title_label)
        
        # 存储路径配置框架
        storage_group = QGroupBox(self.tr("存储路径配置"))
        storage_layout = QVBoxLayout(storage_group)
        
        # 存储路径显示
        storage_path_layout = QHBoxLayout()
        storage_path_layout.addWidget(QLabel(self.tr("存储路径:")))
        
        self.storage_entry = QLineEdit()
        self.storage_entry.setPlaceholderText(self.tr("留空使用默认路径: c:\\log\\yyyymmdd"))
        storage_path_layout.addWidget(self.storage_entry)
        
        browse_storage_btn = QPushButton(self.tr("浏览"))
        browse_storage_btn.clicked.connect(self._browse_storage_path)
        storage_path_layout.addWidget(browse_storage_btn)
        
        storage_layout.addLayout(storage_path_layout)
        content_layout.addWidget(storage_group)
        
        # 更新配置
        update_group = QGroupBox(self.tr("更新配置"))
        update_layout = QVBoxLayout(update_group)

        update_url_layout = QHBoxLayout()
        update_url_layout.addWidget(QLabel(self.tr("版本描述 URL:")))

        self.update_url_entry = QLineEdit()
        self.update_url_entry.setPlaceholderText(self.tr("例如: https://example.com/releases/latest.json"))
        update_url_layout.addWidget(self.update_url_entry)
        update_layout.addLayout(update_url_layout)

        update_download_layout = QHBoxLayout()
        update_download_layout.addWidget(QLabel(self.tr("下载目录:")))

        self.update_download_entry = QLineEdit()
        self.update_download_entry.setPlaceholderText(self.tr("留空使用系统临时目录"))
        update_download_layout.addWidget(self.update_download_entry)

        browse_update_download_btn = QPushButton(self.tr("浏览"))
        browse_update_download_btn.clicked.connect(self._browse_update_download_dir)
        update_download_layout.addWidget(browse_update_download_btn)
        update_layout.addLayout(update_download_layout)

        self.update_auto_launch_checkbox = QCheckBox(self.tr("下载完成后自动打开安装包"))
        update_layout.addWidget(self.update_auto_launch_checkbox)

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel(self.tr("网络超时 (秒):")))

        self.update_timeout_spin = QSpinBox()
        self.update_timeout_spin.setRange(5, 300)
        self.update_timeout_spin.setSingleStep(5)
        timeout_layout.addWidget(self.update_timeout_spin)

        update_layout.addLayout(timeout_layout)

        content_layout.addWidget(update_group)

        # MTK工具配置框架
        mtk_group = QGroupBox(self.tr("ELT路径配置"))
        mtk_layout = QVBoxLayout(mtk_group)
        
        # MTK工具路径显示
        mtk_path_layout = QHBoxLayout()
        mtk_path_layout.addWidget(QLabel(self.tr("ELT路径:")))
        
        self.mtk_entry = QLineEdit()
        mtk_path_layout.addWidget(self.mtk_entry)
        
        detect_mtk_btn = QPushButton(self.tr("自动检测"))
        detect_mtk_btn.clicked.connect(self._detect_mtk_tools)
        mtk_path_layout.addWidget(detect_mtk_btn)
        
        manual_mtk_btn = QPushButton(self.tr("手动选择"))
        manual_mtk_btn.clicked.connect(self._manual_mtk_config)
        mtk_path_layout.addWidget(manual_mtk_btn)
        
        mtk_layout.addLayout(mtk_path_layout)
        
        content_layout.addWidget(mtk_group)
        
        # Wireshark配置框架
        wireshark_group = QGroupBox(self.tr("Wireshark配置"))
        wireshark_layout = QVBoxLayout(wireshark_group)
        
        wireshark_path_layout = QHBoxLayout()
        wireshark_path_layout.addWidget(QLabel(self.tr("Wireshark路径:")))
        
        self.wireshark_entry = QLineEdit()
        wireshark_path_layout.addWidget(self.wireshark_entry)
        
        detect_wireshark_btn = QPushButton(self.tr("自动检测"))
        detect_wireshark_btn.clicked.connect(self._detect_wireshark)
        wireshark_path_layout.addWidget(detect_wireshark_btn)
        
        browse_wireshark_btn = QPushButton(self.tr("手动"))
        browse_wireshark_btn.clicked.connect(self._browse_wireshark)
        wireshark_path_layout.addWidget(browse_wireshark_btn)
        
        wireshark_layout.addLayout(wireshark_path_layout)
        
        content_layout.addWidget(wireshark_group)
        
        # 高通工具配置框架
        qualcomm_group = QGroupBox(self.tr("高通工具配置"))
        qualcomm_layout = QVBoxLayout(qualcomm_group)
        
        # 高通工具路径显示
        qualcomm_path_layout = QHBoxLayout()
        qualcomm_path_layout.addWidget(QLabel(self.tr("高通工具路径:")))
        
        self.qualcomm_entry = QLineEdit()
        qualcomm_path_layout.addWidget(self.qualcomm_entry)
        
        detect_qualcomm_btn = QPushButton(self.tr("自动检测"))
        detect_qualcomm_btn.clicked.connect(self._detect_qualcomm_tools)
        qualcomm_path_layout.addWidget(detect_qualcomm_btn)
        
        manual_qualcomm_btn = QPushButton(self.tr("手动选择"))
        manual_qualcomm_btn.clicked.connect(self._manual_qualcomm_config)
        qualcomm_path_layout.addWidget(manual_qualcomm_btn)
        
        qualcomm_layout.addLayout(qualcomm_path_layout)
        
        content_layout.addWidget(qualcomm_group)

        content_layout.addStretch()
        
        # 按钮框架
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton(self.tr("确定"))
        ok_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton(self.tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # 初始化显示
        self._refresh_mtk_entry()
        self._refresh_qualcomm_entry()
        self.wireshark_entry.setText(self.temp_config.get("wireshark_path", ""))
        self.storage_entry.setText(self.temp_config.get("storage_path", ""))
        self.update_url_entry.setText(self.temp_config.get("update_feed_url", ""))
        self.update_download_entry.setText(self.temp_config.get("update_download_dir", ""))
        self.update_auto_launch_checkbox.setChecked(self.temp_config.get("update_auto_launch_installer", True))
        timeout_value = int(self.temp_config.get("update_timeout", 15) or 15)
        timeout_value = max(self.update_timeout_spin.minimum(), min(self.update_timeout_spin.maximum(), timeout_value))
        self.update_timeout_spin.setValue(timeout_value)
        
    def _refresh_mtk_entry(self):
        """刷新MTK工具输入框"""
        mtk_tools = self.temp_config.get("mtk_tools", [])
        if mtk_tools:
            # 显示第一个工具的信息
            tool = mtk_tools[0]
            display_text = f"{tool['name']} (Python {tool['python_version']}) - {tool['base_path']}"
            self.mtk_entry.setText(display_text)
        else:
            self.mtk_entry.setText("")
    
    def _refresh_qualcomm_entry(self):
        """刷新高通工具输入框"""
        qualcomm_tools = self.temp_config.get("qualcomm_tools", [])
        if qualcomm_tools:
            # 显示第一个工具的信息
            tool = qualcomm_tools[0]
            display_text = f"{tool['name']} - {tool['base_path']}"
            self.qualcomm_entry.setText(display_text)
        else:
            self.qualcomm_entry.setText("")
    
    def _browse_storage_path(self):
        """浏览选择存储路径"""
        try:
            path = QFileDialog.getExistingDirectory(self, self.tr("选择存储路径"))
            
            if path:
                self.storage_entry.setText(path)
                    
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('选择存储路径失败')}: {str(e)}")
    
    def _detect_mtk_tools(self):
        """检测MTK工具"""
        try:
            detected_tools = []
            
            # 常见安装路径
            common_paths = [
                "C:\\Tool\\ELT_*",
                "C:\\Program Files\\ELT_*",
                "C:\\MTK\\ELT_*",
                "D:\\Tool\\ELT_*",
                "D:\\Program Files\\ELT_*"
            ]
            
            for path_pattern in common_paths:
                matches = glob.glob(path_pattern)
                for match in matches:
                    if self._validate_mtk_tool(match):
                        tool_info = self._get_mtk_tool_info(match)
                        if tool_info:
                            detected_tools.append(tool_info)
            
            if detected_tools:
                # 只保留第一个检测到的工具
                tool = detected_tools[0]
                self.temp_config["mtk_tools"] = [tool]
                
                self._refresh_mtk_entry()
                QMessageBox.information(self, self.tr("检测完成"), f"{self.tr('检测到MTK工具:')} {tool['name']}")
            else:
                QMessageBox.information(self, self.tr("检测结果"), self.tr("未检测到MTK工具，请尝试手动输入"))
                
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('检测MTK工具失败')}: {str(e)}")
    
    def _validate_mtk_tool(self, base_path):
        """验证MTK工具路径"""
        try:
            elgcap_path = os.path.join(base_path, "System", "External", "elgcap")
            utilities_path = os.path.join(base_path, "Utilities")
            
            if not os.path.exists(elgcap_path) or not os.path.exists(utilities_path):
                return False
            
            main_py = os.path.join(elgcap_path, "main.py")
            if not os.path.exists(main_py):
                return False
            
            python_dirs = ["Python3", "Python", "Python27", "Python2"]
            for python_dir in python_dirs:
                python_path = os.path.join(utilities_path, python_dir)
                embedded_python = os.path.join(python_path, "EmbeddedPython.exe")
                if os.path.exists(embedded_python):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _get_mtk_tool_info(self, base_path):
        """获取MTK工具信息"""
        try:
            tool_name = os.path.basename(base_path)
            utilities_path = os.path.join(base_path, "Utilities")
            python_dirs = ["Python3", "Python", "Python27", "Python2"]
            python_path = ""
            python_version = "Unknown"
            
            for python_dir in python_dirs:
                test_python_path = os.path.join(utilities_path, python_dir)
                embedded_python = os.path.join(test_python_path, "EmbeddedPython.exe")
                if os.path.exists(embedded_python):
                    python_path = test_python_path
                    try:
                        result = subprocess.run([embedded_python, "--version"], 
                                             capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            python_version = result.stdout.strip()
                    except:
                        if "Python3" in python_dir:
                            python_version = "3.x"
                        elif "Python27" in python_dir:
                            python_version = "2.7"
                        elif "Python2" in python_dir:
                            python_version = "2.x"
                    break
            
            if not python_path:
                return None
            
            return {
                "name": tool_name,
                "base_path": base_path,
                "python_path": python_path,
                "python_version": python_version,
                "elgcap_path": os.path.join(base_path, "System", "External", "elgcap")
            }
            
        except Exception:
            return None
    
    def _manual_mtk_config(self):
        """手动配置MTK工具"""
        try:
            base_path = QFileDialog.getExistingDirectory(self, self.tr("选择MTK工具根目录"))
            
            if not base_path:
                return
            
            if not self._validate_mtk_tool(base_path):
                QMessageBox.critical(self, self.tr("错误"), self.tr("选择的路径不是有效的MTK工具目录"))
                return
            
            tool_info = self._get_mtk_tool_info(base_path)
            if not tool_info:
                QMessageBox.critical(self, self.tr("错误"), self.tr("无法获取MTK工具信息"))
                return
            
            # 直接替换为新的工具
            self.temp_config["mtk_tools"] = [tool_info]
            self._refresh_mtk_entry()
            QMessageBox.information(self, self.tr("成功"), f"{self.tr('已设置MTK工具')}: {tool_info['name']}")
                
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('手动配置失败')}: {str(e)}")
    
    def _detect_wireshark(self):
        """检测Wireshark"""
        try:
            common_paths = [
                "C:\\Program Files\\Wireshark",
                "C:\\Program Files (x86)\\Wireshark",
                "D:\\Program Files\\Wireshark",
                "D:\\Program Files (x86)\\Wireshark"
            ]
            
            for path in common_paths:
                mergecap_exe = os.path.join(path, "mergecap.exe")
                if os.path.exists(mergecap_exe):
                    self.wireshark_entry.setText(path)
                    QMessageBox.information(self, self.tr("检测完成"), f"{self.tr('检测到Wireshark:')} {path}")
                    return
            
            QMessageBox.information(self, self.tr("检测结果"), self.tr("未检测到Wireshark，请手动选择"))
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('检测Wireshark失败')}: {str(e)}")
    
    def _browse_wireshark(self):
        """浏览选择Wireshark路径"""
        try:
            path = QFileDialog.getExistingDirectory(self, self.tr("选择Wireshark安装目录"))
            
            if path:
                mergecap_exe = os.path.join(path, "mergecap.exe")
                if os.path.exists(mergecap_exe):
                    self.wireshark_entry.setText(path)
                else:
                    QMessageBox.critical(self, self.tr("错误"), self.tr("选择的目录中没有找到mergecap.exe"))
                    
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('选择Wireshark路径失败')}: {str(e)}")
    
    def _browse_update_download_dir(self):
        """选择更新下载目录"""
        try:
            path = QFileDialog.getExistingDirectory(self, self.tr("选择下载目录"))
            if path:
                self.update_download_entry.setText(path)
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('选择下载目录失败')}: {str(e)}")

    def _detect_qualcomm_tools(self):
        """检测高通工具"""
        try:
            detected_tools = []
            
            common_paths = [
                "C:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "C:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "D:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "D:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release"
            ]
            
            for path in common_paths:
                if self._validate_qualcomm_tool(path):
                    tool_info = self._get_qualcomm_tool_info(path)
                    if tool_info:
                        detected_tools.append(tool_info)
            
            if detected_tools:
                # 只保留第一个检测到的工具
                tool = detected_tools[0]
                self.temp_config["qualcomm_tools"] = [tool]
                
                self._refresh_qualcomm_entry()
                QMessageBox.information(self, self.tr("检测完成"), f"{self.tr('检测到高通工具:')} {tool['name']}")
            else:
                QMessageBox.information(self, self.tr("检测结果"), 
                    self.tr("未检测到高通工具，请尝试手动输入。\n\n常见路径:\n") +
                    "C:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\n"
                    "C:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\n"
                    "D:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\n"
                    "D:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release")
                
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('检测高通工具失败')}: {str(e)}")
    
    def _validate_qualcomm_tool(self, base_path):
        """验证高通工具路径"""
        try:
            pcap_gen_exe = os.path.join(base_path, "PCAP_Gen_2.0.exe")
            return os.path.exists(pcap_gen_exe)
        except Exception:
            return False
    
    def _get_qualcomm_tool_info(self, base_path):
        """获取高通工具信息"""
        try:
            tool_name = os.path.basename(os.path.dirname(base_path))
            parent_dir = os.path.basename(os.path.dirname(os.path.dirname(base_path)))
            
            return {
                "name": f"{parent_dir}_{tool_name}",
                "base_path": base_path,
                "pcap_gen_exe": os.path.join(base_path, "PCAP_Gen_2.0.exe")
            }
            
        except Exception:
            return None
    
    def _manual_qualcomm_config(self):
        """手动配置高通工具"""
        try:
            base_path = QFileDialog.getExistingDirectory(self, self.tr("选择高通工具目录"))
            
            if not base_path:
                return
            
            if not self._validate_qualcomm_tool(base_path):
                QMessageBox.critical(self, self.tr("错误"), self.tr("选择的路径不是有效的高通工具目录"))
                return
            
            tool_info = self._get_qualcomm_tool_info(base_path)
            if not tool_info:
                QMessageBox.critical(self, self.tr("错误"), self.tr("无法获取高通工具信息"))
                return
            
            # 直接替换为新的工具
            self.temp_config["qualcomm_tools"] = [tool_info]
            self._refresh_qualcomm_entry()
            QMessageBox.information(self, self.tr("成功"), f"{self.tr('已设置高通工具')}: {tool_info['name']}")
                
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('手动配置失败')}: {str(e)}")
    
    def _save_and_close(self):
        """保存配置并关闭"""
        try:
            # 保存Wireshark路径
            wireshark_path = self.wireshark_entry.text().strip()
            if wireshark_path:
                mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
                if not os.path.exists(mergecap_exe):
                    QMessageBox.critical(self, self.tr("错误"), self.tr("Wireshark路径无效，找不到mergecap.exe"))
                    return
                self.temp_config["wireshark_path"] = wireshark_path
            
            # 保存存储路径
            storage_path = self.storage_entry.text().strip()
            if storage_path:
                # 验证路径是否存在，如果不存在则创建
                if not os.path.exists(storage_path):
                    try:
                        os.makedirs(storage_path)
                    except Exception as e:
                        QMessageBox.critical(self, self.tr("错误"), f"{self.tr('无法创建存储路径')}: {str(e)}")
                        return
                self.temp_config["storage_path"] = storage_path
            else:
                # 如果为空，删除存储路径配置，使用默认路径
                self.temp_config.pop("storage_path", None)

            # 保存更新 URL
            update_feed_url = self.update_url_entry.text().strip()
            self.temp_config["update_feed_url"] = update_feed_url

            # 保存下载目录
            update_download_dir = self.update_download_entry.text().strip()
            if update_download_dir:
                if not os.path.exists(update_download_dir):
                    try:
                        os.makedirs(update_download_dir)
                    except Exception as e:
                        QMessageBox.critical(self, self.tr("错误"), f"{self.tr('无法创建下载目录')}: {str(e)}")
                        return
                self.temp_config["update_download_dir"] = update_download_dir
            else:
                self.temp_config.pop("update_download_dir", None)

            self.temp_config["update_auto_launch_installer"] = self.update_auto_launch_checkbox.isChecked()
            self.temp_config["update_timeout"] = int(self.update_timeout_spin.value())
            
            # 更新原始配置
            self.tool_config.clear()
            self.tool_config.update(self.temp_config)
            
            # 保存到文件
            if hasattr(self.parent(), 'other_operations_manager'):
                success = self.parent().other_operations_manager._save_tool_config()
                if not success:
                    QMessageBox.critical(self, self.tr("错误"), self.tr("保存配置文件失败"))
                    return
            
            QMessageBox.information(self, self.tr("成功"), self.tr("工具配置已保存"))
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存配置失败')}: {str(e)}")
