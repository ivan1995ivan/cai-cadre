"""Platforma CRM: mai multe baze pe același server, ca lansatorul din 1C.

    python launcher.py [--host 0.0.0.0] [--port 8000]

Platforma ascultă pe portul obișnuit (8000) și ține lista bazelor în `bases.json` (în directorul platformei:
variabila CRM_PLATFORM_DIR, altfel CRM_INSTANCE_DIR, altfel `instance/`). Fiecare bază e o instalare separată
(propriul director cu configurația, baza de date, fișierele și copiile de rezervă) și rulează ca un server
`run.py` separat, pe un port intern (8301, 8302...), pornit odată cu platforma (ca să nu aștepte nimeni la prima
deschidere).

Scurtătura „CRM” de pe desktop (desktop.py) deschide lista bazelor (`/__platform/`), ca lansatorul din 1C: se alege baza
și se intră. Alegerea se ține într-un cookie al browserului, deci fiecare utilizator lucrează cu baza lui și la pornire
e propusă ultima bază folosită. Cine deschide direct adresa serverului, cu o singură bază intră direct; cu mai multe,
întâi alege. Platforma trimite apoi toate cererile la serverul bazei alese. Bazele se adaugă și se scot din listă doar
de pe calculatorul-server.
"""
import argparse
import html
import http.client
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, quote

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
COOKIE = "crm_base"
PREFIX = "/__platform"
# Porturile interne ale bazelor. CAI ERP (acoperișuri) folosește 8101..., CAI ERP Vânzări 8301...; CAI CADRE — de la 8701, ca
# programe să poată rula pe același server fără să-și „fure” bazele unul altuia. Alt început: CRM_BASE_PORT.
FIRST_PORT = int(os.environ.get("CRM_BASE_PORT") or 8701)
OLD_FIRST_PORT = 8101  # listele de baze făcute de versiunile 1.0–1.2 (se mută singure la pornire)
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade"}


def port_busy(port: int) -> bool:
    """Portul local răspunde deja (îl ține alt program)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


PRODUCT = "cadre"
OTHER_BASE = ("Folderul este al altui program CAI (CAI ERP / CAI ERP Vânzări, cu lista lui de baze). "
              "CAI CADRE nu-l poate deschide: ar transforma baza și celălalt program n-ar mai merge cu ea.")


def base_product(path: Path) -> str:
    """Al cui e folderul bazei: "vanzari", "other" (CAI ERP pentru acoperișuri) sau "" (nu e o bază / necunoscut).
    Bazele Vânzări au în config.json "product": "vanzari"; folderul de date al CAI ERP e %ProgramData%\\CRM."""
    config = path / "config.json"
    if not config.is_file():
        return ""
    try:
        product = json.loads(config.read_text(encoding="utf-8")).get("product", "")
    except (OSError, ValueError):
        product = ""
    if product:
        return "cadre" if product == PRODUCT else "other"
    program_data = os.environ.get("ProgramData") or os.environ.get("PROGRAMDATA")
    if program_data:
        roofing = Path(program_data) / "CRM"
        try:
            if path.resolve() == roofing.resolve() or roofing.resolve() in path.resolve().parents:
                return "other"
        except OSError:
            pass
    return ""


def platform_dir() -> Path:
    raw = os.environ.get("CRM_PLATFORM_DIR") or os.environ.get("CRM_INSTANCE_DIR") or str(PROJECT_DIR / "instance")
    path = Path(raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- Lista bazelor ---------------------------------------------------------------------------------------

class Registry:
    """bases.json: [{"id", "name", "dir", "port"}]. Prima pornire: baza existentă (directorul platformei)."""

    def __init__(self, root: Path):
        self.root = root
        self.file = root / "bases.json"
        self.lock = threading.Lock()

    def load(self) -> list:
        if not self.file.exists():
            bases = [{"id": "main", "name": "Baza principală", "dir": str(self.root), "port": FIRST_PORT}]
            self.save(bases)
            return bases
        bases = json.loads(self.file.read_text(encoding="utf-8"))
        if FIRST_PORT > OLD_FIRST_PORT and any(OLD_FIRST_PORT <= b["port"] < FIRST_PORT for b in bases):
            # porturile vechi (8101...) se ciocneau cu CAI ERP de pe același server: bazele trec pe 8301...
            used = {b["port"] for b in bases if b["port"] >= FIRST_PORT}
            for b in sorted(bases, key=lambda x: x["port"]):
                if OLD_FIRST_PORT <= b["port"] < FIRST_PORT:
                    port = FIRST_PORT + (b["port"] - OLD_FIRST_PORT)
                    while port in used:
                        port += 1
                    b["port"] = port
                    used.add(port)
            self.save(bases)
        return bases

    def save(self, bases):
        self.file.write_text(json.dumps(bases, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, base_id):
        return next((b for b in self.load() if b["id"] == base_id), None)

    def add(self, name: str, directory: str = "") -> dict:
        name = re.sub(r"\s+", " ", name or "").strip()[:80]
        if not name:
            raise ValueError("Scrieți denumirea bazei.")
        with self.lock:
            bases = self.load()
            base_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "baza"
            if any(b["id"] == base_id for b in bases):
                base_id = f"{base_id}-{uuid.uuid4().hex[:4]}"
            path = Path(directory).resolve() if directory else self.root / "bases" / base_id
            if directory and base_product(path) == "other":
                raise ValueError(OTHER_BASE)
            if any(Path(b["dir"]).resolve() == path for b in bases):
                raise ValueError("Această bază este deja în listă.")
            path.mkdir(parents=True, exist_ok=True)
            port = max([b["port"] for b in bases] + [FIRST_PORT - 1]) + 1
            while port_busy(port):  # portul ținut de alt program (de ex. CAI ERP pe același server)
                port += 1
            base = {"id": base_id, "name": name, "dir": str(path), "port": port}
            bases.append(base)
            self.save(bases)
            return base

    def rename(self, base_id, name):
        with self.lock:
            bases = self.load()
            for b in bases:
                if b["id"] == base_id and name.strip():
                    b["name"] = name.strip()[:80]
            self.save(bases)

    def remove(self, base_id):
        """Scoate baza din listă; datele ei rămân pe disc (se poate adăuga înapoi după director)."""
        with self.lock:
            bases = [b for b in self.load() if b["id"] != base_id]
            if not bases:
                raise ValueError("Ultima bază nu se scoate din listă.")
            self.save(bases)


# --- Serverele bazelor -------------------------------------------------------------------------------------

def _kill_on_close_job():
    """Windows: un „job” din care procesele bazelor ies doar odată cu platforma (și la oprirea ei forțată)."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.OpenProcess.restype = wintypes.HANDLE

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = ExtendedLimits()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        return None

    def assign(pid):
        handle = kernel32.OpenProcess(0x0001 | 0x0100, False, pid)  # PROCESS_TERMINATE | PROCESS_SET_QUOTA
        if handle:
            kernel32.AssignProcessToJobObject(job, handle)
            kernel32.CloseHandle(handle)
    return assign


def _kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


class Servers:
    """Pornește `run.py` pentru fiecare bază la prima nevoie și îl repornește dacă se oprește. Baza oprită din consola
    serverului nu se mai pornește singură până nu e pornită din consolă."""

    def __init__(self, python=sys.executable):
        self.python = python
        self.procs = {}
        self.lock = threading.Lock()
        self.assign = _kill_on_close_job()
        self.console_token = secrets.token_urlsafe(32)  # baza primește doar cererile consolei cu acest jeton
        self.stopped = set()  # bazele oprite de administrator
        self.events = []  # opririle neașteptate: {"base", "ts", "code"}

    def running(self, base) -> bool:
        proc = self.procs.get(base["id"])
        return proc is not None and proc.poll() is None

    def is_stopped(self, base) -> bool:
        return base["id"] in self.stopped

    def info(self, base) -> dict:
        proc = self.procs.get(base["id"])
        return {"running": self.running(base), "stopped": self.is_stopped(base), "pid": proc.pid if proc else None,
                "exit_code": proc.poll() if proc else None}

    def start(self, base):
        self.stopped.discard(base["id"])
        self.ensure(base)

    def stop(self, base):
        with self.lock:
            self.stopped.add(base["id"])
            proc = self.procs.pop(base["id"], None)  # oprit de administrator: nu e o „oprire neașteptată”
        if proc is not None:
            _kill_tree(proc)

    def restart(self, base):
        self.stop(base)
        self.start(base)

    def ensure(self, base):
        with self.lock:
            if self.running(base) or self.is_stopped(base):
                return
            old = self.procs.get(base["id"])
            if old is not None and old.returncode not in (0, None):
                self.events = [*self.events[-49:], {"base": base["id"], "ts": time.time(), "code": old.returncode}]
            env = {**os.environ, "CRM_INSTANCE_DIR": base["dir"], "CRM_BASE_ID": base["id"],
                   "CRM_BASE_NAME": base["name"], "PYTHONIOENCODING": "utf-8", "CRM_CONSOLE_TOKEN": self.console_token,
                   "CRM_TRUSTED_PROXY": "127.0.0.1"}  # proxy-ul serverului bazei e platforma (adresa reală vine de la ea)
            log = open(Path(base["dir"]) / "server.log", "ab")  # noqa: SIM115 – rămâne deschis cât trăiește procesul
            self.procs[base["id"]] = subprocess.Popen(
                [self.python, str(BACKEND_DIR / "run.py"), "--host", "127.0.0.1", "--port", str(base["port"])],
                cwd=str(BACKEND_DIR), env=env, stdout=log, stderr=subprocess.STDOUT)
            if self.assign:
                self.assign(self.procs[base["id"]].pid)  # procesele pornite de el intră și ele în job

    @staticmethod
    def ready(base) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", base["port"]), timeout=0.5):
                return True
        except OSError:
            return False

    def stop_all(self):
        """Oprește serverele bazelor cu tot cu procesele lor (run.py pornește serverul într-un proces-copil)."""
        for proc in list(self.procs.values()):
            _kill_tree(proc)


# --- Aplicația WSGI a platformei ------------------------------------------------------------------------------

PAGE = """<!doctype html><html lang="ro" translate="no"><head><meta charset="utf-8"><meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CAI CADRE</title>
<link rel="icon" type="image/png" href="/__platform/icon.png"><style>
:root{--accent:#534ab7;--bg:#f3f4f8;--line:#d9dce6;--text:#1c2030;--muted:#6b7280}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:14px}
main{max-width:760px;margin:40px auto;padding:0 16px} header{display:flex;align-items:center;gap:12px;margin-bottom:14px}
header img{width:36px;height:36px;border-radius:8px} header h1{font-size:20px;margin:0} header small{display:block;color:var(--muted);font-weight:400;font-size:13px}
.win{display:grid;grid-template-columns:1fr 200px;gap:14px} @media (max-width:560px){.win{grid-template-columns:1fr}}
.label{font-size:12px;color:var(--muted);margin:0 0 4px 2px}
ul.list{list-style:none;margin:0;padding:4px;background:#fff;border:1px solid var(--line);border-radius:8px;min-height:260px;max-height:60vh;overflow:auto;outline:none}
ul.list:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(83,74,183,.15)}
li.base{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:6px;cursor:default;user-select:none}
li.base:hover{background:#f1f0fa} li.base.sel{background:var(--accent);color:#fff} li.base.sel small{color:#e4e2f6}
li.base .ico{width:22px;height:22px;flex:none;border-radius:5px;background:var(--accent) url(/__platform/icon.png) center/cover}
li.base b{font-size:15px;font-weight:600} li.base small{display:block;color:var(--muted);font-weight:400;font-size:12px;margin-top:2px}
.buttons{display:flex;flex-direction:column;gap:8px;padding-top:20px} .buttons .gap{height:10px}
button,a.btn{display:block;width:100%;text-align:center;padding:9px 12px;font-size:14px;border-radius:7px;border:1px solid var(--line);background:#fff;color:var(--text);cursor:pointer;text-decoration:none}
button:hover,a.btn:hover{border-color:#b9b5e0;background:#faf9ff} button.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
button.primary:hover{background:#463d9f} button:disabled{opacity:.5;cursor:default}
.err{color:#c0392b;margin:10px 2px} .hint{color:var(--muted);font-size:12px;margin:10px 2px}
.modal{position:fixed;inset:0;background:rgba(20,22,40,.45);display:flex;align-items:center;justify-content:center;padding:16px;z-index:9}
.modal[hidden]{display:none} .box{background:#fff;border-radius:10px;padding:18px 20px;width:560px;max-width:100%;box-shadow:0 10px 40px rgba(0,0,0,.25)}
.box h2{font-size:17px;margin:0 0 12px} .box label{display:block;margin:8px 0 4px;font-size:13px} .box label.radio{display:flex;gap:8px;align-items:flex-start;margin:6px 0}
.box label.radio input{margin-top:3px} .box input[type=text]{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:7px;font-size:14px}
.box input[type=text]:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(83,74,183,.15)}
.path{display:flex;gap:6px;margin-top:8px} .path input{flex:1} .path button{width:auto;padding:6px 10px}
ul.dirs{list-style:none;margin:6px 0 0;padding:4px;border:1px solid var(--line);border-radius:7px;height:200px;overflow:auto;background:#fafbfe}
ul.dirs li{padding:5px 8px;border-radius:5px;cursor:default;user-select:none;display:flex;gap:8px;align-items:center}
ul.dirs li:hover{background:#f1f0fa} ul.dirs li.sel{background:var(--accent);color:#fff} ul.dirs li .ok{margin-left:auto;font-size:12px;color:#1a9a5a}
ul.dirs li.sel .ok{color:#d9f5e4} ul.dirs li.empty{color:var(--muted);cursor:default}
.actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px} .actions button{width:auto;min-width:110px}
.box .err{margin:8px 0 0}
</style></head><body><main>
<header><img src="/__platform/icon.png" alt=""><h1>CAI CADRE<small>Alegeți baza cu care lucrați</small></h1></header>
__ERROR__<div class="win"><div><p class="label">Baze</p><ul class="list" id="list" tabindex="0" role="listbox" aria-label="Baze">__BASES__</ul></div>
<div class="buttons"><button class="primary" id="open" type="button">Deschide</button><div class="gap"></div>__ADMIN__
<a class="btn" href="/__platform/console">Consola serverului</a></div></div>
<p class="hint">Dublu clic sau Enter deschide baza; alegerea se ține în acest browser.</p>
<script>
(function(){var list=document.getElementById('list'),items=[].slice.call(list.querySelectorAll('li.base'));
function sel(){return list.querySelector('li.sel')}
function select(li){items.forEach(function(x){x.classList.remove('sel')});if(li){li.classList.add('sel');li.scrollIntoView({block:'nearest'})}}
function open(){var li=sel();if(li)location.href='/__platform/open/'+encodeURIComponent(li.dataset.id)}
items.forEach(function(li){li.addEventListener('click',function(){select(li)});li.addEventListener('dblclick',open)});
list.addEventListener('keydown',function(e){var i=items.indexOf(sel());
 if(e.key==='ArrowDown'){select(items[Math.min(i+1,items.length-1)]);e.preventDefault()}
 else if(e.key==='ArrowUp'){select(items[Math.max(i-1,0)]);e.preventDefault()}
 else if(e.key==='Enter'){open();e.preventDefault()}});
document.getElementById('open').addEventListener('click',open);
window.crmPost=function(data){var f=document.createElement('form');f.method='post';f.action='/__platform/';
 Object.keys(data).forEach(function(k){var i=document.createElement('input');i.type='hidden';i.name=k;i.value=data[k];f.appendChild(i)});
 document.body.appendChild(f);f.submit()};
window.crmSelected=sel;if(!sel()&&items[0])select(items[0]);list.focus();})();
</script>__ADMIN_SCRIPT__</main></body></html>"""

ADMIN_BUTTONS = ('<button type="button" id="add">Adaugă…</button><button type="button" id="rename">Redenumește…</button>'
                 '<button type="button" id="remove">Scoate</button>')
ADMIN_SCRIPT = """
<div class="modal" id="dlg-add" hidden><div class="box"><h2>Adăugare bază</h2>
<label for="add-name">Denumirea</label><input type="text" id="add-name" placeholder="de ex. Firma 2" maxlength="80">
<label class="radio"><input type="radio" name="add-kind" value="new" checked><span><b>Bază nouă (goală)</b><br>
<small class="hint" id="add-where" style="margin:0"></small><br><small class="hint" style="margin:0">La prima deschidere pornește asistentul de instalare (tipul bazei de date, firma, administratorul).</small></span></label>
<label class="radio"><input type="radio" name="add-kind" value="existing"><span><b>Bază existentă de pe server</b><br>
<small class="hint" style="margin:0">Alegeți folderul ei (cel cu config.json): de ex. o bază mutată de pe alt calculator sau scoasă mai demult din listă.</small></span></label>
<div id="add-browse" hidden><div class="path"><button type="button" id="dir-up" title="Folderul de deasupra">↑</button>
<input type="text" id="add-dir" placeholder="Folderul bazei (de ex. D:\\CRM\\Firma2)"><button type="button" id="dir-go">Deschide</button></div>
<ul class="dirs" id="dir-list"></ul><p class="hint" style="margin:6px 0 0">Clic alege folderul, dublu clic intră în el. ✓ bază CRM = folderul are config.json.</p></div>
<p class="err" id="add-err" hidden></p>
<div class="actions"><button type="button" class="primary" id="add-ok">Adaugă</button><button type="button" data-close="dlg-add">Renunță</button></div></div></div>
<div class="modal" id="dlg-rename" hidden><div class="box"><h2>Redenumire</h2>
<label for="rename-name">Denumirea nouă</label><input type="text" id="rename-name" maxlength="80">
<div class="actions"><button type="button" class="primary" id="rename-ok">Salvează</button><button type="button" data-close="dlg-rename">Renunță</button></div></div></div>
<div class="modal" id="dlg-remove" hidden><div class="box"><h2>Scoaterea din listă</h2><p id="remove-text"></p>
<p class="hint">Datele bazei rămân pe disc; se poate adăuga înapoi ca bază existentă, după folderul ei.</p>
<div class="actions"><button type="button" class="primary" id="remove-ok">Scoate</button><button type="button" data-close="dlg-remove">Renunță</button></div></div></div>
<script>
(function(){var $=function(id){return document.getElementById(id)};
function cur(){var li=window.crmSelected();return li?{id:li.dataset.id,name:li.dataset.name}:null}
function show(id){$(id).hidden=false;var f=$(id).querySelector('input[type=text]');if(f){f.focus();f.select()}}
function hide(id){$(id).hidden=true}
[].forEach.call(document.querySelectorAll('[data-close]'),function(b){b.addEventListener('click',function(){hide(b.dataset.close)})});
[].forEach.call(document.querySelectorAll('.modal'),function(m){m.addEventListener('keydown',function(e){if(e.key==='Escape')hide(m.id)})});
// --- răsfoirea folderelor de pe server ---
var dirs={path:'',parent:'',sel:''};
function kind(){return document.querySelector('input[name=add-kind]:checked').value}
function load(path){fetch('/__platform/dirs?path='+encodeURIComponent(path||'')).then(function(r){return r.json()}).then(function(d){
 if(d.error){err(d.error);return}
 dirs.path=d.path;dirs.parent=d.parent;dirs.sel='';$('add-dir').value=d.path;if(d.default)$('add-where').textContent='Se creează în '+d.default;
 var ul=$('dir-list');ul.innerHTML='';
 if(!d.dirs.length){var e=document.createElement('li');e.className='empty';e.textContent='(fără subfoldere)';ul.appendChild(e)}
 d.dirs.forEach(function(x){var li=document.createElement('li');li.dataset.path=x.path;
  li.innerHTML='<span>📁</span><span></span>'+(x.is_base?'<span class="ok">✓ bază CAI CADRE</span>':x.other?'<span class="err">alt program CAI — nu se poate</span>':'');li.children[1].textContent=x.name;
  li.addEventListener('click',function(){[].forEach.call(ul.children,function(c){c.classList.remove('sel')});li.classList.add('sel');dirs.sel=x.path;$('add-dir').value=x.path});
  li.addEventListener('dblclick',function(){load(x.path)});ul.appendChild(li)})})
 .catch(function(){err('Serverul nu răspunde.')})}
function err(t){$('add-err').textContent=t;$('add-err').hidden=!t}
[].forEach.call(document.querySelectorAll('input[name=add-kind]'),function(r){r.addEventListener('change',function(){$('add-browse').hidden=kind()!=='existing';err('');if(kind()==='existing'&&!dirs.path)load('')})});
$('dir-up').addEventListener('click',function(){load(dirs.parent||'')});
$('dir-go').addEventListener('click',function(){load($('add-dir').value.trim())});
$('add-dir').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();load($('add-dir').value.trim())}});
// --- butoanele ---
$('add').addEventListener('click',function(){$('add-name').value='';err('');load('');show('dlg-add')});
$('add-ok').addEventListener('click',function(){var name=$('add-name').value.trim();if(!name){err('Scrieți denumirea bazei.');$('add-name').focus();return}
 var dir='';if(kind()==='existing'){dir=$('add-dir').value.trim();if(!dir){err('Alegeți folderul bazei.');return}}
 window.crmPost({action:'add',name:name,dir:dir})});
$('add-name').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();$('add-ok').click()}});
$('rename').addEventListener('click',function(){var b=cur();if(!b)return;$('rename-name').value=b.name;show('dlg-rename')});
$('rename-ok').addEventListener('click',function(){var b=cur(),name=$('rename-name').value.trim();if(b&&name&&name!==b.name)window.crmPost({action:'rename',id:b.id,name:name});else hide('dlg-rename')});
$('rename-name').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();$('rename-ok').click()}});
$('remove').addEventListener('click',function(){var b=cur();if(!b)return;$('remove-text').textContent='Scoateți baza „'+b.name+'” din listă?';show('dlg-remove');$('remove-ok').focus()});
$('remove-ok').addEventListener('click',function(){var b=cur();if(b)window.crmPost({action:'remove',id:b.id})});})();
</script>"""


class Platform:
    def __init__(self, registry: Registry, servers: Servers, wait=60):
        import platform_console

        self.registry = registry
        self.servers = servers
        self.wait = wait
        self.console = platform_console.Console(registry, servers, registry.root)

    # utilitare
    @staticmethod
    def _cookie(environ):
        jar = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        return jar[COOKIE].value if COOKIE in jar else None

    @staticmethod
    def _local(environ) -> bool:
        """Cererea făcută chiar de pe server (consola fără parolă). Venită printr-un proxy (X-Forwarded-For) — niciodată
        locală: cu proxy-ul de încredere (config.proxy) adresa e luată din antet și ar putea fi scrisă „127.0.0.1”."""
        return environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1", "localhost") and not environ.get("HTTP_X_FORWARDED_FOR")

    @staticmethod
    def _redirect(start_response, location, cookie=None):
        headers = [("Location", location), ("Cache-Control", "no-store")]
        if cookie is not None:
            headers.append(("Set-Cookie", f"{COOKIE}={quote(cookie)}; Path=/; Max-Age=31536000; SameSite=Lax"))
        start_response("302 Found", headers)
        return [b""]

    @staticmethod
    def _json(start_response, data, status="200 OK"):
        body = json.dumps(data, ensure_ascii=False).encode()
        start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        if path == PREFIX or path.startswith(PREFIX + "/"):
            sub = path[len(PREFIX):] or "/"
            if sub == "/console" or sub.startswith("/console/"):
                return self.console_view(environ, start_response, sub[len("/console"):] or "/")
            return self.platform(environ, start_response, sub)
        if path.startswith("/api/__console"):  # adresa internă a bazei: doar pentru consolă, nu din browser
            return self._json(start_response, {"detail": "Nu există."}, "404 Not Found")
        bases = self.registry.load()
        base = self.registry.get(self._cookie(environ) or "")
        if base is None:
            if len(bases) == 1:
                base = bases[0]
            else:
                return self._redirect(start_response, f"{PREFIX}/")
        return self.forward(environ, start_response, base)

    # pagina de alegere și administrarea listei
    def platform(self, environ, start_response, sub):
        if sub == "/icon.png":
            return self.icon(start_response)
        if sub == "/dirs":
            if not self._local(environ):
                return self._json(start_response, {"error": "Doar de pe calculatorul-server."}, "403 Forbidden")
            raw = (parse_qs(environ.get("QUERY_STRING", "")).get("path") or [""])[0]
            return self._json(start_response, self.folders(raw))
        if sub == "/current":
            base = self.registry.get(self._cookie(environ) or "") or (self.registry.load()[0]
                                                                       if len(self.registry.load()) == 1 else None)
            return self._json(start_response, {"base": base and {"id": base["id"], "name": base["name"]},
                                                "count": len(self.registry.load())})
        m = re.fullmatch(r"/open/([\w-]+)", sub)
        if m:
            base = self.registry.get(m.group(1))
            if base is None:
                return self._redirect(start_response, f"{PREFIX}/")
            return self._redirect(start_response, "/", cookie=base["id"])
        error = ""
        if environ.get("REQUEST_METHOD") == "POST":
            if not self._local(environ):
                error = "Bazele se adaugă și se scot doar de pe calculatorul-server."
            else:
                size = int(environ.get("CONTENT_LENGTH") or 0)
                form = {k: v[0] for k, v in parse_qs(environ["wsgi.input"].read(size).decode("utf-8")).items()}
                try:
                    if form.get("action") == "add":
                        base = self.registry.add(form.get("name", ""), form.get("dir", ""))
                        return self._redirect(start_response, f"{PREFIX}/open/{base['id']}")
                    if form.get("action") == "remove":
                        self.registry.remove(form.get("id", ""))
                    if form.get("action") == "rename":
                        self.registry.rename(form.get("id", ""), form.get("name", ""))
                    return self._redirect(start_response, f"{PREFIX}/")
                except ValueError as exc:
                    error = str(exc)
        return self.page(environ, start_response, error)

    def page(self, environ, start_response, error=""):
        current = self._cookie(environ)
        local = self._local(environ)
        rows = []
        for b in self.registry.load():
            state = "pornită" if self.servers.running(b) else "oprită"
            detail = f"{html.escape(b['dir'])} · {state}" if local else state
            rows.append(f'<li class="base{" sel" if b["id"] == current else ""}" data-id="{html.escape(b["id"])}" '
                        f'data-name="{html.escape(b["name"])}" role="option"><span class="ico"></span>'
                        f'<span><b>{html.escape(b["name"])}</b><small>{detail}</small></span></li>')
        body = (PAGE.replace("__ERROR__", f'<p class="err">{html.escape(error)}</p>' if error else "")
                .replace("__BASES__", "".join(rows))
                .replace("__ADMIN__", ADMIN_BUTTONS if local else "")
                .replace("__ADMIN_SCRIPT__", ADMIN_SCRIPT if local else "")).encode()
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store"),
                                  ("Content-Length", str(len(body)))])
        return [body]

    def folders(self, raw: str) -> dict:
        """Folderele de pe server pentru dialogul „Adăugare bază” (bază existentă): discurile sau subfolderele
        folderului cerut; ✓ la cele care au o bază CRM (config.json)."""
        raw = raw.strip().strip('"')
        if not raw:
            if os.name == "nt":
                roots = [f"{c}:\\" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{c}:\\").is_dir()]
            else:
                roots = ["/"]
            bases_dir = self.registry.root / "bases"
            dirs = [{"name": str(bases_dir), "path": str(bases_dir), "is_base": False}] if bases_dir.is_dir() else []
            dirs += [{"name": r, "path": r, "is_base": False} for r in roots]
            return {"path": "", "parent": "", "dirs": dirs, "is_base": False, "default": str(bases_dir)}
        path = Path(raw)
        if not path.is_dir():
            return {"error": f"Folderul nu există: {raw}"}
        path = path.resolve()
        dirs = []
        try:
            for child in sorted(path.iterdir(), key=lambda c: c.name.lower()):
                if child.name.startswith((".", "$")) or not child.is_dir():
                    continue
                try:
                    is_base = (child / "config.json").is_file()
                    other = is_base and base_product(child) == "other"
                except OSError:
                    is_base = False
                dirs.append({"name": child.name, "path": str(child), "is_base": is_base and not other, "other": other})
        except OSError as exc:
            return {"error": f"Folderul nu se poate citi: {exc.strerror or exc}"}
        parent = "" if path.parent == path else str(path.parent)
        return {"path": str(path), "parent": parent, "dirs": dirs, "is_base": (path / "config.json").is_file(),
                "default": str(self.registry.root / "bases")}

    def icon(self, start_response):
        """Sigla (din interfața compilată) pentru pagina de alegere și pentru fereastra programului."""
        for path in (PROJECT_DIR / "frontend" / "dist" / "icons" / "icon-192.png",
                     PROJECT_DIR / "frontend" / "public" / "icons" / "icon-192.png"):
            if path.is_file():
                body = path.read_bytes()
                start_response("200 OK", [("Content-Type", "image/png"), ("Cache-Control", "public, max-age=86400"),
                                          ("Content-Length", str(len(body)))])
                return [body]
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b""]

    # consola serverului
    def console_view(self, environ, start_response, sub):
        import platform_console

        local = self._local(environ)
        jar = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        token = jar[platform_console.COOKIE].value if platform_console.COOKIE in jar else None
        if sub == "/":
            body = platform_console.page()
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store"),
                                      ("Content-Length", str(len(body)))])
            return [body]
        method = environ.get("REQUEST_METHOD", "GET")
        data = {}
        if method == "POST":
            # cererile care schimbă ceva vin doar din pagina consolei (antetul propriu nu se poate pune dintr-un alt site)
            if environ.get("HTTP_X_REQUESTED_WITH") != "crm-console":
                return self._json(start_response, {"detail": "Cerere respinsă."}, "403 Forbidden")
            size = int(environ.get("CONTENT_LENGTH") or 0)
            try:
                data = json.loads(environ["wsgi.input"].read(size).decode("utf-8") or "{}") if size else {}
            except ValueError:
                data = {}
        auth = self.console.auth
        if sub == "/api/login" and method == "POST":
            try:
                new_token = auth.login(str(data.get("password", "")))
            except platform_console.ConsoleError as exc:
                return self._json(start_response, {"detail": str(exc)}, "401 Unauthorized")
            body = json.dumps({"ok": True}).encode()
            cookie = (f"{platform_console.COOKIE}={new_token}; Path={PREFIX}/console; HttpOnly; SameSite=Strict; "
                      f"Max-Age={platform_console.SESSION_HOURS * 3600}")
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Set-Cookie", cookie),
                                      ("Content-Length", str(len(body)))])
            return [body]
        if sub == "/api/logout" and method == "POST":
            auth.logout(token)
            return self._json(start_response, {"ok": True})
        if not (local or auth.valid(token)):
            return self._json(start_response, {"detail": "Intrați cu parola consolei.", "login": True,
                                               "has_password": auth.has_password()}, "401 Unauthorized")
        try:
            if sub == "/api/state" and method == "GET":
                return self._json(start_response, {**self.console.state(), "local": local,
                                                   "has_password": auth.has_password()})
            if sub == "/api/action" and method == "POST":
                return self._json(start_response, self.console.action(data, local))
        except platform_console.ConsoleError as exc:
            return self._json(start_response, {"detail": str(exc)}, "400 Bad Request")
        return self._json(start_response, {"detail": "Nu există."}, "404 Not Found")

    # trimiterea cererilor la serverul bazei
    def forward(self, environ, start_response, base):
        if getattr(self.servers, "is_stopped", lambda b: False)(base):
            body = ("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=30>"
                    f"<p style='font-family:sans-serif'>Baza „{html.escape(base['name'])}” este oprită de "
                    "administratorul serverului. Încercați mai târziu.</p>").encode()
            start_response("503 Service Unavailable", [("Content-Type", "text/html; charset=utf-8"),
                                                       ("Retry-After", "30")])
            return [body]
        self.servers.ensure(base)
        deadline = time.time() + self.wait
        while not self.servers.ready(base):
            if time.time() > deadline:
                body = ("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=3>"
                        f"<p style='font-family:sans-serif'>Se pornește baza „{html.escape(base['name'])}”…</p>").encode()
                start_response("503 Service Unavailable", [("Content-Type", "text/html; charset=utf-8"),
                                                           ("Retry-After", "3")])
                return [body]
            time.sleep(0.3)
        method = environ.get("REQUEST_METHOD", "GET")
        target = quote(environ.get("PATH_INFO", "/"), safe="/%:@&=+$,;~!*'()")
        if environ.get("QUERY_STRING"):
            target += "?" + environ["QUERY_STRING"]
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                name = key[5:].replace("_", "-").title()
                if name.lower() not in HOP_BY_HOP:
                    headers[name] = value
        for key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            if environ.get(key):
                headers[key.replace("_", "-").title()] = environ[key]
        client_ip = environ.get("REMOTE_ADDR", "")
        headers["X-Forwarded-For"] = ", ".join(filter(None, [environ.get("HTTP_X_FORWARDED_FOR"), client_ip]))
        headers["X-Forwarded-Proto"] = environ.get("wsgi.url_scheme", "http")
        size = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(size) if size else None
        conn = http.client.HTTPConnection("127.0.0.1", base["port"], timeout=600)
        conn.request(method, target, body=body, headers=headers)
        resp = conn.getresponse()
        out = [(k, v) for k, v in resp.getheaders() if k.lower() not in HOP_BY_HOP]
        start_response(f"{resp.status} {resp.reason}", out)

        def stream():
            try:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                conn.close()
        return stream()


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Platforma CRM (mai multe baze)")
    parser.add_argument("--host", default=os.environ.get("CRM_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CRM_PORT", 8000)))
    args = parser.parse_args()
    from waitress import serve

    registry, servers = Registry(platform_dir()), Servers()
    bases = registry.load()
    for base in bases:
        servers.ensure(base)  # toate bazele pornesc odată cu platforma: nimeni nu așteaptă la prima deschidere
    print(f"Platforma CRM: http://{'localhost' if args.host == '0.0.0.0' else args.host}:{args.port} "
          f"({len(bases)} baze, lista: {registry.file})", flush=True)
    import atexit
    import signal

    atexit.register(servers.stop_all)
    for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
        if sig is not None:
            signal.signal(sig, lambda *_: sys.exit(0))
    from config.proxy import waitress_options

    serve(Platform(registry, servers), host=args.host, port=args.port, threads=16, **waitress_options())


if __name__ == "__main__":
    main()
