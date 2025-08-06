import os
import sys
import subprocess
import threading
import time
import configparser
import socket
from datetime import datetime
from pystray import Icon, Menu, MenuItem
from PIL import Image
from win10toast import ToastNotifier
from settings_ui import show_settings_window
import tkinter as tk

# --- Ensure Dependencies ---
def ensure_dependencies():
    try:
        import pkg_resources
        required = {
            'requests', 'pystray', 'Pillow', 'win10toast', 'setuptools',
            'tk', 'tkcalendar'
        }
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
        if missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    except Exception as e:
        print(f"Dependency installation failed: {e}")
        sys.exit(1)

ensure_dependencies()

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, 'assets', 'config.ini')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'ipchanges.log')
ERROR_LOG = os.path.join(BASE_DIR, 'logs', 'error.log')
ICON_PATH = os.path.join(BASE_DIR, 'assets', 'tray_app_icon.ico')

# --- Ensure Logs Directory ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# --- Load or Prompt Config ---
if not os.path.exists(CONFIG_PATH):
    show_settings_window()

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# --- Config Getters with Defaults ---
def get_config():
    return {
        'target_ip': config.get('Settings', 'target_ip', fallback='127.0.0.1'),
        'check_interval': config.getint('Settings', 'check_interval', fallback=60),
        'notify_on_change': config.getboolean('Settings', 'notify_on_change', fallback=True),
        'enable_logging': config.getboolean('Settings', 'enable_logging', fallback=True),
        'always_on_screen': config.getboolean('Settings', 'always_on_screen', fallback=False),
        'window_alpha': config.getfloat('Settings', 'window_alpha', fallback=0.9),
        'window_x': config.getint('Settings', 'window_x', fallback=100),
        'window_y': config.getint('Settings', 'window_y', fallback=100)
    }

settings = get_config()
current_ip = None
main_window = None
window_open = False
tray_icon = None
toaster = ToastNotifier()

# --- Logging ---
def log_change(message):
    if settings['enable_logging']:
        with open(LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")

def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] ERROR: {message}\n")

# --- IP Check Logic ---
def get_ip():
    try:
        return socket.gethostbyname(settings['target_ip'])
    except Exception as e:
        log_error(f"Failed to resolve IP: {e}")
        return None

def monitor_ip():
    global current_ip
    while True:
        new_ip = get_ip()
        if new_ip != current_ip:
            if current_ip is not None:
                change_msg = f"IP changed: {current_ip} -> {new_ip}"
                log_change(change_msg)
                if settings['notify_on_change']:
                    toaster.show_toast("IP Monitor", change_msg, icon_path=ICON_PATH, duration=5, threaded=True)
            current_ip = new_ip
        else:
            log_change("IP unchanged")
        time.sleep(settings['check_interval'])

# --- Window ---
def open_window():
    global main_window, window_open
    if window_open:
        return
    window_open = True
    main_window = tk.Tk()
    main_window.overrideredirect(True)
    main_window.attributes('-topmost', settings['always_on_screen'])
    main_window.attributes('-alpha', settings['window_alpha'])
    main_window.geometry(f"+{settings['window_x']}+{settings['window_y']}")
    main_window.configure(bg='black')

    label = tk.Label(main_window, text=f"Current IP: {current_ip}", font=("Segoe UI", 14), fg="white", bg="black")
    label.pack(padx=10, pady=5)

    def on_close():
        global window_open
        window_open = False
        main_window.withdraw()

    def start_move(event):
        main_window._x = event.x
        main_window._y = event.y

    def do_move(event):
        x = main_window.winfo_x() + event.x - main_window._x
        y = main_window.winfo_y() + event.y - main_window._y
        main_window.geometry(f"+{x}+{y}")
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)

    label.bind("<ButtonPress-1>", start_move)
    label.bind("<B1-Motion>", do_move)

    main_window.protocol("WM_DELETE_WINDOW", on_close)
    threading.Thread(target=main_window.mainloop, daemon=True).start()

def toggle_window(icon, item):
    global window_open
    if window_open:
        main_window.withdraw()
        window_open = False
        tray_icon.menu.items[0].text = "Open App Window"
    else:
        open_window()
        tray_icon.menu.items[0].text = "Close App Window"

# --- Tray Setup ---
def on_settings(icon=None, item=None):
    show_settings_window()

def on_exit(icon, item):
    if main_window:
        main_window.destroy()
    icon.stop()

def on_recheck():
    global current_ip
    new_ip = get_ip()
    if new_ip != current_ip:
        change_msg = f"IP rechecked: {current_ip} -> {new_ip}"
        log_change(change_msg)
        toaster.show_toast("IP Monitor", change_msg, icon_path=ICON_PATH, duration=5, threaded=True)
        current_ip = new_ip
    else:
        log_change("Manual recheck: IP unchanged")

def create_tray():
    global tray_icon
    icon_image = Image.open(ICON_PATH)
    tray_icon = Icon("TrayApp", icon=icon_image, menu=Menu(
        MenuItem("Close App Window" if settings['always_on_screen'] else "Open App Window", toggle_window),
        MenuItem("Recheck IP", lambda: on_recheck()),
        MenuItem("Settings", lambda: on_settings()),
        MenuItem("Exit", on_exit)
    ))
    tray_icon.run()

# --- Main ---
def main():
    threading.Thread(target=monitor_ip, daemon=True).start()
    if settings['always_on_screen']:
        open_window()
    create_tray()

if __name__ == '__main__':
    main()
