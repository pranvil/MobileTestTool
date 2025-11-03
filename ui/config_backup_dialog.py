#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置备份对话框
提供一键导出和导入所有配置的功能
"""

import os
import json
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QMessageBox, QFileDialog, QTextEdit, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.debug_logger import logger


class ConfigBackupDialog(QDialog):
    """配置备份对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        # 获取各个管理器
        self.parent = parent
        self.tab_config_manager = None
        self.custom_button_manager = None
        self.log_keyword_manager = None
        
        if parent:
            if hasattr(parent, 'tab_config_manager'):
                self.tab_config_manager = parent.tab_config_manager
            if hasattr(parent, 'custom_button_manager'):
                self.custom_button_manager = parent.custom_button_manager
            if hasattr(parent, 'log_keyword_manager'):
                self.log_keyword_manager = parent.log_keyword_manager
        
        self.setWindowTitle(self.tr("配置备份与恢复"))
        self.setModal(True)
        self.resize(600, 400)
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel(self.tr("🔄 配置备份与恢复"))
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 描述
        desc = QLabel(self.tr(
            "此功能可以一键导出所有配置，包括：\n"
            "• Tab配置管理\n"
            "• 自定义按钮\n"
            "• AT命令\n"
            "• 暗码数据\n"
            "• 高通NV数据\n"
            "• Log关键字"
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(desc)
        
        # 按钮组（水平布局）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 导出按钮
        self.export_btn = QPushButton("📤 " + self.tr("导出所有配置"))
        self.export_btn.clicked.connect(self.export_all_configs)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        button_layout.addWidget(self.export_btn)
        
        # 导入按钮
        self.import_btn = QPushButton("📥 " + self.tr("导入所有配置"))
        self.import_btn.clicked.connect(self.import_all_configs)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
        
        # 状态显示区域
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(120)
        self.status_text.setPlaceholderText(self.tr("状态信息将显示在这里..."))
        layout.addWidget(self.status_text)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.close_btn = QPushButton(self.tr("关闭"))
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
    
    def log_status(self, message):
        """记录状态信息"""
        self.status_text.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def get_all_configs(self):
        """获取所有配置"""
        configs = {}
        user_config_dir = os.path.expanduser('~/.netui')
        
        try:
            # 1. Tab配置
            if self.tab_config_manager and os.path.exists(self.tab_config_manager.config_file):
                with open(self.tab_config_manager.config_file, 'r', encoding='utf-8-sig') as f:
                    configs['tab_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载Tab配置"))
            
            # 2. 自定义按钮配置
            if self.custom_button_manager and os.path.exists(self.custom_button_manager.config_file):
                with open(self.custom_button_manager.config_file, 'r', encoding='utf-8') as f:
                    configs['button_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载自定义按钮配置"))
            
            # 3. Log关键字配置
            if self.log_keyword_manager and os.path.exists(self.log_keyword_manager.config_file):
                with open(self.log_keyword_manager.config_file, 'r', encoding='utf-8-sig') as f:
                    configs['log_keyword_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载Log关键字配置"))
            
            # 4. AT命令配置
            at_commands_file = os.path.join(user_config_dir, 'at_commands.json')
            if os.path.exists(at_commands_file):
                with open(at_commands_file, 'r', encoding='utf-8') as f:
                    configs['at_commands_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载AT命令配置"))
            
            # 5. 暗码配置
            secret_codes_file = os.path.join(user_config_dir, 'secret_codes.json')
            if os.path.exists(secret_codes_file):
                with open(secret_codes_file, 'r', encoding='utf-8') as f:
                    configs['secret_codes_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载暗码配置"))
            
            # 6. 高通NV配置
            qc_nv_file = os.path.join(user_config_dir, 'qc_nv.json')
            if os.path.exists(qc_nv_file):
                with open(qc_nv_file, 'r', encoding='utf-8') as f:
                    configs['qc_nv_config'] = json.load(f)
                self.log_status(self.tr("✓ 已加载高通NV配置"))
            
        except Exception as e:
            logger.exception(f"{self.tr('获取配置失败:')} {e}")
            self.log_status(f"{self.tr('错误:')} {str(e)}")
        
        return configs
    
    def export_all_configs(self):
        """导出所有配置"""
        try:
            # 选择导出文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                self.tr("导出所有配置"), 
                f"MobileTestTool_All_Config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json)"
            )
            
            if not file_path:
                return
            
            self.status_text.clear()
            self.log_status(self.tr("开始导出配置..."))
            
            # 获取所有配置
            configs = self.get_all_configs()
            
            if not configs:
                self.log_status(self.tr("⚠ 没有找到任何配置"))
                QMessageBox.warning(self, self.tr("警告"), self.tr("没有找到任何配置"))
                return
            
            # 添加元数据
            export_data = {
                'version': '1.0',
                'export_time': datetime.datetime.now().isoformat(),
                'export_note': self.tr('MobileTestTool 全量配置导出'),
                'configs': configs
            }
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.log_status(self.tr(f"✓ 配置已导出到: {file_path}"))
            self.log_status(self.tr(f"✓ 共导出 {len(configs)} 个配置项"))
            
            QMessageBox.information(
                self, 
                self.tr("导出成功"), 
                self.tr(f"配置已成功导出到：\n{file_path}")
            )
            
        except Exception as e:
            logger.exception(f"{self.tr('导出配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"导出失败: {str(e)}"))
    
    def import_all_configs(self):
        """导入所有配置"""
        try:
            # 选择导入文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                self.tr("导入所有配置"), 
                "", 
                "JSON文件 (*.json)"
            )
            
            if not file_path:
                return
            
            # 确认导入
            reply = QMessageBox.question(
                self,
                self.tr("确认导入配置"),
                (self.tr("⚠️ 导入配置将完全覆盖当前所有设置！\n\n") +
                 self.tr("确定要继续导入吗？")),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            self.status_text.clear()
            self.log_status(self.tr("开始导入配置..."))
            
            # 读取配置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证配置格式
            if 'configs' not in import_data:
                QMessageBox.warning(self, self.tr("错误"), self.tr("配置文件格式不正确"))
                return
            
            configs = import_data.get('configs', {})
            user_config_dir = os.path.expanduser('~/.netui')
            os.makedirs(user_config_dir, exist_ok=True)
            
            success_count = 0
            error_count = 0
            
            # 1. 导入Tab配置
            if 'tab_config' in configs and self.tab_config_manager:
                try:
                    config_data = configs['tab_config']
                    self.tab_config_manager.tab_order = config_data.get('tab_order', [])
                    self.tab_config_manager.tab_visibility = config_data.get('tab_visibility', {})
                    self.tab_config_manager.custom_tabs = config_data.get('custom_tabs', [])
                    self.tab_config_manager.custom_cards = config_data.get('custom_cards', [])
                    self.tab_config_manager.save_config()
                    self.log_status(self.tr("✓ Tab配置导入成功"))
                    success_count += 1
                except Exception as e:
                    self.log_status(f"✗ Tab配置导入失败: {str(e)}")
                    error_count += 1
            
            # 2. 导入自定义按钮配置
            if 'button_config' in configs and self.custom_button_manager:
                try:
                    config_data = configs['button_config']
                    self.custom_button_manager.buttons = config_data.get('custom_buttons', [])
                    
                    # 验证Button的Tab和Card引用
                    validation_errors = self._validate_button_references()
                    if validation_errors:
                        # 有验证错误，停止导入并显示错误信息
                        error_msg = self.tr("❌ 自定义按钮配置导入失败！\n\n") + self.tr("发现以下问题：\n\n")
                        error_msg += "\n".join(f"• {error}" for error in validation_errors)
                        error_msg += f"\n\n{self.tr('请检查配置文件中的Tab和Card名称是否正确。')}"
                        self.log_status(f"✗ 自定义按钮配置导入失败: 验证错误")
                        for error in validation_errors:
                            self.log_status(f"  - {error}")
                        error_count += 1
                        # 不保存按钮配置，保持原有配置
                        self.custom_button_manager.load_buttons()
                    else:
                        self.custom_button_manager.save_buttons()
                        self.log_status(self.tr("✓ 自定义按钮配置导入成功"))
                        success_count += 1
                except Exception as e:
                    self.log_status(f"✗ 自定义按钮配置导入失败: {str(e)}")
                    error_count += 1
            
            # 3. 导入Log关键字配置
            if 'log_keyword_config' in configs and self.log_keyword_manager:
                try:
                    config_data = configs['log_keyword_config']
                    self.log_keyword_manager.keywords = config_data.get('log_keywords', [])
                    self.log_keyword_manager.save_keywords()
                    self.log_status(self.tr("✓ Log关键字配置导入成功"))
                    success_count += 1
                except Exception as e:
                    self.log_status(f"✗ Log关键字配置导入失败: {str(e)}")
                    error_count += 1
            
            # 4. 导入AT命令配置
            if 'at_commands_config' in configs:
                try:
                    at_commands_file = os.path.join(user_config_dir, 'at_commands.json')
                    with open(at_commands_file, 'w', encoding='utf-8') as f:
                        json.dump(configs['at_commands_config'], f, ensure_ascii=False, indent=2)
                    self.log_status(self.tr("✓ AT命令配置导入成功"))
                    success_count += 1
                except Exception as e:
                    self.log_status(f"✗ AT命令配置导入失败: {str(e)}")
                    error_count += 1
            
            # 5. 导入暗码配置
            if 'secret_codes_config' in configs:
                try:
                    secret_codes_file = os.path.join(user_config_dir, 'secret_codes.json')
                    with open(secret_codes_file, 'w', encoding='utf-8') as f:
                        json.dump(configs['secret_codes_config'], f, ensure_ascii=False, indent=2)
                    self.log_status(self.tr("✓ 暗码配置导入成功"))
                    success_count += 1
                except Exception as e:
                    self.log_status(f"✗ 暗码配置导入失败: {str(e)}")
                    error_count += 1
            
            # 6. 导入高通NV配置
            if 'qc_nv_config' in configs:
                try:
                    qc_nv_file = os.path.join(user_config_dir, 'qc_nv.json')
                    with open(qc_nv_file, 'w', encoding='utf-8') as f:
                        json.dump(configs['qc_nv_config'], f, ensure_ascii=False, indent=2)
                    self.log_status(self.tr("✓ 高通NV配置导入成功"))
                    success_count += 1
                except Exception as e:
                    self.log_status(f"✗ 高通NV配置导入失败: {str(e)}")
                    error_count += 1
            
            self.log_status(self.tr(f"\n导入完成：成功 {success_count}，失败 {error_count}"))
            
            # 通知主窗口重新加载
            if self.parent and hasattr(self.parent, 'reload_tabs'):
                self.parent.reload_tabs()
                self.log_status(self.tr("✓ 已通知主窗口重新加载"))
            
            # 如果有失败项，显示详细错误信息
            if error_count > 0:
                QMessageBox.warning(
                    self,
                    self.tr("导入完成（有错误）"),
                    self.tr(f"共导入 {success_count} 个配置项\n失败 {error_count} 个\n\n请查看下方的详细日志了解失败原因。")
                )
            else:
                # 确保按钮正确显示 - 触发按钮更新信号
                if self.custom_button_manager:
                    self.custom_button_manager.buttons_updated.emit()
                QMessageBox.information(
                    self,
                    self.tr("导入完成"),
                    self.tr(f"共导入 {success_count} 个配置项\n失败 {error_count} 个")
                )
            
        except Exception as e:
            logger.exception(f"{self.tr('导入配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"导入失败: {str(e)}"))
    
    def _validate_button_references(self):
        """验证Button的Tab和Card引用，返回错误列表"""
        errors = []
        try:
            if not self.tab_config_manager or not self.custom_button_manager:
                return errors
            
            # 获取所有有效的Tab名称
            valid_tab_names = set()
            
            # 添加默认Tab名称
            for tab in self.tab_config_manager.default_tabs:
                valid_tab_names.add(tab['name'])
            
            # 添加自定义Tab名称
            for tab in self.tab_config_manager.custom_tabs:
                valid_tab_names.add(tab['name'])
            
            # 验证每个按钮的Tab和Card引用
            for button in self.custom_button_manager.buttons:
                button_name = button.get('name', '未知按钮')
                button_tab = button.get('tab', '')
                button_card = button.get('card', '')
                
                # 验证Tab是否存在
                if button_tab:
                    if button_tab not in valid_tab_names:
                        errors.append(f"{self.tr('按钮')} '{button_name}' {self.tr('引用的Tab不存在:')} '{button_tab}'")
                        continue
                    
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
                            errors.append(f"{self.tr('按钮')} '{button_name}' {self.tr('引用的Card不存在:')} Tab='{button_tab}', Card='{button_card}'")
                else:
                    # Tab为空也可能是个问题，但这里不报错，因为可能是未配置的按钮
                    pass
                
        except Exception as e:
            logger.exception(f"{self.tr('验证Button引用失败:')} {e}")
            errors.append(f"{self.tr('验证过程出错:')} {str(e)}")
        
        return errors

