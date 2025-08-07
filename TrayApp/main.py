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
root = None                # Main Tk root
target_ip = DEFAULT_IP
enable_notifications = True
enable_logging = True
always_on_screen = True
settings_window = None     # Singleton settings window

# -----------------------
# Config Load & Save
# -----------------------
def load_config():
    global first_run, target_ip, enable_notifications, enable_logging, always_on_screen
    default_cfg = {'Settings': {'target_ip': DEFAULT_IP,
                                'check_interval': '10',
                                'notify_on_change': 'yes',
                                'enable_logging': 'yes',
                                'always_on_screen': 'yes',
                                'window_alpha': '0.85',
                                'window_x': '100',
                                'window_y': '100'}}
    if not os.path.exists(CONFIG_PATH):
        config.read_dict(default_cfg)
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
        first_run = True
    else:
        config.read(CONFIG_PATH)
        first_run = False
    target_ip = config.get('Settings', 'target_ip', fallback=DEFAULT_IP)
    enable_notifications = config.getboolean('Settings', 'notify_on_change', fallback=True)
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
        resp = requests.get(IP_API_URL, timeout=5)
        return resp.json().get('query')
    except Exception as e:
        log_error(e)
        return None

def log_ip(ip, changed, manual=False):
    if enable_logging:
        now = datetime.datetime.now().strftime('%d/%m/%Y|%H:%M:%S')
        with open(LOG_FILE, 'a', newline='') as f:
            w = csv.writer(f, delimiter='|')
            w.writerow([now.split('|')[0], now.split('|')[1], target_ip, ip,
                        'Yes' if changed else 'No', 'Yes' if manual else 'No'])

def log_error(e):
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {e}\n{traceback.format_exc()}\n")

# -----------------------
# Notifications
# -----------------------
toaster = ToastNotifier()

def notify_change(old, new):
    if enable_notifications:
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
        x = config.getint('Settings', 'window_x', 100)
        y = config.getint('Settings', 'window_y', 100)
        self.geometry(f'+{x}+{y}')
        self.attributes('-alpha', config.getfloat('Settings', 'window_alpha', 0.85))
        self.label = tk.Label(self, text='...', bg='black', fg='white', font=('Arial',14))
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
        config['Settings']['window_x'], config['Settings']['window_y'] = str(x), str(y)
        save_config()
    def update_label(self, ip):
        ok = (ip == target_ip)
        self.label.config(text=ip, bg='green' if ok else 'red', fg='black' if ok else 'white')
        if ok:
            self.attributes('-alpha', config.getfloat('Settings','window_alpha',0.85))
        else:
            self.attributes('-alpha', 1.0)

# -----------------------
# GUI Dispatcher
# -----------------------
def process_gui_queue():
    while not gui_queue.empty():
        fn, args = gui_queue.get()
        try:
            fn(*args)
        except Exception as e:
            log_error(e)
    root.after(100, process_gui_queue)

def gui_show_settings(): gui_queue.put((on_settings,()))
def gui_toggle_overlay(): gui_queue.put((toggle_overlay,()))
def gui_update_overlay(ip): gui_queue.put((overlay_update,(ip,)))
def gui_update_icon(): gui_queue.put((icon_update,()))

# -----------------------
# Overlay Helpers
# -----------------------
def toggle_overlay():
    global float_window
    if float_window and float_window.winfo_exists():
        float_window.withdraw() if float_window.state()!='withdrawn' else float_window.deiconify()
    else:
        float_window = FloatingWindow(root)
        float_window.update()

def overlay_update(ip):
    if float_window and float_window.winfo_exists():
        float_window.update_label(ip)

def icon_update():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.title = f"IP: {current_ip or 'Unknown'}"
        except Exception as e:
            log_error(e)

# -----------------------
# Background Tasks
# -----------------------
def update_execution(ip,_): gui_queue.put((overlay_update,(ip,)))

def recheck_ip():
    global last_manual_check,current_ip
    if time.time()-last_manual_check < 2: return
    last_manual_check = time.time()
    new = get_ip()
    if not new: return
    changed = (new != current_ip)
    if changed and current_ip: notify_change(current_ip,new)
    current_ip = new
    update_execution(new,None)
    gui_update_icon()
    log_ip(new,changed,True)

def monitor_ip():
    global current_ip
    while True:
        try:
            new = get_ip()
            if new:
                changed = (new != current_ip)
                if changed and current_ip: notify_change(current_ip,new)
                current_ip = new
                update_execution(new,None)
                gui_update_icon()
                log_ip(new,changed,False)
        except Exception as e:
            log_error(e)
        iv = max(1,min(45,int(config.get('Settings','check_interval',fallback='10'))))
        if monitor_event.wait(timeout=60/iv):
            monitor_event.clear()

# -----------------------
# Tray Icon
# -----------------------
def get_tray_icon(): return ICON_GREEN_PATH if current_ip==target_ip else ICON_RED_PATH

def on_exit(icon_obj,item):
    try:
        if float_window and float_window.winfo_exists(): float_window.destroy()
        icon_obj.stop(); os._exit(0)
    except Exception as e:
        log_error(e)

def create_tray():
    global icon
    def lbl(): return 'Hide IP Window' if float_window and float_window.winfo_exists() and float_window.state()!='withdrawn' else 'Show IP Window'
    icon = pystray.Icon('iPPY', Image.open(get_tray_icon()), pystray.Menu(
        pystray.MenuItem('Settings', lambda i,_: gui_show_settings()),
        pystray.MenuItem(lambda item: lbl(), lambda i,_: gui_toggle_overlay()),
        pystray.MenuItem('Recheck IP', lambda i,_: recheck_ip()),
        pystray.MenuItem('Exit', on_exit)
    ))
    icon.run()

# -----------------------
# Settings GUI
# -----------------------
def on_settings(icon_obj=None,item=None):
    global settings_window
    from tkinter import BooleanVar,StringVar
    if settings_window and settings_window.winfo_exists():
        settings_window.lift(); settings_window.focus_force()
        return
    win = tk.Toplevel(root)
    settings_window = win
    win.title('iPPY Settings'); win.geometry('800x500')
    def on_close():
        global settings_window
        settings_window = None
        win.destroy()
    win.protocol('WM_DELETE_WINDOW', on_close)
    tabs = ttk.Notebook(win)
    main = ttk.Frame(tabs); logs = ttk.Frame(tabs); update_tab = ttk.Frame(tabs)
    tabs.add(main, text='Main'); tabs.add(logs, text='Logs'); tabs.add(update_tab, text='Update')
    tabs.pack(expand=1, fill='both')
    # Main Tab
    tk.Label(main, text='IP To Monitor:').pack()
    ip_e = tk.Entry(main); ip_e.insert(0, config['Settings']['target_ip']); ip_e.pack()
    tk.Label(main, text='Checks/min (1-45):').pack()
    iv_e = tk.Entry(main); iv_e.insert(0, config['Settings']['check_interval']); iv_e.pack()
    notify_var = BooleanVar(value=config.getboolean('Settings','notify_on_change'))
    log_var = BooleanVar(value=config.getboolean('Settings','enable_logging'))
    screen_var= BooleanVar(value=config.getboolean('Settings','always_on_screen'))
    tk.Checkbutton(main, text='Enable Notifications', variable=notify_var).pack(anchor='w')
    tk.Checkbutton(main, text='Enable Logging', variable=log_var).pack(anchor='w')
    tk.Checkbutton(main, text='Always on Screen', variable=screen_var).pack(anchor='w')
    # Logs Tab
    filter_var = BooleanVar(); search_var = StringVar()
    search_e = tk.Entry(logs, textvariable=search_var); search_e.pack(fill='x')
    tree = ttk.Treeview(logs, columns=('Date','Time','Target','Detected','Changed','Manual'), show='headings')
    for c in tree['columns']:
        tree.heading(c, text=c, command=lambda col=c: sort_table(col, False))
        tree.column(c, width=100)
    tree.pack(expand=1, fill='both')
    def sort_table(col, rev):
        data = [(tree.set(k,col),k) for k in tree.get_children('')]
        data.sort(reverse=rev)
        for idx, (_,k) in enumerate(data): tree.move(k,'',idx)
    def refresh_logs():
        tree.delete(*tree.get_children())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                for row in csv.reader(f,delimiter='|'):
                    if len(row)==6 and (not filter_var.get() or row[4]=='Yes') and search_var.get().lower() in '|'.join(row).lower():
                        tree.insert('', 'end', values=row)
    def export_logs():
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if path:
            with open(path,'w',newline='') as f:
                w = csv.writer(f); w.writerow(['Date','Time','Target','Detected','Changed','Manual'])
                for iid in tree.get_children(): w.writerow(tree.item(iid)['values'])
    tk.Checkbutton(logs,text='Only show changed',variable=filter_var,command=refresh_logs).pack(anchor='w')
    tk.Button(logs,text='Export to CSV',command=export_logs).pack(anchor='e')
    search_var.trace_add('write',lambda *a:refresh_logs()); refresh_logs()
    # Update Tab
    status_lbl = tk.Label(update_tab,text='Checking version...'); status_lbl.pack(pady=10)
    upd_btn = tk.Button(update_tab,text='Update Now',state='disabled',command=lambda:perform_update(status_lbl)); upd_btn.pack()
    def check_for_update():
        try:
            local = open(VERSION_PATH).read().strip()
            remote = requests.get(REMOTE_VERSION_URL).text.strip()
            if remote>local: status_lbl.config(text=f'New version {remote}'); upd_btn.config(state='normal')
            else: status_lbl.config(text='Up to date')
        except: status_lbl.config(text='Error'); log_error('Update failed')
    def perform_update(lbl):
        webbrowser.open('https://github.com/GoblinRules/ippy-tray-app'); lbl.config(text='Manual update needed')
    check_for_update()
    # Purge
    pf = tk.Frame(logs); pf.pack(pady=5)
    tk.Label(pf,text='Purge logs older than:').pack(side='left')
    for m in (1,2,3): tk.Button(pf,text=f'{m}m',command=lambda m=m:(purge_logs(m),refresh_logs())).pack(side='left')
    def purge_logs(months):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30*months)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f: rows=list(csv.reader(f,delimiter='|'))
            with open(LOG_FILE,'w',newline='') as f: csv.writer(f,delimiter='|').writerows([r for r in rows if len(r)==6 and datetime.datetime.strptime(r[0],'%d/%m/%Y')>=cutoff])
    # Save & Close
    def save_and_close():
        config.set('Settings','target_ip',ip_e.get().strip())
        config.set('Settings','check_interval',str(max(1,min(45,int(iv_e.get().strip() or '1')))))
        config.set('Settings','notify_on_change','yes' if notify_var.get() else 'no')
        config.set('Settings','enable_logging','yes' if log_var.get() else 'no')
        config.set('Settings','always_on_screen','yes' if screen_var.get() else 'no')
        save_config(); load_config(); gui_update_icon(); monitor_event.set()
        if always_on_screen != screen_var.get(): gui_toggle_overlay()
        on_close()
    tk.Button(win,text='Save & Close',command=save_and_close).pack(pady=5)

# -----------------------
# Main Entrypoint
# -----------------------
if __name__ == '__main__':
    root = tk.Tk(); root.withdraw()
    load_config()
    if first_run: gui_show_settings()
    if always_on_screen: gui_toggle_overlay()
    threading.Thread(target=create_tray,daemon=True).start()
    threading.Thread(target=monitor_ip,daemon=True).start()
    process_gui_queue(); root.mainloop()
