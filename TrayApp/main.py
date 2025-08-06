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
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import requests

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
VERSION_FILE = os.path.join(BASE_DIR, 'assets', 'version.txt')
REMOTE_VERSION_URL = 'https://raw.githubusercontent.com/your/repo/main/assets/version.txt'
REMOTE_MAIN_URL = 'https://raw.githubusercontent.com/your/repo/main/main.py'

# --- Ensure Logs Directory ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# --- Load or Prompt Config ---
config = configparser.ConfigParser()
if not os.path.exists(CONFIG_PATH):
    config['Settings'] = {
        'target_ip': '127.0.0.1',
        'check_interval': '60',
        'notify_on_change': 'yes',
        'enable_logging': 'yes',
        'always_on_screen': 'no',
        'window_alpha': '0.9',
        'window_x': '100',
        'window_y': '100'
    }
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)
config.read(CONFIG_PATH)

def save_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

settings = {
    'target_ip': config.get('Settings', 'target_ip', fallback='127.0.0.1'),
    'check_interval': config.getint('Settings', 'check_interval', fallback=60),
    'notify_on_change': config.getboolean('Settings', 'notify_on_change', fallback=True),
    'enable_logging': config.getboolean('Settings', 'enable_logging', fallback=True),
    'always_on_screen': config.getboolean('Settings', 'always_on_screen', fallback=False),
    'window_alpha': config.getfloat('Settings', 'window_alpha', fallback=0.9),
    'window_x': config.getint('Settings', 'window_x', fallback=100),
    'window_y': config.getint('Settings', 'window_y', fallback=100)
}

current_ip = None
main_window = None
window_open = False
tray_icon = None
toaster = ToastNotifier()
last_logged_hour = -1

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
    global current_ip, last_logged_hour
    while True:
        new_ip = get_ip()
        now = datetime.now()
        if new_ip != current_ip:
            if current_ip is not None:
                change_msg = f"IP changed: {current_ip} -> {new_ip}"
                log_change(change_msg)
                if settings['notify_on_change']:
                    toaster.show_toast("IP Monitor", change_msg, icon_path=ICON_PATH, duration=5, threaded=True)
            current_ip = new_ip
        elif now.hour != last_logged_hour:
            log_change("No change detected in the last hour")
            last_logged_hour = now.hour
        time.sleep(settings['check_interval'])

# --- Floating Window ---
def open_window():
    global main_window, window_open
    if window_open:
        return
    window_open = True
    main_window = tk.Toplevel()
    main_window.overrideredirect(True)
    main_window.attributes('-topmost', settings['always_on_screen'])
    main_window.attributes('-alpha', settings['window_alpha'])
    main_window.geometry(f"+{settings['window_x']}+{settings['window_y']}")
    main_window.configure(bg='black')

    label = tk.Label(main_window, text=f"Current IP: {current_ip or 'Resolving...'}", font=("Segoe UI", 14), fg="white", bg="black")
    label.pack(padx=10, pady=5)

    def on_close():
        global window_open
        window_open = False
        main_window.withdraw()
        update_tray_menu()

    def start_move(event):
        main_window._x = event.x
        main_window._y = event.y

    def do_move(event):
        x = main_window.winfo_x() + event.x - main_window._x
        y = main_window.winfo_y() + event.y - main_window._y
        main_window.geometry(f"+{x}+{y}")
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        save_config()

    label.bind("<ButtonPress-1>", start_move)
    label.bind("<B1-Motion>", do_move)

    main_window.protocol("WM_DELETE_WINDOW", on_close)
    update_tray_menu()

def toggle_window(icon, item):
    global window_open
    if window_open:
        main_window.withdraw()
        window_open = False
    else:
        open_window()
    update_tray_menu()

# --- Tray Setup ---
def show_settings_window():
    settings_win = tk.Tk()
    settings_win.title("iPPY Settings")
    settings_win.geometry("400x450")
    settings_win.resizable(False, False)
    try:
        settings_win.iconbitmap(ICON_PATH)
    except: pass

    tab_control = ttk.Notebook(settings_win)
    main_tab = ttk.Frame(tab_control)
    window_tab = ttk.Frame(tab_control)
    logs_tab = ttk.Frame(tab_control)
    update_tab = ttk.Frame(tab_control)

    tab_control.add(main_tab, text='Main')
    tab_control.add(window_tab, text='App Window')
    tab_control.add(logs_tab, text='Logs')
    tab_control.add(update_tab, text='Updates')
    tab_control.pack(expand=1, fill="both")

    tk.Label(main_tab, text="Target IP:").pack()
    ip_entry = tk.Entry(main_tab)
    ip_entry.insert(0, config['Settings']['target_ip'])
    ip_entry.pack()

    tk.Label(main_tab, text="Checks per Minute (1–45):").pack()
    interval_entry = tk.Entry(main_tab)
    interval_entry.insert(0, config['Settings']['check_interval'])
    interval_entry.pack()

    notify_var = tk.BooleanVar(value=config.getboolean('Settings', 'notify_on_change'))
    log_var = tk.BooleanVar(value=config.getboolean('Settings', 'enable_logging'))
    screen_var = tk.BooleanVar(value=config.getboolean('Settings', 'always_on_screen'))

    tk.Checkbutton(main_tab, text="Enable Notifications", variable=notify_var).pack(anchor="w")
    tk.Checkbutton(main_tab, text="Enable Logging", variable=log_var).pack(anchor="w")
    tk.Checkbutton(main_tab, text="Always on Screen", variable=screen_var).pack(anchor="w")

    tk.Label(window_tab, text="Transparency (0.2 – 1.0):").pack()
    alpha_slider = tk.Scale(window_tab, from_=0.2, to=1.0, resolution=0.01, orient="horizontal")
    alpha_slider.set(float(config['Settings'].get('window_alpha', 0.85)))
    alpha_slider.pack(fill="x")

    def check_updates():
        if not os.path.exists(VERSION_FILE):
            local_version = "0.0.0"
        else:
            with open(VERSION_FILE) as vf:
                local_version = vf.read().strip()

        try:
            r = requests.get(REMOTE_VERSION_URL, timeout=5)
            remote_version = r.text.strip()
        except:
            messagebox.showerror("Error", "Could not reach update server.")
            return

        if remote_version != local_version:
            if messagebox.askyesno("Update Available", f"Update found: {remote_version}\nDownload and apply?"):
                try:
                    new_code = requests.get(REMOTE_MAIN_URL, timeout=10).text
                    with open(__file__, 'w') as mf:
                        mf.write(new_code)
                    with open(VERSION_FILE, 'w') as vf:
                        vf.write(remote_version)
                    messagebox.showinfo("Updated", "App updated. Please restart.")
                    settings_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Update failed: {e}")
        else:
            messagebox.showinfo("Up-to-date", "You are already on the latest version.")

    tk.Button(update_tab, text="Check for Updates", command=check_updates).pack(pady=20)

    def filter_logs():
        keyword = change_only_var.get()
        selected_date = log_date.get_date().strftime('%Y-%m-%d')
        output_box.delete("1.0", tk.END)

        if not os.path.exists(LOG_FILE):
            output_box.insert(tk.END, "No logs found.")
            return

        with open(LOG_FILE, "r") as f:
            for line in f:
                if selected_date in line:
                    if keyword:
                        if "CHANGE" in line:
                            output_box.insert(tk.END, line)
                    else:
                        output_box.insert(tk.END, line)

    change_only_var = tk.BooleanVar()
    tk.Checkbutton(logs_tab, text="Only show changes", variable=change_only_var).pack(anchor="w")
    tk.Label(logs_tab, text="Select Date:").pack()
    log_date = DateEntry(logs_tab, width=12, background='darkblue', foreground='white', borderwidth=2)
    log_date.set_date(datetime.today())
    log_date.pack(pady=5)
    tk.Button(logs_tab, text="Load Logs", command=filter_logs).pack()
    output_box = tk.Text(logs_tab, height=10)
    output_box.pack(fill="both", expand=True, padx=5, pady=5)

    def save():
        config['Settings']['target_ip'] = ip_entry.get().strip()
        config['Settings']['check_interval'] = str(max(1, min(45, int(interval_entry.get().strip() or 1))))
        config['Settings']['notify_on_change'] = 'yes' if notify_var.get() else 'no'
        config['Settings']['enable_logging'] = 'yes' if log_var.get() else 'no'
        config['Settings']['always_on_screen'] = 'yes' if screen_var.get() else 'no'
        config['Settings']['window_alpha'] = str(alpha_slider.get())
        save_config()
        settings_win.destroy()

    tk.Button(settings_win, text="Save", command=save).pack(pady=10)
    settings_win.mainloop()

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

def get_window_toggle_label():
    return "Close App Window" if window_open else "Open App Window"

def update_tray_menu():
    global tray_icon
    tray_icon.menu = Menu(
        MenuItem(get_window_toggle_label(), toggle_window),
        MenuItem("Recheck IP", lambda: on_recheck()),
        MenuItem("Settings", lambda: on_settings()),
        MenuItem("Exit", on_exit)
    )
    tray_icon.title = f"IP: {current_ip or 'Resolving...'}"

def create_tray():
    global tray_icon
    icon_image = Image.open(ICON_PATH)
    tray_icon = Icon("TrayApp", icon=icon_image)
    update_tray_menu()
    tray_icon.run()

# --- Main ---
def main():
    threading.Thread(target=monitor_ip, daemon=True).start()
    if settings['always_on_screen']:
        open_window()
    create_tray()

if __name__ == '__main__':
    main()
