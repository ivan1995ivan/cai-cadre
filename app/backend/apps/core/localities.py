"""Încărcarea localităților din listele livrate cu programul (Constante → Localități: bife pe țări).

- Moldova: CUATM (Biroul Național de Statistică), cu denumirile RO / RU, raionul și comuna;
- România: SIRUTA (INS, data.gov.ro, OGL-ROU-1.0), cu comuna, județul și codul poștal.
Listele se generează cu tools/build_localities.py. Localitățile adăugate de mână nu se ating.
"""
import gzip
import json
from pathlib import Path

from django.db import transaction

DATA = Path(__file__).resolve().parent / "data"
FILES = {"MD": "localities_md.json.gz", "RO": "localities_ro.json.gz"}
FIELDS = ("name", "name_ru", "kind", "region", "region_ru", "commune", "postal_code")


def read(country: str) -> list:
    with gzip.open(DATA / FILES[country], "rt", encoding="utf-8") as fh:
        return json.load(fh)


@transaction.atomic
def load(country: str) -> int:
    from .models import Locality

    rows = read(country)
    existing = {x.code: x for x in Locality.objects.filter(country=country, custom=False)}
    new, changed = [], []
    for r in rows:
        obj = existing.get(r["code"])
        if obj is None:
            new.append(Locality(country=country, code=r["code"], **{f: r.get(f, "") for f in FIELDS}))
        elif any(getattr(obj, f) != r.get(f, "") for f in FIELDS):
            for f in FIELDS:
                setattr(obj, f, r.get(f, ""))
            changed.append(obj)
    Locality.objects.bulk_create(new, batch_size=1000)
    Locality.objects.bulk_update(changed, FIELDS, batch_size=1000)
    return len(rows)


def remove(country: str) -> int:
    from .models import Locality

    return Locality.objects.filter(country=country, custom=False).delete()[0]


def status() -> dict:
    from django.db.models import Count

    from .models import Locality

    counts = dict(Locality.objects.values_list("country").annotate(n=Count("id")).values_list("country", "n"))
    return {"countries": [{"code": c, "name": n, "available": len(read(c)), "loaded": counts.get(c, 0)}
                          for c, n in Locality.COUNTRIES]}
