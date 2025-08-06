# Download and run the installer .bat from GitHub
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/install_ippy.bat" -OutFile "$env:TEMP\install_ippy.bat"
Start-Process -FilePath "$env:TEMP\install_ippy.bat"
