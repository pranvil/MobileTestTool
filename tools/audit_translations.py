#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Audit Tool
Used to check if translation strings in code are defined in translations.json
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Set, Dict, List, Tuple


class TranslationAuditor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.translations_file = self.project_root / "translations.json"
        self.translations = {}
        self.code_keys = set()
        self.missing_keys = set()
        
    def load_translations(self):
        """Load translations.json file"""
        if not self.translations_file.exists():
            print(f"[ERROR] Translation file not found: {self.translations_file}")
            return False
            
        try:
            with open(self.translations_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"[OK] Loaded translation file: {len(self.translations.get('zh', {}))} Chinese, {len(self.translations.get('en', {}))} English translations")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load translation file: {e}")
            return False
    
    def extract_tr_calls(self, file_path: Path) -> Set[str]:
        """Extract tr() call strings from Python files"""
        keys = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Match various tr() call patterns
            patterns = [
                r'self\.tr\([\'"]([^\'"]+)[\'"]\)',  # self.tr('string')
                r'lang_manager\.tr\([\'"]([^\'"]+)[\'"]\)',  # lang_manager.tr('string')
                r'tr_callback\([\'"]([^\'"]+)[\'"]\)',  # tr_callback('string')
                r'tr\([\'"]([^\'"]+)[\'"]\)',  # tr('string')
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                keys.update(matches)
                
        except Exception as e:
            print(f"[WARNING] Failed to read file {file_path}: {e}")
            
        return keys
    
    def scan_code_files(self):
        """Scan all Python files and extract translation strings"""
        print("[INFO] Scanning code files...")
        
        # Scan core directory
        core_dir = self.project_root / "core"
        if core_dir.exists():
            for py_file in core_dir.glob("*.py"):
                keys = self.extract_tr_calls(py_file)
                if keys:
                    self.code_keys.update(keys)
                    print(f"  [FILE] {py_file.relative_to(self.project_root)}: {len(keys)} translation strings")
        
        # Scan ui directory
        ui_dir = self.project_root / "ui"
        if ui_dir.exists():
            for py_file in ui_dir.rglob("*.py"):
                keys = self.extract_tr_calls(py_file)
                if keys:
                    self.code_keys.update(keys)
                    print(f"  [FILE] {py_file.relative_to(self.project_root)}: {len(keys)} translation strings")
        
        # Scan main file
        main_file = self.project_root / "main.py"
        if main_file.exists():
            keys = self.extract_tr_calls(main_file)
            if keys:
                self.code_keys.update(keys)
                print(f"  [FILE] {main_file.relative_to(self.project_root)}: {len(keys)} translation strings")
        
        print(f"[OK] Found {len(self.code_keys)} translation strings in total")
    
    def find_missing_translations(self):
        """Find missing translations"""
        print("\n[INFO] Checking for missing translations...")
        
        zh_translations = self.translations.get('zh', {})
        en_translations = self.translations.get('en', {})
        
        missing_zh = []
        missing_en = []
        
        for key in self.code_keys:
            if key not in zh_translations:
                missing_zh.append(key)
            if key not in en_translations:
                missing_en.append(key)
        
        self.missing_keys = set(missing_zh + missing_en)
        
        print(f"[STATS] Translation coverage:")
        print(f"  Translation strings in code: {len(self.code_keys)}")
        print(f"  Chinese translations: {len(zh_translations)}")
        print(f"  English translations: {len(en_translations)}")
        print(f"  Missing Chinese translations: {len(missing_zh)}")
        print(f"  Missing English translations: {len(missing_en)}")
        
        return missing_zh, missing_en
    
    def save_missing_keys(self, missing_zh: List[str], missing_en: List[str]):
        """Save missing translation keys to file"""
        missing_file = self.project_root / "missing_tr_keys.txt"
        
        with open(missing_file, 'w', encoding='utf-8') as f:
            f.write("Missing translation keys:\n\n")
            
            if missing_zh:
                f.write("Missing Chinese translations:\n")
                for key in sorted(missing_zh):
                    f.write(f"  - {key}\n")
                f.write("\n")
            
            if missing_en:
                f.write("Missing English translations:\n")
                for key in sorted(missing_en):
                    f.write(f"  - {key}\n")
        
        print(f"[OK] Missing translation keys saved to: {missing_file}")
    
    def generate_suggestions(self):
        """Generate translation suggestions"""
        suggestions_file = self.project_root / "tr_usage_suggestions.txt"
        
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            f.write("Translation usage suggestions:\n\n")
            
            # Check self.lang_manager.tr usage
            f.write("Optimization suggestions:\n")
            f.write("- Change self.lang_manager.tr(...) to self.tr(...) for simplicity\n")
            f.write("- Ensure all classes have tr() method or use self.lang_manager.tr(...)\n")
            f.write("- Use lang_manager.tr(...) in standalone functions or pass tr_callback parameter\n\n")
            
            # Statistics
            f.write("Statistics:\n")
            f.write(f"- Total translation strings in code: {len(self.code_keys)}\n")
            f.write(f"- Defined Chinese translations: {len(self.translations.get('zh', {}))}\n")
            f.write(f"- Defined English translations: {len(self.translations.get('en', {}))}\n")
        
        print(f"[OK] Translation suggestions saved to: {suggestions_file}")
    
    def audit(self, save_missing: bool = True, generate_suggestions: bool = True):
        """Perform complete translation audit"""
        print("=" * 60)
        print("Translation Audit Tool")
        print("=" * 60)
        
        # Load translation file
        if not self.load_translations():
            return False
        
        # Scan code files
        self.scan_code_files()
        
        # Find missing translations
        missing_zh, missing_en = self.find_missing_translations()
        
        # Save results
        if save_missing and (missing_zh or missing_en):
            self.save_missing_keys(missing_zh, missing_en)
        
        if generate_suggestions:
            self.generate_suggestions()
        
        # Show detailed results
        if missing_zh:
            print(f"\n[ERROR] Missing Chinese translations ({len(missing_zh)}):")
            try:
                for key in sorted(missing_zh)[:10]:  # Show only first 10
                    print(f"  - {key}")
                if len(missing_zh) > 10:
                    print(f"  ... and {len(missing_zh) - 10} more")
            except UnicodeEncodeError:
                print("  [Chinese characters cannot be displayed in this terminal]")
        
        if missing_en:
            print(f"\n[ERROR] Missing English translations ({len(missing_en)}):")
            try:
                for key in sorted(missing_en)[:10]:  # Show only first 10
                    print(f"  - {key}")
                if len(missing_en) > 10:
                    print(f"  ... and {len(missing_en) - 10} more")
            except UnicodeEncodeError:
                print("  [Some characters cannot be displayed in this terminal]")
        
        if not missing_zh and not missing_en:
            print("\n[OK] All translations are complete!")
        
        print("\n" + "=" * 60)
        return True


def main():
    parser = argparse.ArgumentParser(description="Translation Audit Tool")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--no-save", action="store_true", help="Don't save missing translation keys")
    parser.add_argument("--no-suggestions", action="store_true", help="Don't generate suggestions file")
    parser.add_argument("--all", action="store_true", help="Show all missing translations")
    
    args = parser.parse_args()
    
    auditor = TranslationAuditor(args.project_root)
    success = auditor.audit(
        save_missing=not args.no_save,
        generate_suggestions=not args.no_suggestions
    )
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()