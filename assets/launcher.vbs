Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Tools\TrayApp"
WshShell.Run "pythonw.exe main.py", 0, False
