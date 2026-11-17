"""Suma în litere (contul de plată, actele): română și rusă, cu acordurile corecte.

    amount_in_words(Decimal("1220.50"), "MDL", "ro") → "O mie două sute douăzeci de lei 50 bani"
    amount_in_words(Decimal("1221"), "MDL", "ru")    → "Одна тысяча двести двадцать один лей 00 бань"
"""
from decimal import ROUND_HALF_UP, Decimal

# --- română ---
RO_UNITS_M = ["", "unu", "doi", "trei", "patru", "cinci", "șase", "șapte", "opt", "nouă"]
RO_UNITS_F = ["", "una", "două", "trei", "patru", "cinci", "șase", "șapte", "opt", "nouă"]
RO_TEENS_M = ["zece", "unsprezece", "doisprezece", "treisprezece", "paisprezece", "cincisprezece", "șaisprezece",
              "șaptesprezece", "optsprezece", "nouăsprezece"]
RO_TENS = ["", "", "douăzeci", "treizeci", "patruzeci", "cincizeci", "șaizeci", "șaptezeci", "optzeci", "nouăzeci"]
# moneda: (singular, plural, „un”/„o” la 1, genul la numerale), subunitatea
RO_CURRENCY = {"MDL": (("leu", "lei", "un", "m"), ("ban", "bani")), "RON": (("leu", "lei", "un", "m"), ("ban", "bani")),
               "EUR": (("euro", "euro", "un", "m"), ("cent", "cenți")), "USD": (("dolar", "dolari", "un", "m"), ("cent", "cenți"))}


def _ro_below_1000(n: int, fem: bool) -> str:
    """0–999, cu genul pentru 1 și 2 (feminin: „o mie”, „două mii”)."""
    parts = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        parts.append("o sută" if hundreds == 1 else f"{'două' if hundreds == 2 else RO_UNITS_M[hundreds]} sute")
    if rest:
        units = RO_UNITS_F if fem else RO_UNITS_M
        if rest < 10:
            parts.append(units[rest])
        elif rest < 20:
            parts.append("douăsprezece" if fem and rest == 12 else RO_TEENS_M[rest - 10])
        else:
            tens, u = divmod(rest, 10)
            parts.append(RO_TENS[tens] + (f" și {units[u]}" if u else ""))
    return " ".join(parts)


def _ro_de(n: int) -> bool:
    """„de” înainte de substantiv: 20, 21 de..., 100 de, 120 de; dar 101, 112 fără."""
    return n >= 20 and (n % 100 == 0 or n % 100 >= 20)


def ro_number(n: int, fem: bool = False) -> str:
    if n == 0:
        return "zero"
    out = []
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)
    if millions:
        if millions == 1:
            out.append("un milion")
        else:
            words = _ro_below_1000(millions, fem=True)  # „două milioane”, „douăsprezece milioane”
            out.append(f"{words}{' de' if _ro_de(millions) else ''} milioane")
    if thousands:
        if thousands == 1:
            out.append("o mie")
        else:
            out.append(f"{_ro_below_1000(thousands, fem=True)}{' de' if _ro_de(thousands) else ''} mii")
    if units:
        out.append(_ro_below_1000(units, fem=fem))
    return " ".join(out)


def _ro_amount(whole: int, cents: int, currency: str) -> str:
    (one, many, article, gender), (sub_one, sub_many) = RO_CURRENCY.get(currency, ((currency, currency, "un", "m"),
                                                                                   ("cent", "cenți")))
    if whole == 1:
        words = f"{article} {one}"
    else:
        number = ro_number(whole, fem=gender == "f")
        words = f"{number}{' de' if _ro_de(whole) else ''} {many}"
    return f"{words} {cents:02d} {sub_one if cents == 1 else sub_many}"


# --- rusă ---
RU_UNITS_M = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
RU_UNITS_F = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
RU_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать",
            "семнадцать", "восемнадцать", "девятнадцать"]
RU_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
RU_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]
RU_CURRENCY = {"MDL": (("лей", "лея", "леев", "m"), ("бань", "бани", "бань")),
               "RON": (("лей", "лея", "леев", "m"), ("бань", "бани", "бань")),
               "EUR": (("евро", "евро", "евро", "m"), ("цент", "цента", "центов")),
               "USD": (("доллар", "доллара", "долларов", "m"), ("цент", "цента", "центов"))}


def ru_plural(n: int, forms) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    return forms[0] if n == 1 else forms[1] if 2 <= n <= 4 else forms[2]


def _ru_below_1000(n: int, fem: bool) -> str:
    parts = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        parts.append(RU_HUNDREDS[hundreds])
    if 10 <= rest <= 19:
        parts.append(RU_TEENS[rest - 10])
    else:
        tens, u = divmod(rest, 10)
        if tens:
            parts.append(RU_TENS[tens])
        if u:
            parts.append((RU_UNITS_F if fem else RU_UNITS_M)[u])
    return " ".join(parts)


def ru_number(n: int, fem: bool = False) -> str:
    if n == 0:
        return "ноль"
    out = []
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)
    if millions:
        out.append(f"{_ru_below_1000(millions, False)} {ru_plural(millions, ('миллион', 'миллиона', 'миллионов'))}")
    if thousands:
        out.append(f"{_ru_below_1000(thousands, True)} {ru_plural(thousands, ('тысяча', 'тысячи', 'тысяч'))}")
    if units:
        out.append(_ru_below_1000(units, fem))
    return " ".join(out)


def _ru_amount(whole: int, cents: int, currency: str) -> str:
    forms, sub = RU_CURRENCY.get(currency, ((currency, currency, currency, "m"), ("цент", "цента", "центов")))
    return f"{ru_number(whole, fem=forms[3] == 'f')} {ru_plural(whole, forms)} {cents:02d} {ru_plural(cents, sub)}"


def amount_in_words(amount, currency: str = "MDL", lang: str = "ro") -> str:
    value = Decimal(str(amount or 0)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    whole, cents = int(abs(value)), int((abs(value) * 100) % 100)
    text = _ru_amount(whole, cents, currency) if lang == "ru" else _ro_amount(whole, cents, currency)
    text = ("minus " if lang != "ru" else "минус ") + text if value < 0 else text
    return text[:1].upper() + text[1:]
