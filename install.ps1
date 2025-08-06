Set-StrictMode -Version Latest

$repoRoot = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/TrayApp"
$installDir = "C:\\Tools\\TrayApp"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
$pythonInstaller = "$env:TEMP\\python-installer.exe"
$requirementsFile = "$installDir\\requirements.txt"
$shortcutName = "TrayApp.lnk"
$vbscriptPath = "$installDir\\launcher.vbs"
$pyScript = "$installDir\\main.py"
$startupFolder = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"

function Download-File {
    param ($url, $destination)
    Start-BitsTransfer -Source $url -Destination $destination -ErrorAction Stop
}

function Ensure-Folder {
    param ($path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

Ensure-Folder -path $installDir

Write-Host "Downloading Python installer..."
Download-File -url $pythonInstallerUrl -destination $pythonInstaller

Write-Host "Installing Python..."
Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
Remove-Item $pythonInstaller -Force

$env:Path += ";$env:ProgramFiles\\Python312\\Scripts;$env:ProgramFiles\\Python312\\"

# Dynamically locate python.exe
$pythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
if (-not $pythonExe) {
    Write-Error "Python executable not found in PATH. Installation may have failed."
    exit 1
}

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

Write-Host "Installing Python dependencies..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r $requirementsFile

$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut("$startupFolder\\$shortcutName")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$vbscriptPath`""
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$installDir\\icon.ico"
$shortcut.Save()

Write-Host "Setup complete. The app will launch on next login."
