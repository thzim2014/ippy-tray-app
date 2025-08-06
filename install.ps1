Write-Host "[*] Downloading full Python installer..."
$installerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

bitsadmin /transfer "ipyppy" /priority normal "$installerUrl" "$installerPath"

Write-Host "`n[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1" -Wait

# Locate python.exe manually
$pythonExe = Get-ChildItem -Path "$env:LocalAppData\Programs\Python\Python3*" -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1
if (-not $pythonExe) {
    Write-Host "❌ Python installation not found. Installer may have failed."
    exit 1
}
$pythonDir = Split-Path -Parent $pythonExe
$pipExe    = Join-Path $pythonDir "Scripts\pip.exe"

# Install dependencies
Write-Host "`n[*] Installing dependencies..."
& $pipExe install --no-warn-script-location requests pillow pystray win10toast

# Create VBS launcher for silent tray startup
$trayAppPath = "C:\Tools\iPPY\iPPY.py"
$launcherVbs = "C:\Tools\iPPY\launch_silent.vbs"

New-Item -ItemType Directory -Force -Path "C:\Tools\iPPY" | Out-Null
Set-Content -Path $launcherVbs -Value (
    'Set WshShell = CreateObject("WScript.Shell")' + "`n" +
    "WshShell.Run `"$pythonExe `"$trayAppPath`"`", 0, False"
)

# Create shortcut in Startup
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherVbs
$shortcut.Save()

Write-Host "`n✅ Python installed, dependencies added, and autorun shortcut created."
Write-Host "No further action needed."
