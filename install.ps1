# Requires: PowerShell x64, TLS 1.2-capable .NET
$ErrorActionPreference = "Stop"

# Set paths
$repoRoot = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main"
$toolsDir = "C:\Tools\iPPY"
$pythonUrl = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-embed-amd64.zip"
$pythonZip = "$env:TEMP\python_embed.zip"
$pythonDir = "$toolsDir\Python"
$scriptPath = "$toolsDir\iPPY.py"
$vbsPath = "$toolsDir\launch_ippy.vbs"
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\iPPY.lnk"

# Force TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Create folders
New-Item -Force -ItemType Directory -Path $toolsDir | Out-Null
New-Item -Force -ItemType Directory -Path $pythonDir | Out-Null

# Download embedded Python
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force
Remove-Item $pythonZip

# Enable site module in embedded Python
$pthFile = Get-ChildItem "$pythonDir\python*.pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pthFile) {
    (Get-Content $pthFile.FullName) -replace '^#?import site', 'import site' | Set-Content $pthFile.FullName
} else {
    Write-Host "⚠️ Could not locate python*.pth to enable 'import site'"
}

# Download your Python script and requirements.txt
Invoke-WebRequest "$repoRoot/iPPY.py" -OutFile $scriptPath
Invoke-WebRequest "$repoRoot/requirements.txt" -OutFile "$toolsDir\requirements.txt"

# Install pip
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$toolsDir\get-pip.py"
& "$pythonDir\python.exe" "$toolsDir\get-pip.py"
Remove-Item "$toolsDir\get-pip.py"

# Install dependencies
& "$pythonDir\Scripts\pip.exe" install --upgrade pip setuptools
& "$pythonDir\Scripts\pip.exe" install -r "$toolsDir\requirements.txt"

# Create VBS launcher (silent)
@"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & "$pythonDir\python.exe" & Chr(34) & " " & Chr(34) & "$scriptPath" & Chr(34), 0, False
"@ | Out-File -Encoding ASCII $vbsPath

# Create shortcut to VBS launcher in Startup
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $vbsPath
$shortcut.Save()

