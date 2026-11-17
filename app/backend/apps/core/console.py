"""Consola serverului — partea din fiecare bază (Etapa 14).

Baza ține evidența a ceea ce se întâmplă în ea, iar platforma (launcher.py → platform_console.py) o citește prin adresa
internă `/api/__console/` (doar cu jetonul primit de la platformă la pornire; platforma nu trimite această adresă mai
departe din browser):
- **sesiunile**: fiecare intrare (login) primește un `sid` în jetoane; se vede cine, de unde, cu ce, ultima acțiune;
  sesiunea închisă din consolă nu mai e primită (nici la reîmprospătarea jetonului);
- **cererile în lucru** acum (utilizatorul, ce face, de cât timp) și, la PostgreSQL, interogările și blocările;
- **cererile lente** (peste prag, implicit 3 s): cine, ce, cât, câte interogări — în `SlowRequest`;
- **consumul** pe zi și utilizator (cereri, timp de server, timp în baza de date) — strâns în memorie și scris în
  `UsageDay` la fiecare jumătate de minut;
- **blocarea intrării** (lucrări de întreținere): fișierul `console.json` din directorul bazei, scris de platformă;
  cât e blocată, intră doar administratorii, ceilalți primesc mesajul.
"""
import contextvars
import hmac
import json
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.models import F, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from config.instance import INSTANCE_DIR

INTERNAL_PATH = "/api/__console/"
SETTINGS_FILE = "console.json"
DEFAULT_SLOW_MS = 3000
ONLINE_MINUTES = 30
SEEN_EVERY = 60  # secunde între două scrieri ale „ultimei acțiuni” pe aceeași sesiune
CLOSED_TTL = 20  # secunde cât se ține minte răspunsul „sesiunea e închisă?”
KEEP_SLOW_DAYS = 30

_lock = threading.Lock()
_ctx = contextvars.ContextVar("crm_console_request", default=None)
_active: dict = {}  # cererile în lucru: id → {...}
_usage: dict = {}  # (zi, utilizator) → [user_id, cereri, ms, ms bd, interogări, lente]
_seen: dict = {}  # sid → momentul ultimei scrieri
_closed: dict = {}  # sid → (închisă?, verificat la)
_tasks: dict = {}  # sarcinile de fundal în lucru: nume → pornită la
_task_errors: dict = {}  # nume → (la, mesaj)
_settings = {"checked": 0.0, "mtime": None, "data": {}}
_media = {"checked": 0.0, "size": None}


# --- setările scrise de platformă (blocarea intrării, pragul cererilor lente) ---

def settings_path() -> Path:
    return INSTANCE_DIR / SETTINGS_FILE


def read_settings() -> dict:
    now = time.monotonic()
    if now - _settings["checked"] < 2:
        return _settings["data"]
    _settings["checked"] = now
    path = settings_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _settings.update(mtime=None, data={})
        return {}
    if mtime != _settings["mtime"]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        _settings.update(mtime=mtime, data=data if isinstance(data, dict) else {})
    return _settings["data"]


def blocked() -> dict | None:
    data = read_settings()
    return data if data.get("blocked") else None


def block_message() -> str:
    data = blocked() or {}
    return data.get("message") or "Baza este închisă temporar pentru lucrări de întreținere. Încercați mai târziu."


def slow_ms() -> int:
    try:
        return max(int(read_settings().get("slow_ms") or DEFAULT_SLOW_MS), 100)
    except (TypeError, ValueError):
        return DEFAULT_SLOW_MS


# --- sesiunile ---

def new_sid() -> str:
    return uuid.uuid4().hex


def session_id(token, user) -> str:
    """Jetoanele de dinainte de consolă n-au `sid`: toate ale utilizatorului țin de o sesiune „veche”."""
    return str(token.get("sid") or f"legacy-{user.pk}")


def device(user_agent: str) -> str:
    ua = user_agent or ""
    kind = "Telefon" if re.search(r"Mobile|Android|iPhone|iPad", ua) else "Calculator"
    for name, pattern in (("Edge", r"Edg/"), ("Opera", r"OPR/"), ("Yandex", r"YaBrowser"), ("Chrome", r"Chrome/"),
                          ("Firefox", r"Firefox/"), ("Safari", r"Safari/")):
        if re.search(pattern, ua):
            return f"{kind} · {name}"
    return kind


def open_session(sid, user, request):
    from apps.core.audit import client_ip

    from .models import UserSession

    ua = request.META.get("HTTP_USER_AGENT", "")[:300]
    UserSession.objects.update_or_create(sid=sid, defaults={
        "user": user, "ip": client_ip(request)[:64], "user_agent": ua, "device": device(ua), "last_seen": timezone.now(),
        "last_path": "login"})
    _seen[sid] = time.monotonic()


def is_closed(sid: str) -> bool:
    from .models import UserSession

    now = time.monotonic()
    cached = _closed.get(sid)
    if cached and now - cached[1] < CLOSED_TTL:
        return cached[0]
    closed = UserSession.objects.filter(sid=sid, closed_at__isnull=False).exists()
    _closed[sid] = (closed, now)
    return closed


def close_session(sid: str, reason: str = "Închisă din consola serverului") -> bool:
    from .models import UserSession

    done = UserSession.objects.filter(sid=sid, closed_at__isnull=True).update(closed_at=timezone.now(),
                                                                              closed_reason=reason[:200])
    _closed[sid] = (True, time.monotonic())
    return bool(done)


def note_auth(user, token):
    """Din autentificarea JWT: cine face cererea curentă și din ce sesiune."""
    ctx = _ctx.get()
    if ctx is not None:
        ctx.update(user_id=user.pk, username=user.get_username(), name=str(user.get_full_name() or user.get_username()),
                   sid=session_id(token, user))


def current_sid() -> str:
    """Sesiunea cererii curente (după autentificare); gol în afara unei cereri."""
    ctx = _ctx.get()
    return str((ctx or {}).get("sid") or "")


def _touch_session(ctx):
    from .models import UserSession

    sid = ctx.get("sid")
    if not sid:
        return
    now = time.monotonic()
    if now - _seen.get(sid, 0) < SEEN_EVERY:
        return
    _seen[sid] = now
    fields = {"last_seen": timezone.now(), "last_path": f"{ctx['method']} {ctx['path']}"[:200], "ip": ctx["ip"][:64]}
    if not UserSession.objects.filter(sid=sid).update(**fields):
        ua = ctx["ua"][:300]
        UserSession.objects.get_or_create(sid=sid, defaults={**fields, "user_id": ctx["user_id"], "user_agent": ua,
                                                             "device": device(ua)})


# --- cererile: în lucru, lente, consumul ---

class ConsoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith("/api/") or path.startswith(INTERNAL_PATH):
            return self.get_response(request)
        from apps.core.audit import client_ip

        rid = uuid.uuid4().hex
        ctx = {"id": rid, "method": request.method, "path": path[:300], "started": time.time(), "ip": client_ip(request),
               "ua": request.META.get("HTTP_USER_AGENT", ""), "user_id": None, "username": "", "name": "", "sid": "",
               "queries": 0, "db": 0.0}
        token = _ctx.set(ctx)
        with _lock:
            _active[rid] = ctx

        def count(execute, sql, params, many, context):
            started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                ctx["queries"] += 1
                ctx["db"] += time.perf_counter() - started

        status = 500
        try:
            with connection.execute_wrapper(count):
                response = self.get_response(request)
            status = response.status_code
            return response
        finally:
            with _lock:
                _active.pop(rid, None)
            _ctx.reset(token)
            try:
                _record(ctx, status)
            except Exception:  # noqa: BLE001 — evidența nu strică niciodată cererea
                pass


def _record(ctx, status):
    from .models import SlowRequest

    duration = int((time.time() - ctx["started"]) * 1000)
    db_ms = int(ctx["db"] * 1000)
    is_slow = duration >= slow_ms()
    key = (timezone.localdate(), ctx["username"])
    with _lock:
        row = _usage.setdefault(key, [ctx["user_id"], 0, 0, 0, 0, 0])
        row[1] += 1
        row[2] += duration
        row[3] += db_ms
        row[4] += ctx["queries"]
        row[5] += int(is_slow)
    if is_slow:
        SlowRequest.objects.create(user_id=ctx["user_id"], username=ctx["username"], method=ctx["method"][:8],
                                   path=ctx["path"], status=status, duration_ms=duration, db_ms=db_ms,
                                   queries=ctx["queries"])
    _touch_session(ctx)


def flush_usage():
    """Consumul strâns în memorie → `UsageDay` (adunat la rândul zilei și al utilizatorului)."""
    from .models import UsageDay

    with _lock:
        pending = dict(_usage)
        _usage.clear()
    for (day, username), (user_id, requests, total, db_ms, queries, slow) in pending.items():
        obj, _ = UsageDay.objects.get_or_create(date=day, username=username, defaults={"user_id": user_id})
        UsageDay.objects.filter(pk=obj.pk).update(requests=F("requests") + requests, total_ms=F("total_ms") + total,
                                                  db_ms=F("db_ms") + db_ms, queries=F("queries") + queries,
                                                  slow=F("slow") + slow)


def run_flusher():
    """Firul de fundal al serverului: scrie consumul și curăță cererile lente vechi."""
    from django.db import close_old_connections

    from .models import SlowRequest

    last_prune = 0.0
    while True:
        time.sleep(30)
        close_old_connections()
        try:
            flush_usage()
            if time.monotonic() - last_prune > 3600:
                SlowRequest.objects.filter(at__lt=timezone.now() - timedelta(days=KEEP_SLOW_DAYS)).delete()
                last_prune = time.monotonic()
        except Exception as exc:  # noqa: BLE001
            print(f"Consola: consumul nu s-a scris: {exc}", flush=True)


# --- sarcinile de fundal ---

@contextmanager
def task(name: str):
    """Marchează o sarcină de fundal ca „în lucru” (pentru consolă); eroarea ei se ține minte, apoi merge mai departe."""
    _tasks[name] = time.time()
    try:
        yield
        _task_errors.pop(name, None)
    except Exception as exc:
        _task_errors[name] = (timezone.now().isoformat(), str(exc)[:300])
        raise
    finally:
        _tasks.pop(name, None)


# --- raportul pentru platformă ---

def _db_size():
    vendor = connection.vendor
    try:
        with connection.cursor() as cur:
            if vendor == "postgresql":
                cur.execute("SELECT pg_database_size(current_database())")
                return cur.fetchone()[0]
            if vendor == "mysql":
                cur.execute("SELECT SUM(data_length + index_length) FROM information_schema.tables "
                            "WHERE table_schema = DATABASE()")
                return int(cur.fetchone()[0] or 0)
        if vendor == "sqlite":
            name = Path(str(settings.DATABASES["default"]["NAME"]))
            return sum(p.stat().st_size for p in (name, Path(f"{name}-wal")) if p.exists())
    except Exception:  # noqa: BLE001
        return None
    return None


def _media_size():
    now = time.monotonic()
    if _media["size"] is not None and now - _media["checked"] < 600:
        return _media["size"]
    root = Path(settings.MEDIA_ROOT)
    size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0
    _media.update(checked=now, size=size)
    return size


def _pg_activity():
    if connection.vendor != "postgresql":
        return None
    with connection.cursor() as cur:
        cur.execute(
            "SELECT pid, usename, client_addr::text, state, wait_event_type, wait_event, "
            "EXTRACT(EPOCH FROM now() - query_start)::int, left(query, 400), pg_blocking_pids(pid) "
            "FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() "
            "AND state IS NOT NULL AND state <> 'idle' ORDER BY query_start")
        rows = cur.fetchall()
    return [{"pid": r[0], "db_user": r[1], "client": r[2], "state": r[3], "wait": ":".join(filter(None, r[4:6])),
             "seconds": r[6], "query": r[7], "blocked_by": list(r[8] or [])} for r in rows]


def _backup_info():
    from apps.core.models import SystemSetting
    from apps.setup import backup

    try:
        last = next(iter(backup.list_backups()), None)
    except OSError:
        last = None
    stored = SystemSetting.read(backup.KEY, {}) or {}
    return {"last": last, "daily": backup.config().get("daily"), "error": stored.get("last_error"),
            "error_at": stored.get("last_error_at")}


def state() -> dict:
    from .models import SlowRequest, UsageDay, UserSession

    flush_usage()
    now = timezone.now()
    today = timezone.localdate()
    with _lock:
        active = [{"user": a["name"] or a["username"] or "—", "method": a["method"], "path": a["path"], "ip": a["ip"],
                   "seconds": round(time.time() - a["started"], 1), "queries": a["queries"]} for a in _active.values()]
    sessions = [{"sid": s.sid, "user": str(s.user.get_full_name() or s.user.username), "username": s.user.username,
                 "ip": s.ip, "device": s.device, "user_agent": s.user_agent, "created_at": s.created_at.isoformat(),
                 "last_seen": s.last_seen.isoformat(), "last_path": s.last_path}
                for s in UserSession.objects.filter(closed_at__isnull=True,
                                                    last_seen__gte=now - timedelta(minutes=ONLINE_MINUTES))
                .select_related("user")[:300]]
    slow = [{"at": r.at.isoformat(), "user": r.username or "—", "method": r.method, "path": r.path, "status": r.status,
             "ms": r.duration_ms, "db_ms": r.db_ms, "queries": r.queries} for r in SlowRequest.objects.all()[:100]]

    def usage(qs):
        return [{"user": r["username"] or "—", "requests": r["r"], "ms": r["t"], "db_ms": r["d"], "queries": r["q"],
                 "slow": r["s"]}
                for r in qs.values("username").annotate(r=Sum("requests"), t=Sum("total_ms"), d=Sum("db_ms"),
                                                         q=Sum("queries"), s=Sum("slow")).order_by("-t")[:50]]

    return {
        "version": settings.APP_VERSION, "vendor": connection.vendor, "db_size": _db_size(), "media_size": _media_size(),
        "backup": _backup_info(), "settings": read_settings(), "slow_ms": slow_ms(),
        "tasks": [{"name": n, "seconds": int(time.time() - t)} for n, t in list(_tasks.items())],
        "task_errors": [{"name": n, "at": at, "error": e} for n, (at, e) in list(_task_errors.items())],
        "threads": sorted(t.name for t in threading.enumerate() if t.daemon and not t.name.startswith(("waitress", "Thread"))),
        "sessions": sessions, "active": active, "slow": slow, "pg": _pg_activity(),
        "usage_today": usage(UsageDay.objects.filter(date=today)),
        "usage_week": usage(UsageDay.objects.filter(date__gt=today - timedelta(days=7))),
    }


def cancel_query(pid: int) -> bool:
    if connection.vendor != "postgresql":
        raise ValueError("Oprirea interogării e doar la PostgreSQL.")
    with connection.cursor() as cur:
        cur.execute("SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE pid = %s AND datname = current_database()",
                    [int(pid)])
        row = cur.fetchone()
    return bool(row and row[0])


def _authorized(request) -> bool:
    expected = os.environ.get("CRM_CONSOLE_TOKEN", "")
    given = request.headers.get("X-Console-Token", "")
    return bool(expected) and hmac.compare_digest(expected, given)


@csrf_exempt
def internal(request):
    """Adresa internă pentru platformă: GET raportul, POST {"action": "close_session" | "close_user" | "cancel_query"}."""
    if not _authorized(request):
        return JsonResponse({"detail": "Interzis."}, status=403)
    if request.method == "GET":
        return JsonResponse(state())
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        data = {}
    act = data.get("action")
    try:
        if act == "close_session":
            return JsonResponse({"ok": close_session(str(data.get("sid", "")))})
        if act == "close_user":
            from .models import UserSession

            sids = list(UserSession.objects.filter(user__username=data.get("username", ""), closed_at__isnull=True)
                        .values_list("sid", flat=True))
            for sid in sids:
                close_session(sid)
            return JsonResponse({"ok": True, "closed": len(sids)})
        if act == "cancel_query":
            return JsonResponse({"ok": cancel_query(data.get("pid", 0))})
    except (ValueError, TypeError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"detail": "Acțiune necunoscută."}, status=400)
