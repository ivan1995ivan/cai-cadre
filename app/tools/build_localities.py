"""Generează listele de localități livrate cu programul (backend/apps/core/data/localities_*.json.gz).

    python tools/build_localities.py <CUATM.xlsx> <siruta.csv>

- Moldova: CUATM (Biroul Național de Statistică, statistica.gov.md/files/files/Clasificatoare/CUATM_25.xlsx) — denumirile
  RO și RU, raionul / municipiul, comuna; statutul: 5 municipiu, 3 oraș, 8 comună (satul de reședință), 9 sat din comună,
  6 sat din oraș (2 raion, 4 sector — nu sunt localități).
- România: SIRUTA (INS, data.gov.ro, licența OGL-ROU-1.0), nivelul 3 (localitățile), cu UAT-ul (comuna / orașul),
  județul și codul poștal; numele vin cu majuscule și sedile — se aduc la forma obișnuită (Ș, Ț cu virgulă).
"""
import csv
import gzip
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend" / "apps" / "core" / "data"
SMALL = {"de", "din", "la", "lui", "pe", "cu", "sub", "peste", "și", "si", "în", "cel", "cea", "dintre", "după", "spre", "lângă"}


def ro_letters(text: str) -> str:
    return (text.replace("Ş", "Ș").replace("ş", "ș").replace("Ţ", "Ț").replace("ţ", "ț")
            .replace("Ã", "Ă").replace("ã", "ă"))


def title(text: str) -> str:
    """„VADUL LUI VODĂ” → „Vadul lui Vodă”; „TÂRGU-JIU” → „Târgu-Jiu”."""
    words = ro_letters(text.strip()).lower().split()
    out = []
    for i, w in enumerate(words):
        if i > 0 and w in SMALL:
            out.append(w)
        else:
            out.append("-".join(p[:1].upper() + p[1:] for p in w.split("-")))
    return " ".join(out)


def moldova(path):
    import openpyxl

    rows = list(openpyxl.load_workbook(path, read_only=True).worksheets[0].iter_rows(values_only=True))[1:]
    by_code = {r[0]: r for r in rows if r[0]}
    kinds = {5: "municipiu", 3: "oraș", 8: "comună", 9: "sat", 6: "sat"}

    def region(r):
        node = r
        while node is not None:
            if node[4] == 2:
                return f"r. {node[5].strip()}", f"р-н {node[6].strip()}"
            if node[4] == 5:
                return f"mun. {node[5].strip()}", f"мун. {node[6].strip()}"
            if node[4] is None:
                return node[5].strip(), (node[6] or node[5]).strip()
            node = by_code.get(node[1])
        return "", ""

    out = []
    for r in rows:
        if r[4] not in kinds:
            continue
        reg, reg_ru = region(r)
        parent = by_code.get(r[1])
        commune = parent[5].strip() if parent is not None and r[4] in (9, 6) else ""
        out.append({"code": str(r[2]), "name": r[5].strip(), "name_ru": (r[6] or "").strip(), "kind": kinds[r[4]],
                    "region": reg, "region_ru": reg_ru, "commune": commune, "postal_code": ""})
    return out


def romania(path):
    rows = list(csv.reader(open(path, encoding="latin2"), delimiter=";"))[1:]
    num = lambda v: str(int(float((v or "0").replace(",", "."))))  # noqa: E731
    by_code = {num(r[0]): r for r in rows}
    counties = {r[3]: title(re.sub(r"^(JUDEŢUL|JUDETUL)\s+", "", r[1])) for r in rows if r[6] == "1"}
    out = []
    for r in rows:
        if r[6] != "3":
            continue
        parent = by_code.get(num(r[4]))
        ptype = parent[5] if parent else ""
        tip = r[5]
        if tip == "9":
            kind = "municipiu" if ptype in ("1", "4") else "oraș"
        elif tip == "17":
            kind = "oraș"
        elif tip == "22":
            kind = "comună"
        elif tip == "6":
            kind = "sector"
        else:
            kind = "sat"
        commune = title(re.sub(r"^(MUNICIPIUL|ORAŞ|ORAS|COMUNA)\s+", "", parent[1])) if parent else ""
        postal = num(r[2])
        out.append({"code": num(r[0]), "name": title(r[1]), "name_ru": "", "kind": kind,
                    "region": f"jud. {counties.get(r[3], '')}" if counties.get(r[3]) != "Municipiul București" else "București",
                    "region_ru": "", "commune": commune if commune != title(r[1]) else "",
                    "postal_code": postal if postal != "0" else ""})
    return out


def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / name, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    print(name, len(data))


if __name__ == "__main__":
    write("localities_md.json.gz", moldova(sys.argv[1]))
    write("localities_ro.json.gz", romania(sys.argv[2]))
