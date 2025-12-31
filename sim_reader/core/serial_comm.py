import serial
import re
from serial.tools import list_ports
import time
import logging
from PySide6.QtWidgets import QMessageBox
from core.utils import handle_exception
from threading import Lock
from typing import Tuple
  

class SerialComm:
    """
    串口通信管理类，实现单例模式
    负责处理与SIM卡读卡器的串口通信，包括端口检测、命令发送和响应接收
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SerialComm, cls).__new__(cls)
        return cls._instance

    def __init__(self, baudrate=115200, timeout=1):  
        if not hasattr(self, 'initialized'):
            self.baudrate = baudrate
            self.timeout = timeout
            self.ser = None
            self.port = None
            self._io_lock = Lock()
            self.busy = False
            self._last_tx = 0
            self._consecutive_timeouts = 0
            # AT 命令最小间隔（RX -> 下一次 TX），用于缓解部分模组/SIM在 OK 后的“收尾时间”
            self._min_command_gap_ms = 0
            self._last_rx_mono = 0.0
            self.initialized = False

    def set_min_command_gap_ms(self, ms: int):
        """设置 AT 命令最小间隔（毫秒）。0 表示不做节流。"""
        try:
            ms_int = int(ms)
        except Exception:
            ms_int = 0
        if ms_int < 0:
            ms_int = 0
        # 上限做个保护，避免误配导致“看起来卡死”
        if ms_int > 10_000:
            ms_int = 10_000
        self._min_command_gap_ms = ms_int
        logging.info("[AT][CFG] min_command_gap_ms=%d", self._min_command_gap_ms)

    def get_min_command_gap_ms(self) -> int:
        return int(getattr(self, "_min_command_gap_ms", 0) or 0)

    def initialize(self, show_popup=True) -> bool:
        """
        初始化串口连接，尝试找到并打开支持 AT 命令的端口
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        logging.debug("正在初始化串口通信模块...")
        self.port = self._find_port()
        if not self.port or self.port.startswith("error:"):
            logging.error("初始化失败：未找到支持AT命令的COM口")
            if show_popup:
                QMessageBox.critical(None, "错误", "未找到支持AT命令的COM口", QMessageBox.StandardButton.Ok)
            return False

        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self.initialized = True
            logging.info("串口连接成功：%s", self.port)
            return True
        except Exception as e:
            logging.error("串口打开失败：%s", e)
            if show_popup:
                QMessageBox.critical(None, "错误", f"串口打开失败: {e}", QMessageBox.StandardButton.Ok)
            return False




    def get_all_ports(self):
        """
        获取系统中所有可用的串口列表
        Returns:
            list: 可用串口设备名称列表
        """
        return [port.device for port in list_ports.comports()]

    def test_port(self, port):
        """
        测试指定串口是否支持AT命令
        Args:
            port (str): 要测试的串口设备名称
        Returns:
            bool: 如果端口支持AT命令返回True，否则返回False
        """
        test_ser = None
        if self.ser and self.ser.is_open and self.port == port:
            logging.debug("test_port: 端口 %s 已被当前实例使用，跳过测试", port)
            return True
        try:
            test_ser = serial.Serial(
                port=port, 
                baudrate=115200, 
                timeout=1.0,      
                write_timeout=1.0  
            )
            time.sleep(0.2)
            test_ser.reset_input_buffer()
            test_ser.reset_output_buffer()
            test_ser.write(b'ATE0\r\n')
            time.sleep(0.2)  
            response = test_ser.read_all()
            
            if b'OK' in response:
                try:
                    response_str = response.decode(errors='ignore')
                except Exception:
                    response_str = str(response)
                lines = [line.strip() for line in response_str.splitlines()]
                if 'OK' in lines:        
                    return True
                elif len(response_str) < 10:                        
                    return True
            return False
        except Exception as e:
            logging.error("端口测试失败 [%s]: %s", port, str(e))
            return False
        finally:
            if test_ser and test_ser.is_open:
                test_ser.close()
                time.sleep(0.1)
    
    def _find_port(self):
        """
        自动扫描并查找支持AT命令的串口
        Returns:
            str: 找到的串口设备名称，如果未找到则返回错误信息
        """
        ports = list_ports.comports()
        logging.debug("发现可用串口: %s", [port.device for port in ports])
        found_port = None
       
        for port in ports:
            if self.test_port(port.device):
                found_port = port.device
                break
                    
        if not found_port:
            logging.error("未找到支持AT命令的串口设备")
            return "error: no available port"
            
        return found_port
    
    def switch_port(self, new_port):
        """
        切换到新的串口设备
        Args:
            new_port (str): 新的串口设备名称
        Returns:
            bool: 切换成功返回True，失败返回False
        """
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        try:
            self.ser = serial.Serial(port=new_port, baudrate=115200, timeout=1)
            self.port = new_port
            logging.info("串口切换成功: %s", new_port)
            return True
        except Exception as e:
            logging.error("串口切换失败 [%s]: %s", new_port, str(e))
            return False

    @handle_exception
    def send_command(
        self,
        command: str,
        *,
        wait_timeout_s: float = 2.2,
        max_retries: int = 1,
        retry_backoff_s: float = 0.2,
        reconnect_on_fail: bool = True
    ):
        """
        发送 AT 命令并返回响应。
        内部使用互斥锁 + busy 标志，确保与健康探测不冲突。

        可靠性策略：
        - 若在 wait_timeout_s 内未收到 OK/ERROR：返回明确的 error: timeout
        - 对“读类/查询类”指令允许重发（max_retries）
        - 对“写类 APDU”默认不重发，避免非幂等导致的不确定写入；只尝试重连后返回错误
        """
        with self._io_lock:          # ***** 串口访问全程互斥 *****
            self.busy = True
            try:
                if not (self.ser and self.ser.is_open):
                    logging.error("串口未打开，无法发送命令")
                    return "error: serial port not opened"

                is_write_like = self._is_write_like_command(command)
                retries_allowed = (not is_write_like)

                attempt = 0
                while True:
                    attempt += 1

                    # 轻量恢复：清掉残留数据，避免上一次的回包污染本次解析
                    self._reset_buffers_safely()

                    try:
                        # === 命令节流：保证 RX -> 下一次 TX 至少间隔 N ms ===
                        gap_ms = self.get_min_command_gap_ms()
                        if gap_ms > 0 and self._last_rx_mono:
                            now = time.monotonic()
                            delta_ms = int((now - self._last_rx_mono) * 1000)
                            sleep_ms = gap_ms - delta_ms
                            if sleep_ms > 0:
                                time.sleep(sleep_ms / 1000.0)
                                logging.debug("[AT][GAP] sleep_ms=%d", sleep_ms)

                        tx_t0 = time.monotonic()
                        # TX 日志必须在 write 之前/附近打印，保证时间戳代表“真实发送时刻”
                        logging.debug("[AT][TX] %s", command)
                        self.ser.write((command + "\r\n").encode())
                    except Exception as e:
                        logging.error("串口写入失败: %s", e)
                        if reconnect_on_fail:
                            self._reconnect_locked(reason=f"serial write failed: {e}")
                        if attempt <= max_retries and retries_allowed:
                            time.sleep(retry_backoff_s * attempt)
                            continue
                        return f"error: serial write failed => {e}"

                    # 读取响应直到 OK/ERROR 或超时
                    raw_response, complete, polls = self._read_until_ok_error(wait_timeout_s)
                    rx_t1 = time.monotonic()
                    elapsed_ms = int((rx_t1 - tx_t0) * 1000)
                    # 记录“最后一次 RX 完成时刻”，用于下一条命令节流
                    self._last_rx_mono = rx_t1
                    # RX 日志：时间戳代表“真实接收完成时刻”；内容尽量单行，避免多行造成“重复打印”的错觉
                    logging.debug(
                        "[AT][RX] ok=%s elapsed_ms=%d polls=%d resp=%r",
                        complete, elapsed_ms, polls, raw_response
                    )

                    if not complete:
                        self._consecutive_timeouts += 1
                        logging.warning(
                            "等待响应超时: attempt=%d/%d, write_like=%s, consecutive_timeouts=%d",
                            attempt, max_retries + 1, is_write_like, self._consecutive_timeouts
                        )

                        # 对写类指令：不重发，最多重连一次然后返回错误（让上层做 read-back/校验）
                        if reconnect_on_fail and (is_write_like or self._consecutive_timeouts >= 2):
                            self._reconnect_locked(reason="timeout waiting OK/ERROR")

                        if attempt <= max_retries and retries_allowed:
                            time.sleep(retry_backoff_s * attempt)
                            continue

                        return f"error: timeout waiting response ({attempt}/{max_retries + 1})"

                    # 收到了 OK/ERROR，认为链路恢复
                    self._consecutive_timeouts = 0

                    # === 提取有效数据（沿用旧正则） ===
                    pattern = r'\+(?:CGLA|CSIM): \d+,"([0-9A-Fa-f]+)"'
                    match = re.search(pattern, raw_response)
                    if match:
                        response = match.group(1)
                        # 处理 61xx 继续读取的场景（GET RESPONSE，本质是读类）
                        if response.startswith("61") and len(response) == 4:
                            add_len_hex = response[2:]  # 两位 16 进制长度

                            match_cgla_data = re.search(r'AT\+CSIM=\d+,"([0-9A-Fa-f]+)"', command)
                            if match_cgla_data:
                                payload = match_cgla_data.group(1)
                                if payload.startswith("01"):
                                    add_cmd = f'AT+CSIM=10,"01C00000{add_len_hex}"'
                                else:
                                    add_cmd = f'AT+CSIM=10,"00C00000{add_len_hex}"'
                            else:
                                logging.warning("未能提取 CSIM payload，GET RESPONSE 默认使用00开头")
                                add_cmd = f'AT+CSIM=10,"00C00000{add_len_hex}"'

                            logging.debug("二次发送 GET RESPONSE: %s", add_cmd)

                            self._reset_buffers_safely()
                            tx2_t0 = time.monotonic()
                            logging.debug("[AT][TX] %s", add_cmd)
                            self.ser.write((add_cmd + "\r\n").encode())
                            add_raw, add_complete, add_polls = self._read_until_ok_error(wait_timeout_s)
                            tx2_t1 = time.monotonic()
                            add_elapsed_ms = int((tx2_t1 - tx2_t0) * 1000)
                            logging.debug(
                                "[AT][RX] ok=%s elapsed_ms=%d polls=%d resp=%r",
                                add_complete, add_elapsed_ms, add_polls, add_raw
                            )

                            if not add_complete:
                                if reconnect_on_fail:
                                    self._reconnect_locked(reason="timeout waiting GET RESPONSE")
                                return "error: timeout waiting GET RESPONSE"

                            add_match = re.search(pattern, add_raw)
                            if add_match:
                                response = add_match.group(1)
                            else:
                                logging.error("[61xx] GET RESPONSE 未匹配到数据，收到: %s", add_raw)
                                response = f"error: GET RESPONSE failed ({add_raw.strip()})"
                        return response

                    # 非 +CSIM/+CGLA 场景（例如 AT），原样返回
                    return raw_response.strip()
            finally:
                self._last_tx = time.time()   # ★ 先记录业务完成时刻
                self.busy = False     # ***** 无论成功失败都要复位 *****

    def _reset_buffers_safely(self):
        """尽力清空串口缓冲，避免旧回包污染；失败也不影响主流程。"""
        try:
            if self.ser:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
        except Exception:
            pass

    def _read_until_ok_error(self, wait_timeout_s: float) -> Tuple[str, bool, int]:
        """
        在 wait_timeout_s 内读取串口，直到回包中出现 OK 或 ERROR。
        Returns:
            (raw_response, complete, polls)
        """
        raw_response = ""
        deadline = time.monotonic() + max(0.1, float(wait_timeout_s))
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            time.sleep(0.1)
            try:
                chunk = self.ser.read_all().decode("utf-8", errors="ignore")
            except Exception:
                chunk = ""
            if chunk:
                raw_response += chunk
                if "OK" in chunk or "ERROR" in chunk or "OK\r" in raw_response or "ERROR\r" in raw_response:
                    return raw_response, True, attempt
            # 注意：这里不再每轮打印“等待响应”，避免日志刷屏/重复感
        return raw_response, False, attempt

    def _is_write_like_command(self, command: str) -> bool:
        """
        粗略判断是否为“写类/非幂等”指令：
        - AT+CSIM/AT+CGLA 内的 APDU INS 属于 UPDATE/WRITE 类
        """
        try:
            m = re.search(r'AT\+(?:CSIM|CGLA)=[^"]*"([0-9A-Fa-f]+)"', command)
            if not m:
                return False
            apdu_hex = m.group(1)
            if len(apdu_hex) < 4:
                return False
            ins = apdu_hex[2:4].upper()
            # 常见写类 INS：D6(UPDATE BINARY), DC(UPDATE RECORD), E2(ERASE BINARY, 少见), D0/DA(WRITE)
            return ins in {"D6", "DC", "E2", "D0", "DA"}
        except Exception:
            return False

    def _reconnect_locked(self, reason: str = "") -> bool:
        """
        在已持有 _io_lock 的前提下重连。
        策略：优先重开当前 port；失败再扫描 _find_port()。
        """
        logging.warning("触发串口重连: %s", reason)
        try:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
            time.sleep(0.2)
            # 重连后重置节流参考点
            self._last_rx_mono = 0.0

            # 优先重开当前端口
            if self.port:
                try:
                    self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
                    logging.info("串口重开成功: %s", self.port)
                    return True
                except Exception as e:
                    logging.warning("串口重开失败(%s)，将尝试重新扫描: %s", self.port, e)

            new_port = self._find_port()
            if "error" in new_port:
                logging.error("重连失败：未找到可用AT端口")
                return False
            self.port = new_port
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            logging.info("串口重连成功: %s", self.port)
            return True
        except Exception as e:
            logging.error("串口重连异常: %s", e)
            return False
        

            
    def reconnect(self):
        """
        重新扫描并建立串口连接
        Raises:
            Exception: 当未找到可用AT端口时抛出异常
        """
        # 注意：对外接口需要自己持锁，避免与 send_command 并发
        with self._io_lock:
            ok = self._reconnect_locked(reason="manual reconnect() called")
            if not ok:
                raise Exception("未找到可用的AT串口设备")
    
    def close(self):
        """关闭串口连接"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                logging.info("串口连接已关闭")
            # 重置状态
            self.initialized = False
            self.port = None
        except Exception as e:
            logging.error(f"关闭串口时出错: {e}") 

    def is_port_alive(self) -> bool:
        """
        简化的端口健康检测：
        · 句柄关闭            → False
        · 正在业务 (busy)     → True   (避免插队)
        · 其他情况            → True   (假设连接正常，避免误报)
        
        注意：此方法已简化，不再进行主动探活，避免频繁的误报重连
        """
        if not (self.ser and self.ser.is_open):
            return False
        if self.busy:
            return True
        
        # 简化逻辑：只要串口打开且不忙，就认为连接正常
        # 实际的连接检测将在执行操作前进行
        return True
