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

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.chdir(APP_DIR)

# -----------------------
# Global State
# -----------------------
config = configparser.ConfigParser()
first_run = False
current_ip = None
icon = None
float_window = None
settings_window = None
monitor_event = threading.Event()
root = None

# track manual recheck cooldown and overlay state
last_manual_check = 0
overlay_is_visible = False

target_ip = DEFAULT_IP
notify_on_change = True
enable_logging = True
always_on_screen = True

gui_queue = queue.Queue()

# -----------------------
# Config Load & Save
# -----------------------
def load_config():
    global first_run, target_ip, notify_on_change, enable_logging, always_on_screen
    defaults = {'Settings': {
        'target_ip': DEFAULT_IP,
        'check_interval': '10',
        'notify_on_change': 'yes',
        'enable_logging': 'yes',
        'always_on_screen': 'yes',
        'window_alpha': '0.85',
        'window_x': '100',
        'window_y': '100'
    }}
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(defaults)
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
# IP Fetch & Logging
# -----------------------
def get_ip():
    try:
        r = requests.get(IP_API_URL, timeout=5)
        return r.json().get('query')
    except Exception as e:
        log_error(e)
        return None


def log_ip(ip, changed, manual=False):
    if enable_logging:
        ts = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        with open(LOG_FILE, 'a', newline='') as f:
            csv.writer(f, delimiter='|').writerow([
                ts.split('|')[0], ts.split('|')[1], target_ip,
                ip, 'Yes' if changed else 'No', 'Yes' if manual else 'No'
            ])


def log_error(e):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {e}\n{traceback.format_exc()}\n")

# -----------------------
# Notifications
# -----------------------
toaster = ToastNotifier()

def notify_change(old, new):
    if notify_on_change:
        try:
            toaster.show_toast("IP Change Detected", f"{old} ➔ {new}", duration=5, threaded=True)
        except Exception as e:
            log_error(e)

# -----------------------
# Floating Overlay Window
# -----------------------
class FloatingWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        x = int(config.get('Settings', 'window_x', fallback='100'))
        y = int(config.get('Settings', 'window_y', fallback='100'))
        self.geometry(f'+{x}+{y}')
        self.label = tk.Label(self, text='...', font=('Arial', 14))
        self.label.pack(padx=5, pady=2)
        self.label.bind('<ButtonPress-1>', self._start)
        self.label.bind('<B1-Motion>', self._drag)
        self.protocol('WM_DELETE_WINDOW', self.withdraw)

    def _start(self, e):
        self._sx, self._sy = e.x, e.y

    def _drag(self, e):
        x = self.winfo_x() + e.x - self._sx
        y = self.winfo_y() + e.y - self._sy
        self.geometry(f'+{x}+{y}')
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        save_config()

    def update_label(self, ip):
        ok = (ip == target_ip)
        self.label.config(text=ip, bg='green' if ok else 'red', fg='black' if ok else 'white')
        alpha = float(config.get('Settings', 'window_alpha', fallback='0.85'))
        self.attributes('-alpha', alpha if ok else 1.0)

# -----------------------
# GUI Queue & Helpers
# -----------------------
def process_gui_queue():
    while not gui_queue.empty():
        fn, args = gui_queue.get()
        try:
            fn(*args)
        except Exception as e:
            log_error(e)
    root.after(100, process_gui_queue)

def gui_show_settings(): gui_queue.put((on_settings, ()))

def gui_toggle_overlay(): gui_queue.put((toggle_overlay, ()))

def gui_update_overlay(ip): gui_queue.put((overlay_update, (ip,)))

def gui_update_icon(): gui_queue.put((update_icon, ()))

def toggle_overlay():
    global float_window, overlay_is_visible
    if float_window and float_window.winfo_exists():
        if float_window.state() != 'withdrawn':
            float_window.withdraw()
            overlay_is_visible = False
        else:
            float_window.deiconify()
            overlay_is_visible = True
    else:
        float_window = FloatingWindow(root)
        overlay_is_visible = True
        # ensure label shows something right away
        if current_ip:
            try:
                float_window.update_label(current_ip)
            except Exception as e:
                log_error(e)


def overlay_update(ip):
    try:
        if float_window and float_window.winfo_exists():
            float_window.update_label(ip)
    except Exception as e:
        log_error(e)

# -----------------------
# Tray Icon & Actions
# -----------------------
def get_tray_icon():
    return ICON_GREEN_PATH if current_ip == target_ip else ICON_RED_PATH

def create_tray_icon():
    global icon
    def settings_action(icon_obj, item):
        gui_show_settings()
    def toggle_action(icon_obj, item):
        # Toggle via GUI thread; overlay_is_visible will be updated inside toggle_overlay()
        gui_toggle_overlay()
    def recheck_action(icon_obj, item):
        recheck_ip()
    def exit_action(icon_obj, item):
        on_exit(icon_obj, item)

    icon = pystray.Icon('iPPY', Image.open(get_tray_icon()))
    icon.menu = pystray.Menu(
        pystray.MenuItem('Settings', settings_action),
        pystray.MenuItem(lambda item: 'Hide IP Window' if overlay_is_visible else 'Show IP Window', toggle_action),
        pystray.MenuItem('Recheck IP', recheck_action),
        pystray.MenuItem('Exit', exit_action)
    )
    icon.run_detached()

# -----------------------
# Background Threads: IP Monitoring
# -----------------------
def recheck_ip():
    global current_ip, last_manual_check
    now = time.time()
    if now - last_manual_check < 2:
        return
    last_manual_check = now
    new = get_ip()
    if not new:
        return
    changed = (new != current_ip)
    if changed and current_ip:
        notify_change(current_ip, new)
    current_ip = new
    gui_update_overlay(new)
    gui_update_icon()
    log_ip(new, changed, True)


def monitor_ip():
    global current_ip
    while True:
        try:
            new = get_ip()
            if new:
                changed = (new != current_ip)
                if changed and current_ip:
                    notify_change(current_ip, new)
                current_ip = new
                gui_update_overlay(new)
                gui_update_icon()
                log_ip(new, changed, False)
        except Exception as e:
            log_error(e)
        interval = max(1, min(45, int(config.get('Settings', 'check_interval', fallback='10'))))
        if monitor_event.wait(timeout=60/interval):
            monitor_event.clear()

# -----------------------
# Icon Update Helper
# -----------------------
def update_icon():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.visible = True
        except Exception as e:
            log_error(e)

# -----------------------
# Exit
# -----------------------
def on_exit(icon_obj, item):
    """Exit requested from tray thread. Schedule Tk cleanup on main thread."""
    def _shutdown():
        global overlay_is_visible
        try:
            if settings_window and settings_window.winfo_exists():
                settings_window.destroy()
            if float_window and float_window.winfo_exists():
                float_window.destroy()
            overlay_is_visible = False
            # stop the Tk loop cleanly
            if root:
                try:
                    root.quit()
                except Exception:
                    pass
        except Exception as e:
            log_error(e)
    try:
        # schedule GUI teardown on main thread
        if root:
            root.after(0, _shutdown)
        # stop tray icon thread
        if icon_obj:
            try:
                icon_obj.visible = False
                icon_obj.stop()
            except Exception as e:
                log_error(e)
    finally:
        # hard-exit as a fallback if something is stuck
        threading.Timer(0.8, lambda: os._exit(0)).start()

# -----------------------
# Settings Window
# -----------------------
def on_settings():
    global settings_window
    from tkinter import BooleanVar, StringVar
    if settings_window and settings_window.winfo_exists():
        settings_window.lift()
        settings_window.focus_force()
        return
    win = tk.Toplevel(root)
    settings_window = win
    win.title('iPPY Settings')
    win.geometry('800x500')

    def on_close():
        global settings_window
        settings_window = None
        win.destroy()

    win.protocol('WM_DELETE_WINDOW', on_close)

    tabs = ttk.Notebook(win)
    tab_main = ttk.Frame(tabs)
    tab_logs = ttk.Frame(tabs)
    tab_update = ttk.Frame(tabs)
    tabs.add(tab_main, text='Main')
    tabs.add(tab_logs, text='Logs')
    tabs.add(tab_update, text='Update')
    tabs.pack(expand=1, fill='both')

    # Main Tab Controls
    tk.Label(tab_main, text='IP To Monitor:').pack()
    ip_entry = tk.Entry(tab_main)
    ip_entry.insert(0, config['Settings']['target_ip'])
    ip_entry.pack()

    tk.Label(tab_main, text='Checks per Minute (1-45):').pack()
    interval_entry = tk.Entry(tab_main)
    interval_entry.insert(0, config['Settings']['check_interval'])
    interval_entry.pack()

    notify_var = BooleanVar(value=config.getboolean('Settings','notify_on_change'))
    log_var = BooleanVar(value=config.getboolean('Settings','enable_logging'))
    screen_var = BooleanVar(value=config.getboolean('Settings','always_on_screen'))

    tk.Checkbutton(tab_main, text='Enable Notifications', variable=notify_var).pack(anchor='w')
    tk.Checkbutton(tab_main, text='Enable Logging', variable=log_var).pack(anchor='w')
    tk.Checkbutton(tab_main, text='Always on Screen', variable=screen_var).pack(anchor='w')

    # Logs Tab
    filter_var = BooleanVar()
    search_var = StringVar()
    search_entry = tk.Entry(tab_logs, textvariable=search_var)
    search_entry.pack(fill='x')
    log_table = ttk.Treeview(tab_logs, columns=('Date','Time','Target','Detected','Changed','Manual'), show='headings')
    for col in log_table['columns']:
        log_table.heading(col, text=col, command=lambda c=col: sort_table(c, False))
        log_table.column(col, width=100)
    log_table.pack(expand=1, fill='both')
    def sort_table(col, reverse):
        data = [(log_table.set(k, col), k) for k in log_table.get_children('')]
        data.sort(reverse=reverse)
        for i, (_, k) in enumerate(data):
            log_table.move(k, '', i)
        log_table.heading(col, command=lambda: sort_table(col, not reverse))
    def refresh_logs():
        log_table.delete(*log_table.get_children())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                for row in csv.reader(f, delimiter='|'):
                    if len(row)==6 and (not filter_var.get() or row[4]=='Yes') and search_var.get().lower() in '|'.join(row).lower():
                        log_table.insert('', 'end', values=row)
    def export_logs():
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Date','Time','Target','Detected','Changed','Manual'])
                for iid in log_table.get_children():
                    writer.writerow(log_table.item(iid)['values'])
    tk.Checkbutton(tab_logs, text='Only show changed', variable=filter_var, command=refresh_logs).pack(anchor='w')
    tk.Button(tab_logs, text='Export to CSV', command=export_logs).pack(anchor='e')
    search_var.trace_add('write', lambda *a: refresh_logs()); refresh_logs()

    # Update Tab
    update_label = tk.Label(tab_update, text='Checking version...')
    update_label.pack(pady=10)
    update_button = tk.Button(tab_update, text='Update Now', state='disabled', command=lambda: perform_update(update_label))
    update_button.pack()
    def perform_update(lbl):
        webbrowser.open('https://github.com/GoblinRules/ippy-tray-app')
        lbl.config(text='Manual update required.')
    def check_update():
        try:
            local = open(VERSION_PATH).read().strip()
            remote = requests.get(REMOTE_VERSION_URL).text.strip()
            if remote > local:
                update_label.config(text=f'New version {remote} available')
                update_button.config(state='normal')
            else:
                update_label.config(text='You are up to date.')
        except Exception as e:
            update_label.config(text='Error checking version')
            log_error(e)
    check_update()

    # Purge Logs
    purge_frame = tk.Frame(tab_logs)
    purge_frame.pack(pady=5)
    tk.Label(purge_frame, text='Purge logs older than:').pack(side='left')
    for months in (1,2,3):
        tk.Button(purge_frame, text=f'{months}m', command=lambda m=months: (purge_logs(m), refresh_logs())).pack(side='left')
    def purge_logs(months):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30*months)
        rows = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                rows = list(csv.reader(f, delimiter='|'))
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            for row in rows:
                if len(row)==6 and datetime.datetime.strptime(row[0], '%d/%m/%Y') >= cutoff:
                    writer.writerow(row)

    # Save & Close
    def save_and_close():
        global overlay_is_visible
        # capture previous setting before we change it
        try:
            old_aos = config.getboolean('Settings', 'always_on_screen')
        except Exception:
            old_aos = always_on_screen
        # write settings
        config.set('Settings', 'target_ip', ip_entry.get().strip())
        config.set('Settings', 'check_interval', str(max(1, min(45, int(interval_entry.get().strip() or '1')))))
        config.set('Settings', 'notify_on_change', 'yes' if notify_var.get() else 'no')
        config.set('Settings', 'enable_logging', 'yes' if log_var.get() else 'no')
        config.set('Settings', 'always_on_screen', 'yes' if screen_var.get() else 'no')
        save_config()
        # reload to refresh globals
        load_config()
        gui_update_icon()
        monitor_event.set()
        # reconcile overlay with new setting
        new_aos = screen_var.get()
        if old_aos != new_aos:
            if new_aos and not overlay_is_visible:
                toggle_overlay()
            elif not new_aos and overlay_is_visible:
                toggle_overlay()
        on_close()

    tk.Button(win, text='Save & Close', command=save_and_close).pack(pady=5)

# -----------------------
# Main Entrypoint
# -----------------------
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    load_config()
    create_tray_icon()
    threading.Thread(target=monitor_ip, daemon=True).start()
    if first_run or always_on_screen:
        toggle_overlay()
    if first_run:
        gui_show_settings()
    process_gui_queue()
    root.mainloop()
