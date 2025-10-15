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

REM 强制清理输出目录
echo 清理输出目录...
if exist "c:\MyBuilds\MobileTestTool" (
    echo 正在清理 c:\MyBuilds\MobileTestTool...
    
    REM 尝试终止可能运行的进程
    taskkill /f /im "MobileTestTool.exe" 2>nul
    
    REM 等待进程完全终止
    timeout /t 2 /nobreak >nul
    
    REM 尝试删除目录
    rmdir /s /q "c:\MyBuilds\MobileTestTool" 2>nul
    
    REM 如果删除失败，尝试使用robocopy清空
    if exist "c:\MyBuilds\MobileTestTool" (
        echo 使用robocopy清空目录...
        mkdir "c:\temp_empty" 2>nul
        robocopy "c:\temp_empty" "c:\MyBuilds\MobileTestTool" /mir /nfl /ndl /njh /njs /nc /ns /np >nul 2>&1
        rmdir /s /q "c:\temp_empty" 2>nul
        rmdir /s /q "c:\MyBuilds\MobileTestTool" 2>nul
    )
    
    REM 最终检查
    if exist "c:\MyBuilds\MobileTestTool" (
        echo 警告: 无法完全清理输出目录，但将继续构建...
    ) else (
        echo 输出目录清理完成
    )
)

REM 创建简化的构建命令
echo 开始构建...
pyinstaller --clean --noconfirm --distpath "c:\MyBuilds" MobileTestTool.spec

if errorlevel 1 (
    echo 构建失败
    pause
    exit /b 1
)

echo.
echo 构建完成: c:\MyBuilds\MobileTestTool\MobileTestTool.exe
echo APK文件已包含在打包中
echo.
echo 注意: 如果杀毒软件误报，请将项目目录添加到白名单
echo 详细说明请查看: 杀毒软件白名单说明.md
echo.
pause
