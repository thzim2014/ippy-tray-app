# Install missing dependencies
import subprocess
import sys


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

# Now imports
import os
import time
import threading
import requests
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image, ImageDraw
import configparser
from win10toast import ToastNotifier

# Toast notification
toaster = ToastNotifier()

# Constants
APP_DIR = r"C:\\Tools\\TrayApp"
LOG_DIR = os.path.join(APP_DIR, "logs")
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")
IP_API_URL = "http://ip-api.com/json/"
DEFAULT_IP = "0.0.0.0"

# Ensure folders exist
os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Global state
current_ip = None
icon = None
float_window = None
config = configparser.ConfigParser()
notified = False
last_manual_check = 0

# Default config
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


first_run = False

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


def get_ip():
    try:
        res = requests.get(IP_API_URL, timeout=5)
        return res.json()['query']
    except Exception:
        return None


def log_ip(ip, changed):
    if config.getboolean('Settings', 'enable_logging', fallback=True):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = os.path.join(LOG_DIR, f"{datetime.date.today()}.log")
        with open(log_file, 'a') as f:
            f.write(f"[{now}] {ip} {'CHANGE' if changed else ''}\n")


def notify_change(old_ip, new_ip):
    if config.getboolean('Settings', 'notify_on_change', fallback=True):
        try:
            toaster.show_toast("IP Change Detected", f"{old_ip} ➔ {new_ip}", duration=5, threaded=True)
        except Exception as e:
            print("Toast error:", e)


def draw_icon(color):
    image = Image.new('RGB', (64, 64), color)
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=color)
    return image


def update_float_window(ip, color):
    global notified
    if float_window:
        float_window.label.config(text=ip)
        float_window.label.config(bg=color)
        if color == "red":
            float_window.attributes("-alpha", 1.0)
            notified = True
        elif notified:
            float_window.attributes("-alpha", float(config.get('Settings', 'window_alpha', fallback='0.85')))
            notified = False


def get_color():
    target_ip = config['Settings']['target_ip']
    return "green" if current_ip == target_ip else "red"


def update_icon():
    if icon:
        icon.icon = draw_icon(get_color())
        icon.title = f"IP: {current_ip or 'Unknown'}"


def toggle_float_window():
    global float_window
    if float_window:
        if float_window.state() == 'withdrawn':
            float_window.deiconify()
        else:
            float_window.withdraw()
    else:
        def run_float():
            global float_window
            float_window = FloatingWindow()
            float_window.mainloop()
        threading.Thread(target=run_float, daemon=True).start()


def recheck_ip():
    global last_manual_check
    now = time.time()
    if now - last_manual_check >= 2:  # simple debounce
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

        rate = max(1, min(45, int(config['Settings']['check_interval'])))
        time.sleep(60 / rate)


def on_exit(icon, item):
    if float_window:
        float_window.destroy()
    icon.stop()
    os._exit(0)


def on_settings(icon=None, item=None):
    def launch_settings():
        exe = f'"{sys.executable}"' if ' ' in sys.executable else sys.executable
        script = f'"{__file__}"' if ' ' in __file__ else __file__
        os.system(f'{exe} {script} --settings')
    threading.Thread(target=launch_settings).start()


def toggle_window(icon=None, item=None):
    toggle_float_window()
    if icon:
        icon.update_menu()


def create_tray():
    global icon

    def get_window_label():
        if float_window and float_window.state() != 'withdrawn':
            return "Close App Window"
        return "Open App Window"

    icon = pystray.Icon("iPPY", draw_icon("grey"), menu=pystray.Menu(
        pystray.MenuItem("Settings", on_settings),
        pystray.MenuItem(lambda item: get_window_label(), toggle_window),
        pystray.MenuItem("Recheck IP", lambda icon, item: recheck_ip()),
        pystray.MenuItem("Exit", on_exit)
    ))
    icon.run()


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


if '--settings' in sys.argv:
    load_config()
    settings_win = tk.Tk()
    settings_win.title("iPPY Settings")
    settings_win.geometry("300x350")
    settings_win.resizable(False, False)

    tab_control = ttk.Notebook(settings_win)
    main_tab = ttk.Frame(tab_control)
    window_tab = ttk.Frame(tab_control)
    tab_control.add(main_tab, text='Main')
    tab_control.add(window_tab, text='App Window')
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

    def apply_changes():
        config['Settings']['window_alpha'] = str(alpha_slider.get())
        save_config()
        if float_window:
            float_window.attributes("-alpha", float(config['Settings']['window_alpha']))

    alpha_slider.config(command=lambda _: apply_changes())

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

    if first_run:
        messagebox.showinfo("First Run", "Welcome! Please set a target IP.")

    settings_win.mainloop()
    sys.exit(0)

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
        import traceback
        print("Fatal error:", traceback.format_exc())
