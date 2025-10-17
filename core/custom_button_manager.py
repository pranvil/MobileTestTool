#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义按钮配置管理器
支持用户自定义多种类型的按钮：ADB命令、Python脚本、文件操作等
"""

import os
import json
import datetime
import subprocess
import sys
from PyQt5.QtCore import QObject, pyqtSignal
from core.debug_logger import logger


class CustomButtonManager(QObject):
    """自定义按钮配置管理器"""
    
    # 信号定义
    buttons_updated = pyqtSignal()  # 按钮配置更新
    
    # 按钮类型
    BUTTON_TYPES = {
        'adb': 'ADB命令',
        'python': 'Python脚本',
        'file': '打开文件',
        'program': '运行程序',
        'system': '系统命令'
    }
    
    # 命令黑名单：不允许的持续输出命令
    BLOCKED_COMMANDS = {
        'logcat': '请使用"Log过滤"功能',
        'tcpdump': '请使用"Log控制"标签页的tcpdump功能',
        'ping': '请使用"Network信息"标签页的ping功能',
        'top': '此命令会持续输出，不支持',
        'getevent': '此命令会持续输出，不支持',
        'monkey': '此命令会持续输出，不支持'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.expanduser("~/.netui/custom_buttons.json")
        self.buttons = []
        self.load_buttons()
    
    def load_buttons(self):
        """加载按钮配置"""
        try:
            if os.path.exists(self.config_file):
                # 使用 utf-8-sig 编码来正确处理BOM
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    self.buttons = data.get('custom_buttons', [])
                    logger.info(f"成功加载 {len(self.buttons)} 个自定义按钮")
            else:
                # 创建默认配置
                self.buttons = self._create_default_buttons()
                self.save_buttons()
                logger.info("创建默认自定义按钮配置")
        except Exception as e:
            logger.exception(f"加载自定义按钮配置失败: {e}")
            # 如果配置文件损坏，创建默认配置
            logger.info("尝试创建默认配置...")
            self.buttons = self._create_default_buttons()
            self.save_buttons()
    
    def save_buttons(self):
        """保存按钮配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            data = {
                'custom_buttons': self.buttons,
                'version': '1.0'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(self.buttons)} 个自定义按钮配置")
            self.buttons_updated.emit()
            return True
            
        except Exception as e:
            logger.exception(f"保存自定义按钮配置失败: {e}")
            return False
    
    def _create_default_buttons(self):
        """创建默认按钮示例"""
        return [
            {
                'id': 'default_001',
                'name': '查看设备属性',
                'type': 'adb',
                'command': 'shell getprop',
                'tab': '其他',
                'card': '其他操作',
                'enabled': True,
                'description': '查看设备的所有系统属性'
            },
            {
                'id': 'default_002',
                'name': '查看存储空间',
                'type': 'adb',
                'command': 'shell df -h',
                'tab': '其他',
                'card': '设备信息',
                'enabled': True,
                'description': '查看设备存储空间使用情况'
            }
        ]
    
    def get_all_buttons(self):
        """获取所有按钮"""
        return self.buttons
    
    def get_buttons_by_location(self, tab_name, card_name):
        """根据Tab和Card获取按钮列表"""
        return [
            btn for btn in self.buttons 
            if btn.get('enabled', True) and 
               btn.get('tab') == tab_name and 
               btn.get('card') == card_name
        ]
    
    def get_available_tabs(self):
        """获取可用的Tab列表"""
        return [
            'Log控制',
            'Log过滤',
            '网络信息',
            'TMO CC',
            'TMO Echolocate',
            '24小时背景数据',
            'APP操作',
            '其他'
        ]
    
    def get_available_cards(self, tab_name):
        """获取指定Tab下可用的Card列表"""
        cards_map = {
            'Log控制': ['MTKLOG 控制', 'ADB Log 控制'],
            'Log过滤': ['过滤控制'],
            '网络信息': ['控制', '网络信息'],
            'TMO CC': ['CC配置', '过滤操作'],
            'TMO Echolocate': ['Echolocate 操作', '过滤操作'],
            '24小时背景数据': ['24小时背景数据操作'],
            'APP操作': ['查询操作', 'APK操作', '进程操作', 'APP状态操作'],
            '其他': ['设备信息', '赫拉配置', '其他操作', 'log操作']
        }
        return cards_map.get(tab_name, ['默认'])
    
    def add_button(self, button_data):
        """添加按钮"""
        try:
            # 生成ID
            if 'id' not in button_data:
                button_data['id'] = f"custom_{len(self.buttons) + 1:03d}"
            
            # 验证必填字段
            if not button_data.get('name'):
                logger.error("按钮名称不能为空")
                return False
            
            # 对于非Python脚本类型，验证命令字段
            button_type = button_data.get('type', 'adb')
            if button_type != 'python' and not button_data.get('command'):
                logger.error("命令不能为空")
                return False
            
            # 验证命令安全性（仅对ADB命令类型）
            if button_type == 'adb' and not self.validate_command(button_data.get('command', '')):
                logger.error("ADB命令包含不允许的内容")
                return False
            
            self.buttons.append(button_data)
            return self.save_buttons()
            
        except Exception as e:
            logger.exception(f"添加按钮失败: {e}")
            return False
    
    def update_button(self, button_id, button_data):
        """更新按钮"""
        try:
            for i, btn in enumerate(self.buttons):
                if btn['id'] == button_id:
                    # 根据按钮类型进行不同的验证
                    button_type = button_data.get('type', 'adb')
                    
                    # 验证命令安全性（仅对ADB命令类型）
                    if button_type == 'adb' and not self.validate_command(button_data.get('command', '')):
                        logger.error("ADB命令包含不允许的内容")
                        return False
                    
                    # 保留ID
                    button_data['id'] = button_id
                    self.buttons[i] = button_data
                    return self.save_buttons()
            
            logger.error(f"未找到ID为 {button_id} 的按钮")
            return False
            
        except Exception as e:
            logger.exception(f"更新按钮失败: {e}")
            return False
    
    def delete_button(self, button_id):
        """删除按钮"""
        try:
            self.buttons = [btn for btn in self.buttons if btn['id'] != button_id]
            return self.save_buttons()
            
        except Exception as e:
            logger.exception(f"删除按钮失败: {e}")
            return False
    
    def validate_command(self, command):
        """验证命令是否安全"""
        if not command or not command.strip():
            return False
        
        # 清理命令：如果用户输入了"adb"开头，需要去掉
        clean_command = command.strip()
        if clean_command.lower().startswith('adb '):
            clean_command = clean_command[4:].strip()
        
        # 检查黑名单命令
        cmd_lower = clean_command.lower()
        for blocked_cmd in self.BLOCKED_COMMANDS.keys():
            if blocked_cmd in cmd_lower:
                return False
        
        return True
    
    def get_blocked_reason(self, command):
        """获取命令被阻止的原因"""
        # 清理命令：如果用户输入了"adb"开头，需要去掉
        clean_command = command.strip()
        if clean_command.lower().startswith('adb '):
            clean_command = clean_command[4:].strip()
        
        cmd_lower = clean_command.lower()
        for blocked_cmd, reason in self.BLOCKED_COMMANDS.items():
            if blocked_cmd in cmd_lower:
                return reason
        return None
    
    def import_buttons(self, file_path):
        """从文件导入按钮配置"""
        try:
            # 尝试不同的编码方式
            encodings = ['utf-8-sig', 'utf-8', 'gbk']
            data = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                        break
                except UnicodeDecodeError:
                    continue
            
            if data is None:
                logger.error(f"无法读取文件 {file_path}，尝试了多种编码")
                return False
            
            imported_buttons = data.get('custom_buttons', [])
            
            # 合并按钮（避免ID冲突）
            existing_ids = {btn['id'] for btn in self.buttons}
            for btn in imported_buttons:
                if btn['id'] in existing_ids:
                    # 重新生成ID
                    btn['id'] = f"imported_{len(self.buttons) + 1:03d}"
                self.buttons.append(btn)
            
            return self.save_buttons()
                
        except Exception as e:
            logger.exception(f"导入按钮配置失败: {e}")
            return False
    
    def export_buttons(self, file_path):
        """导出按钮配置到文件"""
        try:
            data = {
                'custom_buttons': self.buttons,
                'version': '1.0',
                'export_time': datetime.datetime.now().isoformat(),
                'export_note': '用户自定义按钮配置导出'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出按钮配置到: {file_path}")
            return True
            
        except Exception as e:
            logger.exception(f"导出按钮配置失败: {e}")
            return False
    
    def backup_config(self, backup_path=None):
        """备份当前配置到指定路径"""
        try:
            if backup_path is None:
                backup_path = os.path.join(os.path.dirname(self.config_file), "custom_buttons_backup.json")
            
            data = {
                'custom_buttons': self.buttons,
                'version': '1.0',
                'backup_time': datetime.datetime.now().isoformat(),
                'backup_note': '用户自定义按钮配置备份'
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已备份到: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.exception(f"备份配置失败: {e}")
            return None
    
    def restore_config(self, backup_path):
        """从备份文件恢复配置"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 使用多种编码尝试读取
            encodings = ['utf-8-sig', 'utf-8', 'gbk']
            data = None
            
            for encoding in encodings:
                try:
                    with open(backup_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                        break
                except UnicodeDecodeError:
                    continue
            
            if data is None:
                logger.error(f"无法读取备份文件: {backup_path}")
                return False
            
            # 恢复按钮配置
            self.buttons = data.get('custom_buttons', [])
            
            # 保存到当前配置文件
            success = self.save_buttons()
            if success:
                logger.info(f"配置已从备份恢复: {backup_path}")
                logger.info(f"恢复了 {len(self.buttons)} 个自定义按钮")
            
            return success
            
        except Exception as e:
            logger.exception(f"恢复配置失败: {e}")
            return False
    
    def get_config_info(self):
        """获取配置信息"""
        return {
            'button_count': len(self.buttons),
            'config_file': self.config_file,
            'buttons': [
                {
                    'name': btn.get('name', ''),
                    'command': btn.get('command', ''),
                    'tab': btn.get('tab', ''),
                    'card': btn.get('card', ''),
                    'enabled': btn.get('enabled', True)
                }
                for btn in self.buttons
            ]
        }
    
    def execute_button_command(self, button_data, device_id=None):
        """执行按钮命令（支持多种类型）"""
        try:
            button_type = button_data.get('type', 'adb')
            command = button_data.get('command', '')
            
            if button_type == 'adb':
                return self._execute_adb_command(command, device_id)
            elif button_type == 'python':
                # Python脚本使用script字段，而不是command字段
                script_code = button_data.get('script', '')
                if not script_code:
                    return False, "Python脚本内容为空"
                return self._execute_python_script(script_code)
            elif button_type == 'file':
                return self._open_file(command)
            elif button_type == 'program':
                return self._run_program(command)
            elif button_type == 'system':
                return self._execute_system_command(command)
            else:
                logger.error(f"不支持的按钮类型: {button_type}")
                return False, f"不支持的按钮类型: {button_type}"
                
        except Exception as e:
            logger.exception(f"执行按钮命令失败: {e}")
            return False, str(e)
    
    def _execute_adb_command(self, command, device_id):
        """执行ADB命令"""
        if not device_id:
            return False, "未选择设备"
        
        # 清理命令格式
        clean_command = command.strip()
        if clean_command.lower().startswith('adb '):
            clean_command = clean_command[4:].strip()
        
        # 构建完整命令
        full_command = f"adb -s {device_id} {clean_command}"
        
        try:
            result = subprocess.run(
                full_command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout if result.stdout else result.stderr
            success = result.returncode == 0
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except Exception as e:
            return False, f"执行失败: {str(e)}"
    
    def _execute_python_script(self, script_code):
        """执行Python脚本"""
        try:
            import io
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            
            # 创建安全的执行环境
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sorted': sorted,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'type': type,
                    'isinstance': isinstance,
                    'hasattr': hasattr,
                    'getattr': getattr,
                    'setattr': setattr,
                    'dir': dir,
                    'help': help,
                    'datetime': __import__('datetime'),
                    'platform': __import__('platform'),
                    'os': __import__('os'),
                    'json': __import__('json'),
                    'math': __import__('math'),
                    'random': __import__('random'),
                    'time': __import__('time'),
                }
            }
            
            safe_locals = {}
            
            # 捕获输出
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            try:
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # 执行脚本
                    exec(script_code, safe_globals, safe_locals)
                
                # 获取输出结果
                stdout_output = output_buffer.getvalue()
                stderr_output = error_buffer.getvalue()
                
                # 组合输出结果
                result_output = ""
                if stdout_output:
                    result_output += f"输出:\n{stdout_output}"
                if stderr_output:
                    result_output += f"\n错误:\n{stderr_output}"
                
                if result_output:
                    return True, result_output
                else:
                    return True, "Python脚本执行完成（无输出）"
                    
            except Exception as exec_error:
                # 如果执行过程中出错，返回错误信息
                return False, f"Python脚本执行错误: {str(exec_error)}"
            
        except Exception as e:
            return False, f"Python脚本执行失败: {str(e)}"
    
    def _open_file(self, file_path):
        """打开文件或文件夹"""
        try:
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            
            return True, f"已打开: {file_path}"
            
        except Exception as e:
            return False, f"打开文件失败: {str(e)}"
    
    def _run_program(self, program_path):
        """运行程序"""
        try:
            if os.path.exists(program_path):
                subprocess.Popen([program_path])
                return True, f"已启动程序: {program_path}"
            else:
                return False, f"程序不存在: {program_path}"
                
        except Exception as e:
            return False, f"运行程序失败: {str(e)}"
    
    def _execute_system_command(self, command):
        """执行系统命令"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout if result.stdout else result.stderr
            success = result.returncode == 0
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except Exception as e:
            return False, f"执行失败: {str(e)}"

