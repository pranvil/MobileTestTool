import serial
import re
from serial.tools import list_ports
import time
import logging
from PyQt5.QtWidgets import QMessageBox
from core.utils import handle_exception
from threading import Lock
  

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
            self.initialized = False

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
                QMessageBox.critical(None, "错误", "未找到支持AT命令的COM口", QMessageBox.Ok)
            return False

        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self.initialized = True
            logging.info("串口连接成功：%s", self.port)
            return True
        except Exception as e:
            logging.error("串口打开失败：%s", e)
            if show_popup:
                QMessageBox.critical(None, "错误", f"串口打开失败: {e}", QMessageBox.Ok)
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
    def send_command(self, command: str):
        """
        发送 AT 命令并返回响应。
        内部使用互斥锁 + busy 标志，确保与健康探测不冲突。
        """
        with self._io_lock:          # ***** 串口访问全程互斥 *****
            self.busy = True
            try:
                if not (self.ser and self.ser.is_open):
                    logging.error("串口未打开，无法发送命令")
                    return "error: serial port not opened"

                # 清空残留数据并发送
                # self.ser.reset_input_buffer()
                self.ser.write((command + '\r\n').encode())
                time.sleep(0.1)

                # === 读取响应（保留你原来的 max_attempts 逻辑） ===
                max_attempts = 20
                attempt = 0
                raw_response = ""

                while attempt < max_attempts:
                    time.sleep(0.1)
                    chunk = self.ser.read_all().decode('utf-8', errors='ignore')
                    if chunk:
                        raw_response += chunk
                        # 一旦看到 OK/ERROR 就结束
                        if "OK" in chunk or "ERROR" in chunk:
                            break
                    attempt += 1
                    logging.debug("等待响应，尝试次数: %d/%d", attempt, max_attempts)

                logging.debug("发送命令: %s", command)
                logging.debug("原始响应: %s", raw_response)

                # === 提取有效数据（沿用旧正则） ===
                pattern = r'\+(?:CGLA|CSIM): \d+,"([0-9A-Fa-f]+)"'
                match = re.search(pattern, raw_response)
                if match:
                    response = match.group(1)
                    # 处理 61xx 继续读取的场景
                    if response.startswith("61") and len(response) == 4:
                        add_len_hex = response[2:]  # 两位 16 进制长度

                        # 判断主命令 payload 前缀是 01 还是 00
                        # match_cgla_data = re.search(r'AT\+CGLA=\d+,\d+,"([0-9A-Fa-f]+)"', command)
                        match_cgla_data = re.search(r'AT\+CSIM=\d+,"([0-9A-Fa-f]+)"', command)
                        if match_cgla_data:
                            payload = match_cgla_data.group(1)
                            if payload.startswith("01"):
                                add_cmd = f'AT+CSIM=10,"01C00000{add_len_hex}"'
                            else:
                                add_cmd = f'AT+CSIM=10,"00C00000{add_len_hex}"'
                        else:
                            # 回退默认使用00（保底处理）
                            logging.warning("未能提取 CGLA payload，默认使用00开头")
                            add_cmd = f'AT+CSIM=10,"00C00000{add_len_hex}"'
                        logging.debug("二次发送命令: %s, %s", command, add_cmd)
                        self.ser.write((add_cmd + '\r\n').encode())

                        # 3) 循环读取，直到收齐 “OK/ERROR” 为止（最久 2 s）
                        add_raw = ""
                        for _ in range(20):                 # 20 × 0.1 s = 2 s
                            time.sleep(0.1)
                            chunk = self.ser.read_all().decode('utf-8', errors='ignore')
                            if chunk:
                                add_raw += chunk
                                if "OK" in chunk or "ERROR" in chunk:
                                    break

                        logging.debug("二次 GET RESPONSE 原始: %s", add_raw)

                        # 4) 提取真正数据
                        add_match = re.search(pattern, add_raw)
                        if add_match:
                            response = add_match.group(1)
                        else:
                            logging.error("[61xx] GET RESPONSE 未匹配到数据，收到: %s", add_raw)
                            response = f"error: GET RESPONSE failed ({add_raw.strip()})"
                else:
                    response = raw_response.strip()
                return response
            finally:
                self._last_tx = time.time()   # ★ 先记录业务完成时刻
                self.busy = False     # ***** 无论成功失败都要复位 *****
        

            
    def reconnect(self):
        """
        重新扫描并建立串口连接
        Raises:
            Exception: 当未找到可用AT端口时抛出异常
        """
        logging.info("正在尝试重新建立串口连接...")
        if self.ser and self.ser.is_open:
            self.ser.close()
            logging.info("已关闭当前串口连接")

        new_port = self._find_port()
        if "error" in new_port:
            raise Exception("未找到可用的AT串口设备")
        
        self.port = new_port
        self.ser = serial.Serial(port=self.port, baudrate=115200, timeout=1)
        logging.info("串口重连成功: %s", self.port)
    
    def close(self):
        """关闭串口连接"""
        if self.ser.is_open:
            self.ser.close()
            logging.info("串口连接已关闭") 

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
