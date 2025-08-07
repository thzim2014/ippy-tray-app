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
gui_queue = queue.Queue()
root = None

target_ip = DEFAULT_IP
notify_on_change = True
enable_logging = True
always_on_screen = True

# -----------------------
# Config Load & Save
# -----------------------
def load_config():
    global first_run, target_ip, notify_on_change, enable_logging, always_on_screen
    defaults = {'Settings': {'target_ip': DEFAULT_IP,
                              'check_interval': '10',
                              'notify_on_change': 'yes',
                              'enable_logging': 'yes',
                              'always_on_screen': 'yes',
                              'window_alpha': '0.85',
                              'window_x': '100',
                              'window_y': '100'}}
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
# IP Utilities
# -----------------------
def get_ip():
    try:
        r = requests.get(IP_API_URL, timeout=5)
        return r.json().get('query')
    except Exception as e:
        log_error(e)
        return None

# -----------------------
# Logging
# -----------------------
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
# Floating Overlay
# -----------------------
class FloatingWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        x = int(config.get('Settings','window_x',fallback='100'))
        y = int(config.get('Settings','window_y',fallback='100'))
        self.geometry(f'+{x}+{y}')
        self.label = tk.Label(self, text='...', font=('Arial',14))
        self.label.pack(padx=5,pady=2)
        self.label.bind('<ButtonPress-1>', self._start)
        self.label.bind('<B1-Motion>', self._drag)
        self.protocol('WM_DELETE_WINDOW', self.withdraw)

    def _start(self, e):
        self._sx, self._sy = e.x, e.y

    def _drag(self, e):
        x = self.winfo_x()+e.x-self._sx
        y = self.winfo_y()+e.y-self._sy
        self.geometry(f'+{x}+{y}')
        config['Settings']['window_x'] = str(x)
        config['Settings']['window_y'] = str(y)
        save_config()

    def update_label(self, ip):
        ok = (ip == target_ip)
        self.label.config(text=ip, bg='green' if ok else 'red', fg='black' if ok else 'white')
        alpha = float(config.get('Settings','window_alpha',fallback='0.85'))
        self.attributes('-alpha', alpha if ok else 1.0)

# -----------------------
# GUI Dispatcher
# -----------------------
def process_gui_queue():
    while not gui_queue.empty():
        fn,args = gui_queue.get()
        try: fn(*args)
        except Exception as e: log_error(e)
    root.after(100, process_gui_queue)

def gui_show_settings(): gui_queue.put((on_settings,()))

def gui_toggle_overlay(): gui_queue.put((toggle_overlay,()))

def gui_update_overlay(ip): gui_queue.put((overlay_update,(ip,)))

def gui_update_icon(): gui_queue.put((update_icon,()))

# -----------------------
# Overlay Helpers
# -----------------------
def toggle_overlay():
    global float_window
    if float_window and float_window.winfo_exists():
        float_window.withdraw() if float_window.state()!='withdrawn' else float_window.deiconify()
    else:
        float_window = FloatingWindow(root)


def overlay_update(ip):
    if float_window and float_window.winfo_exists():
        float_window.update_label(ip)


def update_icon():
    if icon:
        try:
            icon.icon = Image.open(get_tray_icon())
            icon.title = f"IP: {current_ip or 'Unknown'}"
        except Exception as e:
            log_error(e)

# -----------------------
# Background Threads
# -----------------------
def recheck_ip():
    global current_ip, last_manual_check
    now = time.time()
    if now - last_manual_check < 2: return
    last_manual_check = now
    new = get_ip()
    if not new: return
    changed = (new!=current_ip)
    if changed and current_ip: notify_change(current_ip,new)
    current_ip=new
    overlay_update(new)
    gui_update_icon()
    log_ip(new,changed,True)


def monitor_ip():
    global current_ip
    while True:
        try:
            new=get_ip()
            if new:
                changed=(new!=current_ip)
                if changed and current_ip: notify_change(current_ip,new)
                current_ip=new
                overlay_update(new)
                gui_update_icon()
                log_ip(new,changed,False)
        except Exception as e:
            log_error(e)
        iv = max(1,min(45,int(config.get('Settings','check_interval',fallback='10'))))
        if monitor_event.wait(timeout=60/iv): monitor_event.clear()

# -----------------------
# Tray Icon & Menu
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
    def label(): return 'Hide IP Window' if float_window and float_window.winfo_exists() and float_window.state()!='withdrawn' else 'Show IP Window'
    icon = pystray.Icon('iPPY', Image.open(get_tray_icon()), pystray.Menu(
        pystray.MenuItem('Settings', lambda i,_: gui_show_settings()),
        pystray.MenuItem(label, lambda i,_: gui_toggle_overlay()),
        pystray.MenuItem('Recheck IP', lambda i,_: recheck_ip()),
        pystray.MenuItem('Exit', on_exit)
    ))
    icon.run()

# -----------------------
# Settings Window
# -----------------------
def on_settings(icon_obj=None,item=None):
    global settings_window
    from tkinter import BooleanVar,StringVar
    if settings_window and settings_window.winfo_exists():
        settings_window.lift(); settings_window.focus_force(); return
    win = tk.Toplevel(root); settings_window=win
    win.title('iPPY Settings'); win.geometry('800x500')
    def on_close():
        global settings_window
        settings_window=None; win.destroy()
    win.protocol('WM_DELETE_WINDOW',on_close)
    tabs=ttk.Notebook(win)
    tab_main=ttk.Frame(tabs); tab_logs=ttk.Frame(tabs); tab_upd=ttk.Frame(tabs)
    tabs.add(tab_main,text='Main'); tabs.add(tab_logs,text='Logs'); tabs.add(tab_upd,text='Update')
    tabs.pack(expand=1,fill='both')
    # Main
    tk.Label(tab_main,text='IP To Monitor:').pack()
    ip_e=tk.Entry(tab_main); ip_e.insert(0,config['Settings']['target_ip']); ip_e.pack()
    tk.Label(tab_main,text='Checks per minute (1-45):').pack()
    iv_e=tk.Entry(tab_main); iv_e.insert(0,config['Settings']['check_interval']); iv_e.pack()
    nv=BooleanVar(value=config.getboolean('Settings','notify_on_change'))
    lv=BooleanVar(value=config.getboolean('Settings','enable_logging'))
    sv=BooleanVar(value=config.getboolean('Settings','always_on_screen'))
    tk.Checkbutton(tab_main,text='Enable Notifications',variable=nv).pack(anchor='w')
    tk.Checkbutton(tab_main,text='Enable Logging',variable=lv).pack(anchor='w')
    tk.Checkbutton(tab_main,text='Always on Screen',variable=sv).pack(anchor='w')
    # Logs
    fv=BooleanVar(); svp=StringVar()
    se=tk.Entry(tab_logs,textvariable=svp); se.pack(fill='x')
    tree=ttk.Treeview(tab_logs,columns=('Date','Time','Target','Detected','Changed','Manual'),show='headings')
    for c in tree['columns']:
        tree.heading(c,text=c,command=lambda cc=c: sort_table(cc,False))
        tree.column(c,width=100)
    tree.pack(expand=1,fill='both')
    def sort_table(col,rev):
        d=[(tree.set(k,col),k) for k in tree.get_children('')]; d.sort(reverse=rev)
        for i,(_,k) in enumerate(d): tree.move(k,'',i)
    def refresh_logs():
        tree.delete(*tree.get_children())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                for r in csv.reader(f,delimiter='|'):
                    if len(r)==6 and (not fv.get() or r[4]=='Yes') and svp.get().lower() in '|'.join(r).lower():
                        tree.insert('','end',values=r)
    def export_logs():
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
        if p:
            with open(p,'w',newline='') as f:
                w=csv.writer(f); w.writerow(['Date','Time','Target','Detected','Changed','Manual'])
                for iid in tree.get_children(): w.writerow(tree.item(iid)['values'])
    tk.Checkbutton(tab_logs,text='Only show changed',variable=fv,command=refresh_logs).pack(anchor='w')
    tk.Button(tab_logs,text='Export to CSV',command=export_logs).pack(anchor='e')
    svp.trace_add('write',lambda *a:refresh_logs()); refresh_logs()
    # Update
    lbl= tk.Label(tab_upd,text='Checking version...'); lbl.pack(pady=10)
    btn= tk.Button(tab_upd,text='Update Now',state='disabled',command=lambda:perform_update(lbl)); btn.pack()
    def check_update():
        try:
            l=open(VERSION_PATH).read().strip(); r=requests.get(REMOTE_VERSION_URL).text.strip()
            if r>l: lbl.config(text=f'New version {r}'); btn.config(state='normal')
            else: lbl.config(text='Up to date')
        except: lbl.config(text='Error'); log_error('update')
    def perform_update(lb): webbrowser.open('https://github.com/GoblinRules/ippy-tray-app'); lb.config(text='Update manually')
    check_update()
    # Purge
    pf=tk.Frame(tab_logs); pf.pack(pady=5)
    tk.Label(pf,text='Purge logs older than:').pack(side='left')
    for m in (1,2,3): tk.Button(pf,text=f'{m}m',command=lambda mm=m:(purge_logs(mm),refresh_logs())).pack(side='left')
    def purge_logs(months):
        cutoff=datetime.datetime.now()-datetime.timedelta(days=30*months)
        if os.path.exists(LOG_FILE):
            rows=list(csv.reader(open(LOG_FILE),delimiter='|'))
            csv.writer(open(LOG_FILE,'w',newline=''),delimiter='|').writerows([r for r in rows if len(r)==6 and datetime.datetime.strptime(r[0],'%d/%m/%Y')>=cutoff])
    # Save & Close
    def save_and_close():
        config.set('Settings','target_ip',ip_e.get().strip())
        config.set('Settings','check_interval',str(max(1,min(45,int(iv_e.get().strip() or '1')))))
        config.set('Settings','notify_on_change','yes' if nv.get() else 'no')
        config.set('Settings','enable_logging','yes' if lv.get() else 'no')
        config.set('Settings','always_on_screen','yes' if sv.get() else 'no')
        save_config(); load_config(); gui_update_icon(); monitor_event.set()
        if always_on_screen != sv.get(): gui_toggle_overlay()
        on_close()
    tk.Button(win,text='Save & Close',command=save_and_close).pack(pady=5)

# -----------------------
# Main Entrypoint
# -----------------------
if __name__=='__main__':
    root=tk.Tk(); root.withdraw()
    load_config()
    if first_run: gui_show_settings()
    if always_on_screen: gui_toggle_overlay()
    threading.Thread(target=create_tray,daemon=True).start()
    threading.Thread(target=monitor_ip,daemon=True).start()
    process_gui_queue(); root.mainloop()
