"""Pornirea serverului CRM (producție): python run.py [--host 0.0.0.0] [--port 8000]

Serverul rulează într-un proces-copil supravegheat. Când asistentul de instalare termină
(sau după o schimbare a bazei de date), procesul-copil iese cu codul 3 și este repornit automat.
"""
import argparse
import os
import subprocess
import sys
import threading
import time

RESTART_CODE = 3


def serve(host: str, port: int, threads: int):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from waitress import serve as waitress_serve

    from config.proxy import waitress_options
    from config.wsgi import application

    start_background()
    print(f"CRM pornit: http://{host if host != '0.0.0.0' else 'localhost'}:{port}", flush=True)
    threading.Thread(target=warm_up, args=(port,), name="warm-up", daemon=True).start()
    waitress_serve(application, host=host, port=port, threads=threads, **waitress_options())


def warm_up(port: int):
    """Prima cerere după pornire dura ~2 s (Django încarcă atunci toate modulele cu vederi, DRF, șabloanele). Serverul
    își face singur primele cereri, ca primul utilizator să nu le aștepte el."""
    import http.client
    import socket

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.2)
    for path in ("/", "/api/setup/status/", "/api/public/branding/"):
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
            conn.request("GET", path, headers={"X-Forwarded-For": "127.0.0.1"})
            conn.getresponse().read()
            conn.close()
        except OSError:
            return


def start_background():
    """Lucrările de fundal ale serverului instalat: copia zilnică și sarcinile de noapte (apps.core.nightly)."""
    import threading

    from config.instance import is_installed

    if not is_installed():
        return
    threading.Thread(target=daily_backups, name="backups", daemon=True).start()
    from apps.core.console import run_flusher

    threading.Thread(target=run_flusher, name="console", daemon=True).start()


def daily_backups():
    from django.db import close_old_connections

    from apps.core.console import task
    from apps.setup import backup

    while True:
        time.sleep(600)
        close_old_connections()
        try:
            with task("Copia zilnică"):
                done = backup.run_daily_if_due()
            if done:
                print(f"Copia zilnică: {done['name']}", flush=True)
        except Exception as exc:  # noqa: BLE001 – copia nereușită nu oprește serverul
            backup.record_failure(exc)
            print(f"Copia zilnică nu s-a făcut: {exc}", flush=True)
        try:
            from apps.core import nightly

            with task("Sarcinile de noapte"):
                result = nightly.run_if_due()
            if result:
                print(f"Sarcinile de noapte: {result}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Sarcinile de noapte nu s-au făcut: {exc}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Planul managerilor nu s-a trimis: {exc}", flush=True)


def apply_update():
    """Actualizarea pregătită din Administrare → Întreținere se aplică înainte de pornirea serverului."""
    import updater
    from config.instance import INSTANCE_DIR, PROJECT_DIR

    try:
        return updater.apply_pending(PROJECT_DIR, INSTANCE_DIR, log=lambda text: print(text, flush=True))
    except updater.UpdateError as exc:
        print(f"Actualizarea nu a reușit: {exc}", flush=True)
        return None


def supervise(argv):
    while True:
        update = apply_update()
        # La fiecare pornire (și după instalare) baza se aduce la versiunea programului.
        code = subprocess.call([sys.executable, "manage.py", "crm_upgrade"])
        if code != 0 and update:
            import updater
            from config.instance import INSTANCE_DIR, PROJECT_DIR

            print("Baza nu s-a putut actualiza; se revine la versiunea anterioară. "
                  "Dacă migrațiile s-au aplicat parțial, restaurați copia de rezervă.", flush=True)
            updater.rollback(PROJECT_DIR, INSTANCE_DIR, update.get("from_version", ""))
            subprocess.call([sys.executable, "manage.py", "crm_upgrade"])
        code = subprocess.call([sys.executable, __file__, "--child", *argv])
        if code != RESTART_CODE:
            return code
        print("Repornire după schimbarea configurației...", flush=True)
        time.sleep(0.5)


def utf8_output():
    """Mesajele sunt în română/rusă: pe Windows, cu ieșirea redirecționată într-un fișier (serviciu, jurnal),
    codificarea implicită (de ex. cp1251) nu are „ă”, „ț” și procesul ar cădea la primul mesaj."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")  # și pentru procesele-copil
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    utf8_output()
    parser = argparse.ArgumentParser(description="Server CRM")
    parser.add_argument("--host", default=os.environ.get("CRM_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CRM_PORT", 8000)))
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.getcwd())
    if args.child:
        serve(args.host, args.port, args.threads)
        return 0
    passthrough = ["--host", args.host, "--port", str(args.port), "--threads", str(args.threads)]
    if os.environ.get("CRM_DEBUG") != "1":
        subprocess.call([sys.executable, "manage.py", "collectstatic", "--noinput", "-v", "0"])
    return supervise(passthrough)


if __name__ == "__main__":
    sys.exit(main())
