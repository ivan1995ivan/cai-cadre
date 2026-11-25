from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def _upload_to(instance, filename):
    return f"company/{filename}"  # logo-urile: publice (pagina de login)


def _private_upload(instance, filename):
    return f"private/company/{filename}"  # semnătura și ștampila: doar prin API (apps.core.private_files)


class Company(models.Model):
    """Constantele întreprinderii (un singur rând, id=1): datele din antetul formelor și din declarații, semnatarii."""

    THEMES = [("desktop", "Clasic de birou"), ("desktop_dark", "Clasic de birou, întunecat"), ("green", "Verde"),
              ("turquoise", "Turcoaz"), ("blue", "Albastru"), ("dark", "Întunecată"), ("onec", "Ca în 1C (galben)")]

    name_ro = models.CharField("Denumire (RO)", max_length=200)
    name_ru = models.CharField("Denumire (RU)", max_length=200, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=200, blank=True)
    legal_form = models.CharField("Formă juridică", max_length=20, blank=True, help_text="De ex. SRL, SA, ÎI")
    idno = models.CharField("IDNO", max_length=13, blank=True)
    caem = models.CharField("Codul CAEM (genul principal de activitate)", max_length=4, blank=True,
                            help_text="Patru cifre, fără punct (de ex. 6201); intră în antetul declarațiilor IPC21 / IALS21.")
    legal_address = models.CharField("Adresa juridică", max_length=300, blank=True)
    postal_address = models.CharField("Adresa poștală", max_length=300, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    website = models.CharField(max_length=200, blank=True)
    # Semnatarii formelor: numele și funcția (RO / RU); funcția goală = denumirea obișnuită (Director, Contabil-șef …)
    director = models.CharField("Conducătorul (numele)", max_length=150, blank=True)
    director_position_ro = models.CharField("Funcția conducătorului (RO)", max_length=100, blank=True,
                                            help_text="De ex. Director, Director general, Administrator")
    director_position_ru = models.CharField("Funcția conducătorului (RU)", max_length=100, blank=True)
    chief_accountant = models.CharField("Contabil-șef (numele)", max_length=150, blank=True)
    chief_accountant_position_ro = models.CharField("Funcția contabilului (RO)", max_length=100, blank=True)
    chief_accountant_position_ru = models.CharField("Funcția contabilului (RU)", max_length=100, blank=True)
    hr_head = models.CharField("Responsabilul de personal (numele)", max_length=150, blank=True)
    hr_head_position_ro = models.CharField("Funcția responsabilului de personal (RO)", max_length=100, blank=True)
    hr_head_position_ru = models.CharField("Funcția responsabilului de personal (RU)", max_length=100, blank=True)
    payroll_enabled = models.BooleanField("Modulul Salarizare (livrare cu salariu)", default=True)
    military_enabled = models.BooleanField(
        "Modulul Evidența militară", default=False,
        help_text="Evidența militară a rezerviștilor nu mai e obligatorie pentru agenții economici (Legea 112/2023). Oprit — "
                  "fila din dosar, registrul, rapoartele și clasificatoarele militare nu apar, iar API-ul lor nu răspunde.")
    production_enabled = models.BooleanField(
        "Modulul Producția (salarizarea în acord)", default=False,
        help_text="Pentru fabrici și ateliere: grila tarifară, lucrările în acord cu normele lor, brigăzile și rapoartele de "
                  "producție, care intră în calculul salariului. Oprit — meniul, setările și API-ul producției nu apar.")
    transport_enabled = models.BooleanField(
        "Modulul Transportul (cursele, diurnele, plata pe km)", default=False, db_default=False,
        help_text="Pentru transportatori: vehiculele, cursele (foaia de parcurs) cu țările, diurnele șoferilor pe țări și plata pe "
                  "km, care intră în calculul salariului. Oprit — meniul, setările și API-ul transportului nu apar.")
    function_panel = models.BooleanField(
        "Panoul funcțiilor (ca în 1C)", default=False,
        help_text="Secțiunile sus ca file; secțiunea deschide panoul ei: schema de lucru, registrele, clasificatoarele, "
                  "rapoartele. Oprit — meniul în stânga, ca până acum.")
    languages = models.JSONField("Limbile sistemului (ro / ru / en)", default=list, blank=True)

    logo = models.FileField(upload_to=_upload_to, blank=True)
    logo_small = models.FileField(upload_to=_upload_to, blank=True)
    logo_dark = models.FileField(upload_to=_upload_to, blank=True)
    signature = models.FileField(upload_to=_private_upload, blank=True)
    stamp = models.FileField(upload_to=_private_upload, blank=True)

    default_theme = models.CharField(max_length=12, choices=THEMES, default="desktop")
    primary_color = models.CharField("Culoare principală proprie", max_length=7, blank=True)
    installed_at = models.DateTimeField(default=timezone.now)

    # Funcțiile semnatarilor când nu sunt scrise în Constante: (RO, RU, EN)
    DEFAULT_POSITIONS = {
        "director": ("Director", "Директор", "Director"),
        "chief_accountant": ("Contabil-șef", "Главный бухгалтер", "Chief accountant"),
        "hr_head": ("Șef resurse umane", "Начальник отдела кадров", "Head of HR"),
    }

    class Meta:
        verbose_name = "Constante"

    def __str__(self):
        return self.name_ro

    @classmethod
    def get(cls) -> "Company":
        from . import request_cache

        def load():
            obj = cls.objects.filter(pk=1).first()
            return obj if obj is not None else cls.objects.create(pk=1, name_ro="Firma mea")

        return request_cache.get("company", load)  # o singură citire pe cerere (se cere pe fiecare rând / linie)

    def position(self, who: str, lang: str = "ro") -> str:
        """Funcția semnatarului (`director`, `chief_accountant`, `hr_head`) în limba formei. Nescrisă în limba formei —
        cea scrisă în română (e funcția reală din actele firmei); nescrisă deloc — denumirea obișnuită."""
        ro, ru, en = self.DEFAULT_POSITIONS[who]
        own_ro, own_ru = getattr(self, f"{who}_position_ro").strip(), getattr(self, f"{who}_position_ru").strip()
        if lang == "ru":
            return own_ru or own_ro or ru
        return own_ro or (en if lang == "en" else ro)

    def display_name(self, lang: str = "ro") -> str:
        """Denumirea în limba formei, cu forma juridică dacă nu e scrisă deja în denumire: „Exemplu” SRL."""
        name = (lang == "ru" and self.name_ru) or (lang == "en" and self.name_en) or self.name_ro
        form = (self.legal_form or "").strip()
        if form and form.casefold().replace(".", "") not in name.casefold().replace(".", "").split():
            name = f"{name} {form}"
        return name

    def enabled_languages(self) -> list:
        """Limbile în care lucrează sistemul (bifele din Constante); fără bife — toate trei."""
        return [x for x in ("ro", "ru", "en") if x in (self.languages or [])] or ["ro", "ru", "en"]

    def save(self, *args, **kwargs):
        from . import request_cache

        super().save(*args, **kwargs)
        request_cache.forget("company")


class BankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="bank_accounts")
    iban = models.CharField(max_length=34)
    bank_name = models.CharField(max_length=150)
    bic = models.CharField("Cod BIC", max_length=11, blank=True)
    currency = models.CharField(max_length=3, default="MDL")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "id"]

    def __str__(self):
        return f"{self.iban} ({self.bank_name})"


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name_ro = models.CharField(max_length=60)
    name_ru = models.CharField(max_length=60)
    symbol = models.CharField(max_length=8, blank=True)
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    auto_rate = models.BooleanField("Curs automat BNM", default=True)

    class Meta:
        ordering = ["-is_base", "code"]
        verbose_name_plural = "currencies"

    def __str__(self):
        return self.code


class ExchangeRate(models.Model):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="rates")
    date = models.DateField(db_index=True)
    rate = models.DecimalField(max_digits=14, decimal_places=4)  # MDL pentru `nominal` unități
    nominal = models.PositiveIntegerField(default=1)
    source = models.CharField(max_length=10, default="bnm")

    class Meta:
        ordering = ["-date", "currency__code"]
        constraints = [models.UniqueConstraint(fields=["currency", "date"], name="uniq_rate_currency_date")]

    def __str__(self):
        return f"{self.currency.code} {self.date}: {self.rate}"

    @property
    def unit_rate(self) -> Decimal:
        return self.rate / self.nominal


class VatRate(models.Model):
    name = models.CharField(max_length=60)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-rate"]

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """Tipul de plată: numerar, transfer bancar, card POS, plăți instant MIA...
    external_code = valoarea din 1C (ВидОплаты), pentru importul plăților."""

    KINDS = [("cash", "Numerar / casă"), ("bank", "Transfer bancar"), ("card", "Card / POS"), ("instant", "Plată instant"),
             ("other", "Altul")]

    code = models.SlugField(max_length=40, unique=True)
    name_ro = models.CharField(max_length=80)
    name_ru = models.CharField(max_length=80)
    kind = models.CharField(max_length=10, choices=KINDS, default="cash")
    fiscal_receipt = models.BooleanField("Cere bon fiscal", default=False)
    external_code = models.CharField("Cod 1C (ВидОплаты)", max_length=60, blank=True)
    sort = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "name_ro"]

    def __str__(self):
        return self.name_ro


class NumberSeries(models.Model):
    """Numerotarea documentelor, de exemplu OF-2026-00001."""

    doc_type = models.CharField(max_length=40, unique=True)
    name_ro = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    prefix = models.CharField(max_length=10, blank=True)
    include_year = models.BooleanField(default=True)
    padding = models.PositiveSmallIntegerField(default=5)
    reset_yearly = models.BooleanField(default=True)
    next_value = models.PositiveIntegerField(default=1)
    current_year = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["doc_type"]

    def __str__(self):
        return self.name_ro

    def format(self, value: int, year: int) -> str:
        parts = [p for p in (self.prefix, str(year) if self.include_year else "") if p]
        parts.append(str(value).zfill(self.padding))
        return "-".join(parts)

    def preview(self) -> str:
        year = timezone.localdate().year
        value = 1 if (self.reset_yearly and self.current_year != year) else self.next_value
        return self.format(value, year)

    @classmethod
    def next_number(cls, doc_type: str) -> str:
        """Ia următorul număr; blocarea rândului garantează numere unice și cu mai mulți utilizatori simultan."""
        year = timezone.localdate().year
        with transaction.atomic():
            series = cls.objects.select_for_update().get(doc_type=doc_type)
            if series.reset_yearly and series.current_year != year:
                series.next_value = 1
            series.current_year = year
            value = series.next_value
            series.next_value = value + 1
            series.save(update_fields=["next_value", "current_year"])
        return series.format(value, year)


class SystemSetting(models.Model):
    """Setări de sistem cheie–valoare (licență, versiunea schemei etc.)."""

    key = models.CharField(max_length=64, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key

    @classmethod
    def read(cls, key, default=None):
        import copy

        from . import request_cache

        found = request_cache.get(("setting", key), lambda: cls.objects.filter(key=key).values_list("value", flat=True).first())
        return default if found is None else copy.deepcopy(found)  # copie: cine o modifică nu strică memoria cererii

    @classmethod
    def write(cls, key, value):
        from . import request_cache

        cls.objects.update_or_create(key=key, defaults={"value": value})
        request_cache.forget(("setting", key))


class Notification(models.Model):
    """Notificare pentru un utilizator (clopoțelul din antet; rezumatul zilnic merge și pe e-mail)."""

    LEVELS = [("info", "Informație"), ("task", "Sarcină"), ("warning", "Atenție"), ("success", "Succes")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    level = models.CharField(max_length=10, choices=LEVELS, default="info")
    kind = models.CharField(max_length=40, blank=True, help_text="de ex. client_reassigned, offer_approval")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True, help_text="Ruta din interfață, de ex. /clients/15")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

    @classmethod
    def send(cls, user, title, message="", *, level="info", kind="", link="", created_by=None):
        return cls.objects.create(user=user, title=title, message=message, level=level, kind=kind, link=link,
                                  created_by=created_by)


class AuditLog(models.Model):
    ACTIONS = [
        ("create", "Creare"),
        ("update", "Modificare"),
        ("delete", "Ștergere"),
        ("login", "Intrare în sistem"),
        ("login_failed", "Intrare eșuată"),
        ("action", "Acțiune"),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=ACTIONS, db_index=True)
    model = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    # Starea completă după schimbare (versiunea la care se poate reveni) și documentul de care ține rândul
    snapshot = models.JSONField(null=True, blank=True)
    parent_model = models.CharField(max_length=100, blank=True)
    parent_id = models.CharField(max_length=64, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]
        indexes = [models.Index(fields=["model", "object_id"]), models.Index(fields=["parent_model", "parent_id"])]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.username} {self.action} {self.model}"


class Comment(models.Model):
    """Mesaj în conversația despre un obiect (comandă, client, factură...). Cei implicați primesc notificare."""

    model = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=200, blank=True)
    link = models.CharField(max_length=300, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="comments")
    text = models.TextField()
    mentions = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="mentioned_in")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["model", "object_id"])]


class UserSession(models.Model):
    """Intrarea unui utilizator (o pereche de jetoane de la login): de unde, cu ce, ultima acțiune. Consola serverului
    o arată și o poate închide (jetoanele ei nu mai sunt primite)."""

    sid = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    ip = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    device = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)
    last_path = models.CharField(max_length=200, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-last_seen"]


class SlowRequest(models.Model):
    """Cererea care a durat peste prag (consola serverului: cine, ce, cât timp, câte interogări)."""

    at = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    username = models.CharField(max_length=150, blank=True)
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=300)
    status = models.PositiveSmallIntegerField(default=0)
    duration_ms = models.PositiveIntegerField()
    db_ms = models.PositiveIntegerField(default=0)
    queries = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-at"]


class UsageDay(models.Model):
    """Consumul de timp al serverului pe zi și utilizator (cereri, timp total, timp în baza de date, interogări)."""

    date = models.DateField(db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    username = models.CharField(max_length=150, blank=True)
    requests = models.PositiveIntegerField(default=0)
    total_ms = models.PositiveBigIntegerField(default=0)
    db_ms = models.PositiveBigIntegerField(default=0)
    queries = models.PositiveBigIntegerField(default=0)
    slow = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date", "-total_ms"]
        constraints = [models.UniqueConstraint(fields=["date", "username"], name="usage_day_user")]


class Locality(models.Model):
    """Clasificatorul localităților: încărcat din listele oficiale (Moldova — CUATM, România — SIRUTA) sau adăugat de mână.
    Clientul și comanda păstrează localitatea ca text (ales din clasificator), ca datele vechi din 1C să rămână."""

    COUNTRIES = [("MD", "Moldova"), ("RO", "România")]

    country = models.CharField(max_length=2, db_index=True)
    code = models.CharField("Cod (CUATM / SIRUTA)", max_length=20, blank=True)
    name = models.CharField(max_length=120, db_index=True)
    name_ru = models.CharField(max_length=120, blank=True)
    kind = models.CharField("Tipul", max_length=20, blank=True)  # municipiu, oraș, comună, sat, sector
    region = models.CharField("Raionul / județul", max_length=120, blank=True)
    region_ru = models.CharField(max_length=160, blank=True)
    commune = models.CharField("Comuna / orașul", max_length=120, blank=True)
    postal_code = models.CharField("Cod poștal", max_length=10, blank=True)
    custom = models.BooleanField("Adăugată de mână", default=False)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["country", "name", "region"]
        constraints = [models.UniqueConstraint(fields=["country", "code"], condition=models.Q(code__gt=""), name="locality_code")]

    def __str__(self):
        return self.label

    @property
    def label(self) -> str:
        """„Sipoteni, r. Călărași” / „Lelești, com. Buntești, jud. Bihor”."""
        parts = [self.name]
        if self.commune:
            parts.append(f"com. {self.commune}" if self.country == "RO" or self.kind == "sat" else self.commune)
        if self.region and self.region != f"mun. {self.name}":
            parts.append(self.region)
        return ", ".join(parts)


class Bank(models.Model):
    """Clasificatorul băncilor: încărcat din listele oficiale (Moldova — BNM, România — BNR / TransFond) sau adăugat de mână.
    `code` e identificatorul băncii din IBAN (MD: 2 caractere după cifrele de control, RO: 4) — după el se recunoaște banca
    când se scrie IBAN-ul. Conturile bancare păstrează denumirea și BIC-ul ca text (alese din clasificator)."""

    COUNTRIES = Locality.COUNTRIES

    country = models.CharField(max_length=2, db_index=True)
    code = models.CharField("Codul în IBAN", max_length=4, blank=True)
    name = models.CharField("Denumirea", max_length=150, db_index=True)
    short_name = models.CharField("Denumirea scurtă", max_length=80, blank=True)
    bic = models.CharField("Cod BIC / SWIFT", max_length=11, blank=True)
    fiscal_code = models.CharField("IDNO / CUI", max_length=20, blank=True)
    address = models.CharField("Adresa", max_length=250, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.CharField(max_length=150, blank=True)
    website = models.CharField(max_length=150, blank=True)
    note = models.CharField("Notă", max_length=200, blank=True)
    custom = models.BooleanField("Adăugată de mână", default=False)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["country", "name"]
        constraints = [models.UniqueConstraint(fields=["country", "code"], condition=models.Q(code__gt=""), name="bank_code")]

    def __str__(self):
        return self.name
