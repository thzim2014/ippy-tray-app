Write-Host "[*] Downloading full Python installer..."
$installerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

bitsadmin /transfer "ipyppy" /priority normal "$installerUrl" "$installerPath"

Write-Host "`n[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1" -Wait

# Locate python.exe manually by scanning typical local install path
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

# Create folders and launcher
$trayAppPath = "C:\Tools\iPPY\iPPY.py"
$launcherVbs = "C:\Tools\iPPY\launch_silent.vbs"
New-Item -ItemType Directory -Force -Path "C:\Tools\iPPY" | Out-Null

Set-Content -Path $launcherVbs -Value (
    'Set WshShell = CreateObject("WScript.Shell")' + "`n" +
    "WshShell.Run `"$pythonExe`" `"$trayAppPath`", 0, False"
)

# Add shortcut to Startup folder
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherVbs
$shortcut.Save()

Write-Host "`n✅ Setup complete. iPPY will run silently at login."
