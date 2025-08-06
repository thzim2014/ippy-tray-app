@echo off
setlocal

:: Set paths
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip"
set "TOOLS_DIR=C:\Tools\iPPY"
set "PYTHON_DIR=%TOOLS_DIR%\Python"
set "SCRIPT_PATH=%TOOLS_DIR%\iPPY.py"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\iPPY.lnk"
set "VBS_LAUNCHER=%TOOLS_DIR%\launch_ippy.vbs"

:: Create directories
mkdir "%PYTHON_DIR%" >nul 2>&1

:: Download embedded Python if not already present
if not exist "%PYTHON_DIR%\python.exe" (
    echo [*] Downloading embedded Python...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile 'python_embed.zip'"
    powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath '%PYTHON_DIR%' -Force"
    del python_embed.zip
)

:: Ensure pip is available
if not exist "%PYTHON_DIR%\Scripts\pip.exe" (
    echo [*] Installing pip...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'"
    "%PYTHON_DIR%\python.exe" get-pip.py
    del get-pip.py
)

:: Upgrade pip and setuptools
"%PYTHON_DIR%\Scripts\pip.exe" install --upgrade pip setuptools

:: Install dependencies
"%PYTHON_DIR%\Scripts\pip.exe" install requests pillow win10toast

:: Create VBScript launcher (no console window)
(
echo Set WshShell = CreateObject("WScript.Shell") 
echo WshShell.Run """"^& "%PYTHON_DIR%\python.exe" ^& """ """^& "%SCRIPT_PATH%" ^& """", 0, False
) > "%VBS_LAUNCHER%"

:: Create shortcut in Startup folder
powershell -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); ^
    $s.TargetPath='%VBS_LAUNCHER%'; ^
    $s.Save()"

echo [*] Shortcut created in Startup to run iPPY silently.
pause
