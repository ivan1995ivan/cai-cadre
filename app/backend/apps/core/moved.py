"""Ce s-a mutat la Administrare → Setări în 1.4.0: grupa Setări a ieșit din secțiunile meniului, iar Clasificatoarele, Timpul
de muncă și Setările salarizării (până atunci pagini cu file) s-au desfăcut în setări separate.

Datele salvate înainte — favoritele utilizatorilor, meniul principal, bifele de meniu ale rolurilor — le aduce la zi o dată
migrația users 0004. Aceleași funcții trec și prin cererile care le scriu: o filă a browserului rămasă pe programul vechi
(neîncărcată din nou după actualizare) nu mai poate salva adresele și cheile vechi."""

import re

# clasificatoarele mici (DictItem.KINDS la 1.4.0); fiecare e setarea `dict:<tip>`
DICT_KINDS = (
    "qualification", "degree", "title", "education", "education_form", "document", "family", "marital", "nationality",
    "termination", "sanction", "incentive", "employment", "military_group", "military_rank", "military_center", "checklist",
    "vaccine",
)

# funcțiile de meniu de până la 1.4.0 desfăcute în setări separate
SPLIT = {
    "dictionaries": ("occupations", "specialties", "legalBases", "orderTypes", *(f"dict:{k}" for k in DICT_KINDS)),
    "worktime": ("workSchedules", "shiftTypes", "productionCalendar", "worktimeSettings"),
    "payrollSettings": ("payrollTypes", "payrollConstants"),
}

# funcțiile de meniu de până la 1.4.0 care au devenit setări (nu mai stau în secțiunile meniului)
FORMER_FUNCTIONS = frozenset({
    "users", "roles", "constants", "currencies", "numbering", "printTemplates", "mainMenu", "localities", "banks",
    "requiredFields", *SPLIT,
})

# registrele rămase în meniu care aveau setările într-o filă: cine nu vedea registrul nu-i vedea nici setările
TAB_SETTINGS = {"leave": ("leaveSettings",), "alerts": ("alertSettings", "smtpSettings"), "taxReports": ("taxSettings",)}

# adresa veche (favoritele se țin fără parametri) → adresa și cheia de acum
MOVED_PATHS = {
    "/dictionaries": ("/settings", "settings"),
    "/dictionaries/other": ("/settings", "settings"),
    "/worktime": ("/worktime/schedules", "workSchedules"),
    "/payroll/settings": ("/payroll/settings/types", "payrollTypes"),
}
# filele Clasificatoarelor și-au păstrat adresa, dar sunt acum setări cu cheia lor
SETTING_PATHS = {
    "/dictionaries/occupations": "occupations", "/dictionaries/specialties": "specialties",
    "/dictionaries/legal": "legalBases", "/dictionaries/order-types": "orderTypes",
}

_REPORT = re.compile(r"^rep[A-Z]|^taxReports$")


def hidden_keys(keys, tabs=False):
    """Bifele de meniu ale rolului pe cheile de acum: funcția desfăcută ascunde toate setările ei. `tabs` (doar migrația):
    registrul ascuns ascunde și setările care erau fila lui — după 1.4.0 se bifează separat, deci nu la fiecare salvare."""
    out = []
    for key in keys:
        for new in SPLIT.get(key, (key,)) + (TAB_SETTINGS.get(key, ()) if tabs else ()):
            if new not in out:
                out.append(new)
    return out


def favorites(items):
    """Favoritele pe adresele și cheile de acum; două favorite ajunse pe aceeași adresă rămân una."""
    out, seen = [], set()
    for fav in items:
        path = fav["path"].rstrip("/") or "/"
        if path in MOVED_PATHS:
            path, key = MOVED_PATHS[path]
            fav = {"path": path, "key": key, "title": ""}
        elif path in SETTING_PATHS and fav.get("key") != SETTING_PATHS[path]:
            fav = {"path": path, "key": SETTING_PATHS[path], "title": ""}
        if fav["path"] not in seen:
            seen.add(fav["path"])
            out.append(fav)
    return out


def sections(items):
    """Secțiunile meniului cu grupa Setări (până la 1.4.0): funcțiile din ea trec la Rapoarte (rapoartele) sau la Registre
    (restul) din aceeași secțiune; setările ies din secțiuni (sunt toate la Administrare → Setări)."""
    out = []
    for sec in items:
        if not isinstance(sec, dict):
            out.append(sec)
            continue
        sec = dict(sec)
        groups = {g: [k for k in sec.get(g) or [] if k not in FORMER_FUNCTIONS] for g in ("items", "reports")}
        for key in sec.pop("settings", None) or []:
            if isinstance(key, str) and key not in FORMER_FUNCTIONS:
                group = groups["reports" if _REPORT.match(key) else "items"]
                if key not in group:
                    group.append(key)
        out.append({**sec, **groups})
    return out
