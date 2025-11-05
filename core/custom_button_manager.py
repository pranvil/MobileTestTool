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
    # 对话框相关信号（用于脚本中的UI调用）
    dialog_request = pyqtSignal(str, str, str, int, int, object)  # dialog_type, title, message, buttons, default_button, response_handler
    dialog_response = pyqtSignal(int)  # button_clicked (QMessageBox.Yes/No等)
    
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
            return self.save_buttons()
            self.buttons = new_buttons
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
                return self._run_program(command, device_id)
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
        """执行ADB命令"""
        if not device_id:
            return False, self.lang_manager.tr("未选择设备")
        
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
            return False, self.lang_manager.tr("命令执行超时")
        except Exception as e:
            return False, f"{self.lang_manager.tr('执行失败:')} {str(e)}"
    
    def _create_safe_pyqt5_module(self, dialog_request_handler):
        """创建安全的PyQt5模块包装，用于脚本中的UI调用"""
        from PyQt5.QtWidgets import QMessageBox as RealQMessageBox
        
        def show_dialog_in_main_thread(dialog_type, title, message, buttons, default_button):
            """在工作线程中调用，通过信号请求主线程显示对话框"""
            # 直接调用dialog_request_handler，它会在worker中等待响应
            return dialog_request_handler(dialog_type, title, message, buttons, default_button)
        
        # 创建安全的QMessageBox类
        class SafeQMessageBox:
            """线程安全的QMessageBox包装类"""
            # 定义常量
            Yes = RealQMessageBox.Yes
            No = RealQMessageBox.No
            Ok = RealQMessageBox.Ok
            Cancel = RealQMessageBox.Cancel
            Abort = RealQMessageBox.Abort
            Retry = RealQMessageBox.Retry
            Ignore = RealQMessageBox.Ignore
            YesAll = RealQMessageBox.YesAll
            NoAll = RealQMessageBox.NoAll
            Save = RealQMessageBox.Save
            Discard = RealQMessageBox.Discard
            Apply = RealQMessageBox.Apply
            Reset = RealQMessageBox.Reset
            RestoreDefaults = RealQMessageBox.RestoreDefaults
            Help = RealQMessageBox.Help
            SaveAll = RealQMessageBox.SaveAll
            YesToAll = RealQMessageBox.YesToAll
            NoToAll = RealQMessageBox.NoToAll
            Open = RealQMessageBox.Open
            Close = RealQMessageBox.Close
            
            @staticmethod
            def question(parent, title, message, buttons=RealQMessageBox.Yes | RealQMessageBox.No, defaultButton=RealQMessageBox.No):
                return show_dialog_in_main_thread("question", title, message, buttons, defaultButton)
            
            @staticmethod
            def information(parent, title, message, buttons=RealQMessageBox.Ok, defaultButton=RealQMessageBox.Ok):
                return show_dialog_in_main_thread("information", title, message, buttons, defaultButton)
            
            @staticmethod
            def warning(parent, title, message, buttons=RealQMessageBox.Ok, defaultButton=RealQMessageBox.Ok):
                return show_dialog_in_main_thread("warning", title, message, buttons, defaultButton)
            
            @staticmethod
            def critical(parent, title, message, buttons=RealQMessageBox.Ok, defaultButton=RealQMessageBox.Ok):
                return show_dialog_in_main_thread("critical", title, message, buttons, defaultButton)
            
            @staticmethod
            def about(parent, title, message):
                return show_dialog_in_main_thread("about", title, message, RealQMessageBox.Ok, RealQMessageBox.Ok)
        
        # 创建安全的QApplication类
        class SafeQApplication:
            """线程安全的QApplication包装类"""
            _instance = None
            
            @staticmethod
            def instance():
                """返回主线程的QApplication实例"""
                from PyQt5.QtWidgets import QApplication
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
        
        PyQt5_module = type('module', (), {
            'QtWidgets': QtWidgets_module,
        })
        
        return PyQt5_module
    
    def _execute_python_script(self, script_code, device_id=None, dialog_response_handler=None):
        """执行Python脚本"""
        try:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            # 导入需要的模块
            import datetime
            import platform
            import os
            import sys
            import json
            import math
            import random
            import time
            import subprocess
            
            # 创建安全的执行环境
            # 获取真正的内置函数字典
            import builtins
            safe_builtins = {
                '__import__': __import__,  # 允许使用 import 语句
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
            }
            # 安全地添加 help 函数（如果可用）
            if hasattr(builtins, 'help'):
                safe_builtins['help'] = builtins.help
            
            # 创建安全的PyQt5模块（如果提供了对话框响应处理器）
            safe_pyqt5_module = None
            if dialog_response_handler:
                safe_pyqt5_module = self._create_safe_pyqt5_module(dialog_response_handler)
            
            # 创建自定义的__import__函数，拦截PyQt5导入
            original_import = safe_builtins['__import__']
            def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                # 如果导入PyQt5.QtWidgets，返回我们的安全包装模块
                if name == 'PyQt5.QtWidgets' and safe_pyqt5_module:
                    return safe_pyqt5_module.QtWidgets
                elif name == 'PyQt5' and safe_pyqt5_module:
                    return safe_pyqt5_module
                # 其他导入使用原始方法
                return original_import(name, globals, locals, fromlist, level)
            
            safe_builtins['__import__'] = safe_import
            
            safe_globals = {
                '__builtins__': safe_builtins,
                '__name__': '__main__',  # 允许使用 if __name__ == "__main__" 模式
                'datetime': datetime,
                'platform': platform,
                'os': os,
                'sys': sys,
                'json': json,
                'math': math,
                'random': random,
                'time': time,
                'subprocess': subprocess,
            }
            
            # 如果创建了安全的PyQt5模块，直接注入到全局环境
            if safe_pyqt5_module:
                safe_globals['PyQt5'] = safe_pyqt5_module
            
            # 同时将常用的内置函数添加到全局作用域，确保可以直接访问
            for key in ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'range', 'enumerate', 
                       'zip', 'sorted', 'min', 'max', 'sum', 'abs', 'round', 'type', 'isinstance', 
                       'hasattr', 'getattr', 'setattr', 'dir']:
                safe_globals[key] = safe_builtins[key]
            if 'help' in safe_builtins:
                safe_globals['help'] = safe_builtins['help']
            
            # 添加设备ID到全局环境（如果提供）
            if device_id:
                safe_globals['DEVICE_ID'] = device_id
                # 创建一个便捷的adb_shell函数
                # 使用闭包捕获 device_id
                current_device_id = device_id
                def adb_shell_func(cmd):
                    """在脚本中可用的ADB shell命令辅助函数"""
                    if current_device_id:
                        full_cmd = ['adb', '-s', current_device_id] + cmd
                    else:
                        full_cmd = ['adb'] + cmd
                    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
                safe_globals['adb_shell'] = adb_shell_func
            
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
                    result_output += f"{self.lang_manager.tr('输出:')}\n{stdout_output}"
                if stderr_output:
                    result_output += f"\n{self.lang_manager.tr('错误:')}\n{stderr_output}"
                
                if result_output:
                    return True, result_output
                else:
                    return True, self.lang_manager.tr("Python脚本执行完成（无输出）")
                    
            except Exception as exec_error:
                # 如果执行过程中出错，返回错误信息
                return False, f"{self.lang_manager.tr('Python脚本执行错误:')} {str(exec_error)}"
            
        except Exception as e:
            return False, f"{self.lang_manager.tr('Python脚本执行失败:')} {str(e)}"
    
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
        """运行程序"""
        try:
            if not os.path.exists(program_path):
                return False, f"{self.lang_manager.tr('程序不存在:')} {program_path}"
            
            # 构建命令
            cmd = [program_path]
            
            # 如果是Python脚本，使用python解释器运行，并传递设备ID
            if program_path.lower().endswith('.py'):
                import sys
                cmd = [sys.executable, program_path]
                
                # 传递设备ID作为命令行参数
                if device_id:
                    cmd.append(device_id)
            
            # 启动程序
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 读取输出（非阻塞）
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout:
                    logger.info(f"程序输出: {stdout}")
                if stderr:
                    logger.warning(f"程序错误: {stderr}")
            except subprocess.TimeoutExpired:
                # 程序仍在运行，这是正常的
                pass
            
            return True, f"{self.lang_manager.tr('已启动程序:')} {program_path}"
                
        except Exception as e:
            return False, f"{self.lang_manager.tr('运行程序失败:')} {str(e)}"
    
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

