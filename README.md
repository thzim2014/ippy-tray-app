# IP Tray App Installer

![Tray App Icon](https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/assets/icon.png)

A lightweight, Python-based system tray application to monitor the public IP address of a specific target (e.g., remote device, server, etc.). Displays changes, logs them, and optionally notifies the user.

---

## 🚀 Features

* Runs silently in the Windows system tray.
* Monitors a target IP address at configurable intervals.
* Detects changes and notifies the user (via Win10 toast notification).
* Launches on login.
* Configurable behavior (interval, transparency, on-screen locking, etc.).
* Logging option for detected changes.
* Click-and-drag window positioning.

---

## 🔧 Installation

### 🆕 One-Line Install (Modern Systems)

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/install.ps1' | iex"
```

### 🖥️ Fix for Older Windows Systems (pre-TLS 1.2)

Run this first to enable TLS 1.2 and strong crypto:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
```

Then run:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/install.ps1' | iex"
```

---

## 📂 App Structure

```
C:\Tools\TrayApp\
├── main.py           # Main tray app script
├── launcher.vbs      # VBS silent launcher
├── config.ini        # Settings file (auto-created if missing)
├── requirements.txt  # Python dependencies
```

---

## ⚙️ Configuration (`config.ini`)

The config file is located at:

```
C:\Tools\TrayApp\config.ini
```

If it's missing on first run, it is automatically created and the settings window will pop up.

Example:

```ini
[Settings]
target_ip = 127.0.0.1
check_interval = 30
notify_on_change = yes
enable_logging = yes
always_on_screen = no
window_alpha = 0.99
window_x = 100
window_y = 500
```

| Setting                | Description                                         |
| ---------------------- | --------------------------------------------------- |
| `target_ip`            | IP address to monitor (must be set on first run)    |
| `check_interval`       | How often (in seconds) to recheck the IP            |
| `notify_on_change`     | Show system notification if IP changes (`yes`/`no`) |
| `enable_logging`       | Save changes to `ip_log.txt` (`yes`/`no`)           |
| `always_on_screen`     | Force tray window to stay visible (`yes`/`no`)      |
| `window_alpha`         | Transparency (0.0 to 1.0)                           |
| `window_x`, `window_y` | Initial screen position                             |

---

## 🔁 Usage

* The tray app **starts automatically on login** via a shortcut in the `Startup` folder.
* If run for the first time and no config exists, the **settings window will pop up** and prompt you to set an IP.
* To **manually relaunch** after crash:

  ```
  C:\Tools\TrayApp\main.py
  ```
* To **close the app**, right-click the tray icon and choose **Exit**.
* To **reopen the window**, right-click the tray icon and choose **Open**.

---

## 🌐 IP Checking Logic

* The script checks the **public IP of the target IP** by sending a request to:

  ```
  http://ip-api.com/json/{target_ip}
  ```
* This API has a **rate limit of 45 requests per minute per IP**. Keep your `check_interval` above `2` seconds to stay safe.

---

## 🖼️ Screenshots

| Tray Icon                                                                             | Settings                                                                                  | Notifications                                                                          |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| ![](https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/assets/icon.png) | ![](https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/assets/settings.png) | ![](https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/assets/toast.png) |

---

## 🧼 Uninstall

* Remove the shortcut from:

  ```
  %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TrayApp.lnk
  ```
* Delete folder:

  ```
  C:\Tools\TrayApp
  ```

---

## 🧠 Notes

* Requires Windows with Python 3.12 (installer included in script).
* Fully self-contained: all required dependencies are installed automatically.
* Built-in auto-repair for malformed `requirements.txt`.

---

## 🛠️ Maintainer

**GoblinRules** – [GitHub](https://github.com/GoblinRules)
