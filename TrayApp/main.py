import subprocess
import sys
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
import queue

# -----------------------
# Ensure Dependencies
# -----------------------
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
# Constants & Paths
# -----------------------
APP_DIR = r"C:\Tools\TrayApp"
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOG_DIR = os.path.join(APP_DIR, "logs")
CONFIG_PATH = os.path.join(ASSETS_DIR, "config.ini")
VERSION_PATH = os.path.join(ASSETS_DIR, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/GoblinRules/ippy-tray-app/main/TrayApp/assets/version.txt"
ICON_GREEN_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_g.ico")
ICON_RED_PATH = os.path.join(ASSETS_DIR, "tray_app_icon_r.ico")
LOG_FILE = os.path.join(LOG_DIR, "ipchanges.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")
IP_API_URL = "http://ip-api.com/json/"
DEFAULT_IP = "0.0.0.0"

for folder in (APP_DIR, ASSETS_DIR, LOG_DIR):
    os.makedirs(folder, exist_ok=True)
os.chdir(APP_DIR)

# -----------------------
# Global State
# -----------------------
config = configparser.ConfigParser()
notified = False
last_manual_check = 0
first_run = False
current_ip = None
icon = None
float_window = None
monitor_event = threading.Event()
gui_queue = queue.Queue()
root = None  # main Tkinter root

# Runtime settings
# (Will be set in load_config)
target_ip = DEFAULT_IP
notify_on_change = True
enable_logging = True
always_on_screen = True

# -----------------------
# Config: Load & Save
# -----------------------
def load_config():
    global first_run, target_ip, notify_on_change, enable_logging, always_on_screen
    default_config = {
        'Settings': {
            'target_ip': DEFAULT_IP,
            'check_interval': '10',
            'notify_on_change': 'yes',
            'enable_logging': 'yes',
            'always_on_screen': 'yes',
            'window_alpha': '0.85',
            'window_x': '1115',
            'window_y': '303'
        }
    }
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(default_config)
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
        first_run = True
    else:
        config.read(CONFIG_PATH)
        first_run = False
    target_ip = config.get('Settings', 'target_ip', fallback=DEFAULT_IP)
    notify_on_change = config.getboolean('Settings', 'notify_on_change', fallback=True)
    enable_logging = config.getboolean('Settings', 'enable_logging', fallback=True)
    always_on_screen = config.getboolean('Settings', 'always_on_screen', fallback=True)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

# -----------------------
# IP Detection
# -----------------------
def get_ip():
    try:
        res = requests.get(IP_API_URL, timeout=5)
        return res.json().get('query', None)
    except Exception as e:
        log_error(e)
        return None

# -----------------------
# Logging Logic
# -----------------------
def log_ip(ip, changed, manual=False):
    if enable_logging:
        now = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow([
                now.split('|')[0],
                now.split('|')[1],
                target_ip,
                ip,
                'Yes' if changed else 'No',
                'Yes' if manual else 'No'
            ])

def log_error(err):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {str(err)}\n{traceback.format_exc()}\n")

# -----------------------
# Toast Notifications
# -----------------------
toaster = ToastNotifier()

def notify_change(old_ip, new_ip):
    if notify_on_change:
        try:
            toaster.show_toast("IP Change Detected", f"{old_ip} ➔ {new_ip}", duration=5, threaded=True)
        except Exception as e:
            log_error(e)

# -----------------------
# Floating Overlay Window (Thread-safe via main thread dispatcher)
# -----------------------
class FloatingWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
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

    def update_label(self, ip, correct):
        self.label.config(text=ip)
        display_color = 'green' if correct else 'red'
        fg_color = 'black' if correct else 'white'
        self.configure(bg=display_color)
        self.label.config(bg=display_color, fg=fg_color)
        if not correct:
            self.attributes("-alpha", 1.0)
        else:
            self.attributes("-alpha", float(config.get('Settings', 'window_alpha', fallback='0.85')))

# -----------------------
# GUI QUEUE DISPATCHER
# -----------------------
def process_gui_queue():
    while not gui_queue.empty():
        func, args = gui_queue.get()
        try:
            func(*args)
        except Exception as e:
            log_error(e)
    root.after(100, process_gui_queue)

# --- GUI API: All background threads use these! ---
def gui_show_settings():
    on_settings()

def gui_toggle_float_window():
    global float_window
    if float_window and float_window.winfo_exists():
        if float_window.state() == 'withdrawn':
            float_window.deiconify()
        else:
            float_window.withdraw()
    else:
        float_window = FloatingWindow(master=root)
        float_window.update()

def gui_update_float_label(ip):
    if float_window and float_window.winfo_exists():
        correct = ip == target_ip
        float_window.update_label(ip, correct)

def gui_update_icon():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.title = f"IP: {current_ip or 'Unknown'}"
        except Exception as e:
            log_error(e)

# -----------------------
# Thread-safe update hooks
# -----------------------
def update_float_window(ip, _):
    gui_queue.put((gui_update_float_label, (ip,)))
    # notified logic (can be handled here or left global if needed)

# -----------------------
# Manual Recheck Button (Rate Limited)
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
            gui_queue.put((gui_update_icon, ()))
            log_ip(new_ip, changed, manual=True)

# -----------------------
# Background Monitor Thread
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
                gui_queue.put((gui_update_icon, ()))
                log_ip(new_ip, changed, manual=False)
        except Exception as e:
            log_error(e)
        interval = max(1, min(45, int(config.get('Settings', 'check_interval', fallback='1'))))
        if monitor_event.wait(timeout=60 / interval):
            monitor_event.clear()

# -----------------------
# Tray Icon Display & Toggle Float Window
# -----------------------
def toggle_float_window():
    gui_queue.put((gui_toggle_float_window, ()))

def get_tray_icon():
    return ICON_GREEN_PATH if current_ip == target_ip else ICON_RED_PATH

# (update_icon now called via queue)

def update_icon():
    gui_queue.put((gui_update_icon, ()))

# -----------------------
# Tray Exit Logic
# -----------------------
def on_exit(icon, item):
    try:
        if float_window and float_window.winfo_exists():
            float_window.destroy()
        icon.stop()
        os._exit(0)
    except Exception as e:
        log_error(e)

# -----------------------
# Create the Tray Menu
# -----------------------
def create_tray():
    global icon
    def get_window_label():
        if float_window and float_window.winfo_exists() and float_window.state() != 'withdrawn':
            return "Hide IP Window"
        return "Show IP Window"
    icon = pystray.Icon("iPPY", Image.open(get_tray_icon()), menu=pystray.Menu(
        pystray.MenuItem("Settings", lambda i, _: toggle_float_window()),
        pystray.MenuItem(lambda item: get_window_label(), lambda i, _: toggle_float_window()),
        pystray.MenuItem("Recheck IP", lambda i, _: recheck_ip()),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()

# -----------------------
# Settings Window (Main, Logs, Update Tabs)
# -----------------------
def on_settings(icon=None, item=None):
    from tkinter import BooleanVar, StringVar
    win = tk.Toplevel(root)
    win.title("iPPY Settings")
    win.geometry("800x500")
    tabs = ttk.Notebook(win)
    main = ttk.Frame(tabs)
    logs = ttk.Frame(tabs)
    update = ttk.Frame(tabs)
    tabs.add(main, text="Main")
    tabs.add(logs, text="Logs")
    tabs.add(update, text="Update")
    tabs.pack(expand=1, fill='both')
    # --- MAIN TAB ---
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
    # --- LOGS TAB ---
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
    # --- UPDATE TAB ---
    update_status = tk.Label(update, text="Checking version...")
    update_status.pack(pady=10)
    update_button = tk.Button(update, text="Update Now", state='disabled', command=lambda: perform_update(update_status))
    update_button.pack()
    def check_for_update():
        try:
            with open(VERSION_PATH, 'r') as f:
                local = f.read().strip()
            remote = requests.get(REMOTE_VERSION_URL).text.strip()
            if remote > local:
                update_status.config(text=f"New version {remote} available")
                update_button.config(state='normal')
            else:
                update_status.config(text="You are up to date.")
        except Exception as e:
            update_status.config(text="Error checking version")
            log_error(e)
    def perform_update(status):
        webbrowser.open("https://github.com/GoblinRules/ippy-tray-app")
        status.config(text="Manual update required.")
    check_for_update()
    # --- PURGE LOGS ---
    purge_frame = tk.Frame(logs)
    purge_frame.pack(pady=5)
    tk.Label(purge_frame, text="Purge logs older than:").pack(side='left')
    for months in [1, 2, 3]:
        tk.Button(
            purge_frame,
            text=f"{months}m",
            command=lambda m=months: (purge_logs(m), refresh_logs())
        ).pack(side=''left', padx=5)

    def purge_logs(months):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30 * months)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                rows = list(csv.reader(f, delimiter='|'))
            filtered = [row for row in rows if len(row) == 6 and datetime.datetime.strptime(row[0], '%d/%m/%Y') >= cutoff]
            with open(LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f, delimiter='|')
                writer.writerows(filtered)

    # --- SAVE AND CLOSE ---
    def save_and_close():
        config.set('Settings', 'target_ip', ip_entry.get().strip())
        config.set('Settings', 'check_interval', str(max(1, min(45, int(interval_entry.get().strip() or 1)))))
        config.set('Settings', 'notify_on_change', 'yes' if notify_var.get() else 'no')
        config.set('Settings', 'enable_logging', 'yes' if log_var.get() else 'no')
        config.set('Settings', 'always_on_screen', 'yes' if screen_var.get() else 'no')
        save_config()
        load_config()
        gui_update_icon()
        monitor_event.set()
        # Handle always_on_screen immediately
        try:
            if always_on_screen:
                if not float_window or not float_window.winfo_exists() or float_window.state() == 'withdrawn':
                    gui_toggle_float_window()
            else:
                if float_window and float_window.winfo_exists() and float_window.state() != 'withdrawn':
                    gui_toggle_float_window()
        except Exception as e:
            log_error(e)
        win.destroy()

    tk.Button(win, text="Save & Close", command=save_and_close).pack(pady=5)
    win.mainloop()

# -----------------------
# MAIN APPLICATION START
# -----------------------
if __name__ == '__main__':
    try:
        root = tk.Tk()
        root.withdraw()  # Hide root window, used for floats and dialogs
        load_config()
        if first_run:
            gui_queue.put((gui_show_settings, ()))
        if always_on_screen:
            gui_queue.put((gui_toggle_float_window, ()))
        threading.Thread(target=create_tray, daemon=True).start()
        threading.Thread(target=monitor_ip, daemon=True).start()
        process_gui_queue()
        root.mainloop()
    except Exception as e:
        log_error(e)
