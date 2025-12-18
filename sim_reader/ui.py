from PyQt5.QtWidgets import (
    QMainWindow, QTreeWidget, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QDialog, QTableWidget, QMessageBox,QGridLayout,
    QTableWidgetItem, QSizePolicy, QAbstractItemView, QFormLayout,
    QProgressDialog, QApplication, QFileDialog, QInputDialog, QComboBox,
    QScrollArea, QCheckBox, QHeaderView
)   
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent, QTimer, pyqtSlot
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
import json
import os
import logging
from core.serial_comm import SerialComm
from core.data_handler import admin, reset_sim
from core.sim_service import SimService, resize_ef
from tree_manager import TreeManager
import time

class CloseProgressDialogEvent(QEvent):
    """自定义事件类，用于在主线程中安全关闭进度对话框
    继承自QEvent，使用自定义事件类型确保线程安全
    """
    EVENT_TYPE = QEvent.Type(QEvent.User + 1)
    def __init__(self):
        super().__init__(self.EVENT_TYPE)


class AdminThread(QThread):
    """后台执行ADM PIN验证的线程类
    用于异步处理ADM PIN验证，避免阻塞主UI线程
    """
    result_ready = pyqtSignal(str)

    def __init__(self, comm, pin):
        super().__init__()
        self.comm = comm
        self.pin = pin

    def run(self):
        try:
            response = admin(self.comm, pin=self.pin)
            self.result_ready.emit(response)
        except Exception as e:
            logging.error("ADM PIN验证失败: %s", str(e))
            self.result_ready.emit(f"error: {e}")


class EFManagerDialog(QDialog):
    """
    EF文件管理对话框
    提供创建和删除EF文件的功能，包含完整的参数验证和错误处理
    """
    def __init__(self, sim_service, parent=None):
        super().__init__(parent)
        self.sim_service = sim_service
        self.setWindowTitle("Manage EF")
        self.setFixedSize(300, 300)
        logging.debug("初始化EF管理对话框")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 表单部分
        form_layout = QFormLayout()

        self.ef_id_input = QLineEdit()
        self.sfi_input = QLineEdit()

        self.adf_combo = QComboBox()
        self.adf_combo.addItems(["USIM", "ISIM", "5G-EF", "DF", "MF"])

        self.structure_combo = QComboBox()
        self.structure_combo.addItems(["transparent", "linear"])

        self.record_len_input = QLineEdit()
        self.record_num_input = QLineEdit()
        self.security_attr_input = QLineEdit()

        form_layout.addRow("EF ID(M):", self.ef_id_input)
        form_layout.addRow("SFI(O):", self.sfi_input)
        form_layout.addRow("ADF/DF(M):", self.adf_combo)
        form_layout.addRow("Structure(M):", self.structure_combo)
        form_layout.addRow("Record/Binary length(M):", self.record_len_input)
        form_layout.addRow("Number of record(C):", self.record_num_input)
        form_layout.addRow("Security Attr(M):", self.security_attr_input)

        layout.addLayout(form_layout)

        # 按钮区
        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        btn_layout.addWidget(self.delete_btn)

        self.create_btn = QPushButton("Create")
        self.create_btn.clicked.connect(self.on_create_clicked)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

    def on_delete_clicked(self):
        """删除 EF 文件，先提醒安全属性"""
        ef_id = self.ef_id_input.text().strip().upper()
        adf = self.adf_combo.currentText()

        logging.info("用户尝试删除文件: ef_id=%s, adf=%s", ef_id, adf)

        if not ef_id:
            QMessageBox.warning(self, "error", "EF ID cannot be empty.")
            return

        # === Step 1: 获取安全属性 ===
        ef_info = self.sim_service.get_ef_structure(adf, ef_id)
        if not ef_info:
            QMessageBox.warning(self, "Error", f"无法获取 {ef_id} 的结构信息。")
            return

        sec_attr = ef_info.get("sec_attr", "unknown")
        self.last_deleted_sec_attr = sec_attr  # 可选：保留用于创建时使用

        # === Step 2: 弹出提示框，包含 sec_attr 信息 ===
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认删除")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(f"准备删除: EF {ef_id}\n务必记住下面安全属性，在下次创建的时候使用:\n\nSecurity Attr: {sec_attr}\n\n是否继续？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        user_response = msg_box.exec_()

        if user_response != QMessageBox.Yes:
            logging.info("用户取消删除操作: %s", ef_id)
            return  # 用户点击 Cancel，直接返回

        # === Step 3: 继续删除 ===
        result = self.sim_service.delete_ef(ef_id, adf)
        if result == "9000":
            QMessageBox.information(self, "Success", f"EF {ef_id} deleted successfully.")
        elif result == "6982":
            QMessageBox.warning(self, "error", f"Verify Admin PIN and try again.")
        else:
            QMessageBox.warning(self, "error", f"Failed to delete EF {ef_id}: {result}")


    def on_create_clicked(self):
        """创建 EF"""
        ef_id = self.ef_id_input.text().strip()
        sfi = self.sfi_input.text().strip()
        adf = self.adf_combo.currentText()
        structure = self.structure_combo.currentText()
        record_len = self.record_len_input.text().strip()
        record_num = self.record_num_input.text().strip()
        security_attrs = self.security_attr_input.text().strip()

        logging.info("[on_create_clicked] 用户创建文件参数: ef_id=%s, sfi=%s, adf=%s, structure=%s, record_len=%s, record_num=%s, security_attrs=%s",
                    ef_id, sfi, adf, structure, record_len, record_num, security_attrs)

        if not ef_id:
            logging.warning("[on_create_clicked] EF ID为空")
            QMessageBox.warning(self, "error", "EF ID cannot be empty.")
            return
        if not security_attrs:
            logging.warning("[on_create_clicked] Security Attr为空")
            QMessageBox.warning(self, "error", "Security Attr cannot be empty.")
            return

        # Check if record_len and record_num are numeric
        if not record_len.isdigit():
            QMessageBox.warning(self, "error", "Record/Binary length must be a number.")
            return
        if structure == "linear" and not record_num.isdigit():
            QMessageBox.warning(self, "error", "Number of record must be a number.")
            return


        logging.info("用户创建文件: ef_id=%s, record_len=%s, adf=%s, structure=%s, record_num=%s, security_attrs=%s, sfi=%s", 
                    ef_id, record_len, adf, structure, record_num, security_attrs, sfi)

        result = self.sim_service.create_file(
            ef_id, record_len, adf, structure, record_num, security_attrs, sfi
        )
        if result == "9000":
            QMessageBox.information(self, "Success", f"EF {ef_id} created successfully.")
        elif result == "6982":
            QMessageBox.warning(self, "error", f"Verify Admin PIN and try again.")
        else:
            QMessageBox.warning(self, "error", f"Failed to create EF {ef_id}: {result}")


class SimEditorUI(QMainWindow):
    """SIM卡编辑器主界面
    提供SIM卡数据的读取、写入、管理等功能
    实现了多线程操作和完整的错误处理机制
    """
    data_ready = pyqtSignal(list)  # 数据读取完成信号
    json_load_done = pyqtSignal(bool, str)  # JSON加载完成信号
    error_occurred = pyqtSignal(str)  # 错误发生信号
    show_message = pyqtSignal(str, str)  # 通用消息显示信号

    def __init__(self):
        super().__init__()
        logging.info("初始化SIM编辑器主界面")

        # 初始化核心组件
        self.selected_row = None
        self.sim_service = SimService()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.comm = SerialComm()
        self.comm_lock = Lock()
        self.port_disconnect_warned = False  # 添加标志变量，用于控制端口断开警告的显示

        # 初始化UI组件
        self.init_ui()

        # 初始化树形管理器
        self.tree_manager = TreeManager(self.tree)
        self.tree_manager.populate_tree()

        # 设置窗口属性
        self.setWindowTitle("SIM Tool v1.8")
        self.setGeometry(500, 300, 800, 600)

        # 连接信号和槽
        self.data_ready.connect(self.display_read_data)
        self.json_load_done.connect(self.on_json_load_done)
        self.error_occurred.connect(self.show_error_dialog)
        self.show_message.connect(self.display_message)
        logging.debug("SIM编辑器主界面初始化完成")
        # --- 端口刷新定时器（简化版，仅检测端口变化） ---
        self.port_timer = QTimer(self)
        self.port_timer.setInterval(30000)     # 30 秒刷新一次，减少资源消耗
        self.port_timer.timeout.connect(self.update_port_list)
        self.port_timer.start()
        # === 启动时检测是否有串口 ===
        # if not self.comm.get_all_ports():
        #     QMessageBox.warning(
        #         self,
        #         "No Ports Found",
        #         "未检测到任何可用串口设备，请确在使用前认设备已经连接并且AT端口已经打开。",
        #         QMessageBox.Ok
        #     )



    def init_ui(self):
        """初始化主界面布局"""
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 左侧：树形视图
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(250)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        main_layout.addWidget(self.tree)

        # 右侧布局
        right_layout = QVBoxLayout()

        # Tab
        self.tabs = QTabWidget()
        self.add_sim_data_tab()
        self.add_pins_management_tab()  # 你的 PIN 管理 Tab
        self.tabs.setFixedHeight(120)
        right_layout.addWidget(self.tabs, 1)

        # 表格显示读取结果
        self.read_data_display = QTableWidget()
        self.read_data_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.read_data_display.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.read_data_display.itemClicked.connect(self.on_read_data_item_clicked)
        right_layout.addWidget(self.read_data_display)

        # 动态写入区域
        self.write_data_scroll_area = QScrollArea()
        self.write_data_scroll_area.setWidgetResizable(True)  # 让内部 widget 根据内容大小变化
        self.write_data_widget = QWidget()
        self.write_data_layout = QFormLayout()
        self.write_data_widget.setLayout(self.write_data_layout)
        self.write_data_scroll_area.setWidget(self.write_data_widget)  # 让滚动区域包裹 write_data_widget

        right_layout.addWidget(self.write_data_scroll_area)  #


        
        # 按钮区域
        button_layout = QHBoxLayout()
        refresh_port_button = QPushButton("Refresh Port")
        refresh_port_button.clicked.connect(self.on_refresh_port_button_clicked)
        button_layout.addWidget(refresh_port_button)

        refresh_button = QPushButton("Refresh SIM")
        refresh_button.clicked.connect(self.on_refresh_button_clicked)
        button_layout.addWidget(refresh_button)

        json_load_button = QPushButton("Load JSON")
        json_load_button.clicked.connect(self.on_load_json_clicked)
        button_layout.addWidget(json_load_button)

        # gid1_button = QPushButton("GID1")
        # gid1_button.clicked.connect(lambda: self.on_gid_button_clicked("GID1", "6F3E"))
        # button_layout.addWidget(gid1_button)

        # gid2_button = QPushButton("GID2")
        # gid2_button.clicked.connect(lambda: self.on_gid_button_clicked("GID2", "6F3F"))
        # button_layout.addWidget(gid2_button)

        manage_ef_button = QPushButton("Manage EF")
        manage_ef_button.clicked.connect(self.on_manage_ef_clicked)
        button_layout.addWidget(manage_ef_button)

        right_layout.addLayout(button_layout)
        main_layout.addLayout(right_layout)

 

    def on_batch_read_button_clicked(self):
        """批量读取所有EF文件
        遍历所有预定义的EF文件，逐个读取并保存结果
        结果将保存到json_data/batch_read_result.json文件中
        """
        logging.info("[on_batch_read_button_clicked] 点击 'Read All EF' 按钮，批量读取所有EF文件")
        
        # 检查连接状态
        is_connected, msg = self.check_connection_before_operation()
        if not is_connected:
            logging.error("批量读取前连接检查失败: %s", msg)
            QMessageBox.warning(self, "连接错误", f"连接检查失败: {msg}\n请先选择端口并连接")
            return
        
        os.makedirs("json_data", exist_ok=True)
        force_raw = self.raw_checkbox.isChecked()
        
        # 定义受保护的 EF ID 列表
        protected_ef_ids = ["6F06", "2F00", "2F06"]
        
        # 过滤掉受保护的 EF ID
        filtered_file_paths = {
            file_name: ef_id for file_name, ef_id in self.tree_manager.file_paths.items()
            if ef_id not in protected_ef_ids
        }
        
        total_efs = len(filtered_file_paths)
        logging.info("开始批量读取EF文件，总数: %d (已过滤受保护文件)", total_efs)
        
        self.progress_dialog = QProgressDialog("Reading all EF...", None, 0, total_efs, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        QApplication.processEvents()

        ef_list = []
        success_count = 0
        fail_count = 0
        fail_details = {}

        for idx, (file_name, ef_id) in enumerate(filtered_file_paths.items()):
            adf_type = self.tree_manager.get_adf_type(file_name)
            logging.debug("正在读取EF文件 [%d/%d]: %s:%s", idx + 1, total_efs, adf_type, ef_id)
            
            result = self.sim_service.read_data(adf_type, ef_id, save_single=False, force_raw=force_raw)

            if isinstance(result, str) and result.startswith("error"):
                fail_count += 1
                # 去掉"error:"前缀
                error_msg = result[6:] if result.startswith("error:") else result
                fail_details[f"{adf_type.upper()}:{ef_id}"] = error_msg
                logging.warning("读取EF文件失败 [%s:%s]: %s", adf_type, ef_id, error_msg)
            else:
                success_count += 1
                if not isinstance(result, list):
                    result = [result]
                ef_obj = {
                    "ef_id": ef_id,
                    "adf_type": adf_type.upper(),
                    "records": result
                }
                ef_list.append(ef_obj)
                logging.debug("成功读取EF文件 [%s:%s]", adf_type, ef_id)

            self.progress_dialog.setValue(idx + 1)
            QApplication.processEvents()

        self.progress_dialog.close()
        logging.info("批量读取完成: 成功=%d, 失败=%d", success_count, fail_count)

        final_json = { "EF_list": ef_list }
        out_path = os.path.join("json_data", "batch_read_result.json")

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(final_json, f, ensure_ascii=False, indent=4)
            logging.info("批量读取结果已保存到: %s", out_path)

            msg = (
                f"Batch read complete!\n"
                f"Total EF: {total_efs}\n"
                f"Success: {success_count}\n"
                f"Fail: {fail_count}\n"
                f"Results saved to {out_path}"
            )

            if fail_details:
                msg += "\n\nFail details:\n"
                for ef_key, reason in fail_details.items():
                    msg += f"  - {ef_key} => {reason}\n"
                logging.warning("批量读取失败详情: %s", fail_details)

            QMessageBox.information(self, "Read All EF", msg)
        except Exception as e:
            error_msg = f"Failed to save read results: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)


    def on_manage_ef_clicked(self):
        """点击 Manage EF 按钮，弹出对话框"""
        logging.info("[on_manage_ef_clicked] 打开EF管理对话框")
        dlg = EFManagerDialog(self.sim_service, self)
        dlg.exec_()

    def closeEvent(self, event):
        """关闭窗口时需要做的清理操作"""
        if hasattr(self, "port_timer"):
            self.port_timer.stop()
        
        # 关闭串口连接
        if hasattr(self, 'comm') and self.comm:
            try:
                # 先尝试使用 close() 方法
                if hasattr(self.comm, 'close'):
                    self.comm.close()
                # 确保串口被关闭
                if hasattr(self.comm, 'ser') and self.comm.ser is not None:
                    if self.comm.ser.is_open:
                        self.comm.ser.close()
                        time.sleep(0.1)  # 给串口一点时间完全关闭
                # 重置初始化标志和端口信息
                if hasattr(self.comm, 'initialized'):
                    self.comm.initialized = False
                if hasattr(self.comm, 'port'):
                    self.comm.port = None
                if hasattr(self.comm, 'ser'):
                    self.comm.ser = None
                logging.info("[SimEditorUI] 串口连接已关闭并清理")
            except Exception as e:
                logging.error(f"[SimEditorUI] 关闭串口时出错: {e}")
        
        self.executor.shutdown(wait=False)
        super().closeEvent(event)

    # ========== 添加的两个 Tabs  ==========
    def add_sim_data_tab(self):
        """SIM Data 选项卡：两行布局，按钮右对齐"""
        tab = QWidget()
        outer = QVBoxLayout(tab)
        grid = QGridLayout()
        outer.addLayout(grid)

        # -------- 第 0 行：Filepath / ADF / 三个主按钮 --------
        fp_lbl = QLabel("Filepath:")
        self.file_path_input = QLineEdit()
        # self.file_path_input.setReadOnly(True)

        adf_lbl = QLabel("ADF type:")
        self.adf_type_input = QLineEdit()
        # self.adf_type_input.setReadOnly(True)

        raw_lbl = QLabel("Raw:")
        self.raw_checkbox = QCheckBox()

        read_btn = QPushButton("Read")
        read_btn.clicked.connect(self.on_read_button_clicked)

        update_btn = QPushButton("Update")
        update_btn.clicked.connect(self.on_update_button_clicked)

        all_btn = QPushButton("Read All EF")
        all_btn.clicked.connect(self.on_batch_read_button_clicked)

        # 放到网格   (row, col, rowSpan, colSpan)
        grid.addWidget(fp_lbl,          0, 0)
        grid.addWidget(self.file_path_input, 0, 1, 1, 2)   # 跨 2 列
        grid.addWidget(adf_lbl,         0, 3)
        grid.addWidget(self.adf_type_input, 0, 4)
        grid.addWidget(read_btn,   0, 6)
        grid.addWidget(update_btn, 0, 7)
        grid.addWidget(all_btn,    0, 8)

        # -------- 第 1 行：pSIM / eSIM / 端口选择 --------
        psim_btn = QPushButton("pSIM")
        psim_btn.clicked.connect(self.on_psim_button_clicked)

        esim_btn = QPushButton("eSIM")
        esim_btn.clicked.connect(self.on_esim_button_clicked)

        # 添加端口选择下拉框
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        # 添加占位提示
        self.port_combo.addItem("-- 请选择端口 --")
        self.port_combo.setCurrentIndex(0)  # 默认选中占位项
        self.update_port_list()  # 初始化端口列表
        self.port_combo.currentTextChanged.connect(self.on_port_changed)
        grid.addWidget(raw_lbl, 1, 4)
        grid.addWidget(self.raw_checkbox, 1, 5)
        grid.addWidget(psim_btn, 1, 6)
        grid.addWidget(esim_btn, 1, 7)
        grid.addWidget(self.port_combo, 1, 8)

        # -------- 网格弹性列，避免挤压 --------
        grid.setColumnStretch(5, 1)   # 第 5 列吸收多余空间
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        outer.addStretch()            # 其余空间给表格 / 滚动区
        self.tabs.addTab(tab, "SIM Data")

    def update_port_list(self):
        """简化的端口列表更新 - 仅检测端口变化，不自动重连"""
        if getattr(self.comm, "busy", False):
            logging.debug("[PortScanSkip] 串口忙，跳过端口检查")
            return

        current_port = self.comm.port
        all_ports = self.comm.get_all_ports()
        old_ports = self._get_combo_items(self.port_combo)
        # 从旧端口列表中排除占位项
        old_ports = [p for p in old_ports if p != "-- 请选择端口 --"]

        # === 端口列表无变化时，直接返回 ===
        if set(all_ports) == set(old_ports):
            return

        # === 刷新下拉框 ===
        self.port_combo.blockSignals(True)
        current_selection = self.port_combo.currentText()
        self.port_combo.clear()
        # 添加占位项
        self.port_combo.addItem("-- 请选择端口 --")
        self.port_combo.addItems(all_ports)

        if current_port and current_port in all_ports:
            # 当前端口仍然存在，保持选中
            self.port_combo.setCurrentText(current_port)
            self.port_disconnect_warned = False
            logging.debug("端口 %s 仍然可用", current_port)

        elif current_port and current_port not in all_ports:
            # 当前端口已断开
            logging.info("端口 %s 已断开", current_port)
            # 选择占位项
            self.port_combo.setCurrentIndex(0)
            if not self.port_disconnect_warned:
                QMessageBox.information(
                    self, "端口断开",
                    f"端口 '{current_port}' 已断开，请手动选择其他端口并重新连接。"
                )
                self.port_disconnect_warned = True

        elif not current_port and all_ports:
            # 初次打开时，不自动选择端口，等待用户手动选择
            logging.info("发现可用端口: %s，等待用户选择", all_ports)
            # 默认选中占位项（索引0）
            self.port_combo.setCurrentIndex(0)

        self.port_combo.blockSignals(False)



    def _get_combo_items(self, combo: QComboBox) -> list[str]:
        """返回 QComboBox 中当前所有条目文本"""
        return [combo.itemText(i) for i in range(combo.count())]

    def on_port_changed(self, new_port):
        """端口选择改变时的处理：测试端口并连接"""
        if not new_port or new_port == "-- 请选择端口 --":
            return

        # 如果是当前已连接的端口，不重复连接
        if self.comm.port == new_port and self.comm.initialized:
            # 测试当前连接是否正常
            try:
                response = self.comm.send_command('AT')
                if 'OK' in response:
                    logging.info("当前端口 %s 连接正常", new_port)
                    # 不显示消息框，避免干扰用户
                    return
            except Exception as e:
                logging.warning("当前端口测试失败: %s", e)
                # 连接可能已断开，继续执行连接流程

        logging.info("用户选择端口: %s，开始测试和连接", new_port)

        try:
            # 测试端口是否支持AT命令
            logging.info("正在测试端口 %s 是否支持AT命令...", new_port)
            if not self.comm.test_port(new_port):
                error_msg = f"端口 {new_port} 不支持AT命令或不可用\n\n请确认：\n1. 端口是否正确\n2. 设备是否已连接\n3. 端口是否被其他程序占用"
                logging.warning(error_msg)
                QMessageBox.warning(
                    self, 
                    "端口不可用", 
                    error_msg
                )
                # 恢复选择（如果有之前已连接的端口，否则恢复到占位项）
                self.port_combo.blockSignals(True)
                if self.comm.port:
                    index = self.port_combo.findText(self.comm.port)
                    if index >= 0:
                        self.port_combo.setCurrentIndex(index)
                    else:
                        self.port_combo.setCurrentIndex(0)  # 恢复到占位项
                else:
                    self.port_combo.setCurrentIndex(0)  # 恢复到占位项
                self.port_combo.blockSignals(False)
                return

            # 测试通过，尝试连接端口
            logging.info("端口 %s 测试通过，开始连接...", new_port)
            if self.comm.switch_port(new_port):
                # 验证连接是否正常
                try:
                    response = self.comm.send_command('AT')
                    if 'OK' in response:
                        logging.info("端口 %s 连接成功", new_port)
                        QMessageBox.information(
                            self, 
                            "连接成功", 
                            f"已成功连接到端口 {new_port}\n端口测试正常，可以使用SIM卡功能。"
                        )
                        self.comm.initialized = True
                        self.update_port_list()
                    else:
                        logging.warning("端口 %s 连接后测试异常: %s", new_port, response)
                        QMessageBox.warning(
                            self, 
                            "连接异常", 
                            f"已连接到端口 {new_port}，但测试响应异常：{response}\n\n请检查设备连接状态。"
                        )
                        self.comm.initialized = False
                        self.update_port_list()
                except Exception as e:
                    logging.error("端口 %s 连接后测试失败: %s", new_port, e)
                    QMessageBox.warning(
                        self, 
                        "连接测试失败", 
                        f"已连接到端口 {new_port}，但无法与设备通信：{str(e)}\n\n请检查设备连接状态。"
                    )
                    self.comm.initialized = False
                    self.update_port_list()
            else:
                error_msg = f"无法连接到端口 {new_port}\n\n可能的原因：\n1. 端口被其他程序占用\n2. 设备驱动问题\n3. 端口权限不足"
                logging.error(error_msg)
                QMessageBox.critical(
                    self, 
                    "连接失败", 
                    error_msg
                )
                # 恢复选择（恢复到占位项或之前已连接的端口）
                self.port_combo.blockSignals(True)
                if self.comm.port:
                    index = self.port_combo.findText(self.comm.port)
                    if index >= 0:
                        self.port_combo.setCurrentIndex(index)
                    else:
                        self.port_combo.setCurrentIndex(0)  # 恢复到占位项
                else:
                    self.port_combo.setCurrentIndex(0)  # 恢复到占位项
                self.port_combo.blockSignals(False)
                self.update_port_list()
        except Exception as e:
            error_msg = f"连接端口时发生错误：{str(e)}"
            logging.exception(error_msg)
            QMessageBox.critical(
                self, 
                "连接错误", 
                error_msg
            )
            # 恢复选择
            self.port_combo.blockSignals(True)
            if self.comm.port:
                index = self.port_combo.findText(self.comm.port)
                if index >= 0:
                    self.port_combo.setCurrentIndex(index)
                else:
                    self.port_combo.setCurrentIndex(-1)
            else:
                self.port_combo.setCurrentIndex(-1)
            self.port_combo.blockSignals(False)
            self.update_port_list()

    def add_pins_management_tab(self):
        """添加PIN管理Tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        pin_layout = QHBoxLayout()
        layout.addLayout(pin_layout)

        pin_label = QLabel("ADM:")
        pin_layout.addWidget(pin_label)
        self.pin_input = QLineEdit()
        self.pin_input.setMaxLength(8)
        pin_layout.addWidget(self.pin_input)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.on_pin_submit)
        pin_layout.addWidget(submit_button)

        self.tabs.addTab(tab, "PIN Management")

    # ========== 树节点点击 ==========
    def on_tree_item_clicked(self, item):
        """左侧树节点点击事件"""
        # 先清空写入区域
        for i in reversed(range(self.write_data_layout.count())):
            self.write_data_layout.itemAt(i).widget().deleteLater()

        # 获取文件路径与ADF类型
        item_text = item.text(0)
        file_path = self.tree_manager.get_file_path(item_text)
        adf_type = self.tree_manager.get_adf_type(item_text)
        self.file_path_input.setText(file_path)
        self.adf_type_input.setText(adf_type)

    # ========== 读取 SIM ==========
    def on_read_button_clicked(self):
        """点击 'Read' 按钮，后台读取"""
        logging.info("[on_read_button_clicked] 点击 'Read' 按钮，读取数据")
        self.progress_dialog = QProgressDialog("Reading SIM...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        QApplication.processEvents()

        # 后台线程执行
        self.executor.submit(self.read_data_async)



    def check_connection_before_operation(self):
        """在执行操作前检查连接状态"""
        try:
            # 简单的连接测试
            response = self.comm.send_command('AT')
            if 'OK' not in response:
                logging.warning("连接检查失败，响应: %s", response)
                return False, f"串口连接异常，响应: {response}"
            return True, "连接正常"
        except Exception as e:
            logging.error("连接检查异常: %s", e)
            return False, f"串口连接失败: {e}"

    def read_data_async(self):
        """异步读取SIM卡数据
        在后台线程中执行数据读取操作，避免阻塞UI
        读取完成后通过信号将结果传递给主线程
        """
        try:
            file_path = self.file_path_input.text().strip()
            adf_type = self.adf_type_input.text().strip()
            logging.info("开始异步读取数据: adf=%s, file=%s", adf_type, file_path)
            
            # 验证 ADF 和 EF ID 是否为空
            if not adf_type:
                logging.warning("[read_data_async] ADF 类型为空")
                self.show_message.emit("error", "请先选择或输入 ADF 类型（如 USIM、ISIM 等）")
                return
            
            if not file_path:
                logging.warning("[read_data_async] EF ID 为空")
                self.show_message.emit("error", "请先选择或输入 EF ID（如 6F07、6F06 等）")
                return
            
            # 检查连接状态
            is_connected, msg = self.check_connection_before_operation()
            if not is_connected:
                logging.error("读取前连接检查失败: %s", msg)
                self.show_message.emit("error", f"连接检查失败: {msg}\n请先选择端口并连接")
                return
            
            with self.comm_lock:
                force_raw = self.raw_checkbox.isChecked()
                data = self.sim_service.read_data(adf_type, file_path, save_single=True, force_raw=force_raw)

                if isinstance(data, str) and data.startswith("error"):
                    logging.error("读取数据失败: %s", data)
                    # 去掉"error:"前缀
                    error_msg = data[6:] if data.startswith("error:") else data
                    self.show_message.emit("error", error_msg)
                    return

            if data:
                ordered_data = [OrderedDict((key, row[key]) for key in data[0]) for row in data]
                logging.debug("数据读取成功，记录数: %d", len(ordered_data))
            else:
                ordered_data = data
                logging.warning("读取的数据为空")

            self.data_ready.emit(ordered_data)

        except Exception as e:
            error_msg = f"读取数据时出错: {e}"
            logging.error(error_msg)
            self.show_message.emit("error", error_msg)
        finally:
            QTimer.singleShot(0, self.close_progress_dialog)

    def display_read_data(self, data):
        """将读取到的数据展示到表格"""
        if not data:
            self.read_data_display.setRowCount(0)
            self.read_data_display.setColumnCount(0)
            return
    

        column_order = list(data[0].keys())  # 直接使用第一条记录的键顺序

        self.read_data_display.setRowCount(len(data))
        self.read_data_display.setColumnCount(len(column_order))
        self.read_data_display.setHorizontalHeaderLabels(column_order)  # 设置表头
        
        # 允许手动调整所有列的列宽
        header = self.read_data_display.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(len(column_order)):
            header.setSectionResizeMode(i, QHeaderView.Interactive)

        # 按照列顺序填充数据
        for row_idx, row_dict in enumerate(data):
            for col_idx, key in enumerate(column_order):
                item = QTableWidgetItem(str(row_dict.get(key, "")))  # 如果键不存在，则填充空字符串
                self.read_data_display.setItem(row_idx, col_idx, item)


        # 默认选中第一行
        self.set_default_values()

    def set_default_values(self):
        """默认选中表格第一行"""
        if self.read_data_display.rowCount() > 0:
            first_item = self.read_data_display.item(0, 0)
            if first_item:
                self.on_read_data_item_clicked(first_item)

    def on_read_data_item_clicked(self, item):
        """表格某行被点击"""
        row = item.row()
        self.selected_row = row

        # 清空写入区域
        for i in reversed(range(self.write_data_layout.count())):
            self.write_data_layout.itemAt(i).widget().deleteLater()

        data = {}
        for col in range(self.read_data_display.columnCount()):
            cell_item = self.read_data_display.item(row, col)
            if cell_item:
                key = self.read_data_display.horizontalHeaderItem(col).text()
                value = cell_item.text()
                data[key] = value

        for key, value in data.items():
            label = QLabel(key)
            input_field = QLineEdit(str(value))
            input_field.setObjectName(key)
            self.write_data_layout.addRow(label, input_field)

        return row

    # ========== 更新 SIM ==========
    def on_update_button_clicked(self):
        force_raw = self.raw_checkbox.isChecked()
        """点击 'Update' 按钮（后台执行），显示进度对话框"""
        file_path = self.file_path_input.text().strip()
        adf_type = self.adf_type_input.text().strip()
        
        # 检查是否为受保护的文件
        protected_files = ["6F66", "2F00"]
        if file_path in protected_files:
            logging.warning("[on_update_button_clicked] 不允许更新受保护的文件: %s", file_path)
            QMessageBox.warning(self, "Warning", f"不允许更新 {file_path} 文件")
            return
            
        logging.info("[on_update_button_clicked] 点击 'Update' 按钮，更新数据: file_path=%s, adf_type=%s", file_path, adf_type)
        
        if not file_path or not adf_type:
            logging.warning("[on_update_button_clicked] 无效的文件路径或ADF类型")
            QMessageBox.warning(self, "error", "无效的文件路径或 ADF 类型")
            return

        # 在 raw 模式下，不要求必须选中行（因为 raw 模式只有一行）
        if force_raw:
            # 如果没有选择行，设置为 0（对于 transparent EF，row_index 实际上不会被使用）
            if self.selected_row is None:
                self.selected_row = 0
            
            # 如果没有输入框，自动创建一个 raw_data 输入框
            if self.write_data_layout.rowCount() == 0:
                label = QLabel("raw_data")
                input_field = QLineEdit()
                input_field.setObjectName("raw_data")
                self.write_data_layout.addRow(label, input_field)
                logging.info("[on_update_button_clicked] raw 模式下自动创建输入框")
        else:
            # 非 raw 模式下，需要选中行
            if self.selected_row is None:
                logging.warning("[on_update_button_clicked] 未选择记录")
                QMessageBox.information(self, "Info", "请先选择一条记录")
                return

        # 获取写入值
        input_values = self.get_input_values()
        logging.info("[on_update_button_clicked] 用户输入值: %s", input_values)
        
        # 在 raw 模式下，检查是否有输入值
        if force_raw:
            # 在 raw 模式下，无论输入框的 label 是什么，都应该将所有输入框的值合并或使用第一个非空值
            # 因为 raw 模式下只有一个输入框，且 label 可能是解析后的字段名（如 "IMSI"）
            if 'raw_data' not in input_values:
                # 检查写入区域是否有任何输入框
                if self.write_data_layout.rowCount() > 0:
                    # 遍历所有输入框，找到第一个有值的输入框
                    found_value = False
                    for i in range(self.write_data_layout.rowCount()):
                        label_item = self.write_data_layout.itemAt(i, QFormLayout.LabelRole)
                        input_item = self.write_data_layout.itemAt(i, QFormLayout.FieldRole)
                        if label_item and input_item:
                            input_widget = input_item.widget()
                            if isinstance(input_widget, QLineEdit):
                                input_value = input_widget.text().strip()
                                if input_value:
                                    input_values['raw_data'] = input_value
                                    logging.info("[on_update_button_clicked] raw 模式下使用第 %d 个输入框的值 (label: %s): %s", 
                                                i+1, label_item.widget().text() if label_item.widget() else "unknown", input_value)
                                    found_value = True
                                    break
                    
                    # 如果所有输入框都没有值，但 input_values 中有其他键的值，也尝试使用
                    if not found_value and input_values:
                        # 使用第一个非空值
                        for key, value in input_values.items():
                            if value and str(value).strip():
                                input_values['raw_data'] = str(value).strip()
                                logging.info("[on_update_button_clicked] raw 模式下使用 input_values 中的值 (key: %s): %s", key, input_values['raw_data'])
                                found_value = True
                                break
            
            # 验证 raw_data 是否有值
            raw_data_value = input_values.get('raw_data', '').strip()
            if not raw_data_value:
                logging.warning("[on_update_button_clicked] raw 模式下 raw_data 为空，input_values: %s", input_values)
                QMessageBox.warning(self, "Warning", 
                    "Raw 模式下输入数据为空。\n\n"
                    "请直接在输入框中输入十六进制数据，或先点击 'Read' 按钮读取数据。")
                return

        # 显示进度对话框（无限滚动）
        self.progress_dialog = QProgressDialog("Writing to SIM...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        QApplication.processEvents()

        # 后台执行更新
        self.executor.submit(self.update_data_async, adf_type, file_path, input_values, force_raw)
    
    @pyqtSlot(str)
    def show_error_dialog(self, message):
        """在主线程中显示错误信息"""

        dialog = QDialog(self)
        dialog.setWindowTitle("error")

        layout = QVBoxLayout(dialog)
        label = QLabel(message)
        layout.addWidget(label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.setModal(True)
        dialog.exec_()


    def update_data_async(self, adf_type, file_path, input_values, force_raw):
        """异步更新SIM卡数据
        在后台线程中执行数据更新操作，避免阻塞UI
        更新完成后通过信号将结果传递给主线程
        """
        try:
            logging.info("开始异步更新数据: adf=%s, file=%s, values=%s", 
                        adf_type, file_path, input_values)
            
            # 检查连接状态
            is_connected, msg = self.check_connection_before_operation()
            if not is_connected:
                logging.error("更新前连接检查失败: %s", msg)
                self.show_message.emit("error", f"连接检查失败: {msg}\n请先选择端口并连接")
                return
            
            with self.comm_lock:
                result = self.sim_service.update_single_record(adf_type, file_path, 
                                                            self.selected_row, input_values, force_raw)

            if isinstance(result, str) and result.startswith("error"):
                logging.error("更新数据失败: %s", result)
                # 去掉"error:"前缀
                error_msg = result[6:] if result.startswith("error:") else result
                self.error_occurred.emit(error_msg)
            elif result == "9000":
                logging.info("file_path: %s, record_index: %s 数据更新成功", file_path, self.selected_row+1)
                self.show_message.emit("info", f"EF {file_path} record {self.selected_row+1} updated successfully!")
            elif result == "6982":
                logging.warning("需要ADM PIN验证")
                QTimer.singleShot(0, self._show_admin_code_dialog)
            elif result == "6983":
                logging.error("SIM卡已锁定")
                self.show_message.emit("warning", "SIM card blocked!")
            else:
                logging.warning("未知错误: %s", result)
                self.show_message.emit("warning", f"Unknown error => {result}")

        except Exception as e:
            error_msg = f"更新数据时发生异常: {e}"
            logging.error(error_msg)
            self.show_message.emit("error", str(e))
        finally:
            QTimer.singleShot(0, self.close_progress_dialog)

    def get_input_values(self):
        """获取写入区域里的所有输入值"""
        input_values = {}
        for i in range(self.write_data_layout.rowCount()):
            label_item = self.write_data_layout.itemAt(i, QFormLayout.LabelRole)
            input_item = self.write_data_layout.itemAt(i, QFormLayout.FieldRole)

            label_widget = label_item.widget() if label_item else None
            input_widget = input_item.widget() if input_item else None
            if isinstance(label_widget, QLabel) and isinstance(input_widget, QLineEdit):
                label_text = label_widget.text()
                input_value = input_widget.text()
                input_values[label_text] = input_value
        return input_values

    # ========== ADM PIN 提交 ==========
    def on_pin_submit(self):
        """处理ADM PIN提交
        验证用户输入的ADM PIN，并在后台线程中执行验证
        """
        admin_code = self.pin_input.text()
        logging.info("[on_pin_submit] 用户输入ADM PIN: %s", admin_code)
        if not admin_code:
            logging.warning("[on_pin_submit] ADM PIN为空")
            QMessageBox.warning(self, "Input error", "Please enter the Admin PIN.")
            return

        logging.info("[on_pin_submit] 开始验证ADM PIN")
        self.admin_thread = AdminThread(self.comm, pin=admin_code)
        self.admin_thread.result_ready.connect(self._on_admin_result)
        self.admin_thread.start()

    def _on_admin_result(self, result):
        """处理ADM PIN验证结果
        Args:
            result: 验证结果，9000表示成功，其他值表示失败
        """
        if result == "9000":
            logging.info("ADM PIN验证成功")
            QMessageBox.information(self, "Success", "Admin code verify passed.")
        else:
            if result.startswith("63C"):
                last_char = result[3]
                decimal_value = int(last_char, 16)
                logging.warning("ADM PIN验证失败，剩余重试次数: %d", decimal_value)
                QMessageBox.warning(self, "Warning",
                                    f"Admin code error. Remaining retries: {decimal_value}")
            elif result.startswith("67"):
                logging.warning("ADM PIN长度错误")
                QMessageBox.warning(self, "Warning", "Admin code length incorrect.")
            else:
                logging.error("ADM PIN验证未知错误: %s", result)
                QMessageBox.warning(self, "Warning", f"Unknown error: {result}")

    def _show_admin_code_dialog(self):
        """弹窗让用户输入Admin Code"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Input Admin Code")

        layout = QVBoxLayout(dialog)
        code_label = QLabel("Enter Admin Code:")
        layout.addWidget(code_label)

        code_input = QLineEdit(dialog)
        layout.addWidget(code_input)
        code_input.setMaxLength(8)

        confirm_button = QPushButton("Confirm", dialog)
        layout.addWidget(confirm_button)

        def on_confirm():
            admin_code = code_input.text().strip()
            if not admin_code:
                QMessageBox.warning(dialog, "Input error", "Admin code cannot be empty.")
                return
            # 再次发起验证
            self.update_thread = AdminThread(self.comm, pin=admin_code)
            self.update_thread.result_ready.connect(self._on_admin_result)
            self.update_thread.start()
            dialog.accept()

        confirm_button.clicked.connect(on_confirm)
        dialog.exec_()

    # ========== 刷新 SIM ==========
    def on_refresh_button_clicked(self):
        """刷新SIM卡"""
        progress_dialog = QProgressDialog("Refreshing SIM..., take about 20 seconds...", None, 0, 0, self)
        progress_dialog.setWindowTitle("Please Wait")
        progress_dialog.setWindowModality(Qt.ApplicationModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()

        QApplication.processEvents()  # 强制 UI 更新

        try:
            reset_sim(self.comm)
            QMessageBox.information(self, "Success", "SIM has been refreshed!")
            # file_path = self.file_path_input.text()
            # adf_type = self.adf_type_input.text()
            # if file_path and adf_type:
            #     # 如果需要读数据，可以直接再次调用 on_read_button_clicked
            #     # 或者调用 read_data_async (需额外处理进度对话框)
            #     self.read_data_async()
            #     QMessageBox.information(self, "Success", "SIM has been refreshed and data read!")
            # else:
            #     QMessageBox.information(self, "Success", "SIM has been refreshed!")
        except Exception as e:
            QMessageBox.warning(self, "error", f"Failed to refresh SIM: {e}")
        finally:
            progress_dialog.close()

    # ========== JSON 加载写入 ==========
    def on_load_json_clicked(self):
        """点击 'Load JSON' 按钮, 在后台执行"""
        logging.info("[on_load_json_clicked] 点击 'Load JSON' 按钮，加载JSON文件")
        file_dialog = QFileDialog()
        json_file, _ = file_dialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
        if not json_file:
            return

        # 先读取 JSON 文件获取总文件数
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            if not isinstance(json_data, dict) or "EF_list" not in json_data:
                QMessageBox.warning(self, "Error", "Invalid JSON format. Must have EF_list as a list.")
                return
            forbidden_efs = {"6F06", "2F06", "2F00"}
            ef_ids = {item["ef_id"].upper() for item in json_data["EF_list"] if "ef_id" in item}
            if forbidden_efs & ef_ids:
                QMessageBox.warning(
                    self,
                    "Not Allowed",
                    "JSON 文件中包含不允许写入的 EF 文件（6F06, 2F06, 2F00）。\n"
                    "请删除这些文件的内容后再重试。"
                )
                return
            total_files = len(json_data["EF_list"])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load JSON: {str(e)}")
            return

        # 创建进度对话框，显示具体进度
        self.progress_dialog = QProgressDialog("Writing JSON to SIM...", None, 0, total_files, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(Qt.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        QApplication.processEvents()

        # 后台线程加载 JSON
        self.executor.submit(self.load_json_async, json_file)

    def load_json_async(self, json_file):
        """后台解析并写入 JSON"""
        force_raw = self.raw_checkbox.isChecked()
        try:
            # 检查连接状态
            is_connected, msg = self.check_connection_before_operation()
            if not is_connected:
                logging.error("批量写入前连接检查失败: %s", msg)
                self.json_load_done.emit(False, f"连接检查失败: {msg}\n请先选择端口并连接")
                return
            
            with self.comm_lock:
                # 读取 JSON 文件获取总文件数
                with open(json_file, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                total_files = len(json_data["EF_list"])
                
                # 定义进度回调函数
                def update_progress(current):
                    self.progress_dialog.setValue(current)
                    QApplication.processEvents()
                
                # 执行写入操作，传入进度回调
                result = self.sim_service.load_and_write_from_json(json_file, progress_callback=update_progress, force_raw=force_raw)
                logging.info("load_json_async result => %s", result)

            if result == "success":
                # 更新进度到100%
                self.progress_dialog.setValue(total_files)
                # 发射成功信号
                self.json_load_done.emit(True, "JSON data written successfully.")
            else:
                self.json_load_done.emit(False, result)
        except Exception as e:
            self.json_load_done.emit(False, str(e))
        finally:
            # 关闭进度对话框
            QTimer.singleShot(0, self.close_progress_dialog)

    # 4) 主线程中处理信号，弹出框
    def on_json_load_done(self, is_success, message):
        """主线程槽函数"""
        # 这里也可以再次 close_progress_dialog()，确保对话框已经关闭
        # self.close_progress_dialog()
        if is_success:
            # 这里就可以安全地使用 QTimer.singleShot(0, lambda: ...)
            QTimer.singleShot(0, lambda:
                QMessageBox.information(self, "Success", message)
            )
        else:
            QTimer.singleShot(0, lambda:
                QMessageBox.warning(self, "error", message)
            )

    # ========== 工具函数：关闭进度对话框 ==========
    def close_progress_dialog(self):
        """关闭进度对话框（在主线程）"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    # # ========== GID删除==========
    # def on_gid_button_clicked(self, gid_type, ef_id):
    #     """处理 GID1 / GID2 按钮点击事件"""
    #     num_str, ok = QInputDialog.getText(self, f"Enter {gid_type}", "Please enter GID length(输入字节长度，非位数):")
    #     if ok:
    #         if not num_str:  # 如果输入为空，返回错误
    #             logging.warning("[on_gid_button_clicked] 用户输入为空")
    #             QMessageBox.warning(self, "Warning", "Please enter a valid number")
    #             return
    #         try:
    #             num = int(num_str)
    #             logging.info("[on_gid_button_clicked] 用户输入 %s 长度: %s", gid_type, num)
    #         except ValueError:
    #             logging.warning("[on_gid_button_clicked] 用户输入无效数字: %s", num_str)
    #             QMessageBox.warning(self, "Warning", "Please enter a valid number")
    #             return
    #         adf_type = "USIM"
    #         structure = "transparent"
    #         record_num = 1
    #         security_Attributes = ""
    #         sfi = ""
            
    #         logging.info("resize_ef参数: ef_id=%s, length=%s, adf_type=%s, structure=%s, record_num=%s, security_Attributes=%s, sfi=%s", 
    #                     ef_id, num, adf_type, structure, record_num, security_Attributes, sfi)
            
    #         result = resize_ef(self.sim_service, ef_id, num, adf_type, structure, record_num, security_Attributes, sfi)

    #         if result != "9000":
    #             logging.error("resize_ef失败: %s", result)
    #             QMessageBox.warning(self, "error", f"Failed to create EF {ef_id}: {result}")
    #         else:
    #             logging.info("resize_ef成功: %s 长度已更新为 %s", gid_type, num)
    #             QMessageBox.information(self, "Success",
    #                                 f"{gid_type} EF {ef_id} length updated to {num} !")
            
    #         # resize_ef(self, ef_id, length, adf, structure, record_num = 1, security_Attributes = "", sfi = "")

    @pyqtSlot(str, str)
    def display_message(self, message_type, message):
        """在主线程中显示信息"""
        if message_type == "info":
            QMessageBox.information(self, "Info", message)
        elif message_type == "warning":
            QMessageBox.warning(self, "Warning", message)
        elif message_type == "error":
            QMessageBox.critical(self, "error", message)

    def on_refresh_port_button_clicked(self):
        """刷新端口列表
        更新端口下拉菜单，不进行连接操作
        """
        logging.info("刷新端口列表")
        try:
            # 直接调用更新端口列表方法
            self.update_port_list()
            # 显示提示信息
            port_count = self.port_combo.count()
            if port_count > 1:  # 大于1是因为有占位项
                QMessageBox.information(
                    self, 
                    "刷新完成", 
                    f"端口列表已刷新\n发现 {port_count - 1} 个可用端口"
                )
            else:
                QMessageBox.information(
                    self, 
                    "刷新完成", 
                    "端口列表已刷新\n未发现可用端口"
                )
        except Exception as e:
            error_msg = f"刷新端口列表失败: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def on_psim_button_clicked(self):
        """切换到pSIM
        尝试使用AT+ESUO=4或AT$QCSIMAPP=0命令切换到pSIM
        """
        try:
            logging.info("开始切换到pSIM")
            response = self.comm.send_command('AT+ESUO=4')
            logging.debug("AT+ESUO=4响应: %s", response)
            time.sleep(1)
            
            if "OK" in response:
                logging.info("成功切换到pSIM")
                QMessageBox.information(self, "Success", "Successfully switched to pSIM")
                return
                
            logging.info("AT+ESUO=4失败，尝试AT$QCSIMAPP=0")
            response = self.comm.send_command('AT$QCSIMAPP=0')
            logging.debug("AT$QCSIMAPP=0响应: %s", response)
            time.sleep(1)
            
            if "OK" in response:
                logging.info("成功切换到pSIM")
                QMessageBox.information(self, "Success", "Successfully switched to pSIM")
            else:
                logging.error("切换到pSIM失败: %s", response)
                QMessageBox.warning(self, "Error", f"Failed to switch to pSIM: {response}")
        except Exception as e:
            error_msg = f"切换到pSIM时发生异常: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def on_esim_button_clicked(self):
        """切换到eSIM
        尝试使用AT+ESUO=5或AT$QCSIMAPP=1命令切换到eSIM
        """
        try:
            logging.info("开始切换到eSIM")
            response = self.comm.send_command('AT+ESUO=5')
            logging.debug("AT+ESUO=5响应: %s", response)
            time.sleep(1)
            
            if "OK" in response:
                logging.info("成功切换到eSIM")
                QMessageBox.information(self, "Success", "Successfully switched to eSIM")
                return
                
            logging.info("AT+ESUO=5失败，尝试AT$QCSIMAPP=1")
            response = self.comm.send_command('AT$QCSIMAPP=1')
            logging.debug("AT$QCSIMAPP=1响应: %s", response)
            time.sleep(1)
            
            if "OK" in response:
                logging.info("成功切换到eSIM")
                QMessageBox.information(self, "Success", "Successfully switched to eSIM")
            else:
                logging.error("切换到eSIM失败: %s", response)
                QMessageBox.warning(self, "Error", f"Failed to switch to eSIM: {response}")
        except Exception as e:
            error_msg = f"切换到eSIM时发生异常: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)


# ========== 程序入口 ==========
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = SimEditorUI()
    w.show()
    sys.exit(app.exec_())
