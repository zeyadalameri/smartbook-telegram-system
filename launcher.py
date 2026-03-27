import os
import sys
import time
import socket
import ctypes
import subprocess

MUTEX_NAME = "Global\\SmartBookTelegramMonitorMutex_2026"
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

def already_running():
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not mutex:
        return False
    return ctypes.get_last_error() == 183

def wait_for_port(host="127.0.0.1", port=5000, timeout=25):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False

def run_hidden(py_file):
    return subprocess.Popen(
        [sys.executable, py_file],
        cwd=os.getcwd(),
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def main():
    if already_running():
        os.system('start "" "http://127.0.0.1:5000"')
        return

    run_hidden("dashboard.py")

    if wait_for_port("127.0.0.1", 5000, timeout=25):
        os.system('start "" "http://127.0.0.1:5000"')

    run_hidden("telegram_receiver.py")

    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
