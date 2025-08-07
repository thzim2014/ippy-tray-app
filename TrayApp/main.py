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
settings_window = None  # singleton settings window

# Runtime settings
target_ip = DEFAULT_IP
notify_on_change = True
enable_logging = True
always_on_screen = True

# -----------------------
# Config: Load & Save
# -----------------------
def load_config():
    global first_run, target_ip, notify_on_change, enable_logging, always_on_screen
    default_cfg = {
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
        config.read_dict(default_cfg)
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
        f.write(f"[{datetime.datetime.now()}] {err}\n{traceback.format_exc()}\n")

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
# Floating Overlay Window
# -----------------------
class FloatingWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{config.get('Settings','window_x',fallback='10')}+{config.get('Settings','window_y',fallback='900')}")
        self.attributes("-alpha", float(config.get('Settings','window_alpha',fallback='0.85')))
        self.configure(bg="black")
        self.label = tk.Label(self, text="...", font=("Arial",14), fg="white", bg="black")
        self.label.pack(padx=5,pady=2)
        self.make_draggable(self.label)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
    def make_draggable(self, w):
        w.bind("<ButtonPress-1>", self.start)
        w.bind("<B1-Motion>", self.move)
    def start(self,e): self._x, self._y = e.x, e.y
    def move(self,e):
        x, y = self.winfo_x()+e.x-self._x, self.winfo_y()+e.y-self._y
        self.geometry(f"+{x}+{y}")
        config['Settings']['window_x'],config['Settings']['window_y']=str(x),str(y)
        config['Settings']['window_alpha']=str(self.attributes("-alpha"))
        save_config()
    def update_label(self, ip, correct):
        self.label.config(text=ip)
        bg = 'green' if correct else 'red'
        fg = 'black' if correct else 'white'
        self.configure(bg=bg); self.label.config(bg=bg,fg=fg)
        self.attributes("-alpha", 1.0 if not correct else float(config.get('Settings','window_alpha',fallback='0.85')))

# -----------------------
# GUI Queue Dispatcher
# -----------------------
def process_gui_queue():
    while not gui_queue.empty():
        func,args = gui_queue.get()
        try: func(*args)
        except Exception as e: log_error(e)
    root.after(100, process_gui_queue)

# Thread-safe GUI API
def gui_show_settings(): gui_queue.put((on_settings,()))
def gui_toggle_overlay(): gui_queue.put((toggle_overlay,()))
def gui_update_label(ip): gui_queue.put((_update_label,(ip,)))
def gui_update_icon(): gui_queue.put((_update_icon,()))

def toggle_overlay():
    global float_window
    if float_window and float_window.winfo_exists():
        float_window.deiconify() if float_window.state()=='withdrawn' else float_window.withdraw()
    else:
        float_window = FloatingWindow(root)

def _update_label(ip):
    if float_window and float_window.winfo_exists():
        float_window.update_label(ip, ip==target_ip)

def _update_icon():
    if icon:
        try: icon.icon=Image.open(get_tray_icon()); icon.title=f"IP: {current_ip or 'Unknown'}"
        except Exception as e: log_error(e)

# -----------------------
# Worker Hooks
# -----------------------
def update_float_window(ip,_): gui_queue.put((gui_update_label,(ip,)))

def recheck_ip():
    global last_manual_check,current_ip
    if time.time()-last_manual_check>=2:
        last_manual_check=time.time()
        new=get_ip()
        if new:
            ch=new!=current_ip
            if ch: notify_change(current_ip,new)
            current_ip=new
            update_float_window(new,None)
            gui_update_icon(); log_ip(new,ch,True)

def monitor_ip():
    global current_ip
    while True:
        try:
            new=get_ip()
            if new:
                ch=new!=current_ip
                if ch and current_ip: notify_change(current_ip,new)
                current_ip=new; update_float_window(new,None); gui_update_icon(); log_ip(new,ch,False)
        except Exception as e: log_error(e)
        iv=max(1,min(45,int(config.get('Settings','check_interval',fallback='1'))))
        if monitor_event.wait(timeout=60/iv): monitor_event.clear()

# -----------------------
# Tray & Icon
# -----------------------
def get_tray_icon(): return ICON_GREEN_PATH if current_ip==target_ip else ICON_RED_PATH
def toggle_icon_overlay(): gui_queue.put((toggle_overlay,()))
def on_exit(icon,item):
    try:
        if float_window and float_window.winfo_exists(): float_window.destroy()
        icon.stop(); os._exit(0)
    except Exception as e: log_error(e)

def create_tray():
    global icon
    def label(): return 'Hide IP Window' if float_window and float_window.winfo_exists() and float_window.state()!='withdrawn' else 'Show IP Window'
    icon=pystray.Icon('iPPY',Image.open(get_tray_icon()),menu=pystray.Menu(
        pystray.MenuItem('Settings',lambda i,_:gui_show_settings()),
        pystray.MenuItem(label,lambda i,_:toggle_icon_overlay()),
        pystray.MenuItem('Recheck IP',lambda i,_:recheck_ip()),
        pystray.MenuItem('Exit',on_exit)
    ))
    icon.run()

# -----------------------
# Settings GUI
# -----------------------
def on_settings(icon=None,item=None):
    global settings_window
    from tkinter import BooleanVar,StringVar
    if settings_window and settings_window.winfo_exists(): settings_window.lift(); settings_window.focus_force(); return
    win=tk.Toplevel(root); settings_window=win
    win.title('iPPY Settings'); win.geometry('800x500')
    def on_close(): global settings_window; settings_window=None; win.destroy()
    win.protocol('WM_DELETE_WINDOW',on_close)
    tabs=ttk.Notebook(win)
    main=ttk.Frame(tabs); logs=ttk.Frame(tabs); upd=ttk.Frame(tabs)
    tabs.add(main,text='Main'); tabs.add(logs,text='Logs'); tabs.add(upd,text='Update')
    tabs.pack(expand=1,fill='both')
    # Main Tab
    tk.Label(main,text='IP To Monitor:').pack()
    ip_e=tk.Entry(main); ip_e.insert(0,config['Settings']['target_ip']); ip_e.pack()
    tk.Label(main,text='Checks per Minute (1-45):').pack()
    iv_e=tk.Entry(main); iv_e.insert(0,config['Settings']['check_interval']); iv_e.pack()
    nv=BooleanVar(value=config.getboolean('Settings','notify_on_change'))
    lv=BooleanVar(value=config.getboolean('Settings','enable_logging'))
    sv=BooleanVar(value=config.getboolean('Settings','always_on_screen'))
    tk.Checkbutton(main,text='Enable Notifications',variable=nv).pack(anchor='w')
    tk.Checkbutton(main,text='Enable Logging',variable=lv).pack(anchor='w')
    tk.Checkbutton(main,text='Always on Screen',variable=sv).pack(anchor='w')
    # Logs Tab
    fv=BooleanVar(); svr=StringVar()
    se=tk.Entry(logs,textvariable=svr); se.pack(fill='x')
    lt=ttk.Treeview(logs,columns=('Date','Time','Expected','Detected','Changed','Manual'),show='headings')
    for c in lt['columns']: lt.heading(c,text=c,command=lambda c=c: sort_table(c,False)); lt.column(c,width=100)
    lt.pack(expand=1,fill='both')
    def sort_table(col,rev):
        data=[(lt.set(k,col),k) for k in lt.get_children('')]; data.sort(reverse=rev)
        for idx,(_,k) in enumerate(data): lt.move(k,'',idx)
    def refresh_logs():
        lt.delete(*lt.get_children());
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                for r in csv.reader(f,delimiter='|'):
                    if len(r)==6 and (not fv.get() or r[4]=='Yes') and svr.get().lower() in '|'.join(r).lower(): lt.insert('','end',values=r)
    def export_logs():
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
        if p:
            with open(p,'w',newline='') as f:
                w=csv.writer(f); w.writerow(['Date','Time','Expected IP','Detected IP','Changed','Manual']);
                for ch in lt.get_children(): w.writerow(lt.item(ch)['values'])
    tk.Checkbutton(logs,text='Only show changed',variable=fv,command=refresh_logs).pack(anchor='w')
    tk.Button(logs,text='Export to CSV',command=export_logs).pack(anchor='e')
    svr.trace_add('write',lambda *a:refresh_logs()); refresh_logs()
    # Update Tab
    us=tk.Label(upd,text='Checking version...'); us.pack(pady=10)
    ub=tk.Button(upd,text='Update Now',state='disabled',command=lambda:perform_update(us)); ub.pack()
    def check_update():
        try:
            with open(VERSION_PATH) as f: lv=f.read().strip()
            rv=requests.get(REMOTE_VERSION_URL).text.strip()
            if rv>lv: us.config(text=f'New version {rv} available'); ub.config(state='normal')
            else: us.config(text='You are up to date.')
        except: us.config(text='Error checking version'); log_error('Update check failed')
    def perform_update(lbl): webbrowser.open('https://github.com/GoblinRules/ippy-tray-app'); lbl.config(text='Manual update required.')
    check_update()
    # Purge & Save
    pf=tk.Frame(logs); pf.pack(pady=5); tk.Label(pf,text='Purge logs older than:').pack(side='left')
    for m in (1,2,3): tk.Button(pf,text=f'{m}m',command=lambda m=m:(purge_logs(m),refresh_logs())).pack(side='left')
    def purge_logs(months):
        cutoff=datetime.datetime.now()-datetime.timedelta(days=30*months)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f: rows=list(csv.reader(f,delimiter='|'))
            with open(LOG_FILE,'w',newline='') as f: csv.writer(f,delimiter='|').writerows([r for r in rows if len(r)==6 and datetime.datetime.strptime(r[0],'%d/%m/%Y')>=cutoff])
    def save_and_close():
        config.set('Settings','target_ip',ip_e.get().strip()); config.set('Settings','check_interval',str(max(1,min(45,int(iv_e.get().strip()or'1')))))
        config.set('Settings','notify_on_change','yes' if nv.get() else 'no'); config.set('Settings','enable_logging','yes' if lv.get() else 'no')
        config.set('Settings','always_on_screen','yes' if sv.get() else 'no'); save_config(); load_config(); gui_update_icon(); monitor_event.set()
        try: toggle_overlay() if always_on_screen!=sv.get() else None
        except: pass
        on_close()
    tk.Button(win,text='Save & Close',command=save_and_close).pack(pady=5)

# -----------------------
# Main Entrypoint
# -----------------------
if __name__=='__main__':
    root=tk.Tk(); root.withdraw()
    load_config()
    if first_run: gui_queue.put((on_settings,()))
    if always_on_screen: gui_queue.put((toggle_overlay,()))
    threading.Thread(target=create_tray,daemon=True).start()
    threading.Thread(target=monitor_ip,daemon=True).start()
    process_gui_queue(); root.mainloop()
