$ErrorActionPreference = 'Stop'

# Configuration
$installDir = "C:\Tools\iPPY"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$installerPath = "$env:TEMP\python_installer.exe"
$repoZipUrl = "https://github.com/GoblinRules/ippy-tray-app/archive/refs/heads/main.zip"
$repoZipPath = "$env:TEMP\ippy.zip"

# Ensure install directory exists
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host "`n[+] Downloading full Python installer..."
bitsadmin /transfer "ipyppy" /priority normal $pythonInstallerUrl $installerPath | Out-Null

Write-Host "`n[+] Installing Python silently..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 TargetDir=`"$installDir\Python`"" -Wait

Write-Host "`n[+] Installing dependencies..."
& "$installDir\Python\python.exe" -m pip install --upgrade pip
& "$installDir\Python\python.exe" -m pip install -r "$installDir\requirements.txt" -q

Write-Host "`n[+] Downloading application files..."
Invoke-WebRequest -Uri $repoZipUrl -OutFile $repoZipPath
Expand-Archive $repoZipPath -DestinationPath $installDir -Force
Move-Item "$installDir\ippy-tray-app-main\*" "$installDir" -Force
Remove-Item "$installDir\ippy-tray-app-main", $repoZipPath, $installerPath -Recurse -Force

Write-Host "`n[+] Creating VBS launcher..."
$vbscript = @'
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Tools\iPPY\Python\python.exe" & chr(34) & " C:\Tools\iPPY\iPPY.py", 0
Set WshShell = Nothing
'@
Set-Content -Path "$installDir\launch_silent.vbs" -Value $vbscript -Encoding ASCII

Write-Host "`n[+] Creating Startup shortcut..."
$startupShortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.vbs"
Copy-Item "$installDir\launch_silent.vbs" $startupShortcut -Force

Write-Host "`n[✓] Setup complete. iPPY will run silently at login."
