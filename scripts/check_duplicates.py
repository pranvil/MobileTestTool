#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 translations.json 中的重复键
"""

import json
import os
import sys

def check_duplicates(translations_file):
    """检查并报告重复的键"""
    with open(translations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    keys = list(data['zh'].keys())
    seen = {}
    duplicates = []
    
    for i, key in enumerate(keys):
        if key in seen:
            duplicates.append((key, seen[key], i))
        else:
            seen[key] = i
    
    print(f"总键数: {len(keys)}")
    print(f"唯一键数: {len(seen)}")
    print(f"重复键数: {len(duplicates)}")
    
    if duplicates:
        print("\n重复的键:")
        for i, (key, first_pos, dup_pos) in enumerate(duplicates[:100], 1):
            print(f"  {i}. \"{key}\"")
            print(f"     首次出现: 第 {first_pos+1} 行")
            print(f"     重复位置: 第 {dup_pos+1} 行")
            print(f"     值1: {data['zh'][key]}")
            print()
    
    return duplicates

def remove_duplicates(translations_file):
    """删除重复的键，保留第一个出现的"""
    with open(translations_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data['zh'])
    seen = {}
    new_translations = {}
    removed = []
    
    for key, value in data['zh'].items():
        if key not in seen:
            seen[key] = True
            new_translations[key] = value
        else:
            removed.append(key)
    
    data['zh'] = new_translations
    
    print(f"原始键数: {original_count}")
    print(f"删除重复后: {len(new_translations)}")
    print(f"删除了 {len(removed)} 个重复项")
    
    if removed:
        print("\n删除的重复键:")
        for key in removed[:50]:
            print(f"  - \"{key}\"")
        if len(removed) > 50:
            print(f"  ... 还有 {len(removed) - 50} 个")
    
    # 保存文件
    with open(translations_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n文件已保存: {translations_file}")

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    translations_file = os.path.join(project_root, 'translations.json')
    
    print("检查重复项...")
    duplicates = check_duplicates(translations_file)
    
    if duplicates:
        print(f"\n找到 {len(duplicates)} 个重复项")
        print("自动删除重复项...")
        remove_duplicates(translations_file)
    else:
        print("\n没有找到重复项！")
