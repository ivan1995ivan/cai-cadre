"""Video-ul instrucțiunii transportului (RO): navigarea prin program, cu subtitrări pe ecran. Rulează în copia de probă."""
import json
import shutil
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://app:8000"


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
emp_id = call("/api/transport/trips/1/tacho/", tok=A)["people"][0]["employee"]
pays = call("/api/payroll/payrolls/?year=2026&month=11", tok=A)
pay_id = (pays["results"] if isinstance(pays, dict) else pays)[0]["id"]

CAPTION = """(t) => {
  let d = document.getElementById('__cap');
  if (!d) {
    d = document.createElement('div'); d.id = '__cap';
    d.style.cssText = 'position:fixed;left:50%;bottom:44px;transform:translateX(-50%);max-width:1100px;z-index:100000;' +
      'background:rgba(20,32,56,.92);color:#fff;font:600 21px/1.4 Segoe UI,Arial,sans-serif;padding:14px 22px;border-radius:10px;' +
      'box-shadow:0 6px 24px rgba(0,0,0,.35);text-align:center;pointer-events:none';
    document.body.appendChild(d);
  }
  d.innerHTML = t;
}"""
TITLE = """(h) => {
  let d = document.getElementById('__title');
  if (!d) { d = document.createElement('div'); d.id = '__title'; document.body.appendChild(d); }
  d.style.cssText = 'position:fixed;inset:0;z-index:100001;background:linear-gradient(135deg,#14325c,#1f5fa8);color:#fff;display:flex;' +
    'flex-direction:column;align-items:center;justify-content:center;font-family:Segoe UI,Arial,sans-serif;text-align:center';
  d.innerHTML = h;
}"""
MARK = "(e) => { e.style.outline = '4px solid #ff4d4f'; e.style.outlineOffset = '3px'; e.style.borderRadius = '4px' }"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 720}, locale="ro-RO", timezone_id="Europe/Chisinau",
                        record_video_dir="/video/raw", record_video_size={"width": 1280, "height": 720})
    ctx.add_init_script(f"localStorage.setItem('crm.access', {json.dumps(A)}); localStorage.setItem('crm.refresh', {json.dumps(tok['refresh'])}); localStorage.setItem('crm.lang', 'ro');")
    page = ctx.new_page()

    def go(path, wait=1800):
        page.goto(BASE + path)
        page.wait_for_timeout(wait)
        page.mouse.move(1270, 710)

    def cap(text, ms=5200):
        page.evaluate(CAPTION, text)
        page.wait_for_timeout(ms)

    def mark(locator):
        try:
            locator.first.scroll_into_view_if_needed()
            locator.first.evaluate(MARK)
        except Exception:  # noqa: BLE001
            pass

    def title(html, ms=5000):
        page.evaluate(TITLE, html)
        page.wait_for_timeout(ms)
        page.evaluate("() => document.getElementById('__title')?.remove()")

    go("/", 1500)
    title("<div style='font-size:22px;opacity:.85'>CAI CADRE</div><div style='font-size:44px;font-weight:700;margin:14px 0'>"
          "Transportul: de la angajat la salariu</div><div style='font-size:22px;opacity:.9'>actele șoferului · vehiculele · constantele · "
          "cursa și diurna · tahograful · calculul salariului</div>", 5500)

    # 1. pregătirea
    go("/admin/constants")
    page.get_by_role("tab", name="Module").first.click()
    page.wait_for_timeout(800)
    mark(page.get_by_text("Modulul Transportul", exact=False))
    cap("<b>Pasul 1. Modulul.</b> Administrare → Setări → Constante → Module: porniți „Modulul Transportul” și salvați. "
        "Apar meniurile Curse, Tahograful și setările transportului.", 6500)
    go("/payroll/settings/constants")
    mark(page.get_by_text("per_diem_pct", exact=True))
    cap("<b>Constantele diurnei</b> (Setări → Constantele salarizării): procentul plătit de întreprindere (100 %), minimul de 70 %, "
        "20 % / 40 % la aflările scurte, 20 % cu masa asigurată, diurna în țară.", 7000)
    cap("O constantă nouă = un rând nou cu „În vigoare din”. Calculul ia valoarea valabilă la data cursei / sfârșitul lunii.", 4500)
    go("/admin/currencies")
    cap("<b>Cursul BNM.</b> Setări → Valutele: „Preluarea cursului BNM”. Diurna în lei se socotește la cursul din ziua dinaintea plecării.", 6000)
    go("/transport/vehicles")
    cap("<b>Vehiculele</b>: numărul, felul (cap tractor, semiremorcă, autobuz…), categoria permisului, tahograful, coloana.", 5500)
    go("/transport/km-rates")
    cap("<b>Tarifele pe km</b>, din data dată. Se ia rândul cel mai potrivit cursei: felul cursei, aria, felul vehiculului.", 5500)
    go("/transport/countries")
    cap("<b>Țările și diurnele</b>: 186 de țări cu normele pe zi din HG 10/2012 (anexa nr. 2). Norma nouă — rând nou din data ei.", 5000)
    page.get_by_role("button", name="Normele diurnei").first.click()
    page.wait_for_timeout(1500)
    cap("Istoria normelor unei țări.", 3000)
    page.keyboard.press("Escape")

    # 2. angajatul
    go(f"/employees/{emp_id}?tab=documents", 2200)
    cap("<b>Pasul 2. Șoferul.</b> În fișa angajatului, fila Acte: permisul, certificatul medical, CPC, cardul de tahograf, ADR — "
        "cu „Valabil până la”. Programul avertizează din timp când expiră.", 7000)
    go(f"/employees/{emp_id}?tab=jobs", 2200)
    cap("Raportul de muncă (din ordinul de angajare): funcția, salariul de funcție, modalitatea de remunerare.", 5000)
    go("/orders", 2200)
    cap("<b>Ordinele</b>: angajarea, transferul, concediul, eliberarea — semnate, schimbă singure raportul de muncă și salariul.", 5500)

    # 3. cursa
    go("/transport/trips", 2200)
    cap("<b>Pasul 3. Cursa.</b> Salarizare → Curse (foi de parcurs): lista lunii întoarcerii, „Cursă nouă”, importul din Excel.", 5500)
    go("/transport/trips/new", 2200)
    cap("Foaia de parcurs: șoferul (și al doilea), vehiculul, remorca, felul și aria, plecarea și întoarcerea, kilometrajul.", 6000)
    go("/transport/trips/1", 2800)
    cap("Cursa internațională: Chișinău – Budapesta – Viena – München și înapoi. Km din kilometraj: 3 840.", 4500)
    page.get_by_text("Țările parcurse").first.scroll_into_view_if_needed()
    page.mouse.wheel(0, 120)
    page.wait_for_timeout(600)
    cap("<b>Țările parcurse</b>: câte un rând pe țară, cu ora trecerii frontierei la intrare și la ieșire, încărcarea / descărcarea, masa.", 6500)
    page.get_by_text("Plata pe km și diurna").first.scroll_into_view_if_needed()
    page.wait_for_timeout(600)
    cap("La salvare se socotesc singure: <b>plata pe km</b> (3 840 km × 1,5 lei) și <b>diurna pe zile</b> — țara zilei, norma, cursul BNM, suma.", 7000)
    page.mouse.wheel(0, 400)
    page.wait_for_timeout(800)
    cap("Fiecare rând are explicația: punctul din HG 10/2012 după care s-a socotit (tranzitul, țara de destinație, 100 % pe zi).", 6000)
    cap("<b>Aprobarea</b> verifică totul (curse suprapuse, concediu, tarife, cursul) și fixează sumele. Cursa intră în salariul lunii întoarcerii.", 6000)

    # 4. tahograful
    go("/transport/tachograph", 2000)
    cap("<b>Pasul 4. Tahograful.</b> Salarizare → Tahograful → „Încarcă fișierele .ddd” — descărcările de pe cardul șoferului.", 4500)
    page.set_input_files("input[type=file]", "/out/C_D000012345670000_20261110.ddd")
    page.wait_for_timeout(2500)
    cap("Fișierul se citește și se leagă singur de șofer — după numărul cardului din dosar. Originalul se păstrează pentru control.", 6500)
    go(f"/transport/tachograph?tab=days&employee={emp_id}&month=2026-11", 3000)
    cap("<b>Zilele șoferului</b>: bara celor 24 de ore — conducere (roșu), altă muncă, odihnă; totalurile, km, țările, vehiculul.", 7000)
    cap("<b>Încălcările</b> limitelor (AETR): aici — 5 h de conducere fără pauza de 45 min. Le vede și dispecerul, și contabilul.", 6500)
    go("/transport/trips/1", 2800)
    page.get_by_text("Tahograful în timpul cursei").first.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    cap("În foaia de parcurs: timpii de pe card în timpul cursei și încălcările. Cu tahograful „smart 2” — și butonul „Țările din tahograf”.", 7000)

    # 5. salariul
    go(f"/payroll/{pay_id}", 3000)
    cap("<b>Pasul 5. Salariul.</b> Salarizare → Calculul salariului, luna întoarcerii: „Recalculează”.", 4500)
    page.locator("tr", has_text="Gheorghiță").locator(".ant-table-row-expand-icon").first.click()
    page.wait_for_timeout(1200)
    cap("Rândul șoferului: salariul de funcție + <b>KM</b> (plata pe km, impozabilă, cu CAS) + <b>DIURNA</b> (în limita normelor, neimpozabilă).", 7500)
    cap("Plata pe km intră și în comparația cu salariul minim. Diurna peste norme (procentul peste 100 %) — DIURNAEX, impozabilă.", 6000)
    go("/alerts", 2500)
    cap("<b>Alertele</b>: actele care expiră, cardul de tahograf de descărcat la 28 de zile, încălcările recente.", 5500)
    go("/transport/trips", 1500)
    page.keyboard.press("F1")
    page.wait_for_timeout(1500)
    cap("<b>F1 — Ajutor</b>: instrucțiunea ecranului, documentul Word de descărcat și acest video.", 5500)
    title("<div style='font-size:40px;font-weight:700;margin-bottom:16px'>Gata: de la angajat la salariu</div>"
          "<div style='font-size:22px;opacity:.9'>Instrucțiunea completă — în program: Ajutor (F1) → Transportul</div>", 4500)
    video = page.video
    ctx.close()
    b.close()
    shutil.copy(video.path(), "/video/transport-video.webm")
print("ok", Path("/video/transport-video.webm").stat().st_size)
