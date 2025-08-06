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

# Force TLS 1.2 for all web requests
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
# Rebuild .pth file if missing (and enable 'import site')
# -------------------------
$pthFile = Get-ChildItem "$pythonDir\python*.pth" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $pthFile) {
    Write-Warning "⚠️ No .pth file found, creating one manually..."
    $ver = (Get-ChildItem "$pythonDir\python*.zip").Name -replace '\.zip$',''
    $pthFilePath = "$pythonDir\$ver._pth"
    Set-Content -Encoding ASCII -Path $pthFilePath -Value @"
$ver.zip
.
import site
"@
    Write-Host "[*] Created $($ver)._pth and enabled import site"
} else {
    (Get-Content $pthFile.FullName) -replace '^#?import site', 'import site' | Set-Content $pthFile.FullName
    Write-Host "[*] Enabled 'import site' in $($pthFile.Name)"
}

# -------------------------
# Download your script and requirements
# -------------------------
Write-Host "[*] Downloading project files..."
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
# Install required packages
# -------------------------
Write-Host "[*] Installing dependencies..."
& "$pythonDir\Scripts\pip.exe" install --upgrade pip setuptools
& "$pythonDir\Scripts\pip.exe" install -r $reqsPath

# -------------------------
# Create VBS launcher (no console)
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
# Autorun after install
# -------------------------
Write-Host "[*] Launching iPPY for first run..."
Start-Process -WindowStyle Hidden "$vbsPath"

Write-Host "`n✅ iPPY installed and running. Set to auto-start with Windows."
