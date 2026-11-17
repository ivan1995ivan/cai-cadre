"""Cursul oficial al Băncii Naționale a Moldovei (BNM)."""
import datetime
from decimal import Decimal

import requests
from defusedxml import ElementTree

from .models import Currency, ExchangeRate

BNM_URL = "https://www.bnm.md/en/official_exchange_rates"


class BnmError(Exception):
    pass


def parse_xml(content: bytes) -> dict:
    """Întoarce {"EUR": (nominal, curs), ...} din XML-ul BNM."""
    root = ElementTree.fromstring(content)
    result = {}
    for valute in root.findall("Valute"):
        code = (valute.findtext("CharCode") or "").strip().upper()
        nominal = int(valute.findtext("Nominal") or 1)
        value = Decimal((valute.findtext("Value") or "0").replace(",", "."))
        if code and value:
            result[code] = (nominal, value)
    return result


def fetch(date: datetime.date) -> dict:
    try:
        response = requests.get(
            BNM_URL, params={"get_xml": 1, "date": date.strftime("%d.%m.%Y")}, timeout=15
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise BnmError(f"Nu s-a putut obține cursul de la BNM: {exc}") from exc
    rates = parse_xml(response.content)
    if not rates:
        raise BnmError("BNM nu a întors niciun curs pentru această dată.")
    return rates


def update_rates(date: datetime.date | None = None, rates: dict | None = None) -> int:
    """Salvează cursurile pentru valutele active cu „curs automat”. Întoarce câte s-au salvat."""
    date = date or datetime.date.today()
    rates = rates if rates is not None else fetch(date)
    saved = 0
    for currency in Currency.objects.filter(is_active=True, auto_rate=True, is_base=False):
        if currency.code not in rates:
            continue
        nominal, value = rates[currency.code]
        ExchangeRate.objects.update_or_create(
            currency=currency, date=date, defaults={"rate": value, "nominal": nominal, "source": "bnm"}
        )
        saved += 1
    return saved


def rate_on(code: str, date: datetime.date) -> Decimal | None:
    """Cursul (MDL pentru 1 unitate) valabil la dată: ultimul cunoscut până la data respectivă."""
    rate = (
        ExchangeRate.objects.filter(currency__code=code, date__lte=date).order_by("-date").first()
    )
    return rate.unit_rate if rate else None
