Write-Host "[*] Downloading full Python installer..."
$installerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

bitsadmin /transfer "ipyppy" /priority normal "$installerUrl" "$installerPath"

Write-Host "`n[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1" -Wait

# Locate installed python.exe
$pythonExe = Get-ChildItem -Path "$env:LocalAppData\Programs\Python" -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1
if (-not $pythonExe) {
    Write-Host "❌ Failed to find python.exe. Aborting."
    exit 1
}

$pipExe = Join-Path (Split-Path $pythonExe) "Scripts\pip.exe"

Write-Host "`n[*] Installing dependencies..."
& $pipExe install --no-warn-script-location requests pillow pystray win10toast charset-normalizer idna urllib3 six pywin32

# Download app files from GitHub
Write-Host "`n[*] Downloading app source..."
$zipUrl = "https://github.com/GoblinRules/ippy-tray-app/archive/refs/heads/main.zip"
$zipPath = "$env:TEMP\ippy.zip"
$appFolder = "C:\Tools\iPPY"
$tempExtract = "$env:TEMP\ippy-extract"

# Clean up any previous failed attempts
Remove-Item -Force -Recurse $appFolder -ErrorAction SilentlyContinue
Remove-Item -Force -Recurse $tempExtract -ErrorAction SilentlyContinue

bitsadmin /transfer "ippyZip" /priority normal "$zipUrl" "$zipPath"
Expand-Archive -Path $zipPath -DestinationPath $tempExtract -Force
Copy-Item "$tempExtract\ippy-tray-app-main\*" -Destination $appFolder -Recurse -Force

# Create VBScript launcher
Write-Host "`n[*] Creating VBS launcher..."
$launcherVbs = "$appFolder\launch_silent.vbs"
$launcherContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$pythonExe"" ""$appFolder\iPPY.py""", 0, False
"@
Set-Content -Path $launcherVbs -Value $launcherContent -Encoding ASCII

# Create shortcut in Startup folder
Write-Host "`n[*] Creating Startup shortcut..."
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherVbs
$shortcut.Save()

Write-Host "`n✅ Setup complete. iPPY will run silently at login."
