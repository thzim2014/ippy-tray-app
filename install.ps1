$ErrorActionPreference = "Stop"

# -------------------------
# Configuration
# -------------------------
$repoRoot      = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main"
$toolsDir      = "C:\Tools\iPPY"
$pythonUrl     = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip"
$pythonZip     = "$env:TEMP\python_embed.zip"
$pythonDir     = "$toolsDir\Python"
$scriptPath    = "$toolsDir\iPPY.py"
$reqsPath      = "$toolsDir\requirements.txt"
$vbsPath       = "$toolsDir\launch_ippy.vbs"
$shortcutPath  = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# -------------------------
# Create directories
# -------------------------
New-Item -Force -ItemType Directory -Path $toolsDir | Out-Null
New-Item -Force -ItemType Directory -Path $pythonDir | Out-Null

# -------------------------
# Download embedded Python
# -------------------------
Write-Host "[*] Downloading embedded Python..."
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip

if (!(Test-Path $pythonZip)) {
    Write-Error "❌ Failed to download Python zip file."
    exit 1
}

Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force
Remove-Item $pythonZip

# -------------------------
# Always create ._pth and enable site
# -------------------------
$pyZip = Get-ChildItem "$pythonDir\python*.zip" | Select-Object -First 1
if (!$pyZip) { Write-Error "Python zip not found"; exit 1 }

$ver = $pyZip.Name -replace '\.zip$', ''
$pthPath = "$pythonDir\$ver._pth"

@"
$ver.zip
.
import site
"@ | Set-Content -Encoding ASCII -Path $pthPath

Write-Host "[*] Created $ver._pth with 'import site' enabled"

# -------------------------
# Download script and requirements.txt
# -------------------------
Write-Host "[*] Downloading app files..."
Invoke-WebRequest "$repoRoot/iPPY.py" -OutFile $scriptPath
Invoke-WebRequest "$repoRoot/requirements.txt" -OutFile $reqsPath

# -------------------------
# Install pip
# -------------------------
Write-Host "[*] Installing pip..."
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$toolsDir\get-pip.py"
& "$pythonDir\python.exe" "$toolsDir\get-pip.py"
Remove-Item "$toolsDir\get-pip.py"

# -------------------------
# Force install setuptools + deps
# -------------------------
Write-Host "[*] Installing setuptools and requirements..."
& "$pythonDir\Scripts\pip.exe" install --force-reinstall setuptools
& "$pythonDir\Scripts\pip.exe" install --upgrade pip
& "$pythonDir\Scripts\pip.exe" install -r $reqsPath

# -------------------------
# Test pkg_resources
# -------------------------
try {
    & "$pythonDir\python.exe" -c "import pkg_resources" | Out-Null
    Write-Host "[*] pkg_resources is working."
} catch {
    Write-Error "❌ pkg_resources still not available!"
}

# -------------------------
# Create silent VBS launcher
# -------------------------
Write-Host "[*] Creating VBS launcher..."
@"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & "$pythonDir\python.exe" & Chr(34) & " " & Chr(34) & "$scriptPath" & Chr(34), 0, False
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
# Auto-launch app now
# -------------------------
Write-Host "[*] Launching app..."
Start-Process -WindowStyle Hidden "$vbsPath"

Write-Host "`n✅ iPPY installed, dependencies loaded, and app launched silently."
