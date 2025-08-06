$ErrorActionPreference = "Stop"

# -------------------------
# Configuration
# -------------------------
$repoRoot      = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main"
$toolsDir      = "C:\Tools\iPPY"
$installerUrl  = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python_installer.exe"
$scriptPath    = "$toolsDir\iPPY.py"
$reqsPath      = "$toolsDir\requirements.txt"
$vbsPath       = "$toolsDir\launch_ippy.vbs"
$shortcutPath  = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"

# -------------------------
# Download and install Python
# -------------------------
Write-Host "[*] Downloading full Python installer..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1" -Wait
Remove-Item $installerPath

# -------------------------
# Resolve Python paths
# -------------------------
$pythonExe = (Get-Command python.exe).Source
$pythonDir = Split-Path -Parent $pythonExe
$pipExe    = Join-Path $pythonDir "Scripts\pip.exe"

# -------------------------
# Create tools directory
# -------------------------
New-Item -Force -ItemType Directory -Path $toolsDir | Out-Null

# -------------------------
# Download script and requirements.txt
# -------------------------
Write-Host "[*] Downloading app files..."
Invoke-WebRequest "$repoRoot/iPPY.py" -OutFile $scriptPath
Invoke-WebRequest "$repoRoot/requirements.txt" -OutFile $reqsPath

# -------------------------
# Install dependencies
# -------------------------
Write-Host "[*] Installing dependencies..."
& $pipExe install --upgrade pip setuptools
& $pipExe install -r $reqsPath

# -------------------------
# Create VBS launcher (no console)
# -------------------------
Write-Host "[*] Creating VBS launcher..."
@"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & "$pythonExe" & Chr(34) & " " & Chr(34) & "$scriptPath" & Chr(34), 0, False
"@ | Out-File -Encoding ASCII $vbsPath

# -------------------------
# Create Startup shortcut
# -------------------------
Write-Host "[*] Creating Startup shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $vbsPath
$shortcut.Save()

# -------------------------
# Launch app now
# -------------------------
Write-Host "[*] Launching app..."
Start-Process -WindowStyle Hidden "$vbsPath"

Write-Host "`n✅ Full Python installed, iPPY launched, and set to run at login."

