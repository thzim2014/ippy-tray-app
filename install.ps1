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
# Enable 'import site' in .pth
# -------------------------
$pthFile = Get-ChildItem "$pythonDir\python*.pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pthFile) {
    (Get-Content $pthFile.FullName) -replace '^#?import site', 'import site' | Set-Content $pthFile.FullName
    Write-Host "[*] Enabled 'import site' in $($pthFile.Name)"
} else {
    Write-Warning "⚠️ No .pth file found to enable 'import site'"
}

# -------------------------
# Download app script and requirements.txt
# -------------------------
Write-Host "[*] Downloading app files..."
Invoke-WebRequest "$repoRoot/iPPY.py" -OutFile $scriptPath
Invoke-WebRequest "$repoRoot/requirements.txt" -OutFile "$toolsDir\requirements.txt"

# -------------------------
# Install pip
# -------------------------
Write-Host "[*] Installing pip..."
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$toolsDir\get-pip.py"
& "$pythonDir\python.exe" "$toolsDir\get-pip.py"
Remove-Item "$toolsDir\get-pip.py"

# -------------------------
# Install dependencies
# -------------------------
Write-Host "[*] Installing dependencies..."
& "$pythonDir\Scripts\pip.exe" install --upgrade pip setuptools
& "$pythonDir\Scripts\pip.exe" install -r "$toolsDir\requirements.txt"

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

Write-Host "`n✅ iPPY installed and set to run at login. No further action needed."
