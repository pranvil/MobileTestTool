#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加缺失的翻译并检查重复项
"""

import json
import re
import os

def extract_missing_translations(failures_file):
    """从翻译失败日志中提取缺失的翻译文本"""
    missing_texts = set()
    
    with open(failures_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('例如：'):
                continue
            
            # 提取时间戳后的文本
            if '] ' in line:
                text = line.split('] ', 1)[1].strip()
                if text:
                    missing_texts.add(text)
    
    return missing_texts

def load_translations(translations_file):
    """加载翻译文件"""
    with open(translations_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_duplicates(translations):
    """检查并返回重复的键"""
    seen = {}
    duplicates = []
    
    for key in translations['zh'].keys():
        if key in seen:
            duplicates.append(key)
        else:
            seen[key] = True
    
    return duplicates

def add_missing_translations(translations, missing_texts):
    """添加缺失的翻译"""
    added_count = 0
    
    # 定义翻译映射
    translation_map = {
        "正在初始化...": "Initializing...",
        "个自定义按钮": " custom buttons",
        "成功加载Tab配置": "Successfully loaded Tab configuration",
        "Root&&Remount": "Root&&Remount",
        "点击切换语言 / Click to switch language": "Click to switch language",
        "开始初始化所有Tab页面...": "Starting to initialize all Tab pages...",
        "log操作:": "Log operations:",
        "PR翻译 - 将中文PR内容翻译成英文并生成Word文档": "PR Translation - Translate Chinese PR content to English and generate Word document",
        "转码工具 - ASCII和GSM 7-bit编码的双向转换": "Encoding Tool - Bidirectional conversion of ASCII and GSM 7-bit encoding",
        "日志区域行数": "Log area line count",
        "所有Tab页面初始化完成": "All Tab pages initialized",
        "支持快速执行一次性ADB命令": "Supports quick execution of one-time ADB commands",
        "例如: adb devices, adb shell pm list packages 等": "For example: adb devices, adb shell pm list packages, etc.",
        "不支持持续输出命令（logcat、top等），请使用对应功能": "Continuous output commands (logcat, top, etc.) are not supported, please use corresponding features",
        "提示: 使用上下键可以浏览历史命令": "Tip: Use up/down arrow keys to browse command history",
        "拉取 Bugreport": "Pull Bugreport",
        "Ping": "Ping",
        "开始为所有Tab加载自定义按钮...": "Starting to load custom buttons for all Tabs...",
        "处理预制Tab:": "Processing predefined Tabs:",
        "默认": "Default",
        "尝试向预制卡片": "Attempting to inject into predefined card",
        "注入": "Inject",
        "个按钮": " buttons",
        "找到": "Found",
        "个Frame": " frames",
        "找到匹配的预制卡片:": "Found matching predefined card:",
        "直接使用QHBoxLayout作为按钮布局": "Directly using QHBoxLayout as button layout",
        "找到按钮布局，准备填充": "Found button layout, ready to populate",
        "添加自定义按钮": "Add custom button",
        "到": "to",
        "处理自定义Tab...": "Processing custom Tab...",
        "检查Tab:": "Check Tab:",
        "所有Tab的自定义按钮加载完成": "Custom buttons for all Tabs loaded",
        "语言已切换到:": "Language switched to:",
        "中文": "Chinese",
        "中/EN": "中/EN",
        "输入文件路径或点击浏览按钮选择...": "Enter file path or click browse button to select...",
        "浏览文件夹": "Browse Folder",
        "脚本\\命令": "Script\\Command",
        "输入ADB命令（多行支持，不需要加 'adb -s {device}'）...": "Enter ADB commands (multi-line supported, no need to add 'adb -s {device}')...",
        "Tab配置已保存": "Tab configuration saved",
        "检测到Tab配置更新，重新加载Tab...": "Tab configuration update detected, reloading Tab...",
        "此功能可以一键导出所有配置，包括：": "This feature can export all configurations with one click, including:",
        "• Tab配置管理": "• Tab Configuration Management",
        "• 自定义按钮": "• Custom Buttons",
        "• AT命令": "• AT Commands",
        "• 暗码数据": "• Secret Code Data",
        "• 高通NV数据": "• Qualcomm NV Data",
        "• Log关键字": "• Log Keywords",
        "连线ADB Log按钮被点击，当前is_running状态: ": "Online ADB Log button clicked, current is_running state: ",
        "开始录制视频": "Start Recording Video",
        "是否在MTKLOG启动成功后开始录制视频？": "Start recording video after MTKLOG starts successfully?",
        "注意：录制视频过程中USB连接不能断开。": "Note: USB connection cannot be disconnected during video recording.",
        "尝试连接设备:": "Attempting to connect device:",
        "停止并导出 MTKLOG...": "Stopping and exporting MTKLOG...",
        "设备连接成功，查找按钮:": "Device connected successfully, finding button:",
        "按钮存在，checked状态:": "Button exists, checked state:",
        "是否导出手机录制的视频和截图？": "Export videos and screenshots recorded on the phone?",
        "选择": "Select",
        "是": "Yes",
        "将导出这些媒体文件。": "These media files will be exported.",
        "开始停止并导出MTKLOG操作，设备:": "Starting stop and export MTKLOG operation, device:",
        ", 日志名称:": ", log name:",
        ", 导出媒体:": ", export media:",
        "检查并停止视频录制进程...": "Checking and stopping video recording process...",
        "未检测到screenrecord进程": "No screenrecord process detected",
        "屏幕状态检查完成": "Screen status check completed",
        "启动logger应用命令:": "Start logger app command:",
        "启动应用结果 - returncode:": "Start app result - returncode:",
        "Logger正在运行，开始执行停止命令": "Logger is running, starting stop command",
        "执行停止命令:": "Executing stop command:",
        "停止命令执行结果 - returncode:": "Stop command execution result - returncode:",
        "停止命令stdout:": "Stop command stdout:",
        "停止命令stderr:": "Stop command stderr:",
        "设置 MTKLOG 大小...": "Setting MTKLOG size...",
        "第": "th",
        "次检查按钮状态，已等待": " time checking button status, waited",
        "秒": " seconds",
        "可用存储容量: 正在获取...": "Available storage capacity: Getting...",
        "可用存储容量: {} MB": "Available storage capacity: {} MB",
        "Logger已成功停止，checked=false": "Logger stopped successfully, checked=false",
        "停止检查完成，总耗时:": "Stop check completed, total time:",
        "秒，检查次数:": " seconds, check count:",
        "创建目录:": "Creating directory:",
        "创建日志文件夹:": "Creating log folder:",
        "检查文件夹:": "Checking folder:",
        "检查命令结果 - returncode:": "Check command result - returncode:",
        "文件夹不存在，跳过:": "Folder does not exist, skipping:",
        "正在导出": "Exporting",
        "执行pull命令:": "Executing pull command:",
        "Pull命令结果 - returncode:": "Pull command result - returncode:",
        "导出成功": "Export successful",
        "MTKLOG停止并导出操作完成，导出路径:": "MTKLOG stop and export operation completed, export path:",
        "MTKLOG已导出到: ": "MTKLOG exported to: ",
        "设置 MTKLOG SD模式...": "Setting MTKLOG SD mode...",
        "已设置为SD模式 -": "Set to SD mode -",
        "设置 MTKLOG USB模式...": "Setting MTKLOG USB mode...",
        "已设置为USB模式 -": "Set to USB mode -",
        "安装 MTKLOGGER...": "Installing MTKLOGGER...",
    }
    
    for text in missing_texts:
        if text not in translations['zh']:
            # 如果翻译映射中有，使用映射；否则使用默认翻译
            if text in translation_map:
                translations['zh'][text] = translation_map[text]
                added_count += 1
            else:
                # 对于没有映射的文本，暂时使用原文（后续可以手动添加）
                print(f"Warning: No translation for '{text}', using original text")
                translations['zh'][text] = text
                added_count += 1
    
    return added_count

def remove_duplicates(translations):
    """删除重复的键，保留第一个出现的"""
    seen = {}
    new_translations = {}
    removed_count = 0
    
    for key, value in translations['zh'].items():
        if key not in seen:
            seen[key] = True
            new_translations[key] = value
        else:
            removed_count += 1
            print(f"Removed duplicate: '{key}'")
    
    translations['zh'] = new_translations
    return removed_count

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failures_file = os.path.join(project_root, 'logs', 'translation_failures.txt')
    translations_file = os.path.join(project_root, 'translations.json')
    
    print("提取缺失的翻译...")
    missing_texts = extract_missing_translations(failures_file)
    print(f"找到 {len(missing_texts)} 个缺失的翻译文本")
    
    print("加载翻译文件...")
    translations = load_translations(translations_file)
    
    print("检查重复项...")
    duplicates = check_duplicates(translations)
    if duplicates:
        print(f"找到 {len(duplicates)} 个重复的键")
        for dup in duplicates:
            print(f"  - {dup}")
    else:
        print("没有找到重复的键")
    
    print("添加缺失的翻译...")
    added_count = add_missing_translations(translations, missing_texts)
    print(f"添加了 {added_count} 个翻译")
    
    print("删除重复项...")
    removed_count = remove_duplicates(translations)
    print(f"删除了 {removed_count} 个重复项")
    
    print("保存翻译文件...")
    with open(translations_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)
    
    print("完成！")

if __name__ == '__main__':
    main()
