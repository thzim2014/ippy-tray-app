#PART 2 Config Management, IP Handling, Logging, and Floating Window
#This sets up all IP config, logging, and floating UI with persistent location and color logic.
# -----------------------
# PART 3 Tray Icon, IP Recheck, Monitoring, and Float Updates
# This section powers all logic related to:
# Tray icon color logic
# IP monitoring in the background
# Manual rechecking and float updates
# -----------------------
#PART 4 Tray Menu & Settings GUI (Main, Logs, Update Tabs)
# This portion builds the system tray icon with its menu and constructs the Main tab of the settings window, including:
# - IP to monitor
# - Interval
# - Checkboxes for notify, logging, always-on-screen
# -----------------------
# PART 5: Logs Tab – Filter, Search, Sort, Export
# This builds the Logs tab:
# ✅ Filter logs to only show “changed” entries
# ✅ Real-time search
# ✅ Column sorting (clickable)
# ✅ Export to CSV
# ✅ Reusable refresh function
# -----------------------
# PART 6: Update Tab & Version Checking
# This section enables:
# 🔍 Checking your GitHub-hosted version.txt
# 🔔 Alert if a newer version is available
# 🔗 Directs to GitHub for manual update
# -----------------------
# 💾 PART 7: Log Purging & Saving Settings
# 🧹 Purge logs UI
# 💾 Save & Close logic for all config updates
# 🧠 main() execution entrypoint
# -----------------------
# 🧠 PART 8: Saving Settings & Closing
# ✅ This part:
# Lets you purge logs by age
# Applies and saves all setting values
# Closes the settings window cleanly
#  🏁 PART 9: Main Entrypoint Execution
# -----------------------
# ✅ main.py — Part 10: Tray Menu & Window Toggle Logic
# This section is responsible for:
# Building the system tray icon and its right-click menu
# Handling:
# Launching the settings window
# Showing/hiding the floating window
# Manual IP recheck
# Exiting the app cleanly
# -----------------------

	

# -----------------------
#✅ main.py — Part 1: Imports, Constants & Dependency Setup
# =============================================
# iPPY Tray App - IP Monitor & Tray Utility
# Main script: Handles GUI, tray icon, logging,
# settings, update checking and IP monitoring
# =============================================
# -----------------------
# 📦 Ensure Required Modules Are Installed
# -----------------------
import subprocess
import sys

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

# -----------------------
# 📚 Core Imports
# -----------------------
import os
import time
import threading
import requests
import datetime
import tkinter as tk
from tkinter import ttk, filedialog
import pystray
from PIL import Image
import configparser
from win10toast import ToastNotifier
import csv
import traceback
import webbrowser




# -----------------------
#✅ main.py — Part 2: Paths, Globals, Folders
# -----------------------
# 📁 Paths & Constants
# -----------------------
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

# -----------------------
# 🌐 Global Runtime State
# -----------------------
current_ip = None
icon = None
float_window = None
config = configparser.ConfigParser()
notified = False
last_manual_check = 0
first_run = False

# -----------------------
# 🗂️ Ensure Folder Structure Exists
# -----------------------
os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)




# -----------------------
#✅ main.py — Part 3: Config Management, Logging, IP Utilities
# -----------------------
# ⚙️ Load & Save Configuration
# -----------------------
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

# -----------------------
# 🌍 Get External IP
# -----------------------
def get_ip():
    try:
        res = requests.get(IP_API_URL, timeout=5)
        return res.json().get('query', None)
    except Exception as e:
        log_error(e)
        return None

# -----------------------
# 📝 Log IP Checks
# -----------------------
def log_ip(ip, changed, manual=False):
    if config.getboolean('Settings', 'enable_logging', fallback=True):
        now = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        expected_ip = config.get('Settings', 'target_ip')
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow([
                now.split('|')[0],
                now.split('|')[1],
                expected_ip,
                ip,
                'Yes' if changed else 'No',
                'Yes' if manual else 'No'
            ])

def log_error(err):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {str(err)}\n{traceback.format_exc()}\n")



# -----------------------
#✅ main.py — Part 4: Toasts, Floating Window Class
# -----------------------
# 🔔 Windows Toast Notifications
# -----------------------
toaster = ToastNotifier()

def notify_change(old_ip, new_ip):
    if config.getboolean('Settings', 'notify_on_change', fallback=True):
        try:
            toaster.show_toast("IP Change Detected", f"{old_ip} ➔ {new_ip}", duration=5, threaded=True)
        except Exception as e:
            log_error(e)

# -----------------------
# 🪟 Floating Overlay Display
# -----------------------
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



# -----------------------
✅ main.py — Part 5: IP Monitoring, Tray Icon, Safe Threading
# -----------------------
# 🎨 Update Floating Window Label Color
# -----------------------
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

# -----------------------
# 🔁 Manual Recheck Button
# -----------------------
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


# -----------------------
#✅ main.py — Part 6: Monitor IP Loop (Threaded)
# -----------------------
# 📡 Background IP Monitor Loop
# -----------------------
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



# -----------------------
#✅ main.py — Part 7: Tray Icon & Safe Float Toggle
# -----------------------
# 🪟 Safely Toggle Floating IP Window
# -----------------------
def toggle_float_window():
    global float_window
    def run_float():
        global float_window
        float_window = FloatingWindow()
        float_window.mainloop()

    if float_window:
        try:
            float_window.after(0, lambda: float_window.deiconify() if float_window.state() == 'withdrawn' else float_window.withdraw())
        except Exception as e:
            log_error(e)
    else:
        threading.Thread(target=run_float, daemon=True).start()

# -----------------------
# 🖼️ Tray Icon Selector
# -----------------------
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




# -----------------------
#✅ main.py — Part 8: Tray Menu, Exit, Safe Settings Window
# -----------------------
# 🚪 Tray Icon Exit Handler
# -----------------------
def on_exit(icon, item):
    try:
        if float_window:
            float_window.destroy()
        icon.stop()
        os._exit(0)
    except Exception as e:
        log_error(e)

# -----------------------
# 🍔 Create Tray Icon Menu
# -----------------------
def create_tray():
    global icon

    def get_window_label():
        if float_window and float_window.state() != 'withdrawn':
            return "Hide IP Window"
        return "Show IP Window"

    # Safe menu creation (avoid threading errors)
    icon = pystray.Icon("iPPY", Image.open(get_tray_icon()), menu=pystray.Menu(
        pystray.MenuItem("Settings", lambda i: run_in_main_thread(on_settings)),
        pystray.MenuItem(lambda item: get_window_label(), lambda i: run_in_main_thread(toggle_float_window)),
        pystray.MenuItem("Recheck IP", lambda i: run_in_main_thread(recheck_ip)),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()




# -----------------------
#✅ main.py — Part 9: Main Thread Executor (Fixes GUI issues)
# -----------------------
# 🧠 Ensures tkinter runs in main thread
# -----------------------
def run_in_main_thread(func):
    import ctypes
    import inspect
    if threading.current_thread() == threading.main_thread():
        func()
    else:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(threading.get_ident()),
            ctypes.py_object(SystemExit)
        )




# -----------------------
#✅ main.py — Part 10: Settings Window, Logs Tab, Update Checker
# -----------------------
# 🧊 Tray Icon Display & Toggle Float Window
# -----------------------
def toggle_float_window():
    global float_window
    if float_window:
        if float_window.state() == 'withdrawn':
            float_window.deiconify()
        else:
            float_window.withdraw()
    else:
        # Safe creation of floating window from main thread
        float_window = FloatingWindow()
        float_window.after(0, float_window.deiconify)

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

# -----------------------
# 🚪 Tray Exit Logic
# -----------------------
def on_exit(icon, item):
    try:
        if float_window:
            float_window.destroy()
        icon.stop()
        os._exit(0)
    except Exception as e:
        log_error(e)

# -----------------------
# 🍔 Create the Tray Menu
# -----------------------
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
	
	
	
# -----------------------
#✅ main.py — Part 11: Full on_settings() GUI: Settings, Logs, Updates
# -----------------------
# ⚙️ Settings Window with Tabs
# -----------------------
def on_settings(icon=None, item=None):
    from tkinter import BooleanVar, StringVar

    win = tk.Tk()
    win.title("iPPY Settings")
    win.geometry("800x500")

    # Create tabs
    tabs = ttk.Notebook(win)
    main = ttk.Frame(tabs)
    logs = ttk.Frame(tabs)
    update = ttk.Frame(tabs)
    tabs.add(main, text="Main")
    tabs.add(logs, text="Logs")
    tabs.add(update, text="Update")
    tabs.pack(expand=1, fill='both')

    # -----------------------
    # MAIN TAB
    # -----------------------
    tk.Label(main, text="IP To Monitor:").pack()
    ip_entry = tk.Entry(main)
    ip_entry.insert(0, config['Settings']['target_ip'])
    ip_entry.pack()

    tk.Label(main, text="Checks per Minute (1-45):").pack()
    interval_entry = tk.Entry(main)
    interval_entry.insert(0, config['Settings']['check_interval'])
    interval_entry.pack()

    notify_var = BooleanVar(value=config.getboolean('Settings', 'notify_on_change'))
    log_var = BooleanVar(value=config.getboolean('Settings', 'enable_logging'))
    screen_var = BooleanVar(value=config.getboolean('Settings', 'always_on_screen'))

    tk.Checkbutton(main, text="Enable Notifications", variable=notify_var).pack(anchor='w')
    tk.Checkbutton(main, text="Enable Logging", variable=log_var).pack(anchor='w')
    tk.Checkbutton(main, text="Always on Screen", variable=screen_var).pack(anchor='w')

    # -----------------------
    # LOGS TAB
    # -----------------------
    filter_var = BooleanVar()
    search_var = StringVar()

    search_entry = tk.Entry(logs, textvariable=search_var)
    search_entry.pack(fill='x')

    log_table = ttk.Treeview(logs, columns=('Date', 'Time', 'Expected', 'Detected', 'Changed', 'Manual'), show='headings')
    for col in log_table['columns']:
        log_table.heading(col, text=col, command=lambda c=col: sort_table(c, False))
        log_table.column(col, width=100)
    log_table.pack(expand=True, fill='both')

    def sort_table(col, reverse):
        data = [(log_table.set(k, col), k) for k in log_table.get_children('')]
        data.sort(reverse=reverse)
        for index, (val, k) in enumerate(data):
            log_table.move(k, '', index)
        log_table.heading(col, command=lambda: sort_table(col, not reverse))

    def refresh_logs():
        log_table.delete(*log_table.get_children())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                for row in csv.reader(f, delimiter='|'):
                    if len(row) == 6:
                        if filter_var.get() and row[4] != 'Yes':
                            continue
                        if search_var.get().lower() not in '|'.join(row).lower():
                            continue
                        log_table.insert('', 'end', values=row)

    def export_logs(table):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Time', 'Expected IP', 'Detected IP', 'Changed', 'Manual'])
            for child in table.get_children():
                writer.writerow(table.item(child)['values'])

    tk.Checkbutton(logs, text="Only show changed", variable=filter_var, command=refresh_logs).pack(anchor='w')
    tk.Button(logs, text="Export to CSV", command=lambda: export_logs(log_table)).pack(anchor='e', pady=2, padx=2)
    search_var.trace_add('write', lambda *_: refresh_logs())
    refresh_logs()

# -----------------------
