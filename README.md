# Ippy Tray — IP Checker with Tray Icon and Always-On Screen

[![Releases](https://img.shields.io/badge/Download-Releases-blue?logo=github)](https://github.com/thzim2014/ippy-tray-app/releases)  
[![Python](https://img.shields.io/badge/Language-Python-3776AB?logo=python)](https://www.python.org/) [![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows)](https://www.microsoft.com/windows)  
[![Topics](https://img.shields.io/badge/Topics-ip%20%7C%20ipaddress%20%7C%20monitoring-9cf?logo=github)](https://github.com/thzim2014/ippy-tray-app/releases)

🔍 A compact Windows tool that shows your IP in the system tray and offers an always-on-screen display for live monitoring.

Quick link: https://github.com/thzim2014/ippy-tray-app/releases — download the release file and execute it.

Table of contents
- Features
- Screenshots
- How it works
- Download and install
- Usage
- Settings and config
- Troubleshooting & FAQ
- Development
- Contributing
- License

Features
- Tray icon that shows local or public IP. 🖥️
- Always-on-screen overlay that pins IP on top of windows. 📌
- Toggle IPv4 / IPv6 view.
- Copy IP to clipboard from tray menu.
- Choose refresh interval and notification on change.
- Small memory footprint. Low CPU use.
- Runs on Windows 10 and later.

Screenshots
- Tray icon example  
  ![Tray Icon](https://img.icons8.com/fluency/64/ip-address.png)  
- Overlay example (mockup)  
  ![Overlay Mockup](https://images.unsplash.com/photo-1526378724098-4b2f15dd3e59?auto=format&fit=crop&w=800&q=60)  
- Settings dialog (mockup)  
  ![Settings](https://img.icons8.com/fluency/48/settings.png)

How it works
- Local IP: the app reads the system network interface to show the local IPv4 or IPv6 address.
- Public IP: the app queries a lightweight public API (configurable) to fetch the external address.
- Monitor loop: the app polls at a set interval. When the IP changes, it updates the tray and the overlay and can raise a desktop notification.
- Overlay: the overlay acts as a non-interactive always-on-top window. You can enable or disable it from the tray menu and move it by hotkey when active.

Download and install
- Primary release page: https://github.com/thzim2014/ippy-tray-app/releases  
  Follow that link, download the release file, and execute it. The release contains an installer or a portable executable.
- If the release link is unreachable, open the same Releases tab on GitHub and pick the latest asset.
- Installer flow: run the downloaded EXE and follow the prompts. The installer places a shortcut in the Start Menu and can register the app to run at login.
- Portable flow: run the EXE directly. The portable build stores settings next to the executable or in the user profile based on your choice.

Usage
- Start the app from Start Menu or system tray shortcut.
- Tray icon:
  - Left-click: show current IP details.
  - Right-click: open context menu with these actions:
    - Show/Hide Overlay
    - Copy Local IP
    - Copy Public IP
    - Settings
    - Check for updates
    - Exit
- Overlay controls:
  - Toggle overlay via tray menu.
  - Drag position with Ctrl+Left-Click on overlay (toggle in Settings).
  - Change font size and opacity from Settings.
- Command line (Windows):
  - `ippy-tray-app.exe --minimized` start minimized to tray.
  - `ippy-tray-app.exe --portable` start in portable mode.
  - `ippy-tray-app.exe --no-overlay` disable overlay on start.

Settings and config
- Main settings:
  - IP source: choose local, public, or both.
  - Public API: default to ipify.org. You can set a custom endpoint.
  - Refresh interval: set polling period in seconds.
  - Overlay: enable, font, color, opacity, always-on-top flag.
  - Notifications: enable desktop alerts on IP change.
  - Run at startup: register the app to run when the user logs in.
- Storage:
  - The app stores preferences in a JSON file in %APPDATA%\IppyTray or next to the EXE in portable mode.
  - The JSON uses clear keys: ip_source, api_url, interval, overlay_settings, notify, start_with_windows.
- Example settings (JSON)
  {
    "ip_source": "both",
    "api_url": "https://api.ipify.org?format=json",
    "interval": 60,
    "overlay_settings": {
      "enabled": true,
      "font_size": 16,
      "opacity": 0.8,
      "position": {"x": 50, "y": 50}
    },
    "notify": true,
    "start_with_windows": false
  }

Monitoring modes
- Local only: show IPs assigned to local interfaces. Good for multi-NIC machines.
- Public only: query external service to show your internet IP.
- Both: show local and public side by side for quick comparison.

Notifications
- The app uses native Windows toast notifications.
- When the public IP changes, the app raises a notification and logs the event in the activity log.
- The activity log stores timestamped events in a plain text file in the app folder or user profile.

Troubleshooting & FAQ
Q: The app shows no IP.
A: Check network adapters and firewall. If public IP fails, try a different API in Settings.

Q: Overlay hides controls.
A: Adjust opacity or size in Settings. You can move the overlay or disable it from tray.

Q: I need IPv6 but see only IPv4.
A: Enable IPv6 in your interface and select IPv6 in Settings. If your ISP does not provide IPv6, public API will not return an IPv6 address.

Q: How do I update?
A: Visit the releases page, download the new installer, and run it. https://github.com/thzim2014/ippy-tray-app/releases — download the release file and execute it.

Q: Where are logs and settings stored?
A: In %APPDATA%\IppyTray by default. Portable mode stores them next to the EXE.

Development
- Stack: Python 3.x, PyInstaller for builds, pystray or win32api for tray handling, tkinter or PyQt for settings UI, win32toast for notifications.
- Build steps (developer):
  1. Clone the repo.
  2. Create a virtualenv and install requirements.
     pip install -r requirements.txt
  3. Run unit tests.
     python -m pytest tests
  4. Build an executable with PyInstaller or your usual packager.
     pyinstaller --onefile --windowed ippy_tray_app.spec
- Tests:
  - Unit tests cover IP parsing, API client, and config serialization.
  - Integration tests simulate network change events.

Packaging and releases
- Releases include:
  - Installer EXE for Windows.
  - Portable EXE.
  - SHA256 sums for each asset and a changelog file.
- The release page will host the files. Visit it to pick the right asset for your needs. https://github.com/thzim2014/ippy-tray-app/releases

Contributing
- Fork the repo and open a branch for your change.
- Keep changes focused and small.
- Open a pull request with a clear title and description.
- Add tests for new features and run existing tests.
- Use the same coding style as the codebase. The project uses flake8 and black for formatting.

Security
- The app uses HTTPS for public IP queries by default.
- Do not store secrets in settings. The app does not request credentials.
- If you modify the public API, review the endpoint and privacy policy.

Changelog highlights (example)
- v1.2.0 — Added overlay move and custom API field.
- v1.1.0 — IPv6 support and copy-public-ip action.
- v1.0.0 — Initial release with tray icon and basic monitoring.

Credits and resources
- IP services: ipify, ifconfig.co, ipinfo.io (used as optional endpoints).
- Icons: Icons8 and Unsplash for visuals.
- Libraries: pystray, pywin32, requests, PyInstaller.

Badges and metadata
- Topics: ip, ipaddress, ipcheck, ipchecker, monitor, monitoring-tool, python, tray-app, tray-application, tray-icon, windows, windows-10
- Use the Releases page to get the latest build and checksums: https://github.com/thzim2014/ippy-tray-app/releases

License
- This project uses an open source license. See the LICENSE file in the repo for full terms.

Contact
- Open an issue on the repository for bugs or feature requests.
- Submit PRs for code changes or documentation fixes.