# install.ps1

Write-Host "`n[*] Creating folder structure..."
$appFolder = "C:\Tools\iPPY"
$pythonFolder = "$appFolder\Python"
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

New-Item -ItemType Directory -Force -Path $appFolder | Out-Null
New-Item -ItemType Directory -Force -Path $pythonFolder | Out-Null

# Download and install full Python silently
Write-Host "`n[*] Downloading full Python installer..."
$installerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python_installer.exe"

# Use bitsadmin to download Python installer
bitsadmin /transfer "pydl" /priority normal "$installerUrl" "$installerPath"

while (-not (Test-Path $installerPath)) {
    Start-Sleep -Milliseconds 500
}

Write-Host "`n[*] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 TargetDir=$pythonFolder" -Wait

# Ensure pip works and install required modules
Write-Host "`n[*] Installing dependencies..."
$pythonExe = "$pythonFolder\python.exe"
$requirements = @("requests", "pillow", "pystray", "pywin32", "win10toast", "charset_normalizer", "urllib3", "idna", "six")

foreach ($package in $requirements) {
    & $pythonExe -m pip install $package
}

# Download app files from GitHub
Write-Host "`n[*] Downloading app source..."
$zipUrl = "https://github.com/GoblinRules/ippy-tray-app/archive/refs/heads/main.zip"
$zipPath = "$env:TEMP\ippy.zip"
$tempExtract = "$env:TEMP\ippy-extract"

Remove-Item -Force -Recurse $tempExtract -ErrorAction SilentlyContinue
Remove-Item -Force -Recurse "$appFolder\*" -ErrorAction SilentlyContinue

bitsadmin /transfer "ippyZip" /priority normal "$zipUrl" "$zipPath"

while (-not (Test-Path $zipPath)) {
    Start-Sleep -Milliseconds 500
}

Expand-Archive -Path $zipPath -DestinationPath $tempExtract -Force
Copy-Item "$tempExtract\ippy-tray-app-main\*" -Destination $appFolder -Recurse -Force

# Create VBS launcher to run silently
Write-Host "`n[*] Creating VBS launcher..."
$vbsPath = "$appFolder\launch_silent.vbs"
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "$pythonExe" & chr(34) & " "$appFolder\iPPY.py"", 0
Set WshShell = Nothing
"@
$vbsContent | Out-File -Encoding ASCII -FilePath $vbsPath

# Add to Startup
Write-Host "`n[*] Adding to Startup folder..."
$shortcutPath = "$startupFolder\iPPY.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $vbsPath
$shortcut.WorkingDirectory = $appFolder
$shortcut.Save()

Write-Host "`n✓ Setup complete. iPPY will run silently at login."
