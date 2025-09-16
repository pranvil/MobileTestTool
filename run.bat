@echo off
echo 启动 ADB Logcat 关键字过滤工具...
echo.
echo 请确保：
echo 1. 已安装 Android SDK 并配置 adb 命令
echo 2. Android 设备已连接并启用 USB 调试
echo.
pause
python adb_logcat_filter.py
