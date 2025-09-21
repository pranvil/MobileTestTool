@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

echo ========================================
echo   手机测试辅助工具 - 打包
echo ========================================
echo.

REM 检查Python环境
echo 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: Python未找到或未正确安装
    pause
    exit /b 1
)

REM 检查PyInstaller
echo 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo 错误: PyInstaller安装失败
        pause
        exit /b 1
    )
)

REM 清理之前的构建
echo 清理之前的构建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 创建简化的构建命令
echo 开始构建...
pyinstaller --onedir --windowed --icon "icon.ico" --name "MobileTestTool" --hidden-import uiautomator2 --collect-all uiautomator2 --clean --noupx --strip main.py

if errorlevel 1 (
    echo 构建失败
    pause
    exit /b 1
)

echo.
echo 构建完成: dist\MobileTestTool\MobileTestTool.exe
echo.
echo 注意: 如果杀毒软件误报，请将项目目录添加到白名单
echo 详细说明请查看: 杀毒软件白名单说明.md
echo.
pause
