# ------------------------------
# iPPY Tray App Installer Script
# ------------------------------
# This script:
# - Downloads and installs Python 3.12.2 silently
# - Installs pip and all required packages
# - Pulls all tray app files from GitHub
# - Sets up a startup shortcut using launcher.vbs
# ------------------------------

Set-StrictMode -Version Latest

# --- Ensure TLS 1.2 support for Invoke-WebRequest ---
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Define Paths and URLs ---
$repoRoot = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main"
$installDir = "C:\\Tools\\TrayApp"
$assetsDir = "$installDir\\assets"
$logsDir = "$installDir\\logs"
$startupFolder = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
$shortcutName = "TrayApp.lnk"

$pythonInstaller = "$env:TEMP\\python-installer.exe"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"

$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$getPipScript = "$env:TEMP\\get-pip.py"

$requirementsFile = "$assetsDir\\requirements.txt"
$vbscriptPath = "$assetsDir\\launcher.vbs"
$pyScript = "$installDir\\main.py"
$iconPath = "$assetsDir\\tray_app_icon.ico"

# --- Utility: File Downloader ---
function Download-File {
    param (
        [string]$url,
        [string]$destination
    )
    try {
        Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Error "❌ Failed to download $url"
        exit 1
    }
}

# --- Create Required Folders ---
function Ensure-Folder {
    param ([string]$path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

Ensure-Folder $installDir
Ensure-Folder $assetsDir
Ensure-Folder $logsDir

# --- Download and Install Python ---
Write-Host "📦 Downloading Python..."
Download-File -url $pythonInstallerUrl -destination $pythonInstaller

Write-Host "🛠 Installing Python..."
Start-Process -FilePath $pythonInstaller -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_test=0', 'TargetDir="C:\\Program Files\\Python312"' -Wait
Remove-Item $pythonInstaller -Force

# --- Extend Path for Python ---
$env:Path += ";C:\\Program Files\\Python312\\Scripts;C:\\Program Files\\Python312\\"
$env:Path += ";$env:LOCALAPPDATA\\Programs\\Python\\Python312\\Scripts;$env:LOCALAPPDATA\\Programs\\Python\\Python312\\"

# --- Locate Python Executable ---
$pythonExe = $null
$pythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonExe = $pythonCmd.Source
}

if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    $fallbacks = @( 
        "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
        "$env:ProgramFiles\\Python312\\python.exe",
        "C:\\Python312\\python.exe"
    )
    foreach ($path in $fallbacks) {
        if (Test-Path $path) {
            $pythonExe = $path
            break
        }
    }
}

if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    Write-Error "❌ Python installation failed or python.exe not found."
    exit 1
}

# --- Install pip (if missing) ---
$pipCheck = & $pythonExe -m pip --version 2>$null
if ($LASTEXITCODE -ne 0 -or $pipCheck -match "No module named") {
    Write-Host "📥 Installing pip manually..."
    Download-File -url $getPipUrl -destination $getPipScript
    & $pythonExe $getPipScript
    & $pythonExe -m ensurepip
    & $pythonExe -m pip install --upgrade pip setuptools wheel
    Remove-Item $getPipScript -Force
}

# --- Fix pkg_resources if needed ---
try {
    & $pythonExe -c "import pkg_resources; print('OK')"
} catch {
    Write-Warning "⚠ pkg_resources not available. Reinstalling setuptools."
    & $pythonExe -m pip install setuptools
}

# --- Download Tray App Files ---
Write-Host "📥 Downloading tray app files..."

# Files in root install directory
$rootFiles = @("main.py")

# Files in assets directory (includes new green/red icons)
$assetFiles = @(
    "config.ini",
    "requirements.txt",
    "launcher.vbs",
    "tray_app_icon.ico",
    "tray_app_icon_g.ico",
    "tray_app_icon_r.ico",
    "version.txt"
)

foreach ($file in $rootFiles) {
    $url = "$repoRoot/TrayApp/$file"
    $target = Join-Path $installDir $file
    Download-File -url $url -destination $target
}

foreach ($file in $assetFiles) {
    $url = "$repoRoot/assets/$file"
    $target = Join-Path $assetsDir $file
    Download-File -url $url -destination $target
}

# --- Fix malformed requirements.txt (if one-liner from GitHub) ---
Write-Host "🧹 Checking requirements.txt formatting..."
if (Test-Path $requirementsFile) {
    $content = Get-Content $requirementsFile -Raw
    if ($content -notmatch "[\r\n]" -and $content -match "[a-zA-Z]+") {
        $split = ($content -replace '(\w)(?=\w)', '$1 ') -split ' '
        $cleaned = ($split | Where-Object { $_ -match '^\w+$' }) -join "`n"
        Set-Content -Path $requirementsFile -Value $cleaned -Encoding UTF8
    }
}

# --- Install Python Dependencies ---
Write-Host "📦 Installing Python dependencies..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r $requirementsFile

# --- Create Startup Shortcut ---
Write-Host "🔗 Creating startup shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut("$startupFolder\\$shortcutName")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = '"' + $vbscriptPath + '"'
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$iconPath"
$shortcut.Save()

Write-Host "`n✅ Install complete. Tray App will run on next login."
exit 0
