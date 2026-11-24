"""Capturile pentru instrucțiunea transportului (RO), din copia de probă."""
import json, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://app:8000"
OUT = "/shots"


def call(path, body=None, method=None, tok=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    return json.loads(urllib.request.urlopen(req).read() or b"null")


tok = call("/api/auth/login/", {"username": "admin", "password": "Parola-Sigura-2026"})
A = tok["access"]
call("/api/auth/me/", {"language": "ro"}, "PATCH", A)
files = call("/api/transport/tacho-files/?page_size=100", tok=A)
for f in (files["results"] if isinstance(files, dict) else files):  # încărcarea se arată de la zero
    call(f"/api/transport/tacho-files/{f['id']}/remove/", {}, "POST", A)
trip = call("/api/transport/trips/1/", tok=A)
info = call("/api/transport/trips/1/tacho/", tok=A)
emp_id = info["people"][0]["employee"]
from urllib.parse import quote
found = call("/api/orders/orders/?page_size=300", tok=A)
found = found["results"] if isinstance(found, dict) else found
hire = [o for o in found if "angaj" in json.dumps(o, ensure_ascii=False).lower()]
found = hire or found
order_id = found[0]["id"] if found else None
print("ordin", order_id, found[0].get("number") if found else "")
pays = call("/api/payroll/payrolls/?year=2026&month=11", tok=A)
pays = pays["results"] if isinstance(pays, dict) else pays
pay_id = pays[0]["id"]
errors, done = [], []


def mark(page, selector_or_loc):
    loc = page.locator(selector_or_loc) if isinstance(selector_or_loc, str) else selector_or_loc
    try:
        loc.first.evaluate("e => { e.style.outline = '3px solid #e5484d'; e.style.outlineOffset = '2px' }")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mark: {exc}"[:200])


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="ro-RO", device_scale_factor=1,
                        timezone_id="Europe/Chisinau")
    ctx.add_init_script(f"localStorage.setItem('crm.access', {json.dumps(A)}); localStorage.setItem('crm.refresh', {json.dumps(tok['refresh'])}); localStorage.setItem('crm.lang', 'ro');")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    def shot(name, path=None, wait=2200, act=None):
        try:
            if path:
                page.goto(BASE + path)
                page.wait_for_timeout(wait)
            if act:
                act()
                page.wait_for_timeout(1200)
            page.mouse.move(1430, 890)
            page.wait_for_timeout(300)
            page.screenshot(path=f"{OUT}/{name}.png")
            done.append(name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}"[:300])

    def tab(label):
        return lambda: page.get_by_role("tab", name=label).first.click()

    shot("01-modules", "/admin/constants", act=lambda: (tab("Module")(), page.wait_for_timeout(800),
                                                          mark(page, page.get_by_text("Modulul Transportul", exact=False))))
    shot("02-constants", "/payroll/settings/constants", act=lambda: (page.get_by_text("per_diem_day_pct", exact=True).first.scroll_into_view_if_needed(),
                                                                     page.mouse.wheel(0, 150)))
    shot("03-currencies", "/admin/currencies")
    shot("04-vehicles", "/transport/vehicles")
    shot("05-kmrates", "/transport/km-rates")
    shot("06-countries", "/transport/countries")
    shot("07-norms", None, act=lambda: page.get_by_role("button", name="Normele diurnei").first.click())
    page.keyboard.press("Escape")
    shot("08-employee", f"/employees/{emp_id}")
    shot("09-documents", f"/employees/{emp_id}?tab=documents")
    shot("10-jobs", f"/employees/{emp_id}?tab=jobs")
    shot("11-orders", "/orders")
    import re as _re
    def new_order():
        page.locator(".ant-card-extra button, .ant-card button").filter(has_text=_re.compile("nou", _re.I)).first.click()
        page.wait_for_timeout(1200)
        sel = page.locator(".ant-modal .ant-select").first
        sel.click(); page.keyboard.type("Angajare"); page.wait_for_timeout(1000)
    shot("12-order", "/orders", act=new_order)
    page.keyboard.press("Escape"); page.keyboard.press("Escape")
    shot("13-trips", "/transport/trips")
    shot("14-trip-new", "/transport/trips/new")
    shot("15-trip", "/transport/trips/1", wait=3000)
    shot("16-trip-legs", None, act=lambda: page.get_by_text("Țările parcurse").first.scroll_into_view_if_needed())
    shot("17-trip-diem", None, act=lambda: page.get_by_text("Plata pe km și diurna").first.scroll_into_view_if_needed())
    shot("18-trip-import", "/transport/trips", act=lambda: page.get_by_role("button", name="Curse din Excel").first.click())
    page.keyboard.press("Escape")
    shot("19-print", "/transport/trips/1", wait=2500, act=lambda: page.get_by_role("button", name="Tipar").first.click())
    page.keyboard.press("Escape")
    # tahograful: încărcarea fișierului de pe card
    def upload():
        page.set_input_files("input[type=file]", "/out/C_D000012345670000_20261110.ddd")
        page.wait_for_timeout(2500)
    shot("20-tacho-upload", "/transport/tachograph", act=upload)
    shot("21-tacho-days", f"/transport/tachograph?tab=days&employee={emp_id}&month=2026-11", wait=3000)
    shot("22-tacho-findings", "/transport/tachograph?tab=findings&month=2026-11", wait=3000)
    shot("23-trip-tacho", "/transport/trips/1", wait=3000, act=lambda: page.get_by_text("Tahograful în timpul cursei").first.scroll_into_view_if_needed())
    shot("24-timesheets", "/timesheets")
    shot("25-payroll", f"/payroll/{pay_id}", wait=3000)
    shot("26-payroll-line", f"/payroll/{pay_id}", wait=3000,
         act=lambda: page.locator("tr", has_text="Gheorghiță").locator(".ant-table-row-expand-icon").first.click())
    page.keyboard.press("Escape")
    shot("27-alerts", "/alerts", wait=3000)
    shot("28-help", "/transport/trips", act=lambda: page.keyboard.press("F1"))
    ctx.close()
    b.close()
print("făcute:", " ".join(done))
print("\n".join(errors[:40]) or "fără erori")
