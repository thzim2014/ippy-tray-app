# 🛰️ IP Tray App Installer

![Tray App Icon](https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/assets/icon.png)

A lightweight, Python-based system tray application that monitors your public IP address. It runs silently, logs any changes, notifies the user, and includes a GUI for configuration and history browsing.

---

## 🚀 Features

- ✅ Runs silently in the Windows system tray
- 📡 Monitors your public IP at configurable intervals
- 🔔 Notifies you of changes via Windows toast notifications
- 🧠 Remembers settings across reboots (stored in config.ini)
- 📁 Logs all checks (with timestamps, expected vs detected IPs, manual flag, change detection)
- 🧪 Sort, search, filter and export logs from the Settings > Logs tab
- ♻️ Purge logs older than 1/2/3 months
- 🆕 Update checker in Settings > Update tab (compares local and GitHub version)
- 🖥️ Floating window with draggable position and live IP display (green = match, red = mismatch)
- 🌐 Optionally always-on-screen floating IP status
- 🔧 Fully configurable with built-in GUI
- ☁️ Auto-launches silently on system startup
- 🐍 Automatically installs Python and dependencies
- 🛠️ Error logging to `logs/errors.log`

---

## 🔧 Installation

### One-Line Install

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/install.ps1' | iex"
```

### For Older Windows (pre-TLS 1.2)

Enable TLS 1.2 manually:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
```

Then run the install command again.

---

## 📂 File Structure

```
C:\Tools\TrayApp
│
├── main.py
├── logs\
│   ├── ipchanges.log
│   └── errors.log
├── assets\
│   ├── tray_app_icon.ico
│   ├── tray_app_icon_g.ico
│   ├── tray_app_icon_r.ico
│   ├── icon.png
│   ├── launcher.vbs
│   ├── requirements.txt
│   └── config.ini
```

---

## ⚙️ Configuration

The `config.ini` is auto-generated at first run and stores all app settings.

```ini
[Settings]
target_ip = 1.2.3.4
check_interval = 10
notify_on_change = yes
enable_logging = yes
always_on_screen = no
window_alpha = 0.85
window_x = 10
window_y = 900
```

---

## 🛠️ Usage

- Right-click the tray icon for:
  - Settings
  - Recheck IP
  - Show/Hide IP Window
  - Exit
- First run triggers the Settings window if no `config.ini` is found
- Logs are viewable and exportable from the Logs tab
- IP mismatch sets tray icon to red and floating window background to red
- All errors logged to `logs/errors.log`

---

## 🧼 Uninstall

Delete the following:
- Shortcut from:  
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TrayApp.lnk`
- Folder:  
  `C:\Tools\TrayApp`

---

## 👤 Maintainer

**GoblinRules**  
[🔗 GitHub Profile](https://github.com/GoblinRules)

---

## 📦 License

MIT License – do whatever you want, but don’t blame me if it breaks 😊