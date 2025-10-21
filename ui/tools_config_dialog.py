#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具配置对话框
"""

import os
import glob
import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QLineEdit, QGroupBox,
                             QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt


class ToolsConfigDialog(QDialog):
    """工具配置对话框"""
    
    def __init__(self, tool_config, parent=None):
        super().__init__(parent)
        self.tool_config = tool_config
        self.temp_config = tool_config.copy()
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
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel(self.tr("工具路径配置"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # MTK工具配置框架
        mtk_group = QGroupBox(self.tr("ELT路径配置"))
        mtk_layout = QVBoxLayout(mtk_group)
        
        # 按钮行
        mtk_button_layout = QHBoxLayout()
        detect_mtk_btn = QPushButton(self.tr("自动检测"))
        detect_mtk_btn.clicked.connect(self._detect_mtk_tools)
        mtk_button_layout.addWidget(detect_mtk_btn)
        
        manual_mtk_btn = QPushButton(self.tr("手动选择"))
        manual_mtk_btn.clicked.connect(self._manual_mtk_config)
        mtk_button_layout.addWidget(manual_mtk_btn)
        
        mtk_button_layout.addStretch()
        mtk_layout.addLayout(mtk_button_layout)
        
        # MTK工具列表
        self.mtk_list = QListWidget()
        self.mtk_list.setMaximumHeight(100)
        mtk_layout.addWidget(self.mtk_list)
        
        layout.addWidget(mtk_group)
        
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
        
        layout.addWidget(wireshark_group)
        
        # 高通工具配置框架
        qualcomm_group = QGroupBox(self.tr("高通工具配置"))
        qualcomm_layout = QVBoxLayout(qualcomm_group)
        
        # 按钮行
        qualcomm_button_layout = QHBoxLayout()
        detect_qualcomm_btn = QPushButton(self.tr("自动检测"))
        detect_qualcomm_btn.clicked.connect(self._detect_qualcomm_tools)
        qualcomm_button_layout.addWidget(detect_qualcomm_btn)
        
        manual_qualcomm_btn = QPushButton(self.tr("手动选择"))
        manual_qualcomm_btn.clicked.connect(self._manual_qualcomm_config)
        qualcomm_button_layout.addWidget(manual_qualcomm_btn)
        
        qualcomm_button_layout.addStretch()
        qualcomm_layout.addLayout(qualcomm_button_layout)
        
        # 高通工具列表
        self.qualcomm_list = QListWidget()
        self.qualcomm_list.setMaximumHeight(100)
        qualcomm_layout.addWidget(self.qualcomm_list)
        
        layout.addWidget(qualcomm_group)
        
        # 按钮框架
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton(self.tr("确定"))
        ok_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton(self.tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 初始化显示
        self._refresh_mtk_list()
        self._refresh_qualcomm_list()
        self.wireshark_entry.setText(self.temp_config.get("wireshark_path", ""))
        
    def _refresh_mtk_list(self):
        """刷新MTK工具列表"""
        self.mtk_list.clear()
        for tool in self.temp_config.get("mtk_tools", []):
            display_text = f"{tool['name']} (Python {tool['python_version']}) - {tool['base_path']}"
            self.mtk_list.addItem(display_text)
    
    def _refresh_qualcomm_list(self):
        """刷新高通工具列表"""
        self.qualcomm_list.clear()
        for tool in self.temp_config.get("qualcomm_tools", []):
            display_text = f"{tool['name']} - {tool['base_path']}"
            self.qualcomm_list.addItem(display_text)
    
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
                # 添加到配置中
                for tool in detected_tools:
                    exists = any(t["base_path"] == tool["base_path"] 
                               for t in self.temp_config.get("mtk_tools", []))
                    if not exists:
                        if "mtk_tools" not in self.temp_config:
                            self.temp_config["mtk_tools"] = []
                        self.temp_config["mtk_tools"].append(tool)
                
                self._refresh_mtk_list()
                QMessageBox.information(self, self.tr("检测完成"), f"{self.tr('检测到')} {len(detected_tools)} {self.tr('个MTK工具')}")
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
            
            if "mtk_tools" not in self.temp_config:
                self.temp_config["mtk_tools"] = []
            
            exists = any(t["base_path"] == tool_info["base_path"] 
                        for t in self.temp_config["mtk_tools"])
            if not exists:
                self.temp_config["mtk_tools"].append(tool_info)
                self._refresh_mtk_list()
                QMessageBox.information(self, self.tr("成功"), f"{self.tr('已添加MTK工具')}: {tool_info['name']}")
            else:
                QMessageBox.information(self, self.tr("提示"), self.tr("该MTK工具已存在"))
                
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
                if "qualcomm_tools" not in self.temp_config:
                    self.temp_config["qualcomm_tools"] = []
                
                for tool in detected_tools:
                    exists = any(t["base_path"] == tool["base_path"] 
                               for t in self.temp_config["qualcomm_tools"])
                    if not exists:
                        self.temp_config["qualcomm_tools"].append(tool)
                
                self._refresh_qualcomm_list()
                QMessageBox.information(self, self.tr("检测完成"), f"{self.tr('检测到')} {len(detected_tools)} {self.tr('个高通工具')}")
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
            
            if "qualcomm_tools" not in self.temp_config:
                self.temp_config["qualcomm_tools"] = []
            
            exists = any(t["base_path"] == tool_info["base_path"] 
                        for t in self.temp_config["qualcomm_tools"])
            if not exists:
                self.temp_config["qualcomm_tools"].append(tool_info)
                self._refresh_qualcomm_list()
                QMessageBox.information(self, self.tr("成功"), f"{self.tr('已添加高通工具')}: {tool_info['name']}")
            else:
                QMessageBox.information(self, self.tr("提示"), self.tr("该高通工具已存在"))
                
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
            
            # 更新原始配置
            self.tool_config.clear()
            self.tool_config.update(self.temp_config)
            
            QMessageBox.information(self, self.tr("成功"), self.tr("工具配置已保存"))
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存配置失败')}: {str(e)}")
