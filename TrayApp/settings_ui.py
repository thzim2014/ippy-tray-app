# settings_ui.py - Settings Window with Tabs for Main, Window, Logs, and Update

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import datetime
import requests
import os

def launch(config, config_path, log_path, version_file, remote_version_url, remote_main_url, icon_path):
    settings_win = tk.Tk()
    settings_win.title("iPPY Settings")
    settings_win.geometry("400x450")
    settings_win.resizable(False, False)
    try:
        settings_win.iconbitmap(icon_path)
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

    # --- Main Tab ---
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

    # --- App Window Tab ---
    tk.Label(window_tab, text="Transparency (0.2 – 1.0):").pack()
    alpha_slider = tk.Scale(window_tab, from_=0.2, to=1.0, resolution=0.01, orient="horizontal")
    alpha_slider.set(float(config['Settings'].get('window_alpha', 0.85)))
    alpha_slider.pack(fill="x")

    # --- Logs Tab ---
    def filter_logs():
        keyword = change_only_var.get()
        selected_date = log_date.get_date().strftime('%Y-%m-%d')
        output_box.delete("1.0", tk.END)

        if not os.path.exists(log_path):
            output_box.insert(tk.END, "No logs found.")
            return

        with open(log_path, "r") as f:
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
    log_date.set_date(datetime.date.today())
    log_date.pack(pady=5)
    tk.Button(logs_tab, text="Load Logs", command=filter_logs).pack()
    output_box = tk.Text(logs_tab, height=10)
    output_box.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Updates Tab ---
    def check_updates():
        if not os.path.exists(version_file):
            local_version = "0.0.0"
        else:
            with open(version_file) as vf:
                local_version = vf.read().strip()

        try:
            r = requests.get(remote_version_url, timeout=5)
            remote_version = r.text.strip()
        except:
            messagebox.showerror("Error", "Could not reach update server.")
            return

        if remote_version != local_version:
            if messagebox.askyesno("Update Available", f"Update found: {remote_version}\nDownload and apply?"):
                try:
                    new_code = requests.get(remote_main_url, timeout=10).text
                    with open(os.path.join(os.path.dirname(config_path), 'main.py'), 'w') as mf:
                        mf.write(new_code)
                    with open(version_file, 'w') as vf:
                        vf.write(remote_version)
                    messagebox.showinfo("Updated", "App updated. Please restart.")
                    settings_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Update failed: {e}")
        else:
            messagebox.showinfo("Up-to-date", "You are already on the latest version.")

    tk.Button(update_tab, text="Check for Updates", command=check_updates).pack(pady=20)

    # --- Save Button ---
    def save():
        config['Settings']['target_ip'] = ip_entry.get().strip()
        config['Settings']['check_interval'] = str(max(1, min(45, int(interval_entry.get().strip() or 1))))
        config['Settings']['notify_on_change'] = 'yes' if notify_var.get() else 'no'
        config['Settings']['enable_logging'] = 'yes' if log_var.get() else 'no'
        config['Settings']['always_on_screen'] = 'yes' if screen_var.get() else 'no'
        config['Settings']['window_alpha'] = str(alpha_slider.get())
        with open(config_path, 'w') as f:
            config.write(f)
        settings_win.destroy()

    tk.Button(settings_win, text="Save", command=save).pack(pady=10)
    settings_win.mainloop()
