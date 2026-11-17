"""Clasificatorul băncilor (Administrare → Bănci): listele livrate cu programul și recunoașterea băncii după IBAN.

- Moldova: băncile licențiate (bnm.md — adrese, telefoane, SWIFT) și identificatorii din IBAN (BNM, lista participanților
  la SAPI), plus Trezoreria de Stat și BNM;
- România: codurile BIC ale participanților la SENT (TransFond), CUI și sediile din registrul ASF; codul din IBAN e
  începutul BIC-ului (BTRL, RNCB...). Sunt păstrate și băncile fuzionate, pentru IBAN-urile vechi.
Listele se încarcă la instalare (migrarea 0010); băncile adăugate de mână nu se ating.
"""
import json
import re
from pathlib import Path

from django.db import transaction

DATA = Path(__file__).resolve().parent / "data" / "banks.json"
FIELDS = ("name", "short_name", "bic", "fiscal_code", "address", "phone", "email", "website", "note")


def read() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@transaction.atomic
def load(country: str, model=None) -> int:
    """Încarcă / actualizează țara; `model` — modelul istoric, când se cheamă dintr-o migrare."""
    if model is None:
        from .models import Bank as model

    rows = read()[country]
    existing = {x.code: x for x in model.objects.filter(country=country, custom=False)}
    new, changed = [], []
    for r in rows:
        obj = existing.get(r["code"])
        if obj is None:
            new.append(model(country=country, code=r["code"], **{f: r.get(f, "") for f in FIELDS}))
        elif any(getattr(obj, f) != r.get(f, "") for f in FIELDS):
            for f in FIELDS:
                setattr(obj, f, r.get(f, ""))
            changed.append(obj)
    model.objects.bulk_create(new)
    model.objects.bulk_update(changed, FIELDS)
    return len(rows)


def remove(country: str) -> int:
    from .models import Bank

    return Bank.objects.filter(country=country, custom=False).delete()[0]


def status() -> dict:
    from django.db.models import Count

    from .models import Bank

    lists = read()
    counts = dict(Bank.objects.values_list("country").annotate(n=Count("id")).values_list("country", "n"))
    return {"countries": [{"code": c, "name": n, "available": len(lists.get(c, [])), "loaded": counts.get(c, 0)}
                          for c, n in Bank.COUNTRIES]}


def normalize_iban(iban: str) -> str:
    return re.sub(r"\s+", "", iban or "").upper()


def by_iban(iban: str):
    """Banca după identificatorul din IBAN: MD24 AG00… → maib, RO49 BTRL… → Banca Transilvania. None dacă nu e."""
    from .models import Bank

    iban = normalize_iban(iban)
    if len(iban) < 6:
        return None
    for bank in Bank.objects.filter(country=iban[:2]).exclude(code=""):
        if iban[4:4 + len(bank.code)] == bank.code:
            return bank
    return None


def fill(attrs: dict) -> dict:
    """Completează denumirea băncii și BIC-ul după IBAN, dacă nu sunt scrise (contul firmei, al clientului, importul)."""
    if attrs.get("iban") and not (attrs.get("bank_name") and attrs.get("bic")):
        bank = by_iban(attrs["iban"])
        if bank:
            attrs["bank_name"] = attrs.get("bank_name") or bank.name
            attrs["bic"] = attrs.get("bic") or bank.bic
    return attrs
