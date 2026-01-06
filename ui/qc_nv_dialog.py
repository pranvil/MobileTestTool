#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通 NV 管理对话框
管理高通NV信息
"""

import os
import json
import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QMessageBox, QFileDialog, QLabel,
                             QDialogButtonBox, QTextEdit, QFormLayout,
                             QSplitter, QWidget, QRadioButton, QButtonGroup,
                             QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from core.debug_logger import logger
from core import pcat_nv


class PlainTextEdit(QTextEdit):
    """只接受纯文本粘贴的文本编辑器"""
    
    def insertFromMimeData(self, source):
        """重写粘贴方法，只粘贴纯文本"""
        if source.hasText():
            # 只提取纯文本，忽略所有格式
            plain_text = source.text()
            # 插入纯文本
            text_cursor = self.textCursor()
            text_cursor.insertText(plain_text)
            self.setTextCursor(text_cursor)


class PcatNvWorker(QThread):
    finished = Signal(bool, str, str, str)  # success, value, stdout, stderr

    def __init__(self, device_id: str, nv_item: str, sub_id: int, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.nv_item = nv_item
        self.sub_id = sub_id

    def run(self):
        try:
            cmd = pcat_nv.build_read_cmd(self.device_id, self.nv_item, self.sub_id)
            result = pcat_nv.run_pcat(cmd, timeout=90)
            output = result.output
            success = pcat_nv.is_success(output) and (pcat_nv.extract_nv_value(output) is not None)
            value = pcat_nv.extract_nv_value(output) or ""
            self.finished.emit(success, value, result.stdout, result.stderr)
        except Exception as e:
            self.finished.emit(False, "", "", str(e))


class PcatNvWriteWorker(QThread):
    finished = Signal(bool, str, str, str)  # success, message, stdout, stderr

    def __init__(self, device_id: str, nv_item: str, sub_id: int, value: str, use_json: bool, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.nv_item = nv_item
        self.sub_id = sub_id
        self.value = value
        self.use_json = use_json

    def run(self):
        try:
            cmd = pcat_nv.build_write_cmd(self.device_id, self.nv_item, self.sub_id, self.value, self.use_json)
            result = pcat_nv.run_pcat(cmd, timeout=120)
            output = result.output
            success = pcat_nv.is_success(output)
            msg = "OK" if success else (result.stderr.strip() or result.stdout.strip() or "WRITE failed")
            self.finished.emit(success, msg, result.stdout, result.stderr)
        except Exception as e:
            self.finished.emit(False, str(e), "", str(e))


class PcatResetWorker(QThread):
    """PCAT 重启设备 Worker"""
    finished = Signal(bool, str)  # success, message

    def __init__(self, device_id: str, parent=None):
        super().__init__(parent)
        self.device_id = device_id

    def run(self):
        try:
            cmd = pcat_nv.build_reset_cmd(self.device_id)
            result = pcat_nv.run_pcat(cmd, timeout=30)
            output = result.output
            success = pcat_nv.is_success(output) or result.returncode == 0
            msg = "设备重启命令已执行" if success else (result.stderr.strip() or result.stdout.strip() or "重启失败")
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class QCNVDialog(QDialog):
    """高通 NV 管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("高通NV"))
        self.setModal(True)
        self.resize(900, 700)
        
        # 数据存储
        self.nv_data = []  # 存储NV信息的列表 [{"nv_value": "...", "description": "..."}]
        self.config_file = self._get_config_file_path()
        self.backup_dir = self._get_backup_dir()

        # UI 状态
        self._display_indices = []  # table row -> nv_data index
        self._filter_keyword = ""
        self._is_refreshing_table = False
        self._pcat_worker: PcatNvWorker | None = None
        self._pcat_write_worker: PcatNvWriteWorker | None = None
        self._pcat_reset_worker: PcatResetWorker | None = None
        self._pending_write_value: str | None = None
        self._pending_read_request: tuple[str, int] | None = None  # (nv_item, sub_id)
        
        self.setup_ui()
        self.load_data()
    
    def _get_config_file_path(self):
        """获取配置文件路径，兼容exe和开发环境"""
        # 统一保存到 ~/.netui/ 目录，与其他配置保持一致
        user_config_dir = os.path.expanduser('~/.netui')
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, 'qc_nv.json')
    
    def _get_backup_dir(self):
        """获取备份文件目录"""
        # 备份文件保存到 ~/.netui/backups/ 目录
        backup_dir = os.path.join(os.path.expanduser('~/.netui'), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        root_layout = QHBoxLayout(self)

        # ========== 左侧：上列表（80%） + 下读写区（20%）==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_splitter = QSplitter(Qt.Vertical)

        # 上：表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([self.tr("NV值"), self.tr("说明")])
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 420)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #666666;
                border: 1px solid #555555;
            }
            QTableWidget::item {
                border-right: 1px solid #666666;
                border-bottom: 1px solid #666666;
            }
            QHeaderView::section {
                border-right: 1px solid #666666;
                border-bottom: 1px solid #666666;
            }
        """)

        # 双击：直接进入编辑
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_nv())
        # 按需求：选中NV不自动读取，仅在用户点击“读取”时才读取并显示

        left_splitter.addWidget(self.table)

        # 下：读写区（先搭UI，逻辑后续接入）
        rw_container = QWidget()
        rw_layout = QVBoxLayout(rw_container)
        rw_layout.setContentsMargins(8, 8, 8, 8)

        self.rw_value_edit = PlainTextEdit()
        self.rw_value_edit.setPlaceholderText(self.tr("在此输入读取结果或待写入的数据（多字段请使用 {key:'value', ...} 格式，字符串值必须加引号）"))
        self.rw_value_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rw_layout.addWidget(self.rw_value_edit)

        rw_controls = QHBoxLayout()

        # SUB 单选按钮直接放在控制栏
        rw_controls.addWidget(QLabel("SUB:"))
        self.sub0_radio = QRadioButton("sub0")
        self.sub1_radio = QRadioButton("sub1")
        self.sub_group = QButtonGroup(self)
        self.sub_group.setExclusive(True)
        self.sub_group.addButton(self.sub0_radio, 0)
        self.sub_group.addButton(self.sub1_radio, 1)
        self.sub0_radio.setChecked(True)
        # 按需求：切换sub不自动读取，仅影响后续"读取/写入"的 SUB 参数
        rw_controls.addWidget(self.sub0_radio)
        rw_controls.addWidget(self.sub1_radio)

        rw_controls.addSpacing(20)  # 添加间距
        rw_controls.addStretch()

        self.read_btn = QPushButton(self.tr("读取"))
        self.write_btn = QPushButton(self.tr("写入"))
        self.read_btn.clicked.connect(self._on_read_clicked)
        self.write_btn.clicked.connect(self._on_write_clicked)
        rw_controls.addWidget(self.read_btn)
        rw_controls.addWidget(self.write_btn)

        rw_layout.addLayout(rw_controls)

        left_splitter.addWidget(rw_container)
        left_splitter.setStretchFactor(0, 8)
        left_splitter.setStretchFactor(1, 2)

        left_layout.addWidget(left_splitter)

        # ========== 右侧：竖排工具区 ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)

        right_layout.addWidget(QLabel(self.tr("搜索:")))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("输入搜索关键字..."))
        self.search_input.returnPressed.connect(self.search_data)
        right_layout.addWidget(self.search_input)

        self.search_btn = QPushButton(self.tr("搜索"))
        self.search_btn.clicked.connect(self.search_data)
        right_layout.addWidget(self.search_btn)

        right_layout.addSpacing(10)

        self.add_btn = QPushButton(self.tr("新增"))
        self.add_btn.clicked.connect(self.add_nv)
        right_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton(self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_nv)
        right_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton(self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_nv)
        right_layout.addWidget(self.delete_btn)

        right_layout.addSpacing(10)

        self.import_btn = QPushButton(self.tr("导入"))
        self.import_btn.clicked.connect(self.import_data)
        right_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton(self.tr("导出"))
        self.export_btn.clicked.connect(self.export_data)
        right_layout.addWidget(self.export_btn)

        right_layout.addStretch()

        right_widget.setFixedWidth(180)

        root_layout.addWidget(left_widget, 1)
        root_layout.addWidget(right_widget, 0)

    def _get_selected_nv_item(self):
        nv_index = self._get_selected_nv_index()
        if nv_index is None:
            return None
        return str(self.nv_data[nv_index].get("nv_value", "")).strip() or None

    def _get_sub_id(self) -> int:
        return int(self.sub_group.checkedId()) if self.sub_group.checkedId() in (0, 1) else 0

    def _get_device_id(self):
        parent = self.parent()
        if parent and hasattr(parent, "device_manager"):
            device = parent.device_manager.validate_device_selection()
            if device:
                return device
        return None

    def _set_busy(self, busy: bool, scope: str = "read"):
        """
        scope:
          - read: 仅影响读写区，避免“选中NV自动读取时整页变灰”
          - all:  用于写入等关键操作，禁用整页避免状态被打断
        """
        self.read_btn.setEnabled(not busy)
        self.write_btn.setEnabled(not busy)

        if scope == "all":
            self.table.setEnabled(not busy)
            self.add_btn.setEnabled(not busy)
            self.edit_btn.setEnabled(not busy)
            self.delete_btn.setEnabled(not busy)
            self.import_btn.setEnabled(not busy)
            self.export_btn.setEnabled(not busy)
            self.search_input.setEnabled(not busy)
            self.search_btn.setEnabled(not busy)

    def _on_read_clicked(self):
        nv_item = self._get_selected_nv_item()
        if not nv_item:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要读取的NV"))
            return
        self._trigger_read(nv_item, allow_queue=True)

    def _trigger_read(self, nv_item: str, allow_queue: bool = False):
        if self._pcat_worker and self._pcat_worker.isRunning():
            if allow_queue:
                self._pending_read_request = (nv_item, self._get_sub_id())
            return

        device_id = self._get_device_id()
        if not device_id:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择一个设备"))
            return

        sub_id = self._get_sub_id()
        self._set_busy(True, scope="read")
        self._pcat_worker = PcatNvWorker(device_id=device_id, nv_item=nv_item, sub_id=sub_id, parent=self)
        self._pcat_worker.finished.connect(self._on_read_finished)
        self._pcat_worker.start()

    def _on_read_finished(self, success: bool, value: str, stdout: str, stderr: str):
        self._set_busy(False, scope="read")
        if not success:
            msg = stderr.strip() or stdout.strip() or self.tr("读取失败")
            QMessageBox.warning(self, self.tr("错误"), f"{self.tr('读取失败')}:\n{msg}")
            self._pending_write_value = None
            # 失败也要尝试处理排队的读取请求
            if self._pending_read_request is not None:
                nv_item, sub_id = self._pending_read_request
                self._pending_read_request = None
                # sub_id 变化已包含在 nv_item/sub_id，直接触发
                self._trigger_read(nv_item, allow_queue=False)
            return

        # 如果是“写入前预读”，走写入决策；否则正常填充输入框
        if self._pending_write_value is not None:
            self._continue_write_after_preread(read_value=value)
            return

        self.rw_value_edit.setPlainText(value)

        # 处理排队的读取请求（用户在读取期间切换了NV/sub）
        if self._pending_read_request is not None:
            nv_item, sub_id = self._pending_read_request
            self._pending_read_request = None
            self._trigger_read(nv_item, allow_queue=False)

    def _on_write_clicked(self):
        nv_item = self._get_selected_nv_item()
        if not nv_item:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要写入的NV"))
            return

        device_id = self._get_device_id()
        if not device_id:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择一个设备"))
            return

        new_value = self.rw_value_edit.toPlainText().strip()
        if not new_value:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请输入要写入的数据"))
            return

        # 写入前必须先READ（同 NV + 同 SUB）
        self._pending_write_value = new_value
        self._trigger_read(nv_item)

    def _continue_write_after_preread(self, read_value: str):
        nv_item = self._get_selected_nv_item()
        device_id = self._get_device_id()
        if not nv_item or not device_id:
            self._pending_write_value = None
            QMessageBox.warning(self, self.tr("错误"), self.tr("写入前校验失败：未选择NV或设备"))
            return

        sub_id = self._get_sub_id()
        new_value = self._pending_write_value or ""
        self._pending_write_value = None

        multi = pcat_nv.is_multi_value(read_value)
        use_json = False
        if multi:
            ok, err = pcat_nv.validate_json_like(new_value)
            if not ok:
                QMessageBox.warning(
                    self,
                    self.tr("提示"),
                    f"{self.tr('该NV为多字段结构，不允许直接写入。')}\n{self.tr('请使用GUI写入或检查JSON格式。')}\n\n{self.tr('原因')}: {err}",
                )
                return
            use_json = True

        # 执行WRITE
        if self._pcat_write_worker and self._pcat_write_worker.isRunning():
            return

        self._set_busy(True, scope="all")
        self._pcat_write_worker = PcatNvWriteWorker(
            device_id=device_id,
            nv_item=nv_item,
            sub_id=sub_id,
            value=new_value,
            use_json=use_json,
            parent=self,
        )
        self._pcat_write_worker.finished.connect(self._on_write_finished)
        self._pcat_write_worker.start()

    def _on_write_finished(self, success: bool, message: str, stdout: str, stderr: str):
        self._set_busy(False, scope="all")
        if success:
            # 询问是否立即重启生效
            reply = QMessageBox.question(
                self,
                self.tr("写入成功"),
                self.tr("NV写入成功！\n\n是否立即重启设备使更改生效？"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._trigger_reset()
            return

        # key 错/格式错/权限等：展示 stdout+stderr 摘要
        detail = (stderr or "").strip() or (stdout or "").strip() or message
        QMessageBox.critical(self, self.tr("错误"), f"{self.tr('写入失败')}:\n{detail}")

    def _trigger_reset(self):
        """触发设备重启"""
        device_id = self._get_device_id()
        if not device_id:
            QMessageBox.warning(self, self.tr("提示"), self.tr("未选择设备"))
            return

        if self._pcat_reset_worker and self._pcat_reset_worker.isRunning():
            return

        self._pcat_reset_worker = PcatResetWorker(device_id=device_id, parent=self)
        self._pcat_reset_worker.finished.connect(self._on_reset_finished)
        self._pcat_reset_worker.start()
        QMessageBox.information(self, self.tr("提示"), self.tr("正在重启设备，请稍候..."))

    def _on_reset_finished(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, self.tr("成功"), self.tr("设备重启命令已执行，请等待设备重新连接"))
        else:
            QMessageBox.warning(self, self.tr("警告"), f"{self.tr('重启失败')}:\n{message}")
    
    def load_data(self):
        """加载数据"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.nv_data = data.get('nv_list', [])
                    logger.debug(f"加载高通NV数据: {len(self.nv_data)} 条记录")
            else:
                # 创建默认数据
                self.nv_data = []
                logger.debug("创建新的高通NV数据文件")
            
            self.refresh_table()
            
        except Exception as e:
            logger.exception(f"加载高通NV数据失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('加载数据失败')}: {str(e)}")
    
    def save_data(self):
        """保存数据"""
        try:
            # 先备份现有文件
            if os.path.exists(self.config_file):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"qc_nv_backup_{timestamp}.json")
                
                import shutil
                shutil.copy2(self.config_file, backup_file)
                logger.debug(f"备份文件到: {backup_file}")
            
            data = {
                'nv_list': self.nv_data,
                'version': '1.0',
                'update_time': datetime.datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存高通NV数据: {len(self.nv_data)} 条记录")
            
        except Exception as e:
            logger.exception(f"保存高通NV数据失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存数据失败')}: {str(e)}")
    
    def refresh_table(self):
        """刷新表格"""
        self._is_refreshing_table = True
        try:
            keyword = (self._filter_keyword or "").strip().lower()
            self._display_indices = []
            self.table.setRowCount(0)

            for idx, item in enumerate(self.nv_data):
                nv_value = item.get('nv_value', '')
                description = item.get('description', '')
                if keyword:
                    if keyword not in str(nv_value).lower() and keyword not in str(description).lower():
                        continue

                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(nv_value)))
                self.table.setItem(row, 1, QTableWidgetItem(str(description)))
                self._display_indices.append(idx)
        finally:
            self._is_refreshing_table = False

    def _get_selected_nv_index(self):
        """获取当前选中行对应的 nv_data 索引（支持搜索过滤后的映射）"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return None
        if current_row >= len(self._display_indices):
            return None
        return self._display_indices[current_row]
    
    def add_nv(self):
        """新增NV"""
        dialog = NVEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nv_value, description = dialog.get_data()
            if nv_value:
                self.nv_data.append({
                    'nv_value': nv_value,
                    'description': description
                })
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("新增成功！"))
    
    def edit_nv(self):
        """编辑NV"""
        nv_index = self._get_selected_nv_index()
        if nv_index is None:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的项目"))
            return
        
        nv_value = str(self.nv_data[nv_index].get('nv_value', ''))
        description = str(self.nv_data[nv_index].get('description', ''))
        
        dialog = NVEditDialog(nv_value=nv_value, description=description, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_nv_value, new_description = dialog.get_data()
            if new_nv_value:
                # 更新数据
                self.nv_data[nv_index] = {
                    'nv_value': new_nv_value,
                    'description': new_description
                }
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("编辑成功！"))
    
    def delete_nv(self):
        """删除NV"""
        nv_index = self._get_selected_nv_index()
        if nv_index is None:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的项目"))
            return
        
        nv_value = str(self.nv_data[nv_index].get('nv_value', ''))
        
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除')} '{nv_value}' {self.tr('吗？')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.nv_data[nv_index]
            self.save_data()
            self.refresh_table()
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入NV数据"), "",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                imported_data = data.get('nv_list', [])
                if not imported_data:
                    QMessageBox.warning(self, self.tr("提示"), self.tr("导入的文件格式不正确或数据为空"))
                    return
                
                # 询问是否覆盖或追加
                reply = QMessageBox.question(
                    self, self.tr("导入方式"),
                    self.tr("请选择导入方式：\n是 = 追加到现有数据\n否 = 覆盖现有数据\n取消 = 取消操作"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 追加
                    self.nv_data.extend(imported_data)
                elif reply == QMessageBox.StandardButton.No:
                    # 覆盖
                    self.nv_data = imported_data
                else:
                    return
                
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("导入成功！"))
                
            except Exception as e:
                logger.exception(f"导入NV数据失败: {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导入失败')}: {str(e)}")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出NV数据"), "qc_nv_export.json",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            try:
                data = {
                    'nv_list': self.nv_data,
                    'version': '1.0',
                    'export_time': datetime.datetime.now().isoformat(),
                    'export_note': self.tr('高通NV数据导出')
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, self.tr("导出成功"), f"{self.tr('数据已导出到')}\n{file_path}")
                
            except Exception as e:
                logger.exception(f"导出NV数据失败: {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导出失败')}: {str(e)}")
    
    def search_data(self):
        """搜索数据"""
        self._filter_keyword = self.search_input.text().strip()
        self.refresh_table()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_data()
        super().closeEvent(event)


class NVEditDialog(QDialog):
    """NV编辑对话框"""
    
    def __init__(self, nv_value="", description="", parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("编辑NV"))
        self.setModal(True)
        self.resize(500, 200)
        
        self.setup_ui()
        
        # 设置初始值
        self.nv_value_edit.setText(nv_value)
        self.description_edit.setPlainText(description)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.nv_value_edit = QLineEdit()
        self.nv_value_edit.setPlaceholderText(self.tr("请输入NV值"))
        form_layout.addRow(self.tr("NV值*:"), self.nv_value_edit)
        
        layout.addLayout(form_layout)
        
        desc_label = QLabel(self.tr("说明:"))
        layout.addWidget(desc_label)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(self.tr("请输入说明（可选）..."))
        self.description_edit.setMaximumHeight(100)
        layout.addWidget(self.description_edit)
        
        layout.addStretch()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_accept(self):
        """验证并接受"""
        nv_value = self.nv_value_edit.text().strip()
        
        if not nv_value:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请输入NV值"))
            return
        
        self.accept()
    
    def get_data(self):
        """获取数据"""
        return (self.nv_value_edit.text().strip(), 
                self.description_edit.toPlainText().strip())
