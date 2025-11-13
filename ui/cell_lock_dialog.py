#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通 Lock Cell 管理对话框
管理高通设备的cell lock配置
"""

import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QRadioButton, QButtonGroup, QLineEdit,
                             QFileDialog, QMessageBox, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt
from core.debug_logger import logger
# 在模块顶层导入资源路径工具，避免PyInstaller打包时的延迟导入问题
from core.resource_utils import get_resource_path


class LockCellDialog(QDialog):
    """高通 Lock Cell 对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("高通 Lock Cell"))
        self.setModal(True)
        self.resize(500, 400)
        
        # 获取模板文件路径（使用统一的资源路径函数）
        # get_resource_path已在模块顶层导入，避免PyInstaller打包时的延迟导入问题
        self.lte_template = get_resource_path("resources/template/cell_lock_list_LTE")
        self.fg_template = get_resource_path("resources/template/pci_lock_info_5G")
        
        # 用户选择
        self.cell_type = None  # "LTE" or "5G"
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(self.tr("选择Cell Lock类型"))
        title_label.setProperty("class", "section-title")
        layout.addWidget(title_label)
        
        # 单选按钮组
        self.button_group = QButtonGroup(self)
        
        self.lte_radio = QRadioButton(self.tr("LTE"))
        self.button_group.addButton(self.lte_radio, 0)
        
        self.fg_radio = QRadioButton(self.tr("5G"))
        self.button_group.addButton(self.fg_radio, 1)
        
        radio_layout = QVBoxLayout()
        radio_layout.addWidget(self.lte_radio)
        radio_layout.addWidget(self.fg_radio)
        
        layout.addLayout(radio_layout)
        layout.addStretch()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_next)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_next(self):
        """下一步：打开相应的输入对话框"""
        if not self.button_group.checkedButton():
            QMessageBox.warning(self, self.tr("提示"), self.tr("请选择Cell Lock类型"))
            return
        
        if self.lte_radio.isChecked():
            self.cell_type = "LTE"
            dialog = LTEInputDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self.process_lte_config(dialog)
        else:
            self.cell_type = "5G"
            dialog = FiveGInputDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self.process_fg_config(dialog)
    
    def process_lte_config(self, dialog):
        """处理LTE配置"""
        try:
            # 读取模板文件获取大小
            try:
                with open(self.lte_template, "rb") as file:
                    content = file.read()
                    file_size = len(content)
            except FileNotFoundError:
                # 如果模板不存在，使用默认大小
                file_size = 244
            
            # 创建全0的新内容（只使用模板的大小，不复制内容）
            new_content = bytearray([0x00] * file_size)
            new_content[0] = 0x01  # 固定第一个字节为 0x01
            
            # 获取并写入 PCI（位置4-5）
            pci = dialog.get_pci()
            pci_data = self.encode_to_little_endian(pci, min_bytes=2)
            new_content[4:6] = pci_data
            
            # 获取并写入 EARFCN（位置8-11）
            earfcn = dialog.get_earfcn()
            earfcn_data = self.encode_to_little_endian(earfcn, min_bytes=4)
            new_content[8:12] = earfcn_data
            
            # 让用户选择保存路径
            default_dir = os.path.expanduser("~")
            default_filename = os.path.join(default_dir, "cell_lock_list")
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("保存文件"),
                default_filename,
                ""
            )
            
            if output_path:
                with open(output_path, "wb") as file:
                    file.write(new_content)
                QMessageBox.information(self, self.tr("成功"), self.tr(f"文件已保存: {output_path}"))
                self.accept()
        
        except Exception as e:
            logger.exception(f"处理LTE配置失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"处理失败: {e}"))
    
    def process_fg_config(self, dialog):
        """处理5G配置"""
        try:
            # 读取模板文件获取大小
            try:
                with open(self.fg_template, "rb") as file:
                    content = file.read()
                    file_size = len(content)
            except FileNotFoundError:
                # 如果模板不存在，使用默认大小
                file_size = 896
            
            # 创建全0的新内容（只使用模板的大小，不复制内容）
            new_content = bytearray([0x00] * file_size)
            new_content[0] = 0x01  # 固定第一个字节为 0x01
            
            # 获取并写入 PCI（位置2-3）
            pci = dialog.get_pci()
            pci_data = self.encode_to_little_endian(pci, min_bytes=2)
            new_content[2:4] = pci_data
            
            # 获取并写入 NRARFCN（位置20-23）
            nrarfcn = dialog.get_nrarfcn()
            nrarfcn_data = self.encode_to_little_endian(nrarfcn, min_bytes=4)
            new_content[20:24] = nrarfcn_data
            
            # 获取并写入 SCS（位置24）
            scs = dialog.get_scs()
            new_content[24] = scs
            
            # 获取并写入 band（位置26）
            band = dialog.get_band()
            band_data = self.encode_to_little_endian(band - 1, min_bytes=1)
            new_content[26] = band_data[0]
            
            # 让用户选择保存路径
            default_dir = os.path.expanduser("~")
            default_filename = os.path.join(default_dir, "pci_lock_info")
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("保存文件"),
                default_filename,
                ""
            )
            
            if output_path:
                with open(output_path, "wb") as file:
                    file.write(new_content)
                QMessageBox.information(self, self.tr("成功"), self.tr(f"文件已保存: {output_path}"))
                self.accept()
        
        except Exception as e:
            logger.exception(f"处理5G配置失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), self.tr(f"处理失败: {e}"))
    
    def encode_to_little_endian(self, decimal_number, min_bytes=1):
        """
        将十进制数字转换为小端格式，确保字节数符合要求。
        :param decimal_number: 十进制数字
        :param min_bytes: 最小字节数，不足补0
        :return: 小端格式的字节数据
        """
        hex_value = f"{decimal_number:X}"
        if len(hex_value) % 2 != 0:
            hex_value = "0" + hex_value  # 确保偶数字符
        byte_array = [hex_value[i:i+2] for i in range(0, len(hex_value), 2)]
        byte_array = byte_array[::-1]  # 小端格式
        while len(byte_array) < min_bytes:  # 补齐到最小字节数
            byte_array.append("00")
        return bytes.fromhex("".join(byte_array))


class LTEInputDialog(QDialog):
    """LTE输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("LTE Cell Lock 配置"))
        self.setModal(True)
        self.resize(400, 150)
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # PCI输入
        self.pci_input = QLineEdit()
        self.pci_input.setPlaceholderText(self.tr("请输入非负整数"))
        form_layout.addRow(self.tr("PCI*:"), self.pci_input)
        
        # EARFCN输入
        self.earfcn_input = QLineEdit()
        self.earfcn_input.setPlaceholderText(self.tr("请输入非负整数"))
        form_layout.addRow(self.tr("EARFCN*:"), self.earfcn_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_accept(self):
        """验证并接受输入"""
        pci = self.pci_input.text().strip()
        earfcn = self.earfcn_input.text().strip()
        
        if not pci or not earfcn:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请填写所有必填项"))
            return
        
        try:
            pci_val = int(pci)
            if pci_val < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.tr("错误"), self.tr("PCI必须是非负整数"))
            return
        
        try:
            earfcn_val = int(earfcn)
            if earfcn_val < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.tr("错误"), self.tr("EARFCN必须是非负整数"))
            return
        
        self.accept()
    
    def get_pci(self):
        """获取PCI值"""
        return int(self.pci_input.text().strip())
    
    def get_earfcn(self):
        """获取EARFCN值"""
        return int(self.earfcn_input.text().strip())


class FiveGInputDialog(QDialog):
    """5G输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("5G Cell Lock 配置"))
        self.setModal(True)
        self.resize(400, 200)
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # PCI输入
        self.pci_input = QLineEdit()
        self.pci_input.setPlaceholderText(self.tr("请输入非负整数"))
        form_layout.addRow(self.tr("PCI*:"), self.pci_input)
        
        # NRARFCN输入
        self.nrarfcn_input = QLineEdit()
        self.nrarfcn_input.setPlaceholderText(self.tr("请输入非负整数"))
        form_layout.addRow(self.tr("NRARFCN*:"), self.nrarfcn_input)
        
        # SCS输入
        self.scs_input = QLineEdit()
        self.scs_input.setPlaceholderText(self.tr("输入0-4 (0=Unspecified, 1=15kHz, 2=30kHz, 3=60kHz, 4=120kHz)"))
        form_layout.addRow(self.tr("SCS*:"), self.scs_input)
        
        # Band输入
        self.band_input = QLineEdit()
        self.band_input.setPlaceholderText(self.tr("请输入正整数"))
        form_layout.addRow(self.tr("Band*:"), self.band_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_accept(self):
        """验证并接受输入"""
        pci = self.pci_input.text().strip()
        nrarfcn = self.nrarfcn_input.text().strip()
        scs = self.scs_input.text().strip()
        band = self.band_input.text().strip()
        
        if not pci or not nrarfcn or not scs or not band:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请填写所有必填项"))
            return
        
        try:
            pci_val = int(pci)
            if pci_val < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.tr("错误"), self.tr("PCI必须是非负整数"))
            return
        
        try:
            nrarfcn_val = int(nrarfcn)
            if nrarfcn_val < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.tr("错误"), self.tr("NRARFCN必须是非负整数"))
            return
        
        # SCS验证
        scs_mapping = {"0": 0x00, "1": 0x01, "2": 0x02, "3": 0x03, "4": 0x04}
        if scs not in scs_mapping:
            QMessageBox.warning(self, self.tr("错误"), self.tr("SCS必须是0-4之间的整数"))
            return
        
        try:
            band_val = int(band)
            if band_val <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.tr("错误"), self.tr("Band必须是正整数"))
            return
        
        self.accept()
    
    def get_pci(self):
        """获取PCI值"""
        return int(self.pci_input.text().strip())
    
    def get_nrarfcn(self):
        """获取NRARFCN值"""
        return int(self.nrarfcn_input.text().strip())
    
    def get_scs(self):
        """获取SCS值"""
        scs_mapping = {"0": 0x00, "1": 0x01, "2": 0x02, "3": 0x03, "4": 0x04}
        return scs_mapping[self.scs_input.text().strip()]
    
    def get_band(self):
        """获取Band值"""
        return int(self.band_input.text().strip())

