# setup.ps1
$ErrorActionPreference = "Stop"

$installPath = "C:\Tools\iPPY"

# Install Git if missing
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Start-Process "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.1/Git-2.42.0-64-bit.exe" -Wait
}

# Clone the repo
if (-not (Test-Path $installPath)) {
    git clone https://github.com/YourUsername/ippy-tray-app.git $installPath
}

# Download and install Python if needed
$pythonPath = "$installPath\Python"
if (-not (Test-Path "$pythonPath\python.exe")) {
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip" -OutFile "$installPath\python.zip"
    Expand-Archive "$installPath\python.zip" -DestinationPath $pythonPath -Force
    Remove-Item "$installPath\python.zip"
}

# Install pip and dependencies
Set-Location $pythonPath
Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
.\python.exe get-pip.py
.\python.exe -m pip install --upgrade pip setuptools requests pystray Pillow win10toast

# Add to startup
$shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"
$target = "$pythonPath\python.exe"
$script = "$installPath\ippy_tray.py"

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($shortcut)
$sc.TargetPath = $target
$sc.Arguments = "`"$script`""
$sc.WindowStyle = 7
$sc.Save()

# Launch iPPY
Start-Process $target "`"$script`""
