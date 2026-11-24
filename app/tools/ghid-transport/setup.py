"""Datele de transport pentru instrucțiune (copia de probă): modulul, cursul EUR, vehiculele, tarifele, actele șoferilor, cursa
internațională aprobată, o cursă în țară (ciornă), fișierul .ddd al șoferului (pus în /out pentru încărcare), calculul lunii."""
from datetime import date, datetime, timedelta, timezone as tz
from decimal import Decimal as D

from apps.core.models import Company, Currency, ExchangeRate, NumberSeries
from apps.org.models import DictItem, Subdivision
from apps.payroll import engine
from apps.payroll.models import Payroll
from apps.staff.models import EmployeeDocument, Employment
from apps.transport import services
from apps.transport.models import Country, KmRate, Trip, TripLeg, Vehicle
from tests.test_tachograph import card_file, change

UTC = tz.utc
c = Company.get(); c.transport_enabled = True; c.save()
eur, _ = Currency.objects.get_or_create(code="EUR", defaults={"name_ro": "Euro", "name_ru": "Евро", "symbol": "€"})
d = date(2026, 10, 20)
while d <= date(2026, 11, 24):
    ExchangeRate.objects.update_or_create(currency=eur, date=d, defaults={"rate": D("19.6241") + D(d.day) / 1000})
    d += timedelta(days=1)
trn = Subdivision.objects.get(code="TRN")
v1 = Vehicle.objects.create(plate="CAB 101", kind="tractor", brand="Volvo", model="FH 500", category="CE", fuel_norm=D("29.5"), subdivision=trn)
Vehicle.objects.create(plate="CAB 102", kind="tractor", brand="DAF", model="XF 480", category="CE", fuel_norm=D("28.9"), subdivision=trn)
Vehicle.objects.create(plate="TRL 501", kind="trailer", brand="Schmitz", model="Cargobull S.KO", tachograph=False, subdivision=trn)
Vehicle.objects.create(plate="CAB 201", kind="van", brand="Ford", model="Transit", category="B", subdivision=trn)
KmRate.objects.create(date_from=date(2026, 1, 1), rate=D("1.20"), document="Regulamentul de salarizare, anexa 3")
KmRate.objects.create(date_from=date(2026, 1, 1), trip_kind="goods", scope="international", vehicle_kind="tractor", rate=D("1.50"),
                      document="Regulamentul de salarizare, anexa 3")
drivers = list(Employment.objects.filter(occupation__name_ro="Conducător de autocamion", kind="main").select_related("employee")
               .order_by("employee__last_name"))
j1, j2 = drivers[0], drivers[1]
docs = {k: DictItem.objects.get(kind="document", code=k) for k in ("cpc", "medical_cert", "tachograph_card", "adr")}
e1 = j1.employee
EmployeeDocument.objects.create(employee=e1, doc_type=docs["cpc"], number="CPC-0451", issued_by="ANTA", issue_date=date(2022, 3, 1),
                                expiry_date=date(2027, 3, 1))
EmployeeDocument.objects.create(employee=e1, doc_type=docs["medical_cert"], number="086/2025", issued_by="IMSP CS nr. 1",
                                issue_date=date(2025, 1, 10), expiry_date=date(2027, 1, 10))
EmployeeDocument.objects.create(employee=e1, doc_type=docs["tachograph_card"], number="D000012345670000", issued_by="ASP",
                                issue_date=date(2024, 5, 2), expiry_date=date(2029, 5, 1))
EmployeeDocument.objects.create(employee=j2.employee, doc_type=docs["medical_cert"], number="112/2025", issued_by="IMSP CS nr. 1",
                                issue_date=date(2025, 2, 1), expiry_date=date(2026, 12, 5))
loc = lambda *a: datetime(*a, tzinfo=tz(timedelta(hours=2)))  # ora Moldovei în noiembrie
t = Trip.objects.create(number=NumberSeries.next_number("trip"), driver=j1, vehicle=v1, trailer=Vehicle.objects.get(plate="TRL 501"),
                        kind="goods", scope="international", departure=loc(2026, 11, 3, 6), arrival=loc(2026, 11, 8, 20),
                        route="Chișinău – Leușeni – Budapesta – Viena – München și înapoi", odometer_out=412300, odometer_in=416140)
countries = {x.code: x for x in Country.objects.all()}
legs = [("RO", (2026, 11, 3, 10, 30), (2026, 11, 4, 8), False, False), ("HU", (2026, 11, 4, 8), (2026, 11, 4, 18), False, False),
        ("AT", (2026, 11, 4, 18), (2026, 11, 5, 9), False, False), ("DE", (2026, 11, 5, 9), (2026, 11, 6, 16), True, True),
        ("AT", (2026, 11, 6, 16), (2026, 11, 7, 8), False, False), ("HU", (2026, 11, 7, 8), (2026, 11, 7, 16), False, False),
        ("RO", (2026, 11, 7, 16), (2026, 11, 8, 17), False, False)]
for n, (code, a, b, ld, ul) in enumerate(legs, start=1):
    TripLeg.objects.create(trip=t, country=countries[code], entered=loc(*a), left=loc(*b), loading=ld, unloading=ul, sort=n * 10)
services.compute(t, strict=True)
t.status = "approved"; t.approved_at = datetime(2026, 11, 9, 9, tzinfo=UTC); t.save()
t2 = Trip.objects.create(number=NumberSeries.next_number("trip"), driver=j2, vehicle=Vehicle.objects.get(plate="CAB 102"), kind="goods",
                         scope="domestic", departure=loc(2026, 11, 12, 7), arrival=loc(2026, 11, 12, 19), route="Chișinău – Bălți – Chișinău",
                         odometer_out=233100, odometer_in=233420)
services.compute(t2)

# fișierul de pe cardul șoferului 1 (generația 2 v2): zilele 02–10.11, trecerile frontierei, descărcare și încărcare în DE
def day(drive1, brk, drive2, start=240, work=30):
    m = start
    out = [change(0, "R"), change(m, "W")]; m += 20
    out.append(change(m, "D")); m += drive1
    out.append(change(m, "R")); m += brk
    out.append(change(m, "D")); m += drive2
    out.append(change(m, "W")); m += work
    out.append(change(m, "R"))
    return out
rest = [change(0, "R")]
days = [(date(2026, 11, 2), rest, 0), (date(2026, 11, 3), day(240, 45, 230), 760), (date(2026, 11, 4), day(250, 45, 240, start=180), 800),
        (date(2026, 11, 5), day(300, 60, 120, start=200), 520), (date(2026, 11, 6), day(240, 45, 200, start=300, work=90), 640),
        (date(2026, 11, 7), day(255, 45, 240, start=180), 790), (date(2026, 11, 8), day(240, 45, 210, start=200), 330),
        (date(2026, 11, 9), rest, 0), (date(2026, 11, 10), rest, 0)]
u = lambda *a: datetime(*a, tzinfo=UTC)
borders = [(u(2026, 11, 3, 8, 30), 0x23, 0x29, 412520), (u(2026, 11, 4, 6), 0x29, 0x18, 413050), (u(2026, 11, 4, 16), 0x18, 0x01, 413450),
           (u(2026, 11, 5, 7), 0x01, 0x0D, 413780), (u(2026, 11, 6, 14), 0x0D, 0x01, 414300), (u(2026, 11, 7, 6), 0x01, 0x18, 414620),
           (u(2026, 11, 7, 14), 0x18, 0x29, 415050), (u(2026, 11, 8, 15), 0x29, 0x23, 415930)]
loads = [(u(2026, 11, 5, 12), 2, 413900), (u(2026, 11, 6, 9), 1, 414100)]
vehicles = [(u(2026, 11, 3, 4), u(2026, 11, 8, 18), "CAB 101", 412300, 416140)]
places = [(u(2026, 11, 3, 4), 0, 0x23, 412300), (u(2026, 11, 8, 18), 1, 0x23, 416140)]
import unicodedata
plain = lambda x: "".join(ch for ch in unicodedata.normalize("NFKD", x) if not unicodedata.combining(ch)).upper()
data = card_file(number="D0000123456700", surname=plain(e1.last_name), first=plain(e1.first_name), birth=e1.birth_date or date(1985, 6, 15), gen=2,
                 days=days, vehicles=vehicles, places=places, borders=borders, loads=loads, downloaded=u(2026, 11, 10, 8))
open("/out/C_D000012345670000_20261110.ddd", "wb").write(data)

pay = Payroll.objects.create(year=2026, month=11, subdivision=trn, number=NumberSeries.next_number("payroll"))
engine.calculate(pay)
print("ok", e1.full_name(), j2.employee.full_name(), t.number, t2.number, pay.number)
