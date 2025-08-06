# Set strict mode
Set-StrictMode -Version Latest

# Configuration
$repoRoot = "https://raw.githubusercontent.com/YourUsername/YourRepoName/main"
$installDir = "C:\Tools\TrayApp"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$pythonInstaller = "$env:TEMP\python-installer.exe"
$requirementsFile = "$installDir\requirements.txt"
$shortcutName = "TrayApp.lnk"
$vbscriptPath = "$installDir\launcher.vbs"
$pyScript = "$installDir\main.py"
$pythonExe = "$env:ProgramFiles\Python312\python.exe"
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

# Helper: BITS download
function Download-File {
    param ($url, $destination)
    Start-BitsTransfer -Source $url -Destination $destination -ErrorAction Stop
}

# Helper: Ensure Folder Exists
function Ensure-Folder {
    param ($path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

# 1. Ensure target folder
Ensure-Folder -path $installDir

# 2. Download Python installer
Write-Host "Downloading Python installer..."
Download-File -url $pythonInstallerUrl -destination $pythonInstaller

# 3. Install Python silently
Write-Host "Installing Python..."
Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
Remove-Item $pythonInstaller -Force

# 4. Add Python to path if not already
$env:Path += ";$env:ProgramFiles\Python312\Scripts;$env:ProgramFiles\Python312\"

# 5. Download required files from GitHub
Write-Host "Downloading files from GitHub..."

$filesToDownload = @(
    "main.py",
    "requirements.txt",
    "launcher.vbs",
    "config.ini"
)

foreach ($file in $filesToDownload) {
    $url = "$repoRoot/$file"
    $destination = Join-Path $installDir $file
    Write-Host "Downloading $file..."
    Download-File -url $url -destination $destination
}

# 6. Install pip dependencies
Write-Host "Installing Python dependencies..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r $requirementsFile

# 7. Create shortcut in Startup folder
$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut("$startupFolder\$shortcutName")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$vbscriptPath`""
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$installDir\icon.ico"
$shortcut.Save()

Write-Host "Setup complete. The app will launch on next login."
