#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通 Lock Cell 管理对话框
管理高通设备的cell lock配置
"""

import os
import sys
import subprocess
import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QRadioButton, QButtonGroup, QLineEdit,
                             QFileDialog, QMessageBox, QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt
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
        
        # 获取设备管理器
        if parent and hasattr(parent, 'device_manager'):
            self.device_manager = parent.device_manager
        else:
            self.device_manager = None
        
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
        
        # 底部按钮布局
        bottom_layout = QHBoxLayout()
        
        # 左侧解锁按钮
        unlock_lte_btn = QPushButton(self.tr("Unlock LTE"))
        unlock_lte_btn.clicked.connect(self.on_unlock_lte)
        bottom_layout.addWidget(unlock_lte_btn)
        
        unlock_5g_btn = QPushButton(self.tr("Unlock 5G"))
        unlock_5g_btn.clicked.connect(self.on_unlock_5g)
        bottom_layout.addWidget(unlock_5g_btn)
        
        bottom_layout.addStretch()
        
        # 右侧OK/Cancel按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_next)
        button_box.rejected.connect(self.reject)
        bottom_layout.addWidget(button_box)
        
        layout.addLayout(bottom_layout)
    
    def on_next(self):
        """下一步：打开相应的输入对话框"""
        if not self.button_group.checkedButton():
            QMessageBox.warning(self, self.tr("提示"), self.tr("请选择Cell Lock类型"))
            return
        
        if self.lte_radio.isChecked():
            self.cell_type = "LTE"
            dialog = LTEInputDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.process_lte_config(dialog)
        else:
            self.cell_type = "5G"
            dialog = FiveGInputDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
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
                # 检查PCAT环境并执行复制
                self.check_pcat_and_copy(output_path, "LTE")
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
                # 检查PCAT环境并执行复制
                self.check_pcat_and_copy(output_path, "5G")
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
    
    def check_pcat_environment(self):
        """检查PCAT环境是否可用"""
        try:
            result = subprocess.run(
                ["PCAT", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            # 检查输出中是否包含版本信息
            if result.returncode == 0 and "Product Configuration Assistant Tool" in result.stdout:
                # 提取版本信息
                version_match = re.search(r'\[Version\s+([\d.]+)\]', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    logger.info(f"检测到PCAT环境，版本: {version}")
                    return True, version
                return True, None
            return False, None
        except FileNotFoundError:
            logger.warning("未找到PCAT命令")
            return False, None
        except subprocess.TimeoutExpired:
            logger.warning("PCAT版本检查超时")
            return False, None
        except Exception as e:
            logger.exception(f"检查PCAT环境失败: {e}")
            return False, None
    
    def get_device_id(self):
        """获取设备ID"""
        if not self.device_manager:
            return None
        device = self.device_manager.validate_device_selection()
        return device
    
    def build_pcat_copy_cmd(self, file_path, cell_type):
        """构建PCAT复制命令"""
        device_id = self.get_device_id()
        if not device_id:
            return None
        
        # 获取文件名
        filename = os.path.basename(file_path)
        
        if cell_type == "LTE":
            # LTE: 复制到 /nv/item_files/modem/lte/rrc/efs/
            target_path = f"/nv/item_files/modem/lte/rrc/efs/{filename}"
        else:  # 5G
            # 5G: 复制到 /nv/item_files/modem/nr5g/RRC/
            target_path = f"/nv/item_files/modem/nr5g/RRC/{filename}"
        
        # 构建命令
        cmd = [
            "PCAT",
            "-PLUGIN", "EE",
            "-DEVICE", device_id,
            "-FS", "PRI",
            "-MODE", "COPY",
            "-TYPE", "FILE",
            "-FROM", file_path,
            "-TO", target_path,
            "-OVERRIDE", "TRUE"
        ]
        return cmd
    
    def run_pcat_copy(self, cmd):
        """执行PCAT复制命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            output = (result.stdout or "") + ("\n" if result.stdout and result.stderr else "") + (result.stderr or "")
            
            # 检查是否成功（根据示例输出，成功时会有 "Status    - TRUE" 和 "copied successfully"）
            success = (
                result.returncode == 0 and
                ("Status    - TRUE" in output or "copied successfully" in output.lower())
            )
            
            return success, output
        except subprocess.TimeoutExpired:
            return False, self.tr("PCAT执行超时（>90秒）")
        except Exception as e:
            logger.exception(f"执行PCAT复制命令失败: {e}")
            return False, str(e)
    
    def reset_device(self, device_id):
        """重启设备"""
        try:
            cmd = ["PCAT", "-MODE", "RESET", "-DEVICE", device_id]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            logger.exception(f"重启设备失败: {e}")
            return False, str(e)
    
    def check_pcat_and_copy(self, file_path, cell_type):
        """检查PCAT环境并执行文件复制"""
        # 1. 检查PCAT环境
        pcat_available, version = self.check_pcat_environment()
        
        if not pcat_available:
            QMessageBox.warning(
                self,
                self.tr("PCAT未检测到"),
                self.tr("未检测到高通PCAT工具环境。\n\n请安装高通PCAT工具并确保已添加到系统PATH环境变量中。")
            )
            return
        
        # 2. 获取设备ID
        device_id = self.get_device_id()
        if not device_id:
            QMessageBox.warning(
                self,
                self.tr("设备未选择"),
                self.tr("请先选择一个设备")
            )
            return
        
        # 3. 构建并执行复制命令
        cmd = self.build_pcat_copy_cmd(file_path, cell_type)
        if not cmd:
            QMessageBox.warning(
                self,
                self.tr("错误"),
                self.tr("无法构建PCAT命令")
            )
            return
        
        # 显示进度提示
        progress_msg = QMessageBox(self)
        progress_msg.setWindowTitle(self.tr("正在复制文件"))
        progress_msg.setText(self.tr("正在将文件复制到设备，请稍候..."))
        progress_msg.setStandardButtons(QMessageBox.NoButton)
        progress_msg.setAttribute(Qt.WA_DeleteOnClose, True)
        progress_msg.show()
        progress_msg.repaint()
        
        try:
            success, output = self.run_pcat_copy(cmd)
            progress_msg.close()
            progress_msg.deleteLater()
            
            if success:
                # 复制成功，询问是否重启
                reply = QMessageBox.question(
                    self,
                    self.tr("复制成功"),
                    self.tr("文件已成功复制到设备。\n\n是否立即重启设备以使配置生效？"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 执行重启
                    reset_progress = QMessageBox(self)
                    reset_progress.setWindowTitle(self.tr("正在重启设备"))
                    reset_progress.setText(self.tr("正在重启设备，请稍候..."))
                    reset_progress.setStandardButtons(QMessageBox.NoButton)
                    reset_progress.setAttribute(Qt.WA_DeleteOnClose, True)
                    reset_progress.show()
                    reset_progress.repaint()
                    
                    reset_success, reset_output = self.reset_device(device_id)
                    reset_progress.close()
                    reset_progress.deleteLater()
                    
                    if reset_success:
                        QMessageBox.information(
                            self,
                            self.tr("重启成功"),
                            self.tr("设备重启命令已发送。")
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            self.tr("重启失败"),
                            self.tr("设备重启失败:\n{}").format(reset_output)
                        )
            else:
                # 复制失败
                QMessageBox.critical(
                    self,
                    self.tr("复制失败"),
                    self.tr("文件复制到设备失败:\n\n{}").format(output)
                )
        except Exception as e:
            if progress_msg.isVisible():
                progress_msg.close()
                progress_msg.deleteLater()
            logger.exception(f"执行PCAT复制时发生异常: {e}")
            QMessageBox.critical(
                self,
                self.tr("错误"),
                self.tr("执行复制时发生错误: {}").format(e)
            )
    
    def build_pcat_delete_cmd(self, cell_type):
        """构建PCAT删除命令"""
        device_id = self.get_device_id()
        if not device_id:
            return None
        
        if cell_type == "LTE":
            # LTE: 删除 /nv/item_files/modem/lte/rrc/efs/cell_lock_list
            target_path = "/nv/item_files/modem/lte/rrc/efs/cell_lock_list"
        else:  # 5G
            # 5G: 删除 /nv/item_files/modem/nr5g/RRC/pci_lock_info
            target_path = "/nv/item_files/modem/nr5g/RRC/pci_lock_info"
        
        # 构建命令
        cmd = [
            "PCAT",
            "-PLUGIN", "EE",
            "-DEVICE", device_id,
            "-FS", "PRI",
            "-MODE", "DELETE",
            "-TYPE", "FILE",
            "-VALUE", target_path
        ]
        return cmd
    
    def run_pcat_delete(self, cmd):
        """执行PCAT删除命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            output = (result.stdout or "") + ("\n" if result.stdout and result.stderr else "") + (result.stderr or "")
            
            # 检查是否成功
            success = (
                result.returncode == 0 and
                ("Status    - TRUE" in output or "successfully" in output.lower() or "deleted" in output.lower())
            )
            
            return success, output
        except subprocess.TimeoutExpired:
            return False, self.tr("PCAT执行超时（>90秒）")
        except Exception as e:
            logger.exception(f"执行PCAT删除命令失败: {e}")
            return False, str(e)
    
    def on_unlock_lte(self):
        """解锁LTE"""
        self.unlock_cell("LTE")
    
    def on_unlock_5g(self):
        """解锁5G"""
        self.unlock_cell("5G")
    
    def unlock_cell(self, cell_type):
        """解锁Cell Lock"""
        # 1. 检查PCAT环境
        pcat_available, version = self.check_pcat_environment()
        
        if not pcat_available:
            QMessageBox.warning(
                self,
                self.tr("PCAT未检测到"),
                self.tr("未检测到高通PCAT工具环境。\n\n请安装高通PCAT工具并确保已添加到系统PATH环境变量中。")
            )
            return
        
        # 2. 获取设备ID
        device_id = self.get_device_id()
        if not device_id:
            QMessageBox.warning(
                self,
                self.tr("设备未选择"),
                self.tr("请先选择一个设备")
            )
            return
        
        # 3. 确认操作
        cell_type_name = "LTE" if cell_type == "LTE" else "5G"
        reply = QMessageBox.question(
            self,
            self.tr("确认解锁"),
            self.tr("确定要解锁{} Cell Lock吗？\n\n此操作将删除设备上的锁定配置文件。").format(cell_type_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 4. 构建并执行删除命令
        cmd = self.build_pcat_delete_cmd(cell_type)
        if not cmd:
            QMessageBox.warning(
                self,
                self.tr("错误"),
                self.tr("无法构建PCAT命令")
            )
            return
        
        # 显示进度提示
        progress_msg = QMessageBox(self)
        progress_msg.setWindowTitle(self.tr("正在解锁"))
        progress_msg.setText(self.tr("正在删除{} Cell Lock配置，请稍候...").format(cell_type_name))
        progress_msg.setStandardButtons(QMessageBox.NoButton)
        progress_msg.setAttribute(Qt.WA_DeleteOnClose, True)
        progress_msg.show()
        progress_msg.repaint()
        
        try:
            success, output = self.run_pcat_delete(cmd)
            progress_msg.close()
            progress_msg.deleteLater()
            
            if success:
                # 删除成功，询问是否重启
                reply = QMessageBox.question(
                    self,
                    self.tr("解锁成功"),
                    self.tr("{} Cell Lock已成功解锁。\n\n是否立即重启设备以使配置生效？").format(cell_type_name),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 执行重启
                    reset_progress = QMessageBox(self)
                    reset_progress.setWindowTitle(self.tr("正在重启设备"))
                    reset_progress.setText(self.tr("正在重启设备，请稍候..."))
                    reset_progress.setStandardButtons(QMessageBox.NoButton)
                    reset_progress.setAttribute(Qt.WA_DeleteOnClose, True)
                    reset_progress.show()
                    reset_progress.repaint()
                    
                    reset_success, reset_output = self.reset_device(device_id)
                    reset_progress.close()
                    reset_progress.deleteLater()
                    
                    if reset_success:
                        QMessageBox.information(
                            self,
                            self.tr("重启成功"),
                            self.tr("设备重启命令已发送。")
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            self.tr("重启失败"),
                            self.tr("设备重启失败:\n{}").format(reset_output)
                        )
            else:
                # 删除失败
                QMessageBox.critical(
                    self,
                    self.tr("解锁失败"),
                    self.tr("删除{} Cell Lock配置失败:\n\n{}").format(cell_type_name, output)
                )
        except Exception as e:
            if progress_msg.isVisible():
                progress_msg.close()
                progress_msg.deleteLater()
            logger.exception(f"执行PCAT删除时发生异常: {e}")
            QMessageBox.critical(
                self,
                self.tr("错误"),
                self.tr("执行解锁时发生错误: {}").format(e)
            )


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

