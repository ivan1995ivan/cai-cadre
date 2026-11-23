from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models

from .registry import SCOPES


class Permission(models.Model):
    """Un drept din catalog (de exemplu `offers.approve`). Lista vine din registry.py."""

    code = models.CharField(max_length=64, unique=True)
    module = models.CharField(max_length=32, db_index=True)
    action = models.CharField(max_length=32)
    name_ro = models.CharField(max_length=128)
    name_ru = models.CharField(max_length=128)

    class Meta:
        ordering = ["module", "action"]

    def __str__(self):
        return self.code


class Role(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name_ro = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_admin = models.BooleanField(default=False, help_text="Are toate drepturile")
    is_system = models.BooleanField(default=False, help_text="Rol predefinit, nu se poate șterge")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    # {"clients": "own", "offers": "all"}; modulul lipsă = "all"
    data_scopes = models.JSONField(default=dict, blank=True)
    max_discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    # Marja minimă proprie a rolului; gol = se folosește marja minimă a firmei.
    min_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hidden_fields = models.JSONField(default=list, blank=True)
    # Meniul principal: secțiunile („s:vanzari”) și funcțiile („offers”) pe care rolul NU le vede
    menu_hidden = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name_ro"]

    def __str__(self):
        return self.name_ro


class User(AbstractUser):
    THEMES = [("desktop", "Clasic de birou"), ("desktop_dark", "Clasic de birou, întunecat"), ("green", "Verde"),
              ("turquoise", "Turcoaz"), ("blue", "Albastru"), ("dark", "Întunecată"), ("onec", "Ca în 1C (galben)"),
              ("auto", "Automat")]
    BUTTONS = [("2d", "Plate (2D)"), ("3d", "În relief (3D)")]
    LANGUAGES = [("ro", "Română"), ("ru", "Русский"), ("en", "English")]

    middle_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    position = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGES, default="ro")
    theme = models.CharField(max_length=12, choices=THEMES, default="", blank=True)
    density = models.CharField(max_length=10, default="normal")
    buttons = models.CharField(max_length=2, choices=BUTTONS, default="3d")
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    MARGIN_VISIBILITY = [("inherit", "După rol și firmă"), ("show", "Vede marja"), ("hide", "Nu vede marja")]
    margin_visibility = models.CharField(max_length=8, choices=MARGIN_VISIBILITY, default="inherit")
    must_change_password = models.BooleanField(default=False)
    last_seen_version = models.CharField(max_length=20, blank=True)
    tours_done = models.JSONField(default=list, blank=True)
    # Favoritele din stânga jos: [{"path": "/offers", "key": "offers"} sau {"path": "/clients/5", "title": "..."}]
    favorites = models.JSONField(default=list, blank=True)
    # Aranjarea interfeței, a fiecăruia: {"table:<cheie>": {"order", "hidden", "widths"}, "form:<cheie>": {grupele}}
    ui_prefs = models.JSONField(default=dict, blank=True)
    # Managerul de vânzări: intră în planul de încasări, în salariul managerilor și în repartizarea plăților din casă
    is_manager = models.BooleanField("Manager de vânzări", default=False)
    # Vizibilitatea între agenți (Administrare → Utilizatori). Peste nivelul de acces al rolului:
    # „vede toți agenții” = vede datele tuturor; altfel, pe lângă ale lui, vede datele agenților aleși
    # (supervizorul își vede echipa). Fără nimic bifat rămâne ce spune rolul.
    VISIBILITY = [("role", "După rol"), ("own", "Doar ale lui"), ("all", "Toți agenții")]
    agents_visibility = models.CharField("Vede datele altor agenți", max_length=5, choices=VISIBILITY, default="role")
    visible_agents = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="visible_to",
                                            verbose_name="Vede și agenții")
    can_edit_own_route = models.BooleanField("Își face singur ruta pe zile", default=True)

    class Meta:
        ordering = ["last_name", "first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    # --- drepturi --------------------------------------------------------------
    def _role_cache(self):
        if not hasattr(self, "_roles_cached"):
            self._roles_cached = list(self.roles.prefetch_related("permissions"))
        return self._roles_cached

    @property
    def is_crm_admin(self) -> bool:
        return self.is_superuser or any(r.is_admin for r in self._role_cache())

    def permission_codes(self) -> set:
        if hasattr(self, "_codes_cached"):
            return self._codes_cached
        if self.is_crm_admin:
            from .registry import all_permission_codes

            codes = set(all_permission_codes())
        else:
            codes = set()
            for role in self._role_cache():
                codes.update(p.code for p in role.permissions.all())
        from apps.core import license

        enabled = license.enabled_modules()
        codes = {c for c in codes if license.PERMISSION_MODULES.get(c.split(".")[0], "") in ("", *enabled)}
        from apps.core.models import Company

        company = Company.get()
        if not company.military_enabled:  # modulul opțional „Evidența militară” oprit din Constante → Module
            codes = {c for c in codes if not c.startswith("military.")}
        if not company.production_enabled:  # modulul opțional „Producția” (acordul) oprit
            codes = {c for c in codes if not c.startswith("production.")}
        self._codes_cached = codes
        return codes

    def has_crm_perm(self, code: str) -> bool:
        return code in self.permission_codes()

    def data_scope(self, module: str) -> str:
        """Cel mai larg nivel de acces dintre rolurile utilizatorului."""
        if self.is_crm_admin:
            return "all"
        from .registry import MODULES

        if MODULES.get(module, (None, None, None, False))[3] and self.agents_visibility in ("own", "all"):
            return self.agents_visibility  # setarea utilizatorului e mai tare decât rolul
        order = list(SCOPES)  # own < team < all
        best = None
        for role in self._role_cache():
            scope = role.data_scopes.get(module, "all")
            if best is None or order.index(scope) > order.index(best):
                best = scope
        return best or "own"

    def agent_ids(self, module: str):
        """Agenții (managerii) ale căror date le vede utilizatorul în modul: None = toți; altfel el și agenții aleși."""
        if self.data_scope(module) == "all":
            return None
        ids = {self.pk}
        if self.agents_visibility != "own":
            ids |= set(self.visible_agents.values_list("pk", flat=True))
        return ids

    def max_discount(self) -> Decimal:
        if self.is_crm_admin:
            return Decimal("100")
        return max((r.max_discount for r in self._role_cache()), default=Decimal("0"))

    MARGIN_FIELDS = {"cost_price", "margin"}

    def menu_hidden(self) -> list:
        """Ce nu vede în meniu: ascuns doar dacă e ascuns în toate rolurile lui; administratorul vede tot."""
        if self.is_crm_admin:
            return []
        roles = self._role_cache()
        if not roles:
            return []
        hidden = set(roles[0].menu_hidden or [])
        for role in roles[1:]:
            hidden &= set(role.menu_hidden or [])
        return sorted(hidden)

    def hidden_fields(self) -> set:
        """Câmpurile sensibile ascunse pentru utilizator.

        Regula generală: un câmp e ascuns doar dacă e ascuns în TOATE rolurile utilizatorului.
        Pentru marjă și cost, în ordinea priorității:
          1. bifa de pe utilizator (vede / nu vede);
          2. rolurile.
        Administratorul vede totul.
        """
        if self.is_crm_admin:
            return set()
        roles = self._role_cache()
        if roles:
            hidden = set(roles[0].hidden_fields)
            for role in roles[1:]:
                hidden &= set(role.hidden_fields)
        else:
            hidden = set(self.MARGIN_FIELDS)
        if self.margin_visibility == "show":
            hidden -= self.MARGIN_FIELDS
        elif self.margin_visibility == "hide":
            hidden |= self.MARGIN_FIELDS
        return hidden

    def can_see_margin(self) -> bool:
        return "margin" not in self.hidden_fields()

    def min_margin(self) -> Decimal:
        """Marja minimă sub care documentele cer aprobare (cea mai permisivă dintre roluri)."""
        if self.is_crm_admin:
            return Decimal("0")
        values = [r.min_margin for r in self._role_cache() if r.min_margin is not None]
        return min(values) if values else Decimal("0")
