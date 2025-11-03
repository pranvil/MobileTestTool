#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新器
负责在主程序退出后解压更新包并覆盖文件，然后重启主程序
"""

import os
import sys
import time
import shutil
import zipfile
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_main_exe_path():
    """获取主程序可执行文件路径"""
    if is_pyinstaller():
        # 在打包环境中，更新器exe和主程序exe应该在同一个目录
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        # 假设主程序名为 MobileTestTool.exe，更新器名为 updater.exe
        main_exe = os.path.join(exe_dir, "MobileTestTool.exe")
        if os.path.exists(main_exe):
            return main_exe
    
    # 开发环境中，尝试查找主程序
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(script_dir, "main.py")
    if os.path.exists(main_py):
        return (sys.executable, main_py)
    
    # 如果找不到，返回当前目录下的 MobileTestTool.exe
    current_dir = os.path.dirname(os.path.abspath(sys.executable))
    return os.path.join(current_dir, "MobileTestTool.exe")


def wait_for_process_exit(process_name: str, timeout: int = 30) -> bool:
    """等待指定进程退出"""
    print(f"等待进程 {process_name} 退出...")
    start_time = time.time()
    
    # 尝试使用psutil
    try:
        import psutil
        use_psutil = True
    except ImportError:
        use_psutil = False
    
    while time.time() - start_time < timeout:
        found = False
        
        if use_psutil:
            # 使用psutil检查进程
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    proc_exe = proc_info.get('exe', '')
                    
                    # 检查进程名或可执行文件路径
                    if process_name.lower() in proc_name.lower():
                        if 'MobileTestTool' in proc_name or 'MobileTestTool' in (proc_exe or ''):
                            # 排除自己（更新器）
                            if 'updater' not in proc_name.lower() and 'updater' not in (proc_exe or '').lower():
                                found = True
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        else:
            # 使用tasklist命令检查进程（Windows）
            if sys.platform.startswith('win'):
                try:
                    result = subprocess.run(
                        ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    if process_name.lower() in result.stdout.lower():
                        # 检查是否包含MobileTestTool且不包含updater
                        lines = result.stdout.lower().split('\n')
                        for line in lines:
                            if 'mobiletesttool' in line and 'updater' not in line:
                                found = True
                                break
                except Exception:
                    pass
        
        if not found:
            print(f"进程 {process_name} 已退出")
            return True
        
        time.sleep(0.5)
    
    print(f"警告：等待进程退出超时（{timeout}秒）")
    return False


def check_process_running(process_name: str) -> bool:
    """检查进程是否正在运行"""
    try:
        import psutil
        use_psutil = True
    except ImportError:
        use_psutil = False
    
    if use_psutil:
        # 使用psutil检查进程
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                proc_info = proc.info
                proc_name = proc_info.get('name', '')
                proc_exe = proc_info.get('exe', '')
                if 'MobileTestTool' in proc_name or 'MobileTestTool' in (proc_exe or ''):
                    # 排除自己（更新器）
                    if 'updater' not in proc_name.lower() and 'updater' not in (proc_exe or '').lower():
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    else:
        # 使用tasklist命令检查进程（Windows）
        try:
            if sys.platform.startswith('win'):
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if process_name.lower() in result.stdout.lower():
                    # 检查是否包含MobileTestTool且不包含updater
                    lines = result.stdout.lower().split('\n')
                    for line in lines:
                        if 'mobiletesttool' in line and 'updater' not in line:
                            return True
        except Exception:
            pass
    
    return False


def backup_directory(source_dir: str, backup_dir: str) -> Tuple[bool, str]:
    """备份目录"""
    try:
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        
        if os.path.exists(source_dir):
            shutil.copytree(source_dir, backup_dir)
            print(f"已备份到: {backup_dir}")
            return True, ""
        else:
            return False, f"源目录不存在: {source_dir}"
    except Exception as e:
        return False, f"备份失败: {str(e)}"


def restore_backup(backup_dir: str, target_dir: str) -> Tuple[bool, str]:
    """恢复备份"""
    try:
        if not os.path.exists(backup_dir):
            return False, "备份目录不存在"
        
        # 删除目标目录
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        
        # 恢复备份
        shutil.copytree(backup_dir, target_dir)
        print(f"已从备份恢复: {backup_dir} -> {target_dir}")
        return True, ""
    except Exception as e:
        return False, f"恢复备份失败: {str(e)}"


def extract_zip(zip_path: str, extract_to: str) -> Tuple[bool, str]:
    """解压ZIP文件"""
    try:
        if not os.path.exists(zip_path):
            return False, f"ZIP文件不存在: {zip_path}"
        
        print(f"开始解压: {zip_path}")
        print(f"目标目录: {extract_to}")
        
        # 创建目标目录
        os.makedirs(extract_to, exist_ok=True)
        
        # 解压ZIP文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        print("解压完成")
        return True, ""
    except Exception as e:
        return False, f"解压失败: {str(e)}"


def copy_directory(source_dir: str, target_dir: str, exclude_patterns: Optional[list] = None) -> Tuple[bool, str]:
    """复制目录内容，支持排除特定模式"""
    exclude_patterns = exclude_patterns or []
    
    try:
        if not os.path.exists(source_dir):
            return False, f"源目录不存在: {source_dir}"
        
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        copied_files = 0
        failed_files = 0
        
        # 复制文件
        for root, dirs, files in os.walk(source_dir):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            # 计算相对路径
            rel_path = os.path.relpath(root, source_dir)
            target_root = os.path.join(target_dir, rel_path) if rel_path != '.' else target_dir
            
            # 创建目标目录
            os.makedirs(target_root, exist_ok=True)
            
            # 复制文件
            for file in files:
                if any(pattern in file for pattern in exclude_patterns):
                    continue
                
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_root, file)
                
                try:
                    # 如果目标文件存在且被锁定，先尝试删除
                    if os.path.exists(target_file):
                        try:
                            os.remove(target_file)
                        except PermissionError:
                            # 如果无法删除，尝试重命名
                            try:
                                temp_name = target_file + ".old"
                                if os.path.exists(temp_name):
                                    os.remove(temp_name)
                                os.rename(target_file, temp_name)
                            except Exception:
                                pass
                    
                    shutil.copy2(source_file, target_file)
                    copied_files += 1
                except Exception as e:
                    print(f"警告：复制文件失败 {source_file} -> {target_file}: {e}")
                    failed_files += 1
        
        print(f"目录复制完成: {source_dir} -> {target_dir}")
        print(f"已复制 {copied_files} 个文件，失败 {failed_files} 个文件")
        return True, ""
    except Exception as e:
        return False, f"复制目录失败: {str(e)}"


def atomic_replace(source_dir: str, target_dir: str, backup_dir: Optional[str] = None) -> Tuple[bool, str]:
    """原子性替换目录（先备份，再逐个替换文件，失败则恢复）"""
    try:
        # 1. 备份旧版本
        if backup_dir and os.path.exists(target_dir):
            success, error = backup_directory(target_dir, backup_dir)
            if not success:
                print(f"警告：备份失败: {error}，继续更新...")
        
        # 2. 直接复制新版本覆盖旧文件（不删除整个目录，避免删除正在运行的程序）
        print(f"开始替换文件: {source_dir} -> {target_dir}")
        success, error = copy_directory(source_dir, target_dir)
        if not success:
            # 如果复制失败，尝试恢复备份
            if backup_dir and os.path.exists(backup_dir):
                print("尝试恢复备份...")
                restore_backup(backup_dir, target_dir)
            return False, f"复制新版本失败: {error}"
        
        # 3. 清理旧文件（删除新版本中不存在的旧文件，但保留排除的文件）
        print("清理旧文件...")
        try:
            # 获取源目录中的所有文件路径（相对路径）
            source_files = set()
            for root, dirs, files in os.walk(source_dir):
                # 过滤排除的目录
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in ['logs', '*.log', '*.tmp'])]
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), source_dir)
                    source_files.add(rel_path.replace('\\', '/'))
            
            # 删除目标目录中不存在于源目录的文件（排除特定目录）
            deleted_count = 0
            for root, dirs, files in os.walk(target_dir):
                # 跳过排除的目录
                if any(pattern in root for pattern in ['logs', '_internal']):
                    continue
                
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    rel_path_normalized = rel_path.replace('\\', '/')
                    
                    # 如果文件不在新版本中，且不是排除的文件，则删除
                    if rel_path_normalized not in source_files:
                        if not any(pattern in file for pattern in ['*.log', '*.tmp']):
                            try:
                                old_file = os.path.join(root, file)
                                os.remove(old_file)
                                deleted_count += 1
                            except Exception as e:
                                print(f"警告：无法删除旧文件 {old_file}: {e}")
            
            if deleted_count > 0:
                print(f"已删除 {deleted_count} 个旧文件")
        except Exception as e:
            print(f"警告：清理旧文件时出错: {e}")
        
        print(f"替换完成: {target_dir}")
        return True, ""
    except Exception as e:
        # 如果出现异常，尝试恢复备份
        if backup_dir and os.path.exists(backup_dir):
            print("发生错误，尝试恢复备份...")
            restore_backup(backup_dir, target_dir)
        return False, f"替换过程出错: {str(e)}"


def restart_main_program(main_exe_path) -> Tuple[bool, str]:
    """重启主程序
    
    Args:
        main_exe_path: 主程序路径，可以是字符串（exe路径）或元组（python_exe, script_path）
    """
    try:
        # 启动主程序
        if isinstance(main_exe_path, tuple):
            # 开发环境：Python脚本
            python_exe, script_path = main_exe_path
            if not os.path.exists(script_path):
                return False, f"主程序脚本不存在: {script_path}"
            print(f"正在启动主程序: {python_exe} {script_path}")
            subprocess.Popen([python_exe, script_path], cwd=os.path.dirname(script_path))
        else:
            # 生产环境：可执行文件
            if not os.path.exists(main_exe_path):
                return False, f"主程序不存在: {main_exe_path}"
            print(f"正在启动主程序: {main_exe_path}")
            subprocess.Popen([main_exe_path], cwd=os.path.dirname(main_exe_path))
        
        print("主程序已启动")
        return True, ""
    except Exception as e:
        return False, f"启动主程序失败: {str(e)}"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MobileTestTool 自动更新器')
    parser.add_argument('zip_path', help='更新包ZIP文件路径')
    parser.add_argument('install_dir', help='安装目录（主程序所在目录）')
    parser.add_argument('--main-exe', help='主程序可执行文件路径（可选）')
    parser.add_argument('--process-name', default='MobileTestTool.exe', help='主进程名称')
    parser.add_argument('--wait-timeout', type=int, default=30, help='等待进程退出的超时时间（秒）')
    parser.add_argument('--no-backup', action='store_true', help='不备份旧版本')
    parser.add_argument('--exclude', nargs='*', help='排除的文件/目录模式')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MobileTestTool 自动更新器")
    print("=" * 60)
    print()
    
    # 检查ZIP文件
    if not os.path.exists(args.zip_path):
        print(f"错误：更新包不存在: {args.zip_path}")
        try:
            input("按回车键退出...")
        except Exception:
            pass  # 如果无法读取输入（非交互模式），直接退出
        sys.exit(1)
    
    # 检查安装目录
    if not os.path.exists(args.install_dir):
        print(f"错误：安装目录不存在: {args.install_dir}")
        try:
            input("按回车键退出...")
        except Exception:
            pass  # 如果无法读取输入（非交互模式），直接退出
        sys.exit(1)
    
    # 1. 等待主程序退出
    print("步骤 1/5: 等待主程序退出...")
    if not wait_for_process_exit(args.process_name, args.wait_timeout):
        print("警告：主程序可能仍在运行，继续更新可能会有风险")
        # 如果是在后台运行（没有控制台），自动继续；否则询问用户
        try:
            # 尝试检测是否有交互式控制台
            import sys
            if sys.stdin.isatty():
                reply = input("是否继续？(y/n): ")
                if reply.lower() != 'y':
                    print("更新已取消")
                    sys.exit(1)
            else:
                print("自动继续更新（非交互模式）")
        except Exception:
            # 如果检测失败，默认继续
            print("自动继续更新")
    
    # 再次确认进程已退出
    time.sleep(1)
    if check_process_running(args.process_name):
        print("错误：主程序仍在运行，无法更新")
        try:
            input("按回车键退出...")
        except Exception:
            pass  # 如果无法读取输入（非交互模式），直接退出
        sys.exit(1)
    
    # 2. 直接解压到当前目录
    print()
    print("步骤 2/3: 解压更新包到当前目录...")
    print(f"安装目录: {args.install_dir}")
    print(f"更新包: {args.zip_path}")
    
    # 直接读取 ZIP 文件列表，检查结构（不解压）
    try:
        with zipfile.ZipFile(args.zip_path, 'r') as zip_ref:
            zip_entries = zip_ref.namelist()
        
        # 分析 ZIP 结构：获取顶层目录/文件
        top_level_items = set()
        for entry in zip_entries:
            # 跳过目录条目
            if entry.endswith('/'):
                continue
            # 获取第一级路径
            first_level = entry.split('/')[0].split('\\')[0]
            if first_level:
                top_level_items.add(first_level)
        
        top_level_list = sorted(top_level_items)
        print(f"ZIP 顶层内容: {top_level_list}")
        
        # 判断 ZIP 结构
        has_subdir = False
        subdir_name = None
        
        if len(top_level_list) == 1:
            # 只有一个顶层项，可能是子目录
            potential_subdir = top_level_list[0]
            # 检查是否所有文件都在这个子目录下
            all_in_subdir = all(
                entry.startswith(potential_subdir + '/') or entry.startswith(potential_subdir + '\\')
                for entry in zip_entries if not entry.endswith('/')
            )
            if all_in_subdir and 'MobileTestTool' in potential_subdir:
                has_subdir = True
                subdir_name = potential_subdir
                print(f"检测到 ZIP 包含子目录: {subdir_name}")
        
        # 先等待一小段时间，确保文件完全解锁
        time.sleep(1)
        
        if has_subdir:
            # ZIP 包含子目录，需要解压到临时目录，然后复制子目录内容
            temp_extract_dir = os.path.join(tempfile.gettempdir(), f"MobileTestTool_extract_{int(time.time())}")
            try:
                print(f"解压到临时目录: {temp_extract_dir}")
                success, error = extract_zip(args.zip_path, temp_extract_dir)
                if not success:
                    print(f"错误：{error}")
                    try:
                        input("按回车键退出...")
                    except Exception:
                        pass
                    sys.exit(1)
                
                # 获取子目录路径
                subdir_path = os.path.join(temp_extract_dir, subdir_name)
                if os.path.exists(subdir_path):
                    # 复制子目录内容到安装目录
                    print(f"将 {subdir_name} 的内容复制到安装目录...")
                    success, error = copy_directory(subdir_path, args.install_dir, ['logs', '*.log', '*.tmp'])
                    if not success:
                        print(f"错误：{error}")
                        try:
                            input("按回车键退出...")
                        except Exception:
                            pass
                        sys.exit(1)
                else:
                    print(f"错误：找不到子目录 {subdir_path}")
                    sys.exit(1)
            finally:
                # 清理临时目录
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
        else:
            # ZIP 直接包含文件，直接解压到安装目录
            print("ZIP 直接包含文件，解压到安装目录...")
            success, error = extract_zip(args.zip_path, args.install_dir)
            if not success:
                print(f"错误：{error}")
                print("尝试清理旧文件后重试...")
                
                # 如果失败，尝试先清理 _internal 目录中的旧文件
                internal_dir = os.path.join(args.install_dir, "_internal")
                if os.path.exists(internal_dir):
                    print("清理 _internal 目录中的旧文件...")
                    try:
                        # 尝试删除整个 _internal 目录
                        shutil.rmtree(internal_dir, ignore_errors=True)
                        time.sleep(0.5)
                        # 重新解压
                        success, error = extract_zip(args.zip_path, args.install_dir)
                        if not success:
                            print(f"错误：{error}")
                            try:
                                input("按回车键退出...")
                            except Exception:
                                pass
                            sys.exit(1)
                    except Exception as e:
                        print(f"清理失败: {e}")
                        try:
                            input("按回车键退出...")
                        except Exception:
                            pass
                        sys.exit(1)
        
        print("解压完成！")
    except Exception as e:
        print(f"解压过程出错: {e}")
        import traceback
        traceback.print_exc()
        try:
            input("按回车键退出...")
        except Exception:
            pass
        sys.exit(1)
    
    # 3. 清理临时更新器文件（如果是从临时目录运行的）
    print()
    print("清理临时文件...")
    try:
        # 检查当前更新器是否在临时目录中运行
        current_exe = os.path.abspath(sys.executable)
        temp_dir = tempfile.gettempdir()
        if current_exe.startswith(temp_dir) and 'updater' in current_exe.lower():
            try:
                # 等待一小段时间，确保文件完全释放
                time.sleep(0.5)
                if os.path.exists(current_exe):
                    os.remove(current_exe)
                    print(f"已删除临时更新器: {current_exe}")
            except Exception as e:
                print(f"警告：无法删除临时更新器文件: {e}")
                # 尝试使用延迟删除（Windows）
                if sys.platform.startswith('win'):
                    try:
                        import ctypes
                        ctypes.windll.kernel32.MoveFileExW(current_exe, None, 4)  # MOVEFILE_DELAY_UNTIL_REBOOT
                        print("已标记临时更新器在系统重启后删除")
                    except Exception:
                        pass
    except Exception as e:
        print(f"警告：清理临时文件时出错: {e}")
    
    # 4. 重启主程序
    print()
    print("正在重启主程序...")
    main_exe_path = args.main_exe or get_main_exe_path()
    success, error = restart_main_program(main_exe_path)
    if not success:
        print(f"警告：{error}")
        print("请手动启动主程序")
    
    print()
    print("=" * 60)
    print("更新完成！")
    print("=" * 60)
    print()
    
    # 等待几秒后自动退出
    time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n更新已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误：{str(e)}")
        import traceback
        traceback.print_exc()
        try:
            input("按回车键退出...")
        except Exception:
            pass
        sys.exit(1)

