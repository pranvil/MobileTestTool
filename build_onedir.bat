@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

echo ========================================
echo   MobileTestTool - onedir build
echo ========================================
echo.

REM 1) Check Python / PyInstaller
python --version >nul 2>nul || (echo Python not found.& pause & exit /b 1)
python -c "import PyInstaller" 1>nul 2>nul || (echo Installing PyInstaller... & pip install -q pyinstaller || (echo Install failed.& pause & exit /b 1))

REM 2) Write a tiny Python helper to detect Tcl/Tk paths
set "DETECT=%TEMP%\detect_tk_paths.py"
> "%DETECT%" echo import tkinter as tk, pathlib
>>"%DETECT%" echo r = tk.Tk()
>>"%DETECT%" echo tcl = pathlib.Path(r.tk.eval('info library')).resolve()
>>"%DETECT%" echo try:
>>"%DETECT%" echo^    tkd = pathlib.Path(r.tk.eval('set tk_library')).resolve()
>>"%DETECT%" echo except Exception:
>>"%DETECT%" echo^    tkd = tcl.parent / 'tk8.6'
>>"%DETECT%" echo r.destroy()
>>"%DETECT%" echo print(str(tcl)+';'+str(tkd))

REM 3) Run helper and parse "tcl;tk" output
for /f "usebackq tokens=1,2 delims=;" %%i in (`python "%DETECT%"`) do (
  set "TCL_DIR=%%~i"
  set "TK_DIR=%%~j"
)

if not exist "%TCL_DIR%\init.tcl" (
  echo init.tcl not found: %TCL_DIR%
  del "%DETECT%" >nul 2>nul
  pause
  exit /b 1
)
if not exist "%TK_DIR%\tk.tcl" (
  echo tk.tcl not found: %TK_DIR%
  del "%DETECT%" >nul 2>nul
  pause
  exit /b 1
)

for %%# in ("%TCL_DIR%") do set "TCL_BASE=%%~nx#"
for %%# in ("%TK_DIR%") do set "TK_BASE=%%~nx#"

echo Detected:
echo   TCL_DIR = %TCL_DIR%   (-> lib\%TCL_BASE%)
echo   TK_DIR  = %TK_DIR%    (-> lib\%TK_BASE%)
echo.

REM 4) Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"

REM 5) Create a runtime hook to set TCL/TK env at app start
> hook_set_tk_env.py echo import os,sys
>>hook_set_tk_env.py echo from pathlib import Path
>>hook_set_tk_env.py echo base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
>>hook_set_tk_env.py echo os.environ.setdefault("TCL_LIBRARY", str(base / "lib" / "%TCL_BASE%"))
>>hook_set_tk_env.py echo os.environ.setdefault("TK_LIBRARY",  str(base / "lib" / "%TK_BASE%"))

REM 6) Build (ASCII app name avoids path issues)
pyinstaller ^
  --onedir ^
  --windowed ^
  --icon "icon.ico" ^
  --name "手机测试辅助工具 v2.1" ^
  --add-data "README.md;." ^
  --add-data "%TCL_DIR%;lib/%TCL_BASE%" ^
  --add-data "%TK_DIR%;lib/%TK_BASE%" ^
  --hidden-import tkinter ^
  --runtime-hook hook_set_tk_env.py ^
  --clean ^
  main.py

del "%DETECT%" >nul 2>nul

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Build done: dist\手机测试辅助工具 v2.1\手机测试辅助工具 v2.1.exe
pause
