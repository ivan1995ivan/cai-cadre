"""CRM-ul ca program de pe desktop (scurtătura „CRM” pusă de installer): fereastra proprie, fără bara de adrese.

    pythonw.exe desktop.py [--url http://server:8000/]

Deschide lista bazelor (ca lansatorul din 1C) în Microsoft Edge sau Google Chrome în modul „aplicație” — doar titlul și
pagina, ca un program obișnuit, cu profilul lui (%LOCALAPPDATA%\\CRM\\browser), separat de browserul personal. Fără Edge
și Chrome se deschide în browserul obișnuit. Adresa: --url sau variabila CRM_PORT (implicit http://localhost:8000/).
Dacă serverul încă pornește (de ex. imediat după pornirea Windows), așteaptă până la un minut.
"""
import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

CHOOSER = "__platform/"
WAIT_SECONDS = 60


def start_url(url: str = "", port: str = "") -> str:
    """Adresa paginii de pornire (lista bazelor) din adresa serverului sau din port."""
    base = url.strip() or f"http://localhost:{port or os.environ.get('CRM_PORT') or 8000}/"
    if "://" not in base:
        base = "http://" + base
    return base.rstrip("/") + "/" + CHOOSER


def _registry_app_path(exe: str):
    import winreg

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}") as key:
                path, _ = winreg.QueryValueEx(key, "")
                if path and Path(path).is_file():
                    return path
        except OSError:
            continue
    return None


def find_browser():
    """Edge (e în orice Windows) sau Chrome; None dacă lipsesc amândouă."""
    if os.name != "nt":
        return None
    env = os.environ
    candidates = {
        "msedge.exe": [rf"{env.get('ProgramFiles(x86)', '')}\Microsoft\Edge\Application\msedge.exe",
                       rf"{env.get('ProgramFiles', '')}\Microsoft\Edge\Application\msedge.exe",
                       rf"{env.get('LOCALAPPDATA', '')}\Microsoft\Edge\Application\msedge.exe"],
        "chrome.exe": [rf"{env.get('ProgramFiles', '')}\Google\Chrome\Application\chrome.exe",
                       rf"{env.get('ProgramFiles(x86)', '')}\Google\Chrome\Application\chrome.exe",
                       rf"{env.get('LOCALAPPDATA', '')}\Google\Chrome\Application\chrome.exe"],
    }
    for exe, paths in candidates.items():
        found = _registry_app_path(exe) or next((p for p in paths if Path(p).is_file()), None)
        if found:
            return found
    return None


def browser_command(browser: str, url: str, profile_dir: str) -> list:
    """Fereastra „aplicație”: fără bara de adrese, maximizată, cu profilul propriu (fără ecranul de bun venit)."""
    return [browser, f"--app={url}", f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check",
            "--start-maximized"]


def wait_for_server(url: str, seconds: int = WAIT_SECONDS) -> bool:
    parts = urlsplit(url)
    host, port = parts.hostname or "localhost", parts.port or (443 if parts.scheme == "https" else 80)
    deadline = time.time() + seconds
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            if time.time() > deadline:
                return False
            time.sleep(1)


def message(text: str, title: str = "CRM"):
    if os.name == "nt":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR
    else:
        print(text, file=sys.stderr)


def open_app(url: str) -> bool:
    browser = find_browser()
    if not browser:
        return webbrowser.open(url)
    profile = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRM" / "browser"
    profile.mkdir(parents=True, exist_ok=True)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    subprocess.Popen(browser_command(browser, url, str(profile)), creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CRM pe desktop")
    parser.add_argument("--url", default=os.environ.get("CRM_URL", ""), help="adresa serverului (http://server:8000/)")
    parser.add_argument("--port", default="", help="portul serverului local (implicit CRM_PORT sau 8000)")
    args = parser.parse_args(argv)
    url = start_url(args.url, args.port)
    if not wait_for_server(url):
        message(f"Serverul CRM nu răspunde la {url.rsplit(CHOOSER, 1)[0]}\n\n"
                "Verificați dacă sarcina „CRM Server” rulează (Task Scheduler) sau dacă adresa e corectă.")
        return 1
    open_app(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
