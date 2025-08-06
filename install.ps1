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
# Create directories
# -------------------------
New-Item -Force -ItemType Directory -Path $toolsDir | Out-Null

# -------------------------
# Download Python installer using bitsadmin
# -------------------------
Write-Host "[*] Downloading Python installer using bitsadmin..."
bitsadmin /transfer "ipyppy" $installerUrl $installerPath

if (!(Test-Path $installerPath)) {
    Write-Error "❌ bitsadmin failed to download Python installer."
    exit 1
}

# -------------------------
# Silent install Python
# -------------------------
Write-Host "[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1" -Wait
Remove-Item $installerPath

# -------------------------
# Locate installed Python
# -------------------------
$pythonExe = (Get-Command python.exe).Source
$pythonDir = Split-Path -Parent $pythonExe
$pipExe    = Join-Path $pythonDir "Scripts\pip.exe"

# -------------------------
# Download app files
# -------------------------
Write-Host "[*] Downloading script and requirements..."
Invoke-WebRequest "$repoRoot/iPPY.py" -OutFile $scriptPath
Invoke-WebRequest "$repoRoot/requirements.txt" -OutFile $reqsPath

# -------------------------
# Install Python packages
# -------------------------
Write-Host "[*] Installing Python dependencies..."
& $pipExe install --upgrade pip setuptools
& $pipExe install -r $reqsPath

# -------------------------
# Create silent VBS launcher
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
# Run app now
# -------------------------
Write-Host "[*] Launching iPPY..."
Start-Process -WindowStyle Hidden "$vbsPath"

Write-Host "`n✅ Python installed, app deployed, and iPPY is now running."
