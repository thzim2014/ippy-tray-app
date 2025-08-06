# Full main.py (standalone version)
import subprocess
import sys

# --- Ensure dependencies ---
def ensure_dependencies():
    try:
        import pkg_resources
        required = {'tk','requests', 'pystray', 'Pillow', 'win10toast', 'setuptools'}
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
        if missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    except Exception as e:
        print(f"Dependency installation failed: {e}")
        sys.exit(1)

ensure_dependencies()

# --- Imports ---
import os
import time
import threading
import requests
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pystray
from PIL import Image, ImageDraw
import configparser
from win10toast import ToastNotifier
import csv
import traceback
import webbrowser

# --- Constants ---
APP_DIR = r"C:\\Tools\\TrayApp"
LOG_DIR = os.path.join(APP_DIR, "logs")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
CONFIG_PATH = os.path.join(ASSETS_DIR, "config.ini")
VERSION_PATH = os.path.join(ASSETS_DIR, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/refs/heads/main/assets/version.txt"
ICON_GREEN_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_g.ico")
ICON_RED_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_r.ico")
LOG_FILE = os.path.join(LOG_DIR, "ipchanges.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")

IP_API_URL = "http://ip-api.com/json/"
DEFAULT_IP = "0.0.0.0"

# --- Global State ---
current_ip = None
icon = None
float_window = None
config = configparser.ConfigParser()
notified = False
last_manual_check = 0
first_run = False

# --- Ensure directories ---
os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Load and Save Config ---
def load_config():
    global first_run
    default_config = {
        'Settings': {
            'target_ip': DEFAULT_IP,
            'check_interval': '1',
            'notify_on_change': 'yes',
            'enable_logging': 'yes',
            'always_on_screen': 'no',
            'window_alpha': '0.85',
            'window_x': '10',
            'window_y': '900'
        }
    }
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(default_config)
        save_config()
        first_run = True
    else:
        config.read(CONFIG_PATH)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

# --- IP and Logging ---
def get_ip():
    try:
        res = requests.get(IP_API_URL, timeout=5)
        return res.json().get('query', None)
    except Exception as e:
        log_error(e)
        return None

def log_ip(ip, changed, manual=False):
    if config.getboolean('Settings', 'enable_logging', fallback=True):
        now = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        expected_ip = config.get('Settings', 'target_ip')
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow([now.split('|')[0], now.split('|')[1], expected_ip, ip, 'Yes' if changed else 'No', 'Yes' if manual else 'No'])

def log_error(err):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {str(err)}\n{traceback.format_exc()}\n")

# --- Toast Notification ---
toaster = ToastNotifier()
def notify_change(old_ip, new_ip):
    if config.getboolean('Settings', 'notify_on_change', fallback=True):
        try:
            toaster.show_toast("IP Change Detected", f"{old_ip} ➔ {new_ip}", duration=5, threaded=True)
        except Exception as e:
            log_error(e)

# --- Floating Window ---
class FloatingWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{config.get('Settings', 'window_x', fallback='10')}+{config.get('Settings', 'window_y', fallback='900')}")
        self.attributes("-alpha", float(config.get('Settings', 'window_alpha', fallback='0.85')))
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

def toggle_float_window():
    global float_window
    if float_window:
        if float_window.state() == 'withdrawn':
            float_window.deiconify()
        else:
            float_window.withdraw()
    else:
        def run():
            global float_window
            float_window = FloatingWindow()
            float_window.mainloop()
        threading.Thread(target=run, daemon=True).start()

# --- Update tray icon and floating window ---
def get_tray_icon():
    target_ip = config['Settings']['target_ip']
    return ICON_GREEN_PATH if current_ip == target_ip else ICON_RED_PATH

def update_icon():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.title = f"IP: {current_ip or 'Unknown'}"
        except Exception as e:
            log_error(e)

def update_float_window(ip, _):
    global notified
    if float_window:
        float_window.label.config(text=ip)
        target_ip = config.get('Settings', 'target_ip', fallback='0.0.0.0')
        correct = ip == target_ip
        display_color = 'green' if correct else 'red'
        float_window.label.config(bg=display_color)
        if not correct:
            float_window.attributes("-alpha", 1.0)
            notified = True
        elif notified:
            float_window.attributes("-alpha", float(config.get('Settings', 'window_alpha', fallback='0.85')))
            notified = False

# --- Recheck Logic ---
def recheck_ip():
    global last_manual_check, current_ip
    now = time.time()
    if now - last_manual_check >= 2:
        last_manual_check = now
        new_ip = get_ip()
        if new_ip:
            changed = new_ip != current_ip
            if changed:
                notify_change(current_ip, new_ip)
            current_ip = new_ip
            update_float_window(new_ip, None)
            update_icon()
            log_ip(new_ip, changed, manual=True)

# --- Monitor IP Loop ---
def monitor_ip():
    global current_ip
    while True:
        try:
            new_ip = get_ip()
            if new_ip:
                changed = new_ip != current_ip
                if changed:
                    if current_ip:
                        notify_change(current_ip, new_ip)
                    current_ip = new_ip
                update_float_window(new_ip, None)
                update_icon()
                log_ip(new_ip, changed, manual=False)
        except Exception as e:
            log_error(e)
        interval = max(1, min(45, int(config.get('Settings', 'check_interval', fallback='1'))))
        time.sleep(60 / interval)

# --- Tray ---
def on_exit(icon, item):
    try:
        if float_window:
            float_window.destroy()
        icon.stop()
        os._exit(0)
    except Exception as e:
        log_error(e)

def create_tray():
    global icon
    def get_window_label():
        if float_window and float_window.state() != 'withdrawn':
            return "Hide IP Window"
        return "Show IP Window"

    icon = pystray.Icon("iPPY", Image.open(get_tray_icon()), menu=pystray.Menu(
        pystray.MenuItem("Settings", on_settings),
        pystray.MenuItem(lambda item: get_window_label(), lambda i, _: toggle_float_window()),
        pystray.MenuItem("Recheck IP", lambda i, _: recheck_ip()),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()

# --- Settings GUI ---
def on_settings(icon=None, item=None):
    # (This is a placeholder to retain structure — full GUI settings implementation comes next if needed)
    messagebox.showinfo("Settings", "Settings window placeholder")

# --- Main ---
if __name__ == '__main__':
    try:
        load_config()
        if first_run:
            on_settings()
        if config.getboolean('Settings', 'always_on_screen'):
            toggle_float_window()
        threading.Thread(target=create_tray, daemon=True).start()
        monitor_ip()
    except Exception as e:
        log_error(e)
