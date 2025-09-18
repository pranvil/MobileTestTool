@echo off
echo 正在打包 ADB Logcat 过滤工具...
echo.

REM 检查是否安装了PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo 安装 PyInstaller 失败！
        pause
        exit /b 1
    )
)

echo 开始打包...
pyinstaller --onefile --windowed --name "ADB_Logcat_Filter" main.py

if errorlevel 1 (
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo 打包完成！
echo 可执行文件位置: dist\ADB_Logcat_Filter.exe
echo.
pause
