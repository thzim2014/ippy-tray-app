Write-Host "[*] Downloading full Python installer..."
$installerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

bitsadmin /transfer "ipyppy" /priority normal "$installerUrl" "$installerPath"

Write-Host "`n[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1" -Wait

# Locate installed python.exe
$possiblePython = Get-ChildItem -Path "$env:LocalAppData\Programs\Python" -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1
if (-not $possiblePython) {
    Write-Host "❌ Failed to find Python.exe. Aborting."
    exit 1
}

$pythonExe = $possiblePython
$pythonDir = Split-Path $pythonExe
$pipExe = Join-Path $pythonDir "Scripts\pip.exe"

Write-Host "`n[*] Installing dependencies..."
& $pipExe install --no-warn-script-location requests pillow pystray win10toast

# Fetch app files from GitHub
Write-Host "`n[*] Downloading app files from GitHub..."
$appFolder = "C:\Tools\iPPY"
$zipUrl = "https://github.com/GoblinRules/ippy-tray-app/archive/refs/heads/main.zip"
$zipPath = "$env:TEMP\iPPY.zip"
Expand-Archive -Force -Path $zipPath -DestinationPath $env:TEMP -ErrorAction SilentlyContinue
Remove-Item -Force $appFolder -Recurse -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $appFolder | Out-Null
bitsadmin /transfer "ippyZip" /priority normal "$zipUrl" "$zipPath"
Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
Copy-Item "$env:TEMP\ippy-tray-app-main\*" -Destination $appFolder -Recurse -Force

# Create VBScript launcher
$launcherVbs = "$appFolder\launch_silent.vbs"
Set-Content -Path $launcherVbs -Value (
    'Set WshShell = CreateObject("WScript.Shell")' + "`n" +
    "WshShell.Run `"$pythonExe`" `"$appFolder\iPPY.py`", 0, False"
)

# Create shortcut in Startup
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherVbs
$shortcut.Save()

Write-Host "`n✅ Setup complete. iPPY will run silently at login."
