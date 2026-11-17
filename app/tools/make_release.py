"""Instrumentul producătorului: pachetul de actualizare semnat (NU se livrează clienților).

    cd frontend && npm run build && cd ..
    python tools/make_release.py --notes-ro "Ce e nou" --notes-ru "Что нового" [--wheels]

Rezultatul: releases/crm-update-<versiune>.zip. Clientul îl încarcă în Administrare → Întreținere → Actualizări
(sau îl pune la adresa de actualizări). Pachetul e semnat cu aceeași cheie privată ca licențele
(~/.crm-license/private_key.pem); sistemul refuză orice pachet nesemnat sau modificat.
"""
import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization

PROJECT = Path(__file__).resolve().parent.parent
KEY_FILE = Path.home() / ".crm-license" / "private_key.pem"
EXCLUDE_PARTS = {"__pycache__", ".pytest_cache", "tests"}


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def app_version(project: Path) -> str:
    text = (project / "backend" / "config" / "settings.py").read_text(encoding="utf-8")
    return re.search(r'APP_VERSION = "([^"]+)"', text).group(1)


def program_files(project: Path):
    """Fișierele din pachet: codul din git (backend, docs, start.bat) + interfața compilată (frontend/dist)."""
    try:
        listed = subprocess.run(["git", "ls-files", "backend", "docs", "start.bat"], cwd=project, capture_output=True,
                                text=True, check=True).stdout.splitlines()
        files = [project / f for f in listed]
    except (OSError, subprocess.CalledProcessError):
        files = [f for d in ("backend", "docs") for f in (project / d).rglob("*") if f.is_file()]
        files.append(project / "start.bat")
    dist = project / "frontend" / "dist"
    if not (dist / "index.html").exists():
        raise SystemExit("Interfața nu este compilată: rulați `npm run build` în frontend/.")
    files += [f for f in dist.rglob("*") if f.is_file()]
    return [f for f in files if f.exists() and not EXCLUDE_PARTS & set(f.relative_to(project).parts)]


def build(project: Path, out: Path, private_key, version: str, notes_ro="", notes_ru="", wheels_dir: Path | None = None) -> Path:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in program_files(project):
            zf.write(file, file.relative_to(project).as_posix())
        if wheels_dir:
            for wheel in wheels_dir.glob("*"):
                zf.write(wheel, f"wheels/{wheel.name}")
    data = payload.getvalue()
    release = {"version": version, "notes_ro": notes_ro, "notes_ru": notes_ru, "sha256": hashlib.sha256(data).hexdigest()}
    raw = json.dumps(release, ensure_ascii=False, indent=2).encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("release.json", raw)
        zf.writestr("release.sig", b64(private_key.sign(raw)))
        zf.writestr("payload.zip", data)
    return out


def main():
    parser = argparse.ArgumentParser(description="Pachetul de actualizare semnat")
    parser.add_argument("--notes-ro", default="")
    parser.add_argument("--notes-ru", default="")
    parser.add_argument("--wheels", action="store_true", help="Include bibliotecile Python (instalare fără internet)")
    parser.add_argument("--key", default=str(KEY_FILE))
    parser.add_argument("--out", default=str(PROJECT / "releases"))
    args = parser.parse_args()
    key = serialization.load_pem_private_key(Path(args.key).read_bytes(), password=None)
    version = app_version(PROJECT)
    with tempfile.TemporaryDirectory() as tmp:
        wheels = None
        if args.wheels:
            wheels = Path(tmp) / "wheels"
            subprocess.run([sys.executable, "-m", "pip", "download", "-r", str(PROJECT / "backend" / "requirements.txt"),
                            "-d", str(wheels)], check=True)
        out = build(PROJECT, Path(args.out) / f"crm-update-{version}.zip", key, version, args.notes_ro, args.notes_ru, wheels)
    print(f"Pachetul: {out} ({out.stat().st_size // 1024} KB), versiunea {version}")


if __name__ == "__main__":
    main()
