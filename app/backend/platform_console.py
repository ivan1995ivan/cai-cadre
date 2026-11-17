"""Consola serverului (Etapa 14): pagina platformei pentru administratorul serverului, cu toate bazele.

    http://<server>:8000/__platform/console

- **Accesul**: de pe calculatorul-server — direct; din rețea — cu parola consolei (se pune de pe server, din consolă,
  sau cu variabila CRM_CONSOLE_PASSWORD la prima pornire). Parola se ține ca amprentă PBKDF2 în
  `platform-console.json` din directorul platformei.
- **Bazele**: procesul (pornit / oprit, CPU și memoria cu tot cu procesele-copil, de cât timp), mărimea bazei de date
  și a fișierelor, ultima copie de rezervă, sarcinile de fundal; pornește / oprește / repornește baza.
- **Sesiunile, cererile în lucru, cererile lente, consumul** vin din raportul fiecărei baze (apps/core/console.py), cerut
  pe adresa internă cu jetonul dat bazei la pornire; închiderea sesiunii și oprirea interogării se trimit tot acolo.
- **Blocarea intrării** și pragul cererilor lente se scriu în `console.json` din directorul bazei (baza îl citește).
- **Alertele**: baza oprită neașteptat sau care nu răspunde, memoria / discul aproape pline, copia de rezervă
  nereușită sau veche, cererile blocate (în lucru de peste un minut, blocări în PostgreSQL), sarcinile de fundal căzute.
"""
import hashlib
import hmac
import http.client
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import psutil
except ImportError:  # fără psutil consola merge, doar fără CPU / memorie
    psutil = None

PASSWORD_FILE = "platform-console.json"
BASE_SETTINGS = "console.json"
COOKIE = "crm_console"
SESSION_HOURS = 12
STUCK_SECONDS = 60
MEM_ALERT, DISK_ALERT = 90, 90
REPORT_TIMEOUT = 6
INTERNAL_PATH = "/api/__console/"


class ConsoleError(ValueError):
    pass


# --- accesul ---

class ConsoleAuth:
    def __init__(self, root: Path):
        self.file = root / PASSWORD_FILE
        self.tokens: dict = {}
        self.lock = threading.Lock()
        env = os.environ.get("CRM_CONSOLE_PASSWORD", "")
        if env and not self.has_password():
            self.set_password(env)

    def _read(self) -> dict:
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def has_password(self) -> bool:
        return bool(self._read().get("hash"))

    @staticmethod
    def _hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000).hex()

    def set_password(self, password: str):
        if len(password or "") < 8:
            raise ConsoleError("Parola consolei: cel puțin 8 caractere.")
        salt = secrets.token_bytes(16)
        self.file.write_text(json.dumps({"salt": salt.hex(), "hash": self._hash(password, salt)}), encoding="utf-8")
        with self.lock:
            self.tokens.clear()  # parola nouă: intrările din rețea se fac din nou

    def check(self, password: str) -> bool:
        data = self._read()
        if not data.get("hash"):
            return False
        return hmac.compare_digest(self._hash(password or "", bytes.fromhex(data["salt"])), data["hash"])

    def login(self, password: str) -> str:
        if not self.check(password):
            time.sleep(1)  # încercările de ghicire merg încet
            raise ConsoleError("Parola consolei e greșită." if self.has_password() else
                               "Parola consolei nu e pusă. Puneți-o din consolă, de pe calculatorul-server.")
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.tokens[token] = time.time() + SESSION_HOURS * 3600
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        with self.lock:
            expires = self.tokens.get(token)
            if expires and expires < time.time():
                self.tokens.pop(token, None)
                expires = None
        return bool(expires)

    def logout(self, token: str | None):
        with self.lock:
            self.tokens.pop(token or "", None)


# --- procesele bazelor ---

class ProcessStats:
    """CPU și memoria unui proces cu tot cu copiii lui (run.py pornește serverul într-un proces-copil)."""

    def __init__(self):
        self.cache: dict = {}  # pid → psutil.Process (cpu_percent are nevoie de măsurarea anterioară)

    def _proc(self, pid):
        proc = self.cache.get(pid)
        if proc is None or not proc.is_running():
            proc = psutil.Process(pid)
            proc.cpu_percent(None)
            self.cache[pid] = proc
        return proc

    def measure(self, pid: int) -> dict:
        if psutil is None or not pid:
            return {"cpu": None, "memory": None, "started": None, "processes": None}
        try:
            root = self._proc(pid)
            procs = [root] + root.children(recursive=True)
            cpu = mem = 0.0
            for p in procs:
                try:
                    cpu += self._proc(p.pid).cpu_percent(None)
                    mem += p.memory_info().rss
                except psutil.Error:
                    pass
            return {"cpu": round(cpu / (psutil.cpu_count() or 1), 1), "memory": int(mem),
                    "started": datetime.fromtimestamp(root.create_time(), tz=timezone.utc).isoformat(),
                    "processes": len(procs)}
        except psutil.Error:
            return {"cpu": None, "memory": None, "started": None, "processes": None}


def system_info(dirs) -> dict:
    if psutil is None:
        return {"available": False}
    mem = psutil.virtual_memory()
    disks, seen = [], set()
    for d in dirs:
        try:
            anchor = Path(d).resolve().anchor or "/"
            if anchor in seen:
                continue
            seen.add(anchor)
            usage = psutil.disk_usage(anchor)
            disks.append({"path": anchor, "total": usage.total, "used": usage.used, "percent": usage.percent})
        except OSError:
            pass
    return {"available": True, "cpu": psutil.cpu_percent(None), "cpus": psutil.cpu_count(), "memory_total": mem.total,
            "memory_used": mem.total - mem.available, "memory_percent": mem.percent, "disks": disks,
            "boot": datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat()}


# --- setările bazei (blocarea intrării, pragul) ---

def base_settings_path(base) -> Path:
    return Path(base["dir"]) / BASE_SETTINGS


def read_base_settings(base) -> dict:
    try:
        data = json.loads(base_settings_path(base).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_base_settings(base, **changes) -> dict:
    data = {**read_base_settings(base), **changes}
    path = base_settings_path(base)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return data


# --- raportul bazei ---

def base_request(base, token, method="GET", payload=None, timeout=REPORT_TIMEOUT) -> dict:
    conn = http.client.HTTPConnection("127.0.0.1", base["port"], timeout=timeout)
    try:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"X-Console-Token": token, "Content-Type": "application/json"}
        conn.request(method, INTERNAL_PATH, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw or "{}")
        except ValueError:
            raise ConsoleError(f"Baza a răspuns cu eroarea {resp.status} (detaliile în server.log al bazei).") from None
        if resp.status >= 400:
            raise ConsoleError(data.get("detail") or f"Baza a răspuns {resp.status}.")
        return data
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise ConsoleError(f"Baza nu răspunde ({type(exc).__name__}).") from exc
    finally:
        conn.close()


# --- alertele ---

def _ago(iso: str | None) -> timedelta | None:
    if not iso:
        return None
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - moment


def alerts(system: dict, bases: list, events: list) -> list:
    out = []

    def add(level, base, text):
        out.append({"level": level, "base": base, "text": text})

    if system.get("available"):
        if system["memory_percent"] >= MEM_ALERT:
            add("error", "", f"Memoria serverului e aproape plină: {system['memory_percent']:.0f}%.")
        for d in system["disks"]:
            if d["percent"] >= DISK_ALERT:
                add("error", "", f"Discul {d['path']} e aproape plin: {d['percent']:.0f}%.")
    cutoff = time.time() - 24 * 3600
    for ev in events:
        if ev["ts"] >= cutoff:
            add("error", ev["name"], f"Procesul bazei s-a oprit neașteptat (codul {ev['code']}) la "
                                     f"{datetime.fromtimestamp(ev['ts']).strftime('%d.%m %H:%M')}.")
    for b in bases:
        name = b["name"]
        if b["stopped"]:
            add("warning", name, "Baza e oprită de administrator; utilizatorii nu pot intra.")
            continue
        if b["blocked"]:
            add("info", name, "Intrarea în bază e blocată (lucrări de întreținere): intră doar administratorii.")
        if not b["running"]:
            continue
        report = b.get("report") or {}
        if b.get("report_error"):
            add("error", name, b["report_error"])
            continue
        backup = report.get("backup") or {}
        if backup.get("error"):
            add("error", name, f"Copia de rezervă nu s-a făcut: {backup['error']}")
        last = (backup.get("last") or {}).get("created")
        age = _ago(last)
        if backup.get("daily") and (age is None or age > timedelta(days=2)):
            add("warning", name, "Nu există o copie de rezervă din ultimele 2 zile.")
        for t in report.get("task_errors") or []:
            add("warning", name, f"Sarcina de fundal „{t['name']}” a căzut: {t['error']}")
        stuck = [a for a in report.get("active") or [] if a["seconds"] >= STUCK_SECONDS]
        if stuck:
            add("warning", name, f"Cereri în lucru de peste un minut: {len(stuck)} (de ex. {stuck[0]['user']}: "
                                 f"{stuck[0]['method']} {stuck[0]['path']}, {stuck[0]['seconds']:.0f} s).")
        waiting = [q for q in report.get("pg") or [] if q.get("blocked_by")]
        if waiting:
            add("warning", name, f"Interogări care așteaptă blocări în PostgreSQL: {len(waiting)}.")
    return out


# --- consola ---

class Console:
    def __init__(self, registry, servers, root: Path):
        self.registry, self.servers = registry, servers
        self.auth = ConsoleAuth(root)
        self.stats = ProcessStats()

    def state(self) -> dict:
        bases_out = []
        bases = self.registry.load()
        for b in bases:
            info = self.servers.info(b) if hasattr(self.servers, "info") else {"running": self.servers.running(b)}
            settings = read_base_settings(b)
            row = {"id": b["id"], "name": b["name"], "dir": b["dir"], "port": b["port"], "running": info.get("running"),
                   "stopped": info.get("stopped", False), "exit_code": info.get("exit_code"),
                   "blocked": bool(settings.get("blocked")), "block_message": settings.get("message", ""),
                   "slow_ms": settings.get("slow_ms"), **self.stats.measure(info.get("pid"))}
            if row["running"] and self.servers.ready(b):
                try:
                    row["report"] = base_request(b, self.servers.console_token)
                except ConsoleError as exc:
                    row["report_error"] = str(exc)
            elif row["running"]:
                row["report_error"] = "Baza pornește…"
            bases_out.append(row)
        system = system_info([b["dir"] for b in bases])
        events = [{**e, "name": next((b["name"] for b in bases if b["id"] == e["base"]), e["base"])}
                  for e in getattr(self.servers, "events", [])]
        return {"now": datetime.now(timezone.utc).isoformat(), "system": system, "bases": bases_out,
                "alerts": alerts(system, bases_out, events)}

    def action(self, data: dict, local: bool) -> dict:
        act = data.get("action")
        if act == "set_password":
            if not local:
                raise ConsoleError("Parola consolei se schimbă doar de pe calculatorul-server.")
            self.auth.set_password(data.get("password", ""))
            return {"ok": True}
        base = self.registry.get(data.get("base", ""))
        if base is None:
            raise ConsoleError("Baza nu există.")
        if act == "start":
            self.servers.start(base)
        elif act == "stop":
            self.servers.stop(base)
        elif act == "restart":
            self.servers.restart(base)
        elif act == "block":
            write_base_settings(base, blocked=True, message=str(data.get("message", ""))[:300],
                                blocked_at=datetime.now(timezone.utc).isoformat())
        elif act == "unblock":
            write_base_settings(base, blocked=False, message="")
        elif act == "slow_ms":
            try:
                value = int(data.get("value"))
            except (TypeError, ValueError):
                raise ConsoleError("Pragul cererilor lente: un număr de milisecunde.") from None
            if not 200 <= value <= 600_000:
                raise ConsoleError("Pragul cererilor lente: între 200 și 600000 ms.")
            write_base_settings(base, slow_ms=value)
        elif act in ("close_session", "close_user", "cancel_query"):
            if not self.servers.running(base):
                raise ConsoleError("Baza nu e pornită.")
            return base_request(base, self.servers.console_token, "POST",
                                {k: v for k, v in data.items() if k in ("action", "sid", "username", "pid")})
        else:
            raise ConsoleError("Acțiune necunoscută.")
        return {"ok": True}


PAGE_FILE = Path(__file__).resolve().parent / "platform_console.html"


def page() -> bytes:
    return PAGE_FILE.read_bytes()
