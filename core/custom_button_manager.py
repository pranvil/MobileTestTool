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
from PySide6.QtCore import QObject, Signal
from core.debug_logger import logger


class CustomButtonManager(QObject):
    """自定义按钮配置管理器"""
    
    # 信号定义
    buttons_updated = Signal()  # 按钮配置更新
    # 对话框相关信号（用于脚本中的UI调用）
    dialog_request = Signal(str, str, str, int, int, object)  # dialog_type, title, message, buttons, default_button, response_handler
    dialog_response = Signal(int)  # button_clicked (QMessageBox.StandardButton.Yes/No等)
    
    # 按钮类型
    BUTTON_TYPES = {
        'adb': 'ADB命令',
        'python': 'Python脚本',
        'file': '打开文件',
        'program': '运行程序',
        'system': '系统命令',
        'url': '打开网页'
    }
    
    # 命令黑名单：不允许的持续输出命令
    BLOCKED_COMMANDS = {
        'logcat': '请使用Log过滤功能',
        'tcpdump': '请使用Log控制标签页的tcpdump功能',
        'ping': '请使用Network信息标签页的ping功能',
        'top': '此命令会持续输出，不支持',
        'getevent': '此命令会持续输出，不支持',
        'monkey': '此命令会持续输出，不支持'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.expanduser("~/.netui/custom_buttons.json")
        self.buttons = []
        # 新增：跟踪GUI进程，防止孤儿进程
        self._gui_processes = []
        # 从父窗口获取语言管理器和Tab配置管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        # 获取Tab配置管理器引用
        self.tab_config_manager = None
        if parent and hasattr(parent, 'tab_config_manager'):
            self.tab_config_manager = parent.tab_config_manager
        
        self.load_buttons()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def load_buttons(self):
        """加载按钮配置"""
        try:
            if os.path.exists(self.config_file):
                # 使用 utf-8-sig 编码来正确处理BOM
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    self.buttons = data.get('custom_buttons', [])
                    logger.info(f"{self.lang_manager.tr('成功加载')} {len(self.buttons)} {self.lang_manager.tr('个自定义按钮')}")
            else:
                # 创建默认配置
                self.buttons = self._create_default_buttons()
                self.save_buttons()
                logger.info(self.lang_manager.tr("创建默认自定义按钮配置"))
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('加载自定义按钮配置失败:')} {e}")
            # 如果配置文件损坏，创建默认配置
            logger.info(self.lang_manager.tr("尝试创建默认配置..."))
            self.buttons = self._create_default_buttons()
            self.save_buttons()
    
    def save_buttons(self, emit_signal=True):
        """保存按钮配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            data = {
                'custom_buttons': self.buttons,
                'version': '1.0'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{self.lang_manager.tr('成功保存')} {len(self.buttons)} {self.lang_manager.tr('个自定义按钮配置')}")
            if emit_signal:
                self.buttons_updated.emit()
            return True
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('保存自定义按钮配置失败:')} {e}")
            return False
    
    def _create_default_buttons(self):
        """创建默认按钮示例"""
        return [
            {
                'id': 'default_001',
                'name': self.lang_manager.tr('查看设备属性'),
                'type': 'adb',
                'command': 'shell getprop',
                'tab': self.lang_manager.tr('其他'),
                'card': self.lang_manager.tr('其他操作'),
                'enabled': False,
                'description': self.lang_manager.tr('查看设备的所有系统属性')
            },
            {
                'id': 'default_002',
                'name': self.lang_manager.tr('查看存储空间'),
                'type': 'adb',
                'command': 'shell df -h',
                'tab': self.lang_manager.tr('其他'),
                'card': self.lang_manager.tr('设备信息'),
                'enabled': False,
                'description': self.lang_manager.tr('查看设备存储空间使用情况')
            }
        ]
    
    def get_all_buttons(self):
        """获取所有按钮"""
        return self.buttons
    
    def get_buttons_by_location(self, tab_name, card_name):
        """根据Tab和Card获取按钮列表（支持空格变体匹配）"""
        # 规范化card名称用于匹配（去除多余空格）
        normalized_card_name = ' '.join(card_name.split()) if card_name else ''
        
        result = []
        for btn in self.buttons:
            if not btn.get('enabled', True):
                continue
            if btn.get('tab') != tab_name:
                continue
            # 规范化按钮的card名称进行比较
            btn_card = btn.get('card', '')
            normalized_btn_card = ' '.join(btn_card.split()) if btn_card else ''
            if normalized_btn_card == normalized_card_name:
                result.append(btn)
        # 仅在需要详细调试时记录
        if len(result) > 0:
            logger.debug(f"[按钮管理器] Tab '{tab_name}', Card '{card_name}': {len(result)} 个按钮")
        return result
    
    def get_available_tabs(self):
        """获取可用的Tab列表"""
        tabs = [
            self.lang_manager.tr('Log控制'),
            self.lang_manager.tr('Log过滤'),
            self.lang_manager.tr('网络信息'),
            'TMO CC',
            'TMO Echolocate',
            self.lang_manager.tr('24小时背景数据'),
            self.lang_manager.tr('APP操作'),
            self.lang_manager.tr('SIM'),
            self.lang_manager.tr('其他')
        ]
        
        # 添加自定义Tab
        custom_tabs = self.get_custom_tabs()
        for custom_tab in custom_tabs:
            tabs.append(custom_tab['name'])
        
        return tabs
    
    def get_available_cards(self, tab_name):
        """获取指定Tab下可用的Card列表"""
        cards = []
        
        # 首先检查是否是自定义Tab
        custom_tabs = self.get_custom_tabs()
        custom_tab = next((tab for tab in custom_tabs if tab['name'] == tab_name), None)
        
        if custom_tab:
            # 对于自定义Tab，从Tab配置管理器获取其Card
            if self.tab_config_manager:
                custom_cards = self.tab_config_manager.get_custom_cards_for_tab(custom_tab['id'])
                cards.extend([card['name'] for card in custom_cards])
        else:
            # 对于预制Tab，获取默认Card
            cards_map = {
                self.lang_manager.tr('Log控制'): [self.lang_manager.tr('LOG控制'), self.lang_manager.tr('ADB Log 控制')],
                self.lang_manager.tr('Log过滤'): [self.lang_manager.tr('过滤控制')],
                self.lang_manager.tr('网络信息'): [self.lang_manager.tr('控制'), self.lang_manager.tr('网络信息')],
                'TMO CC': [self.lang_manager.tr('CC配置'), self.lang_manager.tr('过滤操作')],
                'TMO Echolocate': [self.lang_manager.tr('Echolocate 操作'), self.lang_manager.tr('过滤操作')],
                self.lang_manager.tr('24小时背景数据'): [self.lang_manager.tr('24小时背景数据操作')],
                self.lang_manager.tr('APP操作'): [self.lang_manager.tr('查询操作'), self.lang_manager.tr('APK操作'), self.lang_manager.tr('进程操作'), self.lang_manager.tr('APP状态操作')],
                self.lang_manager.tr('SIM'): [self.lang_manager.tr('SIM APDU 解析器'), self.lang_manager.tr('SIM 卡读写工具')],
                self.lang_manager.tr('其他'): [self.lang_manager.tr('设备信息'), self.lang_manager.tr('赫拉配置'), self.lang_manager.tr('其他操作'), self.lang_manager.tr('log操作')]
            }
            cards.extend(cards_map.get(tab_name, [self.lang_manager.tr('默认')]))
            
            # 对于预制Tab，也添加自定义Card（如果存在）
            if self.tab_config_manager:
                # 找到对应的Tab ID
                all_tabs = self.tab_config_manager.get_all_tabs()
                tab_id = None
                for tab in all_tabs:
                    if tab['name'] == tab_name:
                        tab_id = tab['id']
                        break
                
                if tab_id:
                    custom_cards = self.tab_config_manager.get_custom_cards_for_tab(tab_id)
                    cards.extend([card['name'] for card in custom_cards])
        
        return cards
    
    def get_custom_tabs(self):
        """获取自定义Tab列表"""
        if self.tab_config_manager:
            return self.tab_config_manager.custom_tabs
        return []
    
    def add_button(self, button_data):
        """添加按钮"""
        try:
            # 生成ID
            if 'id' not in button_data:
                button_data['id'] = f"custom_{len(self.buttons) + 1:03d}"
            
            # 验证必填字段
            if not button_data.get('name'):
                logger.error(self.lang_manager.tr("按钮名称不能为空"))
                return False
            
            # 对于非Python脚本类型，验证命令字段
            button_type = button_data.get('type', 'adb')
            if button_type != 'python' and not button_data.get('command'):
                logger.error(self.lang_manager.tr("命令不能为空"))
                return False
            
            # 验证命令安全性（仅对ADB命令类型）
            if button_type == 'adb' and not self.validate_command(button_data.get('command', '')):
                logger.error(self.lang_manager.tr("ADB命令包含不允许的内容"))
                return False
            
            self.buttons.append(button_data)
            return self.save_buttons()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('添加按钮失败:')} {e}")
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
                        logger.error(self.lang_manager.tr("ADB命令包含不允许的内容"))
                        return False
                    
                    # 保留ID
                    button_data['id'] = button_id
                    self.buttons[i] = button_data
                    return self.save_buttons()
            
            logger.error(f"{self.lang_manager.tr('未找到ID为')} {button_id} {self.lang_manager.tr('的按钮')}")
            return False
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('更新按钮失败:')} {e}")
            return False
    
    def delete_button(self, button_id):
        """删除按钮"""
        try:
            self.buttons = [btn for btn in self.buttons if btn['id'] != button_id]
            return self.save_buttons()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('删除按钮失败:')} {e}")
            return False

    def reorder_buttons(self, ordered_ids):
        """根据给定的按钮ID顺序重新排序按钮列表"""
        try:
            if not ordered_ids:
                logger.warning(self.lang_manager.tr("重新排序按钮失败：ID列表为空"))
                return False

            id_to_button = {btn['id']: btn for btn in self.buttons}

            # 按照新的顺序重建列表
            new_order = []
            for button_id in ordered_ids:
                if button_id in id_to_button:
                    new_order.append(id_to_button.pop(button_id))

            # 将未出现在ordered_ids中的按钮追加在末尾，避免数据丢失
            if id_to_button:
                new_order.extend(id_to_button.values())

            # 如果顺序无变化，则不触发保存
            if len(new_order) != len(self.buttons):
                logger.warning(self.lang_manager.tr("重新排序按钮时检测到ID数量不匹配，已自动修复"))

            if new_order == self.buttons:
                return True

            self.buttons = new_order
            return self.save_buttons()

        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('重新排序按钮失败:')} {e}")
            return False
    
    def reorder_buttons_in_location(self, tab_name, card_name, ordered_ids):
        """仅对指定Tab/Card下的按钮进行重新排序"""
        try:
            if not ordered_ids:
                logger.warning(self.lang_manager.tr("重新排序按钮失败：ID列表为空"))
                return False

            location_buttons = [
                btn for btn in self.buttons
                if btn.get('tab') == tab_name and btn.get('card') == card_name
            ]

            if not location_buttons:
                logger.debug(self.lang_manager.tr("指定位置没有可排序的按钮"))
                return False

            id_to_button = {btn['id']: btn for btn in location_buttons}
            ordered_buttons = []

            for button_id in ordered_ids:
                button = id_to_button.pop(button_id, None)
                if button:
                    ordered_buttons.append(button)

            # 追加未被包含的按钮，避免数据丢失
            if id_to_button:
                ordered_buttons.extend(id_to_button.values())

            if ordered_buttons == location_buttons:
                return True

            new_buttons = []
            ordered_iter = iter(ordered_buttons)
            for btn in self.buttons:
                if btn.get('tab') == tab_name and btn.get('card') == card_name:
                    new_buttons.append(next(ordered_iter))
                else:
                    new_buttons.append(btn)

            self.buttons = new_buttons
            # 不发送信号，因为UI已经通过拖动更新了，不需要重新加载
            logger.debug(f"[按钮排序] Tab '{tab_name}', Card '{card_name}': 已保存 {len(ordered_buttons)} 个按钮的排序")
            return self.save_buttons(emit_signal=False)

        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('重新排序按钮失败:')} {e}")
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
                logger.error(f"{self.lang_manager.tr('无法读取文件')} {file_path}，{self.lang_manager.tr('尝试了多种编码')}")
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
            logger.exception(f"{self.lang_manager.tr('导入按钮配置失败:')} {e}")
            return False
    
    def export_buttons(self, file_path):
        """导出按钮配置到文件"""
        try:
            data = {
                'custom_buttons': self.buttons,
                'version': '1.0',
                'export_time': datetime.datetime.now().isoformat(),
                'export_note': self.lang_manager.tr('用户自定义按钮配置导出')
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{self.lang_manager.tr('成功导出按钮配置到:')} {file_path}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('导出按钮配置失败:')} {e}")
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
                'backup_note': self.lang_manager.tr('用户自定义按钮配置备份')
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{self.lang_manager.tr('配置已备份到:')} {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('备份配置失败:')} {e}")
            return None
    
    def restore_config(self, backup_path):
        """从备份文件恢复配置"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"{self.lang_manager.tr('备份文件不存在:')} {backup_path}")
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
                logger.error(f"{self.lang_manager.tr('无法读取备份文件:')} {backup_path}")
                return False
            
            # 恢复按钮配置
            self.buttons = data.get('custom_buttons', [])
            
            # 保存到当前配置文件
            success = self.save_buttons()
            if success:
                logger.info(f"{self.lang_manager.tr('配置已从备份恢复:')} {backup_path}")
                logger.info(f"{self.lang_manager.tr('恢复了')} {len(self.buttons)} {self.lang_manager.tr('个自定义按钮')}")
            
            return success
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('恢复配置失败:')} {e}")
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
                    return False, self.lang_manager.tr("Python脚本内容为空")
                # 注意：这里不传递dialog_response_handler，因为需要在ButtonCommandWorker中处理
                return self._execute_python_script(script_code, device_id)
            elif button_type == 'file':
                return self._open_file(command)
            elif button_type == 'program':
                # 注意：program类型通常在ButtonCommandWorker中直接处理，不会调用这里
                # 这里保留是为了向后兼容和错误处理
                # 如果进程被启动，需要立即清理，避免成为孤儿进程
                process, success, error_msg = self._run_program(command, device_id)
                if success and process:
                    # 进程不应在这里启动，立即清理
                    try:
                        if process.poll() is None:  # 进程仍在运行
                            process.terminate()
                            process.wait(timeout=2)
                    except:
                        try:
                            process.kill()
                        except:
                            pass
                    return False, self.lang_manager.tr('program类型应该在ButtonCommandWorker中处理，不应直接调用execute_button_command')
                else:
                    return False, error_msg or self.lang_manager.tr('启动程序失败')
            elif button_type == 'system':
                return self._execute_system_command(command)
            elif button_type == 'url':
                return self._open_url(command)
            else:
                logger.error(f"{self.lang_manager.tr('不支持的按钮类型:')} {button_type}")
                return False, f"{self.lang_manager.tr('不支持的按钮类型:')} {button_type}"
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('执行按钮命令失败:')} {e}")
            return False, str(e)
    
    def _execute_adb_command(self, command, device_id):
        """执行ADB命令（支持多行命令）"""
        if not device_id:
            return False, self.lang_manager.tr("未选择设备")
        
        # 清理命令格式
        clean_command = command.strip()
        if clean_command.lower().startswith('adb '):
            clean_command = clean_command[4:].strip()
        
        try:
            # 检查是否是多行命令
            lines = [line.strip() for line in clean_command.split('\n') if line.strip()]
            
            if len(lines) == 1:
                # 单行命令，直接执行
                full_command = f"adb -s {device_id} {clean_command}"
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
            else:
                # 多行命令处理
                # 检查第一行是否包含 'shell'
                first_line = lines[0].lower()
                if 'shell' in first_line:
                    # 如果是 shell 命令，通过 stdin 发送所有命令
                    # 移除每行的 'adb shell' 前缀（如果有）
                    shell_commands = []
                    for line in lines:
                        # 移除可能的 'adb shell' 前缀
                        if line.lower().startswith('adb shell '):
                            shell_commands.append(line[10:].strip())
                        elif line.lower().startswith('shell '):
                            shell_commands.append(line[6:].strip())
                        else:
                            shell_commands.append(line)
                    
                    # 用换行符连接所有命令
                    all_commands = '\n'.join(shell_commands)
                    
                    # 执行 adb shell，通过 stdin 发送所有命令
                    result = subprocess.run(
                        ["adb", "-s", device_id, "shell"],
                        input=all_commands,
                        text=True,
                        capture_output=True,
                        timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    output = result.stdout if result.stdout else result.stderr
                    success = result.returncode == 0
                    
                    return success, output
                else:
                    # 非 shell 命令，逐行执行
                    all_output = []
                    all_success = True
                    
                    for line in lines:
                        # 移除可能的 'adb ' 前缀
                        if line.lower().startswith('adb '):
                            line = line[4:].strip()
                        
                        full_command = f"adb -s {device_id} {line}"
                        result = subprocess.run(
                            full_command, 
                            shell=True, 
                            capture_output=True, 
                            text=True, 
                            timeout=30
                        )
                        
                        if result.stdout:
                            all_output.append(result.stdout)
                        if result.stderr:
                            all_output.append(result.stderr)
                        
                        if result.returncode != 0:
                            all_success = False
                    
                    output = '\n'.join(all_output)
                    return all_success, output
            
        except subprocess.TimeoutExpired:
            return False, self.lang_manager.tr("命令执行超时")
        except Exception as e:
            return False, f"{self.lang_manager.tr('执行失败:')} {str(e)}"
    
    def _create_safe_pyside6_module(self, dialog_request_handler):
        """创建安全的PySide6模块包装，用于脚本中的UI调用（保持向后兼容）"""
        from PySide6.QtWidgets import QMessageBox as RealQMessageBox
        
        def show_dialog_in_main_thread(dialog_type, title, message, buttons, default_button):
            """在工作线程中调用，通过信号请求主线程显示对话框"""
            # 直接调用dialog_request_handler，它会在worker中等待响应
            return dialog_request_handler(dialog_type, title, message, buttons, default_button)
        
        # 创建安全的QMessageBox类
        class SafeQMessageBox:
            """线程安全的QMessageBox包装类"""
            # 定义常量
            Yes = RealQMessageBox.StandardButton.Yes
            No = RealQMessageBox.StandardButton.No
            Ok = RealQMessageBox.StandardButton.Ok
            Cancel = RealQMessageBox.StandardButton.Cancel
            Abort = RealQMessageBox.StandardButton.Abort
            Retry = RealQMessageBox.StandardButton.Retry
            Ignore = RealQMessageBox.StandardButton.Ignore
            YesAll = RealQMessageBox.StandardButton.YesAll
            NoAll = RealQMessageBox.StandardButton.NoAll
            Save = RealQMessageBox.StandardButton.Save
            Discard = RealQMessageBox.StandardButton.Discard
            Apply = RealQMessageBox.StandardButton.Apply
            Reset = RealQMessageBox.StandardButton.Reset
            RestoreDefaults = RealQMessageBox.StandardButton.RestoreDefaults
            Help = RealQMessageBox.StandardButton.Help
            SaveAll = RealQMessageBox.StandardButton.SaveAll
            YesToAll = RealQMessageBox.StandardButton.YesToAll
            NoToAll = RealQMessageBox.StandardButton.NoToAll
            Open = RealQMessageBox.StandardButton.Open
            Close = RealQMessageBox.StandardButton.Close
            
            @staticmethod
            def question(parent, title, message, buttons=RealQMessageBox.StandardButton.Yes | RealQMessageBox.StandardButton.No, defaultButton=RealQMessageBox.StandardButton.No):
                return show_dialog_in_main_thread("question", title, message, buttons, defaultButton)
            
            @staticmethod
            def information(parent, title, message, buttons=RealQMessageBox.StandardButton.Ok, defaultButton=RealQMessageBox.StandardButton.Ok):
                return show_dialog_in_main_thread("information", title, message, buttons, defaultButton)
            
            @staticmethod
            def warning(parent, title, message, buttons=RealQMessageBox.StandardButton.Ok, defaultButton=RealQMessageBox.StandardButton.Ok):
                return show_dialog_in_main_thread("warning", title, message, buttons, defaultButton)
            
            @staticmethod
            def critical(parent, title, message, buttons=RealQMessageBox.StandardButton.Ok, defaultButton=RealQMessageBox.StandardButton.Ok):
                return show_dialog_in_main_thread("critical", title, message, buttons, defaultButton)
            
            @staticmethod
            def about(parent, title, message):
                return show_dialog_in_main_thread("about", title, message, RealQMessageBox.StandardButton.Ok, RealQMessageBox.StandardButton.Ok)
        
        # 创建安全的QApplication类
        class SafeQApplication:
            """线程安全的QApplication包装类"""
            _instance = None
            
            @staticmethod
            def instance():
                """返回主线程的QApplication实例"""
                from PySide6.QtWidgets import QApplication
                return QApplication.instance()
            
            @staticmethod
            def __call__(argv=None):
                """创建QApplication实例（实际上返回主线程的实例）"""
                return SafeQApplication.instance()
        
        # 创建模块结构
        QtWidgets_module = type('module', (), {
            'QMessageBox': SafeQMessageBox,
            'QApplication': SafeQApplication,
        })
        
        PySide6_module = type('module', (), {
            'QtWidgets': QtWidgets_module,
        })
        # 向后兼容：同时支持 PyQt5 和 PySide6 的导入方式
        PyQt5_module = PySide6_module  # 向后兼容别名
        
        return PySide6_module
    
    def _execute_python_script(self, script_code, device_id=None, dialog_response_handler=None):
        """执行Python脚本（无限制版本 - 允许执行任意代码）
        
        警告：此版本移除了所有安全限制，脚本可以：
        - 导入任意模块
        - 使用所有内置函数（包括eval、exec、open等）
        - 访问文件系统
        - 执行系统命令
        - 修改主程序状态
        
        请确保只在可信环境中使用！
        
        注意：如果脚本包含GUI框架（如tkinter），会自动在独立进程中运行以避免冲突。
        """
        try:
            import io
            import tempfile
            from contextlib import redirect_stdout, redirect_stderr
            import subprocess
            import sys
            
            # 检测是否包含GUI框架（tkinter、PyQt等）
            # 这些GUI框架需要在主线程或独立进程中运行
            has_gui = False
            gui_keywords = [
                'import tkinter',
                'from tkinter',
                'tk.Tk()',
                'tkinter.Tk()',
                'QApplication',
                'QWidget',
                'app.mainloop()',
                '.mainloop()'
            ]
            
            script_lower = script_code.lower()
            for keyword in gui_keywords:
                if keyword.lower() in script_lower:
                    has_gui = True
                    break
            
            # 如果包含GUI，在独立进程中运行
            if has_gui:
                return self._execute_gui_script_in_process(script_code, device_id)
            
            # 创建无限制的执行环境
            # 使用完整的__builtins__，允许所有内置函数
            exec_globals = {
                '__builtins__': __builtins__,  # 完整的内置函数，无任何限制
                '__name__': '__main__',
                '__file__': '<custom_button_script>',
            }
            
            # 导入常用模块到执行环境（可选，脚本也可以自己导入）
            import datetime
            import platform
            import os
            import json
            import math
            import random
            import time
            
            exec_globals.update({
                'datetime': datetime,
                'platform': platform,
                'os': os,
                'sys': sys,
                'json': json,
                'math': math,
                'random': random,
                'time': time,
                'subprocess': subprocess,
            })
            
            # 添加设备ID到全局环境（如果提供）
            if device_id:
                exec_globals['DEVICE_ID'] = device_id
                print(f"[DEBUG] 设备ID已设置: {device_id}")
                # 创建一个便捷的adb_shell函数
                current_device_id = device_id
                def adb_shell_func(cmd):
                    """在脚本中可用的ADB shell命令辅助函数"""
                    if current_device_id:
                        full_cmd = ['adb', '-s', current_device_id] + cmd
                    else:
                        full_cmd = ['adb'] + cmd
                    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
                exec_globals['adb_shell'] = adb_shell_func
            else:
                print("[WARNING] 未提供设备ID")
            
            # 如果脚本中使用了 uiautomator2，包装 u2.connect() 以自动使用设备ID
            # 需要在脚本执行前修改 uiautomator2 模块
            # 使用模块级别的标记来避免重复包装
            try:
                import uiautomator2
                # 检查是否已经包装过（通过检查函数是否有特定属性）
                if not hasattr(uiautomator2.connect, '_wrapped_by_custom_button'):
                    original_connect = uiautomator2.connect
                    current_device_id_for_u2 = device_id  # 使用闭包捕获设备ID
                    def u2_connect_with_device(*args, **kwargs):
                        """包装 u2.connect，如果没有参数则使用 DEVICE_ID"""
                        if not args and not kwargs:
                            if current_device_id_for_u2:
                                print(f"[DEBUG] u2.connect() 自动使用设备ID: {current_device_id_for_u2}")
                                try:
                                    return original_connect(current_device_id_for_u2)
                                except Exception as e:
                                    print(f"[ERROR] 使用设备ID连接失败: {e}")
                                    raise
                            else:
                                print("[WARNING] 未提供设备ID，使用默认连接方式")
                                return original_connect()
                        return original_connect(*args, **kwargs)
                    # 标记函数已被包装，避免重复包装
                    u2_connect_with_device._wrapped_by_custom_button = True
                    u2_connect_with_device._original_connect = original_connect
                    # 替换模块级别的 connect 函数
                    uiautomator2.connect = u2_connect_with_device
                    print("[DEBUG] uiautomator2.connect() 已包装")
                else:
                    # 已经包装过，更新设备ID（如果需要）
                    if device_id and hasattr(uiautomator2.connect, '_original_connect'):
                        # 重新包装以使用新的设备ID
                        original_connect = uiautomator2.connect._original_connect
                        current_device_id_for_u2 = device_id
                        def u2_connect_with_device(*args, **kwargs):
                            """包装 u2.connect，如果没有参数则使用 DEVICE_ID"""
                            if not args and not kwargs:
                                if current_device_id_for_u2:
                                    print(f"[DEBUG] u2.connect() 自动使用设备ID: {current_device_id_for_u2}")
                                    try:
                                        return original_connect(current_device_id_for_u2)
                                    except Exception as e:
                                        print(f"[ERROR] 使用设备ID连接失败: {e}")
                                        raise
                                else:
                                    print("[WARNING] 未提供设备ID，使用默认连接方式")
                                    return original_connect()
                            return original_connect(*args, **kwargs)
                        u2_connect_with_device._wrapped_by_custom_button = True
                        u2_connect_with_device._original_connect = original_connect
                        uiautomator2.connect = u2_connect_with_device
                        print("[DEBUG] uiautomator2.connect() 已更新设备ID")
                # 也添加到 exec_globals 中，确保脚本可以使用
                exec_globals['uiautomator2'] = uiautomator2
                # 确保 u2 别名也能工作
                exec_globals['u2'] = uiautomator2
            except ImportError:
                # uiautomator2 未安装，跳过
                print("[WARNING] uiautomator2 未安装")
                pass
            except Exception as e:
                print(f"[WARNING] 包装 uiautomator2.connect 失败: {e}")
            
            # 如果提供了对话框响应处理器，添加PySide6支持
            if dialog_response_handler:
                safe_pyside6_module = self._create_safe_pyside6_module(dialog_response_handler)
                exec_globals['PySide6'] = safe_pyside6_module
                exec_globals['PyQt5'] = safe_pyside6_module  # 向后兼容
            
            # 重要：让 locals 和 globals 指向同一个字典
            # 这样脚本中定义的函数和变量都在同一个命名空间中，可以互相访问
            exec_locals = exec_globals
            
            # 捕获输出
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            try:
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # 执行脚本（无任何限制 - 可以导入任意模块、使用任意函数）
                    # 使用相同的 globals 和 locals，确保所有定义在同一个命名空间
                    exec(script_code, exec_globals, exec_locals)
                    
                    # 不需要在脚本执行后再次包装，因为模块级别的包装已经生效
                    # u2 对象会引用模块级别的 uiautomator2，所以模块级别的包装就足够了
                
                # 获取输出结果
                stdout_output = output_buffer.getvalue()
                stderr_output = error_buffer.getvalue()
                
                # 组合输出结果
                result_output = ""
                if stdout_output:
                    result_output += f"{self.lang_manager.tr('输出:')}\n{stdout_output}"
                if stderr_output:
                    result_output += f"\n{self.lang_manager.tr('错误:')}\n{stderr_output}"
                
                if result_output:
                    return True, result_output
                else:
                    return True, self.lang_manager.tr("Python脚本执行完成（无输出）")
                    
            except Exception as exec_error:
                # 如果执行过程中出错，返回错误信息
                import traceback
                error_trace = traceback.format_exc()
                return False, f"{self.lang_manager.tr('Python脚本执行错误:')} {str(exec_error)}\n{error_trace}"
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return False, f"{self.lang_manager.tr('Python脚本执行失败:')} {str(e)}\n{error_trace}"
    
    def _execute_gui_script_in_process(self, script_code, device_id=None):
        """在独立进程中执行包含GUI的Python脚本"""
        try:
            import tempfile
            import subprocess
            import sys
            import os
            import threading
            import time
            from collections import deque
            
            # 在脚本开头注入设备ID和u2.connect包装（如果提供）
            # 这样脚本可以使用 DEVICE_ID 变量，并且 u2.connect() 会自动使用设备ID
            injected_code = ""
            if device_id:
                injected_code = f"""# 设备ID由主程序自动注入
DEVICE_ID = '{device_id}'

# 自动包装 u2.connect() 以使用设备ID
try:
    import uiautomator2 as u2
    _original_u2_connect = u2.connect
    def _u2_connect_wrapper(*args, **kwargs):
        # 如果没有提供参数，使用 DEVICE_ID
        if not args and not kwargs:
            return _original_u2_connect(DEVICE_ID)
        return _original_u2_connect(*args, **kwargs)
    u2.connect = _u2_connect_wrapper
except ImportError:
    pass  # uiautomator2 未安装，跳过

"""
            
            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                script_path = f.name
                f.write(injected_code + script_code)
            
            try:
                # 获取Python解释器路径
                # 注意：在 PyInstaller 打包后的 EXE（frozen）中，sys.executable 指向本 EXE，
                # 若直接用它执行临时 .py，会导致“再启动一个主程序”的错误行为。
                def _is_frozen():
                    return bool(getattr(sys, 'frozen', False)) and hasattr(sys, '_MEIPASS')
                
                def _check_python_cmd(cmd):
                    """快速检查命令是否可用（只验证能输出版本即可）"""
                    try:
                        r = subprocess.run(
                            [cmd, '--version'],
                            capture_output=True,
                            text=True,
                            timeout=2,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        return r.returncode == 0
                    except Exception:
                        return False
                
                def _pick_system_python():
                    # 1) 环境变量 PYTHON
                    env_py = os.environ.get('PYTHON')
                    if env_py and os.path.exists(env_py):
                        return env_py
                    
                    # 2) PATH 中 python / pythonw / python3
                    for candidate in ('python', 'pythonw', 'python3'):
                        if _check_python_cmd(candidate):
                            return candidate
                    
                    # 3) 常见安装路径（Windows）
                    common_paths = [
                        r'C:\Python39\python.exe',
                        r'C:\Python310\python.exe',
                        r'C:\Python311\python.exe',
                        r'C:\Python312\python.exe',
                        r'C:\Program Files\Python39\python.exe',
                        r'C:\Program Files\Python310\python.exe',
                        r'C:\Program Files\Python311\python.exe',
                        r'C:\Program Files\Python312\python.exe',
                    ]
                    username = os.getenv('USERNAME', '')
                    if username:
                        common_paths.extend([
                            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python39\python.exe',
                            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python310\python.exe',
                            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python311\python.exe',
                            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python312\python.exe',
                        ])
                    for p in common_paths:
                        if os.path.exists(p):
                            return p
                    
                    return None
                
                if _is_frozen():
                    python_exe = _pick_system_python()
                    if not python_exe:
                        return False, self.lang_manager.tr(
                            "在打包环境中无法找到Python解释器。请确保系统已安装Python，并确保 `python --version` 可用，"
                            "或设置 PYTHON 环境变量指向 python.exe。"
                        )
                else:
                    python_exe = sys.executable
                
                # 在独立进程中运行脚本
                # 使用CREATE_NO_WINDOW标志（Windows）避免显示控制台窗口
                creation_flags = 0
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    creation_flags = subprocess.CREATE_NO_WINDOW

                # 捕获子进程输出（为避免缓冲区塞满导致阻塞，启动守护线程持续读取，并保留最近一段内容用于报错展示）
                stdout_buf = deque(maxlen=200)
                stderr_buf = deque(maxlen=200)
                
                def _drain_stream(stream, buf_deque, level='debug'):
                    try:
                        for line in iter(stream.readline, ''):
                            if line is None:
                                break
                            s = line.rstrip('\r\n')
                            if s:
                                buf_deque.append(s)
                                try:
                                    if level == 'error':
                                        logger.error(f"[GUI子进程] {s}")
                                    else:
                                        logger.debug(f"[GUI子进程] {s}")
                                except Exception:
                                    pass
                    except Exception:
                        # 不影响主流程
                        pass
                    finally:
                        try:
                            stream.close()
                        except Exception:
                            pass

                process = subprocess.Popen(
                    [python_exe, '-u', script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=creation_flags
                )

                # 启动输出读取线程，避免 PIPE 缓冲区塞满
                if process.stdout:
                    t_out = threading.Thread(target=_drain_stream, args=(process.stdout, stdout_buf, 'debug'), daemon=True)
                    t_out.start()
                if process.stderr:
                    t_err = threading.Thread(target=_drain_stream, args=(process.stderr, stderr_buf, 'error'), daemon=True)
                    t_err.start()
                
                # ✅ 新增：保存进程引用
                if not hasattr(self, '_gui_processes'):
                    self._gui_processes = []
                self._gui_processes.append(process)
                
                # ✅ 新增：监控进程退出，自动清理引用
                def on_process_exit(proc):
                    """进程退出时的回调"""
                    try:
                        if hasattr(self, '_gui_processes') and proc in self._gui_processes:
                            self._gui_processes.remove(proc)
                            logger.debug(f"GUI进程已退出，PID: {proc.pid}")
                    except Exception as e:
                        logger.exception(f"清理GUI进程引用失败: {e}")
                
                # ✅ 新增：使用守护线程监控进程状态
                def monitor_process():
                    """监控进程状态"""
                    try:
                        process.wait()  # 等待进程结束
                        on_process_exit(process)
                    except Exception as e:
                        logger.exception(f"监控GUI进程失败: {e}")
                
                # 启动监控线程（守护线程，主程序退出时自动结束）
                monitor_thread = threading.Thread(target=monitor_process, daemon=True)
                monitor_thread.start()
                
                logger.debug(f"GUI进程已启动，PID: {process.pid}，当前跟踪的GUI进程数: {len(self._gui_processes)}")

                # 若子进程很快退出（常见于解释器/依赖/语法错误），立刻回显 stderr，避免只显示“已启动”
                try:
                    time.sleep(0.3)
                    rc = process.poll()
                    if rc is not None:
                        stdout_text = "\n".join(list(stdout_buf)[-50:])
                        stderr_text = "\n".join(list(stderr_buf)[-50:])
                        detail = []
                        if stdout_text.strip():
                            detail.append(f"{self.lang_manager.tr('输出:')}\n{stdout_text}")
                        if stderr_text.strip():
                            detail.append(f"{self.lang_manager.tr('错误:')}\n{stderr_text}")
                        detail_text = "\n\n".join(detail).strip()
                        if not detail_text:
                            detail_text = self.lang_manager.tr("无可用输出（可能被安全策略拦截或进程在初始化前退出）")
                        return False, (
                            f"{self.lang_manager.tr('GUI脚本启动后立即退出')} (exit={rc})\n"
                            f"{self.lang_manager.tr('解释器:')} {python_exe}\n"
                            f"{self.lang_manager.tr('临时脚本:')} {script_path}\n\n"
                            f"{detail_text}"
                        )
                except Exception:
                    # 不影响正常返回
                    pass
                
                # 不等待进程结束（GUI应用会持续运行）
                # 返回成功信息
                return True, self.lang_manager.tr("GUI应用已在独立窗口中启动。\n注意：GUI应用会在独立进程中运行，关闭主程序时会自动终止所有GUI进程。")
                
            finally:
                # 延迟删除临时文件（给进程时间读取）
                # 在实际应用中，可以设置一个定时器来删除
                pass
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return False, f"{self.lang_manager.tr('启动GUI应用失败:')} {str(e)}\n{error_trace}"
    
    def cleanup(self):
        """清理所有GUI进程，防止孤儿进程"""
        if not hasattr(self, '_gui_processes'):
            return
        
        if not self._gui_processes:
            return
        
        logger.debug(f"开始清理 {len(self._gui_processes)} 个GUI进程")
        
        for process in self._gui_processes[:]:  # 创建副本，避免修改时出错
            try:
                # 检查进程是否还在运行
                if process.poll() is None:  # None表示进程还在运行
                    logger.debug(f"正在终止GUI进程，PID: {process.pid}")
                    try:
                        # 先尝试优雅终止
                        process.terminate()
                        # 等待进程结束，最多等待2秒
                        process.wait(timeout=2)
                        logger.debug(f"GUI进程已优雅终止，PID: {process.pid}")
                    except subprocess.TimeoutExpired:
                        # 如果进程没有在2秒内退出，强制杀死
                        logger.warning(f"GUI进程终止超时，强制kill，PID: {process.pid}")
                        try:
                            process.kill()
                            process.wait(timeout=1)
                            logger.debug(f"GUI进程已强制终止，PID: {process.pid}")
                        except Exception as e:
                            logger.exception(f"强制终止GUI进程失败，PID: {process.pid}: {e}")
                    except Exception as e:
                        # terminate失败，尝试kill
                        logger.warning(f"终止GUI进程失败，尝试kill，PID: {process.pid}: {e}")
                        try:
                            process.kill()
                            process.wait(timeout=1)
                            logger.debug(f"GUI进程已强制终止，PID: {process.pid}")
                        except Exception as e2:
                            logger.exception(f"强制终止GUI进程失败，PID: {process.pid}: {e2}")
                else:
                    # 进程已经退出
                    logger.debug(f"GUI进程已退出，PID: {process.pid}，退出码: {process.returncode}")
            except Exception as e:
                logger.exception(f"清理GUI进程时发生错误，PID: {process.pid if hasattr(process, 'pid') else 'unknown'}: {e}")
            finally:
                # 从列表中移除（无论成功与否）
                try:
                    if process in self._gui_processes:
                        self._gui_processes.remove(process)
                except Exception:
                    pass
        
        logger.debug(f"GUI进程清理完成，剩余进程数: {len(self._gui_processes)}")
    
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
            
            return True, f"{self.lang_manager.tr('已打开:')} {file_path}"
            
        except Exception as e:
            return False, f"{self.lang_manager.tr('打开文件失败:')} {str(e)}"
    
    def _run_program(self, program_path, device_id=None):
        """运行程序，返回进程对象和错误信息
        
        Returns:
            tuple: (process, success, error_message)
                - process: subprocess.Popen对象，如果启动失败则为None
                - success: bool，是否成功启动
                - error_message: str，错误信息，成功时为None
        """
        try:
            if not os.path.exists(program_path):
                return None, False, f"{self.lang_manager.tr('程序不存在:')} {program_path}"
            
            # 获取程序所在目录作为工作目录（确保能正确导入同目录下的模块）
            working_dir = os.path.dirname(os.path.abspath(program_path))
            
            # 构建命令
            cmd = [program_path]
            
            # 如果是Python脚本，使用python解释器运行，并传递设备ID
            if program_path.lower().endswith('.py'):
                import sys
                
                # 检测是否在PyInstaller打包环境中
                is_frozen = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
                
                if is_frozen:
                    # 在打包环境中，需要找到系统的Python解释器
                    # 尝试多种方式查找Python解释器
                    python_exe = None
                    
                    # 方法1: 检查环境变量PYTHON
                    if 'PYTHON' in os.environ:
                        python_exe = os.environ['PYTHON']
                        if os.path.exists(python_exe):
                            cmd = [python_exe, '-u', program_path]
                    
                    # 方法2: 尝试使用 'python' 命令（在PATH中查找）
                    if not python_exe:
                        try:
                            # 使用 'python' 命令查找Python解释器
                            result = subprocess.run(
                                ['python', '--version'],
                                capture_output=True,
                                text=True,
                                timeout=2,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            if result.returncode == 0:
                                python_exe = 'python'
                                cmd = [python_exe, '-u', program_path]
                        except:
                            pass
                    
                    # 方法3: 尝试使用 'python3' 命令
                    if not python_exe:
                        try:
                            result = subprocess.run(
                                ['python3', '--version'],
                                capture_output=True,
                                text=True,
                                timeout=2,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            if result.returncode == 0:
                                python_exe = 'python3'
                                cmd = [python_exe, '-u', program_path]
                        except:
                            pass
                    
                    # 方法4: 尝试常见的Python安装路径（Windows）
                    if not python_exe:
                        common_paths = [
                            r'C:\Python39\python.exe',
                            r'C:\Python310\python.exe',
                            r'C:\Python311\python.exe',
                            r'C:\Python312\python.exe',
                            r'C:\Program Files\Python39\python.exe',
                            r'C:\Program Files\Python310\python.exe',
                            r'C:\Program Files\Python311\python.exe',
                            r'C:\Program Files\Python312\python.exe',
                        ]
                        # 添加用户目录下的Python路径
                        username = os.getenv('USERNAME', '')
                        if username:
                            common_paths.extend([
                                rf'C:\Users\{username}\AppData\Local\Programs\Python\Python39\python.exe',
                                rf'C:\Users\{username}\AppData\Local\Programs\Python\Python310\python.exe',
                                rf'C:\Users\{username}\AppData\Local\Programs\Python\Python311\python.exe',
                                rf'C:\Users\{username}\AppData\Local\Programs\Python\Python312\python.exe',
                            ])
                        for path in common_paths:
                            if os.path.exists(path):
                                python_exe = path
                                cmd = [python_exe, '-u', program_path]
                                break
                    
                    # 如果仍然找不到Python解释器，返回错误
                    if not python_exe:
                        return None, False, self.lang_manager.tr("在打包环境中无法找到Python解释器。请确保系统已安装Python，或者设置PYTHON环境变量指向Python解释器路径。")
                else:
                    # 非打包环境，直接使用sys.executable
                    cmd = [sys.executable, '-u', program_path]  # -u 参数确保无缓冲输出
                
                # 传递设备ID作为命令行参数
                if device_id:
                    cmd.append(device_id)
            elif program_path.lower().endswith('.bat') or program_path.lower().endswith('.cmd'):
                # Windows 批处理脚本：通过 cmd.exe 启动，才能稳定执行并捕获 stdout/stderr
                cmd = ['cmd.exe', '/c', program_path]
                if device_id:
                    cmd.append(device_id)
            
            # 启动程序
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲，确保输出实时
                cwd=working_dir,  # 设置工作目录
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            return process, True, None  # 返回 (process, success, error_message)
                
        except Exception as e:
            return None, False, f"{self.lang_manager.tr('运行程序失败:')} {str(e)}"
    
    def _execute_system_command(self, command):
        """执行系统命令（支持多行命令）"""
        try:
            # 检查是否是多行命令
            lines = [line.strip() for line in command.split('\n') if line.strip()]
            
            if len(lines) == 1:
                # 单行命令，直接执行
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
            else:
                # 多行命令，使用 && 连接（Windows和Linux都支持）或逐行执行
                # Windows使用 &&，Linux/Mac也可以使用 &&
                # 但为了更好的兼容性，使用换行符连接（在shell中）
                if os.name == 'nt':  # Windows
                    # Windows使用 && 连接命令
                    combined_command = ' && '.join(lines)
                else:  # Linux/Mac
                    # 使用分号连接，或者使用换行符
                    combined_command = '; '.join(lines)
                
                result = subprocess.run(
                    combined_command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                output = result.stdout if result.stdout else result.stderr
                success = result.returncode == 0
                
                return success, output
            
        except subprocess.TimeoutExpired:
            return False, self.lang_manager.tr("命令执行超时")
        except Exception as e:
            return False, f"{self.lang_manager.tr('执行失败:')} {str(e)}"
    
    def _open_url(self, url):
        """打开网页"""
        try:
            import webbrowser
            
            # 验证URL格式
            if not url or not url.strip():
                return False, self.lang_manager.tr("网页地址不能为空")
            
            # 确保URL包含协议
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # 使用webbrowser模块打开URL
            webbrowser.open(url)
            
            return True, f"{self.lang_manager.tr('已打开网页:')} {url}"
            
        except Exception as e:
            return False, f"{self.lang_manager.tr('打开网页失败:')} {str(e)}"

