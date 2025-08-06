Set-StrictMode -Version Latest

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repoRoot = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/TrayApp"
$installDir = "C:\\Tools\\TrayApp"
$startupFolder = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
$shortcutName = "TrayApp.lnk"
$pythonInstaller = "$env:TEMP\\python-installer.exe"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$getPipScript = "$env:TEMP\\get-pip.py"
$requirementsFile = "$installDir\\requirements.txt"
$vbscriptPath = "$installDir\\launcher.vbs"
$pyScript = "$installDir\\main.py"

function Download-File {
    param (
        [string]$url,
        [string]$destination
    )
    try {
        Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Error "Failed to download $url"
        exit 1
    }
}

function Ensure-Folder {
    param ([string]$path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

Ensure-Folder $installDir

Write-Host "Downloading Python..."
Download-File -url $pythonInstallerUrl -destination $pythonInstaller

Write-Host "Installing Python..."
Start-Process -FilePath $pythonInstaller -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_test=0', 'TargetDir="C:\\Program Files\\Python312"' -Wait
Remove-Item $pythonInstaller -Force

# Prepare path
$env:Path += ";C:\\Program Files\\Python312\\Scripts;C:\\Program Files\\Python312\\"
$env:Path += ";$env:LOCALAPPDATA\\Programs\\Python\\Python312\\Scripts;$env:LOCALAPPDATA\\Programs\\Python\\Python312\\"

# Locate Python
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
    Write-Error "Python installation failed or python.exe not found."
    exit 1
}

# Install pip if missing
$pipCheck = & $pythonExe -m pip --version 2>$null
if ($LASTEXITCODE -ne 0 -or $pipCheck -match "No module named") {
    Write-Host "Installing pip manually..."
    Download-File -url $getPipUrl -destination $getPipScript
    & $pythonExe $getPipScript
    & $pythonExe -m ensurepip
    & $pythonExe -m pip install --upgrade pip setuptools wheel
    Remove-Item $getPipScript -Force
}

# Validate pkg_resources
try {
    & $pythonExe -c "import pkg_resources; print('OK')"
} catch {
    Write-Warning "pkg_resources is not available. Installing setuptools again."
    & $pythonExe -m pip install setuptools
}

Write-Host "Downloading app files..."
$files = @("main.py", "requirements.txt", "launcher.vbs", "config.ini")
foreach ($file in $files) {
    $url = "$repoRoot/$file"
    $target = Join-Path $installDir $file
    Download-File -url $url -destination $target
}

Write-Host "Installing dependencies..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r $requirementsFile

Write-Host "Creating startup shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut("$startupFolder\\$shortcutName")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = '"' + $vbscriptPath + '"'
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$installDir\\icon.ico"
$shortcut.Save()

Write-Host "Install complete. App will run on next login."
exit 0
