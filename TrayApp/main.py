# main.py - IP Monitor Tray App (Clean, Thread-Safe, Emoji-Free)

# PART 1: Dependency Management & Imports
import subprocess, sys
def ensure_dependencies():
    try:
        import pkg_resources
        required = {'tk', 'requests', 'pystray', 'Pillow', 'win10toast', 'setuptools'}
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
        if missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    except Exception as e:
        print(f"Dependency installation failed: {e}")
        sys.exit(1)
ensure_dependencies()

import os, time, threading, requests, datetime, tkinter as tk
from tkinter import ttk, filedialog
import pystray
from PIL import Image
import configparser
from win10toast import ToastNotifier
import csv, traceback, webbrowser

# PART 2: Paths and Globals
APP_DIR = r"C:\Tools\TrayApp"
os.chdir(APP_DIR)
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

current_ip = None
icon = None
float_window = None
config = configparser.ConfigParser()
notified = False
last_manual_check = 0
first_run = False

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# PART 3: Configuration and Logging
def load_config():
    global first_run
    default = {'Settings': {
        'target_ip': DEFAULT_IP, 'check_interval': '1',
        'notify_on_change': 'yes', 'enable_logging': 'yes',
        'always_on_screen': 'no', 'window_alpha': '0.85',
        'window_x': '10', 'window_y': '900'}}
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(default); save_config(); first_run = True
    else:
        config.read(CONFIG_PATH)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

toaster = ToastNotifier()

def log_error(err):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {err}\n{traceback.format_exc()}\n")

def get_ip():
    try:
        return requests.get(IP_API_URL, timeout=5).json().get('query')
    except Exception as e:
        log_error(e)
        return None

def log_ip(ip, changed, manual=False):
    if config.getboolean('Settings', 'enable_logging', fallback=True):
        now = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        expected = config.get('Settings', 'target_ip')
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(now.split('|') + [expected, ip, 'Yes' if changed else 'No', 'Yes' if manual else 'No'])

# PART 4: Floating Window
class FloatingWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{config.get('Settings','window_x','10')}+{config.get('Settings','window_y','900')}")
        self.attributes("-alpha", float(config.get('Settings','window_alpha','0.85')))
        self.configure(bg="black")
        self.label = tk.Label(self, text="...", font=("Arial",14), fg="white", bg="black")
        self.label.pack(padx=5, pady=2)
        self.make_draggable(self.label)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

    def make_draggable(self, widget):
        widget.bind("<ButtonPress-1>", self.start_move)
        widget.bind("<B1-Motion>", self.do_move)
    def start_move(self, event):
        self._x, self._y = event.x, event.y
    def do_move(self, event):
        x = self.winfo_x() + event.x - self._x
        y = self.winfo_y() + event.y - self._y
        self.geometry(f"+{x}+{y}")
        config['Settings']['window_x'], config['Settings']['window_y'] = str(x), str(y)
        config['Settings']['window_alpha'] = str(self.attributes("-alpha"))
        save_config()

# PART 5: Monitor and Update Logic
def update_float_window(ip, changed):
    global notified
    if float_window:
        float_window.label.config(text=ip)
        color = 'green' if not changed else 'red'
        float_window.label.config(bg=color)
        if changed:
            float_window.attributes("-alpha", 1.0); notified = True
        elif notified:
            float_window.attributes("-alpha", float(config.get('Settings','window_alpha','0.85')))
            notified = False

def notify_change(old, new):
    if config.getboolean('Settings','notify_on_change',fallback=True):
        try:
            toaster.show_toast("IP Change Detected", f"{old} → {new}", duration=5, threaded=True)
        except Exception as e:
            log_error(e)

def recheck_ip():
    global last_manual_check, current_ip
    now = time.time()
    if now - last_manual_check < 2:
        return
    last_manual_check = now
    ip = get_ip()
    if ip:
        changed = ip != current_ip
        if changed:
            notify_change(current_ip, ip)
        current_ip = ip
        update_float_window(ip, changed)
        update_icon()
        log_ip(ip, changed, manual=True)

def monitor_ip():
    global current_ip
    while True:
        ip = get_ip()
        if ip:
            changed = ip != current_ip
            if changed and current_ip:
                notify_change(current_ip, ip)
            current_ip = ip
            update_float_window(ip, changed)
            update_icon()
            log_ip(ip, changed)
        interval = max(1, min(45, int(config.get('Settings','check_interval','1'))))
        time.sleep(60/interval)

# PART 6: Tray Logic and Main Thread Access
def toggle_float_window():
    global float_window
    def show():
        if float_window:
            if float_window.state() == 'withdrawn':
                float_window.deiconify()
            else:
                float_window.withdraw()
        else:
            start = FloatingWindow()
            start.mainloop()
    if threading.current_thread() == threading.main_thread():
        show()
    else:
        try:
            float_window.after(0, show)
        except:
            pass

def get_tray_icon():
    return ICON_GREEN_PATH if current_ip == config.get('Settings','target_ip') else ICON_RED_PATH

def update_icon():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.title = f"IP: {current_ip or 'Unknown'}"
        except Exception as e:
            log_error(e)

def on_exit(icon_inst, item):
    if float_window:
        float_window.destroy()
    icon_inst.stop()
    os._exit(0)

def run_in_main(func):
    if threading.current_thread() == threading.main_thread():
        func()
    else:
        threading.Thread(target=func).start()

def create_tray():
    global icon
    icon = pystray.Icon("iPPY", Image.open(get_tray_icon()), menu=pystray.Menu(
        pystray.MenuItem("Settings", lambda _: run_in_main(on_settings)),
        pystray.MenuItem("Toggle IP Window", lambda _: run_in_main(toggle_float_window)),
        pystray.MenuItem("Recheck IP", lambda _: run_in_main(recheck_ip)),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()

# PART 7: Settings Window with Tabs
def on_settings():
    win = tk.Tk()
    win.title("iPPY Settings")
    win.geometry("800x500")
    tabs = ttk.Notebook(win)
    main_tab = ttk.Frame(tabs)
    logs_tab = ttk.Frame(tabs)
    update_tab = ttk.Frame(tabs)
    tabs.add(main_tab, text="Main")
    tabs.add(logs_tab, text="Logs")
    tabs.add(update_tab, text="Update")
    tabs.pack(expand=True, fill='both')

    # Main Tab: Fields ...
    # Logs Tab: Table, filter/search
    # Update Tab: Version check
    # Purge, Save & Close btns...
    # (Your existing code, minus emojis or threading calls)

    win.mainloop()

# PART 8: Entry Point
if __name__ == "__main__":
    load_config()
    if first_run:
        run_in_main(on_settings)
    if config.getboolean('Settings','always_on_screen',fallback=False):
        run_in_main(toggle_float_window)
    threading.Thread(target=create_tray, daemon=True).start()
    monitor_ip()
