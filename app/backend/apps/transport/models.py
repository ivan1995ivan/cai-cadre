"""Transportul (S6b, pasul a): vehiculele, tarifele pe km, țările cu normele diurnei, cursele (foaia de parcurs) cu segmentele
pe țări și diurna socotită pe zile. Cursa aprobată intră în calculul salariului lunii întoarcerii: plata pe km (KM) și diurna
(DIURNA — în limita normelor, neimpozabilă; DIURNAEX — peste norme, impozabilă).

Modul opțional: `Company.transport_enabled` (oprit implicit); drepturile `transport.*`.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Subdivision
from apps.staff.models import Employment

VEHICLE_KINDS = [
    ("tractor", "Cap tractor"), ("truck", "Camion / autocamion"), ("trailer", "Semiremorcă / remorcă"), ("bus", "Autobuz"),
    ("minibus", "Microbuz"), ("van", "Autoutilitară"), ("car", "Autoturism"), ("other", "Alta"),
]
TRIP_KINDS = [("goods", "Transport de mărfuri"), ("passengers", "Transport de pasageri")]
SCOPES = [("domestic", "În țară"), ("international", "Internațional")]


class Vehicle(models.Model):
    """Vehiculul (unitatea de transport) sau remorca: numărul de înmatriculare, felul, marca, categoria permisului cerută."""

    plate = models.CharField("Numărul de înmatriculare", max_length=16, unique=True)
    kind = models.CharField("Felul", max_length=10, choices=VEHICLE_KINDS, default="truck")
    brand = models.CharField("Marca", max_length=60, blank=True)
    model = models.CharField("Modelul", max_length=60, blank=True)
    category = models.CharField("Categoria permisului (C, CE, D…)", max_length=10, blank=True)
    tachograph = models.BooleanField("Are tahograf", default=True)
    fuel_norm = models.DecimalField("Norma de consum (l / 100 km)", max_digits=6, decimal_places=2, null=True, blank=True)
    gps_id = models.CharField("Identificatorul în sistemul GPS (obiectul / unitatea)", max_length=60, blank=True, db_index=True,
                              db_default="")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                    verbose_name="Subdiviziunea (coloana)")
    note = models.CharField("Observații", max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["plate"]
        verbose_name = "Vehicul"

    def __str__(self):
        return f"{self.plate} {self.brand} {self.model}".strip()


class KmRate(models.Model):
    """Tariful pe km pentru șofer, din data dată; gol la felul cursei / aria / felul vehiculului = oricare. La o cursă se ia
    rândul cel mai potrivit (cele mai multe potriviri exacte), în vigoare la data plecării."""

    date_from = models.DateField("În vigoare din")
    trip_kind = models.CharField("Felul cursei", max_length=10, choices=TRIP_KINDS, blank=True)
    scope = models.CharField("Aria", max_length=13, choices=SCOPES, blank=True)
    vehicle_kind = models.CharField("Felul vehiculului", max_length=10, choices=VEHICLE_KINDS, blank=True)
    rate = models.DecimalField("Tariful (lei / km)", max_digits=10, decimal_places=4)
    document = models.CharField("Temeiul (contractul colectiv, regulamentul de salarizare)", max_length=200, blank=True)

    class Meta:
        ordering = ["-date_from", "trip_kind", "scope", "vehicle_kind"]
        verbose_name = "Tariful pe km"

    def __str__(self):
        return f"{self.rate} lei/km din {self.date_from:%d.%m.%Y}"


class Country(models.Model):
    """Țara (codul ISO 3166-1 alfa-2) — pentru segmentele cursei și normele diurnei."""

    code = models.CharField("Codul (ISO 2)", max_length=2, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=80)
    name_ru = models.CharField("Denumire (RU)", max_length=80, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=80, blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "name_ro"]
        verbose_name = "Țară"

    def __str__(self):
        return f"{self.code} — {self.name_ro}"


class PerDiemNorm(models.Model):
    """Norma diurnei pe zi pentru deplasarea în țara dată (HG 10/2012), din data dată, în valuta ei."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="norms", verbose_name="Țara")
    date_from = models.DateField("În vigoare din")
    currency = models.CharField("Valuta", max_length=3, default="EUR")
    amount = models.DecimalField("Norma pe zi", max_digits=10, decimal_places=2)
    document = models.CharField("Temeiul", max_length=200, blank=True)

    class Meta:
        ordering = ["country__name_ro", "-date_from"]
        verbose_name = "Norma diurnei"
        constraints = [models.UniqueConstraint(fields=["country", "date_from"], name="uniq_per_diem_norm")]


class Trip(models.Model):
    """Cursa (foaia de parcurs): șoferul (și al doilea șofer), vehiculul, remorca, felul, aria, plecarea și întoarcerea, km,
    ruta și segmentele pe țări. Socotită la salvare, fixată la aprobare; intră în salariul lunii întoarcerii."""

    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    driver = models.ForeignKey(Employment, on_delete=models.PROTECT, related_name="trips", verbose_name="Șoferul (raportul de muncă)")
    co_driver = models.ForeignKey(Employment, on_delete=models.PROTECT, null=True, blank=True, related_name="co_trips",
                                  verbose_name="Al doilea șofer")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips", verbose_name="Vehiculul")
    trailer = models.ForeignKey(Vehicle, on_delete=models.PROTECT, null=True, blank=True, related_name="trailer_trips",
                                verbose_name="Remorca")
    kind = models.CharField("Felul", max_length=10, choices=TRIP_KINDS, default="goods")
    scope = models.CharField("Aria", max_length=13, choices=SCOPES, default="international")
    departure = models.DateTimeField("Plecarea")
    arrival = models.DateTimeField("Întoarcerea")
    route = models.CharField("Ruta", max_length=300, blank=True)
    odometer_out = models.PositiveIntegerField("Kilometrajul la plecare", null=True, blank=True)
    odometer_in = models.PositiveIntegerField("Kilometrajul la întoarcere", null=True, blank=True)
    km = models.DecimalField("Km parcurși", max_digits=9, decimal_places=1, default=Decimal("0"))
    adr = models.BooleanField("Mărfuri periculoase (ADR)", default=False)
    meals_provided = models.BooleanField("Masa asigurată de angajator / beneficiar", default=False)
    per_diem_pct = models.DecimalField("Diurna (% din normă; gol — din Constante)", max_digits=6, decimal_places=2, null=True,
                                       blank=True)
    # combustibilul din foaia de parcurs (pentru KPI „consumul față de normă”): rămășița la plecare + alimentat − rămășița la
    # întoarcere; altfel consumul scris de mână sau din GPS
    fuel_out = models.DecimalField("Combustibil în rezervor la plecare (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    fuel_added = models.DecimalField("Combustibil alimentat în cursă (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    fuel_in = models.DecimalField("Combustibil în rezervor la întoarcere (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    fuel_used = models.DecimalField("Combustibil consumat (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    fuel_adj_pct = models.DecimalField("Corecția normei de consum (%, iarna, munți, aer condiționat…)", max_digits=6,
                                       decimal_places=2, null=True, blank=True)
    docs_submitted = models.DateField("Actele cursei predate la (CMR, foaia de parcurs, bonurile)", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    note = models.TextField("Observații", blank=True)
    # socotite la salvare, fixate la aprobare
    fuel_source = models.CharField("Consumul — de unde", max_length=10, blank=True, db_default="")  # tank / manual / gps
    fuel_norm_l = models.DecimalField("Consumul normat (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    km_rate = models.DecimalField("Tariful pe km aplicat", max_digits=10, decimal_places=4, null=True, blank=True)
    km_amount = models.DecimalField("Plata pe km (de șofer)", max_digits=12, decimal_places=2, default=Decimal("0"))
    how = models.CharField("Explicația", max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-departure", "-id"]
        verbose_name = "Cursa (foaia de parcurs)"

    def __str__(self):
        return f"Foaia de parcurs nr. {self.number or '—'} din {timezone.localtime(self.departure):%d.%m.%Y}"

    def reference(self) -> str:
        day = timezone.localtime(self.departure)
        return f"nr. {self.number} din {day:%d.%m.%Y}" if self.number else f"din {day:%d.%m.%Y}"


class TripLeg(models.Model):
    """Segmentul cursei într-o țară: intrarea și ieșirea (ora trecerii frontierei), încărcarea / descărcarea acolo, masa
    asigurată, km (opțional)."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="legs")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="+", verbose_name="Țara")
    entered = models.DateTimeField("Intrarea")
    left = models.DateTimeField("Ieșirea")
    loading = models.BooleanField("Încărcare", default=False)
    unloading = models.BooleanField("Descărcare", default=False)
    meals = models.BooleanField("Masa asigurată", default=False)
    km = models.DecimalField("Km", max_digits=9, decimal_places=1, null=True, blank=True)
    note = models.CharField("Observații", max_length=200, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "entered", "id"]
        verbose_name = "Segmentul cursei"


class TripDiem(models.Model):
    """Diurna socotită: un rând pe zi (sau perioadă) și persoană, cu țara, orele, procentul, norma, cursul și suma în lei."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="diems")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, related_name="+")
    day = models.DateField("Ziua")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                verbose_name="Țara (gol — în Republica Moldova)")
    hours = models.DecimalField("Ore", max_digits=5, decimal_places=2, default=Decimal("0"))
    pct = models.DecimalField("% din normă", max_digits=6, decimal_places=2, default=Decimal("0"))
    norm = models.DecimalField("Norma pe zi (în valută)", max_digits=10, decimal_places=2, default=Decimal("0"))
    currency = models.CharField("Valuta", max_length=3, default="MDL")
    fx_rate = models.DecimalField("Cursul BNM", max_digits=12, decimal_places=4, default=Decimal("1"))
    amount = models.DecimalField("Suma (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    taxable = models.DecimalField("Peste normă, impozabilă (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    how = models.CharField("Explicația", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["employment", "day", "sort"]
        verbose_name = "Diurna cursei"


# --- tahograful (pasul b): descărcările cardului de conducător ------------------------------------------------------------
def _tacho_upload(instance, filename):
    return f"private/tachograph/{timezone.now():%Y/%m}/{instance.sha256[:20]}.ddd"


class TachoFile(models.Model):
    """Fișierul descărcat de pe cardul de conducător (.ddd), păstrat ca original (pentru control); citit la încărcare —
    activitățile pe zile, vehiculele, locurile, trecerile frontierei. Legat de angajat după numărul cardului din dosar (actul
    „Cardul de conducător auto pentru tahograf”) sau după nume și data nașterii."""

    file = models.FileField("Fișierul", upload_to=_tacho_upload)
    name = models.CharField("Numele fișierului", max_length=200)
    sha256 = models.CharField(max_length=64, unique=True)
    size = models.PositiveIntegerField(default=0)
    generation = models.PositiveSmallIntegerField("Generația tahografului", default=1)
    version = models.PositiveSmallIntegerField("Versiunea (G2)", default=1)
    card_number = models.CharField("Numărul cardului", max_length=20, db_index=True)
    card_nation = models.CharField("Țara emitentă", max_length=3, blank=True)
    authority = models.CharField("Emitentul", max_length=60, blank=True)
    card_issue = models.DateField("Eliberat", null=True, blank=True)
    card_expiry = models.DateField("Valabil până la", null=True, blank=True)
    holder_surname = models.CharField("Numele titularului", max_length=60, blank=True)
    holder_first_names = models.CharField("Prenumele titularului", max_length=60, blank=True)
    birth_date = models.DateField("Data nașterii", null=True, blank=True)
    licence_number = models.CharField("Permisul de conducere", max_length=20, blank=True)
    downloaded_at = models.DateTimeField("Descărcat la", null=True, blank=True)
    first_day = models.DateField("Prima zi", null=True, blank=True)
    last_day = models.DateField("Ultima zi", null=True, blank=True)
    days = models.PositiveIntegerField("Zile cu activități", default=0)
    employee = models.ForeignKey("staff.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="tacho_files",
                                 verbose_name="Angajatul")
    matched_by = models.CharField("Legat după", max_length=20, blank=True)  # card / name / manual
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-downloaded_at", "-uploaded_at", "-id"]
        verbose_name = "Descărcarea cardului de tahograf"

    def __str__(self):
        return f"Cardul {self.card_number} ({self.holder_surname} {self.holder_first_names})".strip()

    def holder(self) -> str:
        return f"{self.holder_surname} {self.holder_first_names}".strip()


class TachoDay(models.Model):
    """Ziua tahografului (00:00–24:00 UTC) a angajatului: intervalele de activitate de pe card (luate din descărcarea cea mai
    nouă care o are), distanța și totalurile în minute."""

    employee = models.ForeignKey("staff.Employee", on_delete=models.CASCADE, related_name="tacho_days")
    file = models.ForeignKey(TachoFile, on_delete=models.CASCADE, related_name="day_rows")
    day = models.DateField("Ziua (UTC)")
    distance = models.PositiveIntegerField("Km în zi", default=0)
    presence = models.PositiveIntegerField("Contorul de prezență", default=0)
    # [[minutul de început, minutul de sfârșit, R/A/W/D/U, echipaj 0/1, introdus manual 0/1], …]
    spans = models.JSONField(default=list)
    driving = models.PositiveIntegerField("Conducere (min)", default=0)
    work = models.PositiveIntegerField("Altă muncă (min)", default=0)
    availability = models.PositiveIntegerField("Disponibilitate (min)", default=0)
    rest = models.PositiveIntegerField("Pauză / odihnă (min)", default=0)
    unknown = models.PositiveIntegerField("Fără card (min)", default=0)

    class Meta:
        ordering = ["employee", "day"]
        verbose_name = "Ziua tahografului"
        constraints = [models.UniqueConstraint(fields=["employee", "day"], name="uniq_tacho_day")]


class TachoEvent(models.Model):
    """Evenimentele de pe card: începutul / sfârșitul perioadei zilnice de muncă cu țara, vehiculele folosite, trecerile
    frontierei și încărcările / descărcările (generația 2 versiunea 2)."""

    KINDS = [("work_begin", "Începutul perioadei zilnice de muncă"), ("work_end", "Sfârșitul perioadei zilnice de muncă"),
             ("vehicle", "Vehiculul folosit"), ("border", "Trecerea frontierei"), ("load", "Încărcare"), ("unload", "Descărcare"),
             ("load_unload", "Încărcare și descărcare")]
    employee = models.ForeignKey("staff.Employee", on_delete=models.CASCADE, related_name="tacho_events")
    file = models.ForeignKey(TachoFile, on_delete=models.CASCADE, related_name="event_rows")
    kind = models.CharField(max_length=12, choices=KINDS)
    at = models.DateTimeField("Ora")
    until = models.DateTimeField("Până la (vehiculul)", null=True, blank=True)
    country = models.CharField("Țara (ISO 2; la frontieră — în care intră)", max_length=3, blank=True)
    country_left = models.CharField("Țara din care iese", max_length=3, blank=True)
    odometer = models.PositiveIntegerField("Kilometrajul", null=True, blank=True)
    odometer_end = models.PositiveIntegerField("Kilometrajul la sfârșit", null=True, blank=True)
    plate = models.CharField("Numărul vehiculului", max_length=16, blank=True)
    manual = models.BooleanField("Introdus de mână", default=False)

    class Meta:
        ordering = ["employee", "at", "id"]
        verbose_name = "Evenimentul de pe card"
        constraints = [models.UniqueConstraint(fields=["employee", "kind", "at"], name="uniq_tacho_event")]


# --- GPS-ul vehiculelor (pasul c): zilele din sistemul de monitorizare ---------------------------------------------------
class GpsDay(models.Model):
    """O zi a unui vehicul din sistemul GPS (importul raportului zilnic din fișier sau din API-ul furnizorului): km, timpul în
    mișcare și cu motorul pornit, prima pornire / ultima oprire, combustibilul, kilometrajul, țările. Se compară cu foaia de
    parcurs (km) și dă consumul cursei când foaia nu-l are."""

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="gps_days", verbose_name="Vehiculul")
    day = models.DateField("Ziua")
    km = models.DecimalField("Km", max_digits=9, decimal_places=1, default=Decimal("0"))
    moving_min = models.PositiveIntegerField("În mișcare (min)", null=True, blank=True)
    engine_min = models.PositiveIntegerField("Cu motorul pornit (min)", null=True, blank=True)
    first_start = models.TimeField("Prima pornire", null=True, blank=True)
    last_stop = models.TimeField("Ultima oprire", null=True, blank=True)
    fuel_l = models.DecimalField("Combustibil consumat (l)", max_digits=9, decimal_places=2, null=True, blank=True)
    odometer_start = models.PositiveIntegerField("Kilometrajul la începutul zilei", null=True, blank=True)
    odometer_end = models.PositiveIntegerField("Kilometrajul la sfârșitul zilei", null=True, blank=True)
    countries = models.CharField("Țările (coduri ISO 2, în ordine)", max_length=60, blank=True)
    source = models.CharField("Sursa (fișierul / furnizorul)", max_length=40, blank=True)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    imported_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["vehicle", "day"]
        verbose_name = "Ziua vehiculului din GPS"
        constraints = [models.UniqueConstraint(fields=["vehicle", "day"], name="uniq_gps_day")]


# --- evenimentele șoferului și KPI (pasul c) --------------------------------------------------------------------------------
class DriverIncident(models.Model):
    """Evenimentul legat de șofer: dauna mărfii / vehiculului, accidentul, amenda, reclamația clientului. Intră în indicatorii
    KPI care le numără (doar cele din vina șoferului). Recuperarea pagubei (CM art. 327 și urm.) nu se face de aici."""

    KINDS = [("damage_cargo", "Dauna mărfii"), ("damage_vehicle", "Dauna vehiculului"), ("accident", "Accident rutier"),
             ("fine", "Amendă"), ("complaint", "Reclamația clientului"), ("other", "Alt eveniment")]
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="driver_incidents",
                                 verbose_name="Șoferul")
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents",
                             verbose_name="Cursa")
    date = models.DateField("Data")
    kind = models.CharField("Felul", max_length=16, choices=KINDS)
    at_fault = models.BooleanField("Din vina șoferului", default=True)
    amount = models.DecimalField("Suma (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    document = models.CharField("Actul (procesul-verbal, decizia, reclamația)", max_length=200, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Evenimentul șoferului"

    def __str__(self):
        return f"{self.get_kind_display()} din {self.date:%d.%m.%Y}"


class KpiIndicator(models.Model):
    """Indicatorul KPI: ce se măsoară (sursa) și cum se notează implicit (0–100 %). Fără indicatori de viteză sau de distanță
    care ar împinge șoferul să încalce regulile (siguranța circulației)."""

    SOURCES = [("fuel", "Consumul de combustibil față de normă (%)"), ("incidents", "Evenimentele șoferului (număr sau sumă)"),
               ("documents", "Actele cursei predate la timp (% din curse)"), ("tacho", "Încălcările timpului de conducere / odihnă"),
               ("manual", "Evaluarea scrisă de mână")]
    MODES = [("linear", "Liniar între „100 %” și „0 %”"), ("step", "Prag: îndeplinit — 100 %, altfel 0")]
    MEASURES = [("count", "Numărul"), ("amount", "Suma (lei)")]
    code = models.CharField("Codul", max_length=20, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=120)
    name_ru = models.CharField("Denumire (RU)", max_length=120, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=120, blank=True)
    source = models.CharField("Ce se măsoară", max_length=10, choices=SOURCES)
    kinds = models.JSONField("Felurile evenimentelor numărate", default=list, blank=True)
    measure = models.CharField("Evenimentele — numărul sau suma", max_length=6, choices=MEASURES, default="count")
    mode = models.CharField("Notarea", max_length=6, choices=MODES, default="linear")
    full_at = models.DecimalField("Valoarea cu nota 100 %", max_digits=12, decimal_places=2)
    zero_at = models.DecimalField("Valoarea cu nota 0 %", max_digits=12, decimal_places=2)
    unit = models.CharField("Unitatea", max_length=20, blank=True)
    description = models.CharField("Cum se măsoară (explicația)", max_length=400, blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "code"]
        verbose_name = "Indicatorul KPI"

    def __str__(self):
        return f"{self.code} — {self.name_ro}"


class KpiScheme(models.Model):
    """Schema KPI (din regulamentul de salarizare / contractul colectiv): baza primei (sumă fixă sau % din salariul de funcție),
    indicatorii cu ponderile lor, pragul punctajului sub care prima nu se plătește. Prima = baza × punctajul (0–100 %)."""

    BASES = [("fixed", "Sumă fixă (lei)"), ("pct", "% din salariul de funcție")]
    code = models.CharField("Codul", max_length=20, unique=True)
    name = models.CharField("Denumirea", max_length=150)
    base_kind = models.CharField("Baza primei", max_length=5, choices=BASES, default="fixed")
    base_amount = models.DecimalField("Suma de bază (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    base_pct = models.DecimalField("Procentul din salariul de funcție", max_digits=6, decimal_places=2, default=Decimal("0"))
    min_score = models.DecimalField("Pragul: sub acest punctaj (%) prima nu se plătește", max_digits=5, decimal_places=2,
                                    default=Decimal("0"))
    prorate = models.BooleanField("Proporțional cu timpul lucrat în lună", default=True)
    needs_trips = models.BooleanField("Doar cu curse aprobate în lună (fără curse — prima nu se socotește)", default=True,
                                      db_default=True)
    document = models.CharField("Temeiul (regulamentul de salarizare, contractul colectiv)", max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Schema KPI"

    def __str__(self):
        return f"{self.code} — {self.name}"


class KpiSchemeItem(models.Model):
    """Indicatorul în schemă: ponderea și, dacă e cazul, alte valori de notare decât cele ale indicatorului."""

    scheme = models.ForeignKey(KpiScheme, on_delete=models.CASCADE, related_name="items")
    indicator = models.ForeignKey(KpiIndicator, on_delete=models.PROTECT, related_name="+", verbose_name="Indicatorul")
    weight = models.DecimalField("Ponderea", max_digits=6, decimal_places=2)
    mode = models.CharField("Notarea (gol — a indicatorului)", max_length=6, choices=KpiIndicator.MODES, blank=True)
    full_at = models.DecimalField("Nota 100 % la (gol — a indicatorului)", max_digits=12, decimal_places=2, null=True, blank=True)
    zero_at = models.DecimalField("Nota 0 % la (gol — a indicatorului)", max_digits=12, decimal_places=2, null=True, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Indicatorul schemei KPI"
        constraints = [models.UniqueConstraint(fields=["scheme", "indicator"], name="uniq_kpi_scheme_item")]


class KpiAssignment(models.Model):
    """Cui se aplică schema: unei funcții (tuturor șoferilor cu funcția) sau unui raport de muncă anume (are întâietate), din
    data dată."""

    scheme = models.ForeignKey(KpiScheme, on_delete=models.CASCADE, related_name="assignments", verbose_name="Schema")
    occupation = models.ForeignKey("org.Occupation", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                   verbose_name="Funcția")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                   verbose_name="Raportul de muncă")
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)

    class Meta:
        ordering = ["date_from", "id"]
        verbose_name = "Aplicarea schemei KPI"


class KpiSheet(models.Model):
    """Fișa KPI a lunii (seria KP): pentru fiecare șofer cu schemă — valorile indicatorilor din curse, evenimente și
    tahograf, notele, punctajul și prima. Socotită la completare, fixată la aprobare; aprobată, prima intră în calculul
    salariului aceleiași luni (tipul KPI)."""

    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                    verbose_name="Subdiviziunea (gol — toată întreprinderea)")
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "-month", "-id"]
        verbose_name = "Fișa KPI a lunii"

    def __str__(self):
        return f"Fișa KPI nr. {self.number or '—'} pe {self.month:02d}.{self.year}"

    def reference(self) -> str:
        return f"nr. {self.number} pe {self.month:02d}.{self.year}" if self.number else f"pe {self.month:02d}.{self.year}"


class KpiLine(models.Model):
    """Un șofer în fișa KPI: schema, baza, valorile și notele indicatorilor (`details`), punctajul, prima pentru luna întreagă
    (în salariu — proporțional cu timpul lucrat, dacă schema o cere). Valorile scrise de mână (`overrides`) rămân la completare."""

    sheet = models.ForeignKey(KpiSheet, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="+")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, related_name="+")
    scheme = models.ForeignKey(KpiScheme, on_delete=models.PROTECT, related_name="+")
    base = models.DecimalField("Baza primei (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    score = models.DecimalField("Punctajul (%)", max_digits=6, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField("Prima (lei, luna întreagă)", max_digits=12, decimal_places=2, default=Decimal("0"))
    prorate = models.BooleanField("Proporțional cu timpul lucrat", default=True)
    details = models.JSONField(default=list, blank=True)
    overrides = models.JSONField("Valorile scrise de mână", default=dict, blank=True)
    note = models.CharField("Explicația", max_length=400, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Rândul fișei KPI"
        constraints = [models.UniqueConstraint(fields=["sheet", "employment"], name="uniq_kpi_line")]
