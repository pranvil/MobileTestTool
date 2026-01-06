#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tab配置管理器
支持tab排序、显示/隐藏、自定义tab和card管理
"""

import os
import json
import datetime
from PySide6.QtCore import QObject, Signal
from core.debug_logger import logger


class TabConfigManager(QObject):
    """Tab配置管理器"""
    
    # 信号定义
    tab_config_updated = Signal()  # Tab配置更新
    custom_tab_created = Signal(dict)  # 自定义tab创建
    custom_tab_deleted = Signal(str)  # 自定义tab删除
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.expanduser("~/.netui/tab_config.json")
        
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        # 默认配置
        self.default_tabs = [
            {'id': 'log_control', 'name': 'Log控制', 'visible': True, 'custom': False},
            {'id': 'log_filter', 'name': 'Log过滤', 'visible': True, 'custom': False},
            {'id': 'network_info', 'name': '网络信息', 'visible': True, 'custom': False},
            {'id': 'tmo_cc', 'name': 'TMO CC', 'visible': False, 'custom': False},
            {'id': 'tmo_echolocate', 'name': 'TMO Echolocate', 'visible': False, 'custom': False},
            {'id': 'background_data', 'name': '24小时背景数据', 'visible': False, 'custom': False},
            {'id': 'app_operations', 'name': 'APP操作', 'visible': True, 'custom': False},
            {'id': 'sim', 'name': 'SIM', 'visible': True, 'custom': False},
            {'id': 'office_tool', 'name': '办公工具', 'visible': True, 'custom': False},
            {'id': 'other', 'name': '其他', 'visible': True, 'custom': False}
        ]
        
        self.tab_order = []
        self.tab_visibility = {}
        self.custom_tabs = []
        self.custom_cards = []
        
        # 防抖保存机制
        self._save_timer = None
        self._pending_save = False
        
        self.load_config()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def can_hide_tab(self, tab_id):
        """检查Tab是否可以隐藏"""
        # "其他"选项卡不能隐藏，因为它是Tab管理的入口
        if tab_id == 'other':
            return False
        return True
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    
                    self.tab_order = data.get('tab_order', [])
                    self.tab_visibility = data.get('tab_visibility', {})
                    self.custom_tabs = data.get('custom_tabs', [])
                    self.custom_cards = data.get('custom_cards', [])
                    
                    logger.info(f"{self.tr('成功加载Tab配置')}")
            else:
                # 创建默认配置
                self._create_default_config()
                self.save_config()
                logger.info(self.tr("创建默认Tab配置"))
                
        except Exception as e:
            logger.exception(f"{self.tr('加载Tab配置失败:')} {e}")
            self._create_default_config()
            self.save_config()
    
    def save_config(self):
        """保存配置（带防抖机制）"""
        try:
            # 如果已经有待保存的请求，标记为待保存
            if self._save_timer and self._save_timer.isActive():
                self._pending_save = True
                return True
            
            # 创建防抖定时器
            if self._save_timer is None:
                from PySide6.QtCore import QTimer
                self._save_timer = QTimer()
                self._save_timer.setSingleShot(True)
                self._save_timer.timeout.connect(self._do_save_config)
            
            # 延迟100ms保存，避免频繁写入
            self._save_timer.start(100)
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('保存Tab配置失败:')} {e}")
            return False
    
    def _do_save_config(self):
        """执行实际的配置保存"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            data = {
                'tab_order': self.tab_order,
                'tab_visibility': self.tab_visibility,
                'custom_tabs': self.custom_tabs,
                'custom_cards': self.custom_cards,
                'version': '1.0',
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"{self.tr('Tab配置已保存')}")
            self.tab_config_updated.emit()
            
            # 如果还有待保存的请求，继续保存
            if self._pending_save:
                self._pending_save = False
                self._do_save_config()
            
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('保存Tab配置失败:')} {e}")
            return False
    
    def _create_default_config(self):
        """创建默认配置"""
        self.tab_order = [tab['id'] for tab in self.default_tabs]
        self.tab_visibility = {tab['id']: tab['visible'] for tab in self.default_tabs}
        self.custom_tabs = []
        self.custom_cards = []
    
    def _fix_tab_order(self):
        """修复tab_order，确保包含所有默认tab和自定义tab"""
        try:
            # 获取所有应该存在的tab ID
            all_tab_ids = set()
            
            # 添加所有默认tab
            for tab in self.default_tabs:
                all_tab_ids.add(tab['id'])
            
            # 添加所有自定义tab
            for tab in self.custom_tabs:
                all_tab_ids.add(tab['id'])
            
            # 找出缺失的tab
            missing_tabs = all_tab_ids - set(self.tab_order)
            
            if missing_tabs:
                logger.info(f"{self.tr('发现缺失的Tab，正在修复tab_order:')} {missing_tabs}")
                
                # 对于缺失的默认tab，按照default_tabs的顺序插入到合适位置
                for tab in self.default_tabs:
                    if tab['id'] in missing_tabs:
                        # 找到该tab在default_tabs中的位置
                        default_index = self.default_tabs.index(tab)
                        # 找到应该插入的位置：找到tab_order中最后一个位置小于default_index的默认tab
                        insert_pos = len(self.tab_order)
                        for i, tid in enumerate(self.tab_order):
                            tid_default_index = next((j for j, t in enumerate(self.default_tabs) if t['id'] == tid), -1)
                            if tid_default_index >= 0 and tid_default_index < default_index:
                                insert_pos = i + 1
                            elif tid_default_index >= 0 and tid_default_index > default_index:
                                insert_pos = i
                                break
                        self.tab_order.insert(insert_pos, tab['id'])
                        logger.debug(f"{self.tr('已添加默认Tab到tab_order:')} {tab['id']} (位置: {insert_pos})")
                
                # 对于缺失的自定义tab，添加到自定义tab区域
                for tab in self.custom_tabs:
                    if tab['id'] in missing_tabs:
                        # 找到最后一个自定义tab的位置
                        last_custom_index = -1
                        for i, tid in enumerate(self.tab_order):
                            if any(t['id'] == tid for t in self.custom_tabs):
                                last_custom_index = i
                        if last_custom_index >= 0:
                            self.tab_order.insert(last_custom_index + 1, tab['id'])
                        else:
                            # 如果没有自定义tab，添加到末尾
                            self.tab_order.append(tab['id'])
                        logger.debug(f"{self.tr('已添加自定义Tab到tab_order:')} {tab['id']}")
                
                logger.info(f"{self.tr('tab_order修复完成')}")
            
        except Exception as e:
            logger.exception(f"{self.tr('修复tab_order失败:')} {e}")
    
    def get_tab_order(self):
        """获取tab顺序"""
        return self.tab_order
    
    def set_tab_order(self, order):
        """设置tab顺序"""
        self.tab_order = order
        self.save_config()
    
    def get_tab_visibility(self):
        """获取tab显示状态"""
        return self.tab_visibility
    
    def set_tab_visibility(self, tab_id, visible):
        """设置tab显示状态"""
        # 检查Tab是否可以隐藏
        if not visible and not self.can_hide_tab(tab_id):
            logger.warning(f"{self.tr('Tab')} '{tab_id}' {self.tr('不能隐藏')}")
            return False
        
        # 如果tab不在tab_order中，需要先添加到tab_order
        # 这样可以确保即使配置不完整，tab也能正常显示/隐藏
        if tab_id not in self.tab_order:
            # 检查是否是默认tab或自定义tab
            is_default_tab = any(tab['id'] == tab_id for tab in self.default_tabs)
            is_custom_tab = any(tab['id'] == tab_id for tab in self.custom_tabs)
            
            if not is_default_tab and not is_custom_tab:
                logger.warning(f"{self.tr('Tab')} '{tab_id}' {self.tr('不存在，无法设置可见性')}")
                return False
            
            # 对于默认tab，尝试按照default_tabs的顺序插入到合适位置
            if is_default_tab:
                # 找到该tab在default_tabs中的位置
                default_index = next((i for i, tab in enumerate(self.default_tabs) if tab['id'] == tab_id), -1)
                if default_index >= 0:
                    # 尝试找到应该插入的位置：找到tab_order中最后一个位置小于default_index的默认tab
                    insert_pos = len(self.tab_order)
                    for i, tid in enumerate(self.tab_order):
                        tid_default_index = next((j for j, tab in enumerate(self.default_tabs) if tab['id'] == tid), -1)
                        if tid_default_index >= 0 and tid_default_index < default_index:
                            insert_pos = i + 1
                        elif tid_default_index >= 0 and tid_default_index > default_index:
                            insert_pos = i
                            break
                    self.tab_order.insert(insert_pos, tab_id)
                    logger.info(f"{self.tr('Tab')} '{tab_id}' {self.tr('已添加到tab_order，位置')}: {insert_pos}")
                else:
                    # 如果找不到，添加到末尾
                    self.tab_order.append(tab_id)
                    logger.info(f"{self.tr('Tab')} '{tab_id}' {self.tr('已添加到tab_order末尾')}")
            else:
                # 对于自定义tab，添加到自定义tab区域（在最后一个自定义tab之后）
                last_custom_index = -1
                for i, tid in enumerate(self.tab_order):
                    if any(tab['id'] == tid for tab in self.custom_tabs):
                        last_custom_index = i
                if last_custom_index >= 0:
                    self.tab_order.insert(last_custom_index + 1, tab_id)
                else:
                    # 如果没有自定义tab，添加到末尾
                    self.tab_order.append(tab_id)
                logger.info(f"{self.tr('Tab')} '{tab_id}' {self.tr('已添加到tab_order')}")
        
        self.tab_visibility[tab_id] = visible
        self.save_config()
        return True
    
    def get_visible_tabs(self):
        """获取可见的tab列表"""
        return [tab_id for tab_id in self.tab_order if self.tab_visibility.get(tab_id, True)]
    
    def get_all_tabs(self):
        """获取所有tab（包括自定义tab）"""
        all_tabs = []
        
        # 添加默认tab
        for tab in self.default_tabs:
            tab_info = tab.copy()
            tab_info['visible'] = self.tab_visibility.get(tab['id'], True)
            
            # 确保"其他"选项卡始终可见
            if tab['id'] == 'other':
                tab_info['visible'] = True
            
            all_tabs.append(tab_info)
        
        # 添加自定义tab
        for custom_tab in self.custom_tabs:
            tab_info = custom_tab.copy()
            tab_info['visible'] = self.tab_visibility.get(custom_tab['id'], True)
            tab_info['custom'] = True
            all_tabs.append(tab_info)
        
        return all_tabs
    
    def create_custom_tab(self, tab_data):
        """创建自定义tab"""
        try:
            # 生成唯一ID
            tab_id = f"custom_{len(self.custom_tabs) + 1:03d}"
            
            custom_tab = {
                'id': tab_id,
                'name': tab_data.get('name', self.tr('自定义Tab')),
                'description': tab_data.get('description', ''),
                'cards': tab_data.get('cards', []),
                'created_time': datetime.datetime.now().isoformat(),
                'visible': True
            }
            
            self.custom_tabs.append(custom_tab)
            self.tab_order.append(tab_id)
            self.tab_visibility[tab_id] = True
            
            self.save_config()
            self.custom_tab_created.emit(custom_tab)
            
            logger.info(f"{self.tr('成功创建自定义Tab:')} {custom_tab['name']}")
            return tab_id
            
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Tab失败:')} {e}")
            return None
    
    def delete_custom_tab(self, tab_id):
        """删除自定义tab"""
        try:
            # 从自定义tab列表中移除
            self.custom_tabs = [tab for tab in self.custom_tabs if tab['id'] != tab_id]
            
            # 从tab顺序中移除
            if tab_id in self.tab_order:
                self.tab_order.remove(tab_id)
            
            # 从可见性配置中移除
            self.tab_visibility.pop(tab_id, None)
            
            self.save_config()
            self.custom_tab_deleted.emit(tab_id)
            
            logger.info(f"{self.tr('成功删除自定义Tab:')} {tab_id}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('删除自定义Tab失败:')} {e}")
            return False
    
    def update_custom_tab(self, tab_id, tab_data):
        """更新自定义tab"""
        try:
            # 查找要更新的Tab
            old_tab = None
            for i, tab in enumerate(self.custom_tabs):
                if tab['id'] == tab_id:
                    old_tab = tab.copy()
                    self.custom_tabs[i].update(tab_data)
                    break
            
            if old_tab is None:
                logger.error(f"{self.tr('未找到Tab:')} {tab_id}")
                return False
            
            # 如果Tab名称发生变化，需要更新相关的Button
            old_name = old_tab.get('name', '')
            new_name = tab_data.get('name', '')
            if old_name != new_name and old_name:
                self._update_buttons_for_tab_name_change(old_name, new_name)
            
            self.save_config()
            logger.info(f"{self.tr('成功更新自定义Tab:')} {tab_id}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('更新自定义Tab失败:')} {e}")
            return False
    
    def _update_buttons_for_tab_name_change(self, old_name, new_name):
        """当Tab名称变化时，更新相关Button的tab字段"""
        try:
            # 尝试多种方式获取按钮管理器
            button_manager = None
            
            # 方式1：从父窗口获取
            if hasattr(self.parent(), 'custom_button_manager'):
                button_manager = self.parent().custom_button_manager
            
            # 方式2：从主窗口获取
            elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'custom_button_manager'):
                button_manager = self.parent().parent().custom_button_manager
            
            # 方式3：直接导入并创建实例（作为备选方案）
            if button_manager is None:
                try:
                    from core.custom_button_manager import CustomButtonManager
                    button_manager = CustomButtonManager()
                except Exception as e:
                    logger.warning(f"{self.tr('无法获取按钮管理器:')} {e}")
                    return
            
            # 更新所有相关按钮的tab字段
            updated_count = 0
            for button in button_manager.buttons:
                if button.get('tab') == old_name:
                    button['tab'] = new_name
                    updated_count += 1
            
            if updated_count > 0:
                button_manager.save_buttons()
                logger.info(f"{self.tr('已更新')} {updated_count} {self.tr('个按钮的Tab名称:')} {old_name} -> {new_name}")
            else:
                logger.info(f"{self.tr('没有找到需要更新的按钮')}")
                    
        except Exception as e:
            logger.exception(f"{self.tr('更新按钮Tab名称失败:')} {e}")
    
    def _update_buttons_for_card_name_change(self, tab_name, old_card_name, new_card_name):
        """当Card名称变化时，更新相关Button的card字段"""
        try:
            # 尝试多种方式获取按钮管理器
            button_manager = None
            
            # 方式1：从父窗口获取
            if hasattr(self.parent(), 'custom_button_manager'):
                button_manager = self.parent().custom_button_manager
            
            # 方式2：从主窗口获取
            elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'custom_button_manager'):
                button_manager = self.parent().parent().custom_button_manager
            
            # 方式3：直接导入并创建实例（作为备选方案）
            if button_manager is None:
                try:
                    from core.custom_button_manager import CustomButtonManager
                    button_manager = CustomButtonManager()
                except Exception as e:
                    logger.warning(f"{self.tr('无法获取按钮管理器:')} {e}")
                    return
            
            # 更新所有相关按钮的card字段（需要同时匹配tab和card名称）
            updated_count = 0
            for button in button_manager.buttons:
                # 规范化card名称用于匹配（去除多余空格）
                btn_tab = button.get('tab', '')
                btn_card = button.get('card', '')
                normalized_btn_card = ' '.join(btn_card.split()) if btn_card else ''
                normalized_old_card = ' '.join(old_card_name.split()) if old_card_name else ''
                
                if btn_tab == tab_name and normalized_btn_card == normalized_old_card:
                    button['card'] = new_card_name
                    updated_count += 1
            
            if updated_count > 0:
                button_manager.save_buttons()
                logger.info(f"{self.tr('已更新')} {updated_count} {self.tr('个按钮的Card名称:')} {old_card_name} -> {new_card_name}")
            else:
                logger.info(f"{self.tr('没有找到需要更新的按钮')}")
                    
        except Exception as e:
            logger.exception(f"{self.tr('更新按钮Card名称失败:')} {e}")
    
    def create_custom_card(self, card_data):
        """创建自定义card"""
        try:
            card_id = f"card_{len(self.custom_cards) + 1:03d}"
            
            custom_card = {
                'id': card_id,
                'name': card_data.get('name', self.tr('自定义Card')),
                'description': card_data.get('description', ''),
                'tab_id': card_data.get('tab_id', ''),
                'buttons': card_data.get('buttons', []),
                'created_time': datetime.datetime.now().isoformat()
            }
            
            self.custom_cards.append(custom_card)
            self.save_config()
            
            logger.info(f"{self.tr('成功创建自定义Card:')} {custom_card['name']}")
            return card_id
            
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Card失败:')} {e}")
            return None
    
    def get_custom_cards_by_tab(self, tab_id):
        """获取指定tab的自定义card"""
        return [card for card in self.custom_cards if card.get('tab_id') == tab_id]
    
    def update_custom_card(self, card_id, card_data):
        """更新自定义card"""
        try:
            # 查找要更新的Card
            old_card = None
            for i, card in enumerate(self.custom_cards):
                if card['id'] == card_id:
                    old_card = card.copy()
                    self.custom_cards[i].update(card_data)
                    break
            
            if old_card is None:
                logger.error(f"{self.tr('未找到Card:')} {card_id}")
                return False
            
            # 如果Card名称发生变化，需要更新相关的Button
            old_card_name = old_card.get('name', '')
            new_card_name = card_data.get('name', '')
            
            # 获取Tab名称
            tab_id = card_data.get('tab_id', old_card.get('tab_id', ''))
            tab_name = None
            all_tabs = self.get_all_tabs()
            for tab in all_tabs:
                if tab['id'] == tab_id:
                    tab_name = tab['name']
                    break
            
            # 如果Card名称改变且找到了Tab名称，更新相关按钮
            if old_card_name != new_card_name and old_card_name and tab_name:
                self._update_buttons_for_card_name_change(tab_name, old_card_name, new_card_name)
            
            self.save_config()
            logger.info(f"{self.tr('成功更新自定义Card:')} {card_id}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('更新自定义Card失败:')} {e}")
            return False
    
    def delete_custom_card(self, card_id):
        """删除自定义card"""
        try:
            self.custom_cards = [card for card in self.custom_cards if card['id'] != card_id]
            self.save_config()
            
            logger.info(f"{self.tr('成功删除自定义Card:')} {card_id}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('删除自定义Card失败:')} {e}")
            return False
    
    def reorder_custom_cards(self, ordered_ids):
        """根据ID顺序重新排列自定义Card"""
        try:
            if not ordered_ids:
                logger.warning(self.tr("重新排序Card失败：ID列表为空"))
                return False

            id_to_card = {card['id']: card for card in self.custom_cards}
            new_order = []

            for card_id in ordered_ids:
                if card_id in id_to_card:
                    new_order.append(id_to_card.pop(card_id))

            # 将未包含的Card附加到末尾，防止丢失
            if id_to_card:
                new_order.extend(id_to_card.values())

            if new_order == self.custom_cards:
                return True

            self.custom_cards = new_order
            return self.save_config()

        except Exception as e:
            logger.exception(f"{self.tr('重新排序自定义Card失败:')} {e}")
            return False

    def get_config_info(self):
        """获取配置信息"""
        return {
            'tab_count': len(self.tab_order),
            'custom_tab_count': len(self.custom_tabs),
            'custom_card_count': len(self.custom_cards),
            'config_file': self.config_file,
            'visible_tabs': self.get_visible_tabs()
        }
    
    def get_custom_cards_for_tab(self, tab_id):
        """获取指定Tab的自定义Card列表"""
        return [card for card in self.custom_cards if card.get('tab_id') == tab_id]
    
    def reset_to_default(self):
        """重置为默认配置"""
        try:
            self._create_default_config()
            self.save_config()
            logger.info(self.tr("已重置为默认Tab配置"))
            return True
            
        except Exception as e:
            logger.exception(f"{self.tr('重置配置失败:')} {e}")
            return False
