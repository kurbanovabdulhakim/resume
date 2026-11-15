import ctypes
import time
from ctypes import wintypes
from pathlib import Path

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_void_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]

def launch_on_default_desktop(cmd: str, creation_flags: int = 0):
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = r"WinSta0\Default"
    si.dwFlags = 1
    si.wShowWindow = 1
    pi = PROCESS_INFORMATION()

    res = ctypes.windll.kernel32.CreateProcessW(
        None, cmd, None, None, False, creation_flags, None, None, ctypes.byref(si), ctypes.byref(pi)
    )
    if not res:
        err = ctypes.GetLastError()
        raise RuntimeError(f"CreateProcessW failed with error {err}")
    return pi.dwProcessId

if __name__ == "__main__":
    edge_bin = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    profile = r"C:\Users\Abdulkhakim\.gemini\hh_main_session"
    port = 51200
    cmd = f'"{edge_bin}" --remote-debugging-port={port} --user-data-dir="{profile}" --window-position=360,20 --window-size=1080,820 "https://tashkent.hh.uz/applicant/negotiations"'
    pid = launch_on_default_desktop(cmd)
    print(f"[OK] Launched Edge on Default desktop, PID={pid}")
    time.sleep(3)

    # Verify CDP endpoint
    import urllib.request, json
    try:
        tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=5).read())
        print(f"[OK] CDP responsive on port {port}. Open tabs: {len(tabs)}")
        for t in tabs:
            if t.get("type") == "page":
                print(f"   Tab: {t.get('title')} ({t.get('url')})")
    except Exception as e:
        print(f"[ERR] Failed to connect to CDP: {e}")
