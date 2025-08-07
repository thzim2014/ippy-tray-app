# main.py - IP Monitor Tray App (Clean, Thread-Safe, with Settings/Logs/Update)
# PART 1: Dependency Management & Imports
import subprocess
import sys
import os
import time
import threading
import requests
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image
import configparser
from win10toast import ToastNotifier
import csv
import traceback
import webbrowser

# Ensure dependencies are installed
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

# PART 2: Paths and Globals
APP_DIR = r"C:\Tools\TrayApp"
os.makedirs(APP_DIR, exist_ok=True)
os.chdir(APP_DIR)

LOG_DIR = os.path.join(APP_DIR, "logs")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(ASSETS_DIR, "config.ini")
VERSION_PATH = os.path.join(ASSETS_DIR, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/refs/heads/main/assets/version.txt"
ICON_GREEN_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_g.ico")
ICON_RED_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_r.ico")
LOG_FILE = os.path.join(LOG_DIR, "ipchanges.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")
IP_API_URL = "http://ip-api.com/json/"
DEFAULT_IP = "0.0.0.0"

config = configparser.ConfigParser()
notified = False
last_manual_check = 0
current_ip = None
icon = None
float_window = None
first_run = False
toaster = ToastNotifier()

# PART 3: Configuration and Logging
def load_config():
    global first_run
    default = {
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
        config.read_dict(default)
        save_config()
        first_run = True
    else:
        config.read(CONFIG_PATH)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

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
        x = config.get('Settings', 'window_x', fallback='10')
        y = config.get('Settings', 'window_y', fallback='900')
        self.geometry(f"+{x}+{y}")
        alpha = float(config.get('Settings', 'window_alpha', fallback='0.85'))
        self.attributes("-alpha", alpha)
        self.configure(bg="black")
        self.label = tk.Label(self, text="...", font=("Arial", 14), fg="white", bg="black")
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
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        config['Settings']['window_alpha'] = str(self.attributes("-alpha"))
        save_config()

# PART 5: Monitoring & Icon Update Logic
def update_float_window(ip, changed):
    global notified
    if float_window:
        float_window.label.config(text=ip)
        bg = 'green' if ip == config.get('Settings', 'target_ip') else 'red'
        float_window.label.config(bg=bg)
        if changed:
            float_window.attributes("-alpha", 1.0)
            notified = True
        elif notified:
            float_window.attributes("-alpha", float(config.get('Settings', 'window_alpha', fallback='0.85')))
            notified = False

def notify_change(old, new):
    if config.getboolean('Settings', 'notify_on_change', fallback=True):
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
        interval = max(1, min(45, int(config.get('Settings', 'check_interval', fallback='1'))))
        time.sleep(60 / interval)

# PART 6: Tray Logic
def toggle_float_window():
    global float_window
    def show_or_hide():
        nonlocal float_window
        if float_window:
            if float_window.state() == 'withdrawn':
                float_window.deiconify()
            else:
                float_window.withdraw()
        else:
            float_window = FloatingWindow()
            float_window.mainloop()

    if threading.current_thread() == threading.main_thread():
        show_or_hide()
    else:
        threading.Thread(target=show_or_hide).start()

def get_tray_icon():
    return ICON_GREEN_PATH if current_ip == config.get('Settings', 'target_ip') else ICON_RED_PATH

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
    icon = pystray.Icon(
        "iPPY",
        Image.open(get_tray_icon()),
        menu=pystray.Menu(
            pystray.MenuItem("Settings", lambda _: run_in_main(on_settings)),
            pystray.MenuItem("Toggle IP Window", lambda _: run_in_main(toggle_float_window)),
            pystray.MenuItem("Recheck IP", lambda _: run_in_main(recheck_ip)),
            pystray.MenuItem("Exit", on_exit)
        )
    )
    icon.run()

# PART 7: Settings Window with Full Tabs
def on_settings():
    win = tk.Tk()
    win.title("iPPY Settings")
    win.geometry("800x600")
    tabs = ttk.Notebook(win)
    tabs.pack(expand=True, fill='both', padx=10, pady=10)

    # Main tab
    main_tab = ttk.Frame(tabs)
    tabs.add(main_tab, text="Main")
    target_var = tk.StringVar(value=config.get('Settings', 'target_ip', fallback=DEFAULT_IP))
    interval_var = tk.StringVar(value=config.get('Settings', 'check_interval', fallback='1'))
    notify_var = tk.BooleanVar(value=config.getboolean('Settings', 'notify_on_change', fallback=True))
    logging_var = tk.BooleanVar(value=config.getboolean('Settings', 'enable_logging', fallback=True))
    always_var = tk.BooleanVar(value=config.getboolean('Settings','always_on_screen',fallback=False))
    alpha_var = tk.StringVar(value=config.get('Settings', 'window_alpha', fallback='0.85'))

    ttk.Label(main_tab, text="Target IP:").pack(anchor='w', padx=10, pady=(10,0))
    ttk.Entry(main_tab, textvariable=target_var).pack(anchor='w', padx=10, pady=5)
    ttk.Label(main_tab, text="Check Frequency (per minute):").pack(anchor='w', padx=10, pady=(10,0))
    ttk.Entry(main_tab, textvariable=interval_var).pack(anchor='w', padx=10, pady=5)
    ttk.Checkbutton(main_tab, text="Notify on Change", variable=notify_var).pack(anchor='w', padx=10, pady=5)
    ttk.Checkbutton(main_tab, text="Enable Logging", variable=logging_var).pack(anchor='w', padx=10, pady=5)
    ttk.Checkbutton(main_tab, text="Always Show Window", variable=always_var).pack(anchor='w', padx=10, pady=5)
    ttk.Label(main_tab, text="Window Transparency (0.0–1.0):").pack(anchor='w', padx=10, pady=(10,0))
    ttk.Entry(main_tab, textvariable=alpha_var).pack(anchor='w', padx=10, pady=5)

    # Logs tab
    logs_tab = ttk.Frame(tabs)
    tabs.add(logs_tab, text="Logs")
    tree = ttk.Treeview(logs_tab, columns=("Date", "Time", "Target", "Detected", "Changed", "Manual"), show='headings')
    for col in tree["columns"]:
        tree.heading(col, text=col)
        tree.column(col, anchor='center')
    tree.pack(expand=True, fill='both', padx=10, pady=10)

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 6:
                    tree.insert('', 'end', values=parts)

    # Purge controls
    purge_frame = ttk.Frame(logs_tab)
    purge_frame.pack(pady=10)
    def purge_logs(months):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30*months)
        lines = []
        with open(LOG_FILE) as f:
            for line in f:
                try:
                    dt = datetime.datetime.strptime(line.split('|')[0].strip(), '%d/%m/%Y')
                    if dt >= cutoff:
                        lines.append(line)
                except:
                    lines.append(line)
        with open(LOG_FILE, 'w') as f:
            f.writelines(lines)
        win.destroy()
        on_settings()

    for m in (1, 3, 6, 12):
        ttk.Button(purge_frame, text=f"Purge older than {m} mo", command=lambda m=m: purge_logs(m)).pack(side='left', padx=5)

    # Update tab
    update_tab = ttk.Frame(tabs)
    tabs.add(update_tab, text="Update")
    def check_update():
        try:
            remote = requests.get(REMOTE_VERSION_URL).text.strip()
            local = open(VERSION_PATH).read().strip() if os.path.exists(VERSION_PATH) else "0"
            if remote > local:
                if messagebox.askyesno("Update", f"New version {remote} available. Download?"):
                    webbrowser.open("https://github.com/GoblinRules/ippy-tray-app/releases")
            else:
                messagebox.showinfo("Update", f"You are on the latest version: {local}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    ttk.Button(update_tab, text="Check for update", command=check_update).pack(pady=20)

    # Save & Close
    def save_and_close():
        config['Settings']['target_ip'] = target_var.get()
        config['Settings']['check_interval'] = interval_var.get()
        config['Settings']['notify_on_change'] = 'yes' if notify_var.get() else 'no'
        config['Settings']['enable_logging'] = 'yes' if logging_var.get() else 'no'
        config['Settings']['always_on_screen'] = 'yes' if always_var.get() else 'no'
        config['Settings']['window_alpha'] = alpha_var.get()
        save_config()
        win.destroy()
    ttk.Button(win, text="Save & Close", command=save_and_close).pack(pady=10)

    win.mainloop()

# PART 8: Entry Point
if __name__ == "__main__":
    load_config()
    if first_run:
        run_in_main(on_settings)
    if config.getboolean('Settings', 'always_on_screen', fallback=False):
        run_in_main(toggle_float_window)
    threading.Thread(target=create_tray, daemon=True).start()
    monitor_ip()
