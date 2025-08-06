# Install missing dependencies
import subprocess
import sys

def ensure_dependencies():
    try:
        import pkg_resources
        required = {'tk', 'requests', 'pystray', 'Pillow', 'win10toast', 'setuptools', 'tkcalendar'}
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
        if missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    except Exception as e:
        print(f"Dependency installation failed: {e}")
        sys.exit(1)

ensure_dependencies()
# main.py - iPPY Tray App with Enhanced Settings, Log Viewer, and Updater

import subprocess
import sys
import os
import time
import threading
import requests
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import pystray
from PIL import Image, ImageDraw, ImageTk
import configparser
from win10toast import ToastNotifier

# --- Setup ---
APP_DIR = r"C:\\Tools\\TrayApp"
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOG_PATH = os.path.join(APP_DIR, "logs", "ipchanges.log")
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")
VERSION_FILE = os.path.join(ASSETS_DIR, "version.txt")
REMOTE_MAIN = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/TrayApp/main.py"
REMOTE_VERSION = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/TrayApp/assets/version.txt"
IP_API_URL = "http://ip-api.com/json/"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# --- Globals ---
current_ip = None
icon = None
float_window = None
notified = False
last_manual_check = 0
last_logged_ip = None
last_log_time = time.time()
first_run = False

# --- Config ---
default_config = {
    'Settings': {
        'target_ip': '0.0.0.0',
        'check_interval': '1',
        'notify_on_change': 'yes',
        'enable_logging': 'yes',
        'always_on_screen': 'no',
        'window_alpha': '0.85',
        'window_x': '10',
        'window_y': '900'
    }
}
config = configparser.ConfigParser()

def load_config():
    global first_run
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(default_config)
        save_config()
        first_run = True
    else:
        config.read(CONFIG_PATH)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

# --- IP Logic ---
def get_ip():
    try:
        res = requests.get(IP_API_URL, timeout=5)
        return res.json()['query']
    except Exception:
        return None

def log_ip(ip, changed):
    global last_logged_ip, last_log_time
    if not config.getboolean('Settings', 'enable_logging', fallback=True):
        return
    now = datetime.datetime.now()
    if changed or (now.timestamp() - last_log_time) >= 3600:
        last_log_time = now.timestamp()
        with open(LOG_PATH, 'a') as f:
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            if changed:
                f.write(f"[{timestamp}] {ip} CHANGE\n")
            else:
                f.write(f"[{timestamp}] No change detected.\n")

# --- Notify ---
toaster = ToastNotifier()
def notify_change(old_ip, new_ip):
    if config.getboolean('Settings', 'notify_on_change', fallback=True):
        try:
            toaster.show_toast("IP Change Detected", f"{old_ip} ➔ {new_ip}", duration=5, threaded=True)
        except: pass

# --- Icon ---
def draw_icon(color):
    image = Image.new('RGB', (64, 64), color)
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=color)
    return image

def get_color():
    return "green" if current_ip == config['Settings']['target_ip'] else "red"

def update_icon():
    if icon:
        icon.icon = draw_icon(get_color())
        icon.title = f"IP: {current_ip or 'Unknown'}"

def update_float_window(ip, color):
    global notified
    if float_window:
        float_window.label.config(text=ip)
        float_window.label.config(bg=color)
        if color == "red":
            float_window.attributes("-alpha", 1.0)
            notified = True
        elif notified:
            float_window.attributes("-alpha", float(config['Settings']['window_alpha']))
            notified = False

# --- Monitor ---
def recheck_ip():
    global last_manual_check
    now = time.time()
    if now - last_manual_check >= 2:
        last_manual_check = now
        new_ip = get_ip()
        if new_ip:
            changed = new_ip != current_ip
            update_float_window(new_ip, get_color())
            update_icon()
            log_ip(new_ip, changed)

def monitor_ip():
    global current_ip
    while True:
        new_ip = get_ip()
        if new_ip:
            changed = new_ip != current_ip
            if changed:
                if current_ip:
                    notify_change(current_ip, new_ip)
                current_ip = new_ip
            update_icon()
            update_float_window(new_ip, get_color())
            log_ip(new_ip, changed)
        time.sleep(60 / max(1, min(45, int(config['Settings']['check_interval']))))

# --- Tray ---
def on_exit(icon, item):
    if float_window:
        float_window.destroy()
    icon.stop()
    os._exit(0)

def on_settings(icon=None, item=None):
    threading.Thread(target=launch_settings).start()

def toggle_window(icon=None, item=None):
    toggle_float_window()
    if icon:
        icon.update_menu()

def create_tray():
    global icon
    def get_window_label():
        return "Close App Window" if float_window and float_window.state() != 'withdrawn' else "Open App Window"
    icon = pystray.Icon("iPPY", draw_icon("grey"), menu=pystray.Menu(
        pystray.MenuItem("Settings", on_settings),
        pystray.MenuItem(lambda item: get_window_label(), toggle_window),
        pystray.MenuItem("Recheck IP", lambda icon, item: recheck_ip()),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()

# --- Floating Window ---
class FloatingWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{config.get('Settings', 'window_x')}+{config.get('Settings', 'window_y')}")
        self.attributes("-alpha", float(config['Settings']['window_alpha']))
        self.configure(bg="black")
        self.label = tk.Label(self, text="...", font=("Arial", 14), fg="white", bg="black")
        self.label.pack(padx=5, pady=2)
        self.make_draggable(self.label)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

    def make_draggable(self, widget):
        widget.bind("<ButtonPress-1>", self.start_move)
        widget.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = self.winfo_x() + event.x - self._x
        y = self.winfo_y() + event.y - self._y
        self.geometry(f"+{x}+{y}")
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        config['Settings']['window_alpha'] = str(self.attributes("-alpha"))
        save_config()

# --- Window and Settings Launcher ---
def toggle_float_window():
    global float_window
    if float_window:
        if float_window.state() == 'withdrawn':
            float_window.deiconify()
        else:
            float_window.withdraw()
    else:
        threading.Thread(target=lambda: FloatingWindow().mainloop(), daemon=True).start()

def launch_settings():
    import settings_ui
    settings_ui.launch(config, CONFIG_PATH, LOG_PATH, VERSION_FILE, REMOTE_VERSION, REMOTE_MAIN, ICON_PATH)

# --- Main ---
if __name__ == "__main__":
    try:
        load_config()
        if first_run:
            on_settings()
        if config.getboolean('Settings', 'always_on_screen'):
            toggle_float_window()
        tray_thread = threading.Thread(target=create_tray, daemon=True)
        tray_thread.start()
        monitor_ip()
    except Exception as e:
        with open(os.path.join(APP_DIR, "error.log"), "w") as f:
            f.write(str(e))
