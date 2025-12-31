@echo off
chcp 65001 >nul
echo ========================================
echo PySide6版本打包脚本 (onedir模式)
echo ========================================
echo.

REM 切换到项目根目录（脚本在 scripts/ 目录下）
cd /d %~dp0\..
set PROJECT_ROOT=%CD%

REM 检查Python环境
echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误：未找到Python环境，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

REM 检查PyInstaller
echo 检查PyInstaller...
python -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)"
if %errorlevel% neq 0 (
    echo 错误：未找到PyInstaller，请运行: pip install pyinstaller
    pause
    exit /b 1
)

REM 清理旧的构建文件
echo.
echo 清理旧的构建文件...
echo 正在关闭可能正在运行的程序...
taskkill /F /IM MobileTestTool.exe /T >nul 2>&1
taskkill /F /IM updater.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo 正在清理构建目录...
REM 尝试多次清理，因为可能有文件被锁定
if exist build (
    echo 清理 build 目录...
    rmdir /s /q build 2>nul
    if exist build (
        timeout /t 1 /nobreak >nul
        rmdir /s /q build 2>nul
    )
)

if exist dist (
    echo 清理 dist 目录...
    REM 先尝试删除子目录
    if exist "dist\MobileTestTool" (
        echo 清理 dist\MobileTestTool 目录...
        rmdir /s /q "dist\MobileTestTool" 2>nul
        if exist "dist\MobileTestTool" (
            echo 警告：dist\MobileTestTool 目录可能被占用，请手动关闭相关程序后重试
            timeout /t 2 /nobreak >nul
            rmdir /s /q "dist\MobileTestTool" 2>nul
        )
    )
    if exist "dist\updater" (
        rmdir /s /q "dist\updater" 2>nul
    )
    if exist "dist\updater.exe" (
        del /f /q "dist\updater.exe" 2>nul
    )
    REM 最后删除整个dist目录
    rmdir /s /q dist 2>nul
    if exist dist (
        echo 警告：dist 目录可能仍被占用，将在打包时尝试清理
    )
)

echo 清理完成

echo.
echo 开始打包主程序 (onedir模式 - 文件夹形式)...
echo 注意：如果遇到权限错误，请确保：
echo   1. 关闭所有正在运行的 MobileTestTool.exe 和 updater.exe
echo   2. 关闭可能占用文件的资源管理器窗口
echo   3. 检查是否有杀毒软件正在扫描该目录
echo.

pyinstaller --clean --noconfirm MobileTestTool.spec

if %errorlevel% neq 0 (
    echo.
    echo 错误：主程序打包失败！
    echo.
    echo 可能的原因：
    echo   1. dist\MobileTestTool 目录正在被其他程序使用
    echo   2. 主程序或更新器正在运行
    echo   3. 资源管理器正在访问该目录
    echo.
    echo 解决方案：
    echo   1. 关闭所有 MobileTestTool.exe 和 updater.exe 进程
    echo   2. 关闭资源管理器中打开的 dist 目录
    echo   3. 等待几秒后重试
    echo   4. 如果问题持续，请手动删除 dist 目录后重试
    echo.
    pause
    exit /b 1
)

echo.
echo 开始打包更新器...
pyinstaller --clean --noconfirm updater.spec

if %errorlevel% neq 0 (
    echo.
    echo 错误：更新器打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo 复制更新器到主程序目录...
if exist "dist\updater.exe" (
    REM 将更新器复制到 _internal 目录（更隐蔽，用户不易发现）
    if exist "dist\MobileTestTool\_internal" (
        copy /Y "dist\updater.exe" "dist\MobileTestTool\_internal\updater.exe" >nul 2>&1
        if not errorlevel 1 (
            echo 更新器已复制到 _internal 目录
        ) else (
            echo 警告：复制更新器到 _internal 目录失败，尝试复制到主目录...
            copy /Y "dist\updater.exe" "dist\MobileTestTool\updater.exe" >nul 2>&1
            if not errorlevel 1 (
                echo 更新器已复制到主程序目录（备用位置）
            ) else (
                echo 警告：复制更新器失败
            )
        )
    ) else (
        echo 警告：_internal 目录不存在，复制到主目录...
        copy /Y "dist\updater.exe" "dist\MobileTestTool\updater.exe" >nul 2>&1
        if not errorlevel 1 (
            echo 更新器已复制到主程序目录
        ) else (
            echo 警告：复制更新器失败
        )
    )
    echo 清理临时文件...
    del /f /q "dist\updater.exe" 2>nul
) else (
    echo 警告：未找到更新器可执行文件 (dist\updater.exe)
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 程序文件夹位置: dist\MobileTestTool\
echo 主程序: dist\MobileTestTool\MobileTestTool.exe
echo 更新器: dist\MobileTestTool\updater.exe
echo.
echo 注意：
echo 1. onedir模式会生成一个包含所有依赖的文件夹
echo 2. 请将整个 MobileTestTool 文件夹分发给用户
echo 3. 此版本已优化exe环境下的MTKlogger兼容性
echo 4. 更新器已包含在主程序目录中，用于自动更新功能
echo.


