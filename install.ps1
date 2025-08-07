# ------------------------------
# iPPY Tray App Installer Script (idempotent)
# ------------------------------

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Required minimum (newer will be preserved) ---
$RequiredVersion = [Version]'3.12.2'

# --- Paths / URLs ---
$repoRoot        = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main"
$installDir      = "C:\Tools\TrayApp"
$assetsDir       = Join-Path $installDir "assets"
$logsDir         = Join-Path $installDir "logs"
$startupFolder   = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutName    = "TrayApp.lnk"

$pythonInstaller    = Join-Path $env:TEMP "python-installer.exe"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"

$getPipUrl    = "https://bootstrap.pypa.io/get-pip.py"
$getPipScript = Join-Path $env:TEMP "get-pip.py"

$requirementsFile = Join-Path $assetsDir "requirements.txt"
$vbscriptPath     = Join-Path $assetsDir "launcher.vbs"
$pyScript         = Join-Path $installDir "main.py"
$iconPath         = Join-Path $assetsDir "tray_app_icon.ico"

# --- Helpers ---
function Download-File {
    param([Parameter(Mandatory)] [string]$url,
          [Parameter(Mandatory)] [string]$destination)
    $dir = Split-Path $destination -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    try   { Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing -ErrorAction Stop }
    catch { Write-Error "❌ Failed to download $url"; throw }
}

function Ensure-Folder([string]$path) {
    if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

function Get-PythonExe {
    # Prefer real installs over the Windows Store alias
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-PythonVersion([string]$pythonExe) {
    try   { return [Version](& $pythonExe -c "import sys;print('.'.join(map(str,sys.version_info[:3])))") }
    catch { return $null }
}

# --- Make dirs ---
Ensure-Folder $installDir
Ensure-Folder $assetsDir
Ensure-Folder $logsDir
Ensure-Folder $startupFolder

# --- Ensure Python (skip if >= required) ---
$pythonExe = Get-PythonExe
$needPythonInstall = $true

if ($pythonExe) {
    $current = Get-PythonVersion $pythonExe
    if ($current) {
        if ($current -ge $RequiredVersion) {
            Write-Host "✅ Python $current already installed at $pythonExe — skipping installation."
            $needPythonInstall = $false
        } else {
            Write-Host "ℹ Found Python $current (< $RequiredVersion). Will install $RequiredVersion."
        }
    } else {
        Write-Host "⚠ Found python.exe but couldn't read version. Will reinstall."
    }
} else {
    Write-Host "ℹ Python not found. Will install $RequiredVersion."
}

if ($needPythonInstall) {
    Write-Host "📦 Downloading Python $RequiredVersion..."
    Download-File -url $pythonInstallerUrl -destination $pythonInstaller
    Write-Host "🛠 Installing Python $RequiredVersion..."
    Start-Process -FilePath $pythonInstaller -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0','TargetDir="C:\Program Files\Python312"' -Wait
    Remove-Item $pythonInstaller -Force -ErrorAction SilentlyContinue

    $pythonExe = Get-PythonExe
    if (-not $pythonExe) { throw "❌ Python installation failed (python.exe not found)." }
    $current = Get-PythonVersion $pythonExe
    if (-not $current -or $current -lt $RequiredVersion) { throw "❌ Python not at required version after install." }

    # Ensure current session PATH can find it
    $env:Path += ";$(Split-Path $pythonExe);$(Join-Path (Split-Path $pythonExe -Parent) 'Scripts')"
} else {
    # Ensure current session PATH can use it
    $env:Path += ";$(Split-Path $pythonExe);$(Join-Path (Split-Path $pythonExe -Parent) 'Scripts')"
}

# --- Ensure pip & base tools ---
try { & $pythonExe -m pip --version *> $null }
catch {
    Write-Host "📥 Installing pip..."
    Download-File -url $getPipUrl -destination $getPipScript
    & $pythonExe $getPipScript
    Remove-Item $getPipScript -Force -ErrorAction SilentlyContinue
}
& $pythonExe -m pip install --upgrade pip setuptools wheel

# --- Download app files ---
Write-Host "📥 Downloading tray app files..."
$rootFiles = @("main.py")
$assetFiles = @(
  "requirements.txt",
  "launcher.vbs",
  "tray_app_icon.ico",
  "tray_app_icon_g.ico",
  "tray_app_icon_r.ico",
  "version.txt"
)
foreach ($f in $rootFiles) { Download-File -url "$repoRoot/TrayApp/$f" -destination (Join-Path $installDir $f) }
foreach ($f in $assetFiles) { Download-File -url "$repoRoot/assets/$f"  -destination (Join-Path $assetsDir $f) }

# --- Clean one-line requirements edge case ---
if (Test-Path $requirementsFile) {
    $raw = Get-Content $requirementsFile -Raw
    if ($raw -and ($raw -notmatch "[\r\n]")) {
        Set-Content -Path $requirementsFile -Value (($raw -replace '[,; ]+', "`n").Trim()) -Encoding UTF8
    }
}

# --- Install Python dependencies ---
Write-Host "📦 Installing Python dependencies..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
if (Test-Path $requirementsFile) {
    & $pythonExe -m pip install -r $requirementsFile
} else {
    & $pythonExe -m pip install requests pystray Pillow win10toast
}

# --- Startup shortcut ---
Write-Host "🔗 Creating startup shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut((Join-Path $startupFolder $shortcutName))
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = '"' + $vbscriptPath + '"'
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = $iconPath
$shortcut.Save()

Write-Host "`n✅ Install complete. Tray App will run on next login."
exit 0
