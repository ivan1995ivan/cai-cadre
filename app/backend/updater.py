"""Actualizările programului (fără Django: le folosește și supervizorul din run.py înainte de pornirea serverului).

Pachetul de actualizare (făcut de producător cu tools/make_release.py) este un ZIP cu:
    release.json  {"version", "notes_ro", "notes_ru", "sha256"}   – sha256 al lui payload.zip
    release.sig   semnătura Ed25519 a lui release.json (cheia producătorului, aceeași ca la licențe)
    payload.zip   fișierele programului: backend/ (cu requirements.txt), frontend/dist/, docs/, start.bat, wheels/ (opțional)

Pașii: stage() verifică semnătura și pune pachetul în instance/updates/pending.zip; la repornire, apply_pending()
copiază fișierele vechi în instance/updates/rollback/<versiune>/, scrie fișierele noi, instalează dependențele dacă
s-au schimbat, iar dacă ceva nu merge readuce fișierele vechi (rollback()).
"""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Ce aparține programului (restul — instance/, .venv/, python/ — nu se atinge).
MANAGED = ["backend", "frontend/dist", "docs", "start.bat"]
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


class UpdateError(RuntimeError):
    pass


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def version_tuple(version: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in str(version).split("."))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_release(package: Path, public_key_b64: str) -> dict:
    """Verifică pachetul: semnătura producătorului și suma de control a fișierelor."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        with zipfile.ZipFile(package) as zf:
            raw = zf.read("release.json")
            signature = _b64decode(zf.read("release.sig").decode().strip())
            payload_info = zf.getinfo("payload.zip")
            work = package.parent / f".{package.stem}-payload.zip"
            with zf.open(payload_info) as src, open(work, "wb") as dst:
                shutil.copyfileobj(src, dst)
    except (KeyError, zipfile.BadZipFile, ValueError) as exc:
        raise UpdateError("Fișierul nu este un pachet de actualizare.") from exc
    try:
        try:
            Ed25519PublicKey.from_public_bytes(_b64decode(public_key_b64)).verify(signature, raw)
        except (InvalidSignature, ValueError) as exc:
            raise UpdateError("Semnătura pachetului nu este validă (nu este de la producător sau a fost modificat).") from exc
        release = json.loads(raw)
        if _sha256(work) != release.get("sha256"):
            raise UpdateError("Pachetul este deteriorat (suma de control nu corespunde).")
    finally:
        work.unlink(missing_ok=True)
    return release


def updates_dir(instance_dir: Path) -> Path:
    path = Path(instance_dir) / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stage(package: Path, instance_dir: Path, public_key_b64: str, current_version: str) -> dict:
    release = read_release(package, public_key_b64)
    if version_tuple(release["version"]) <= version_tuple(current_version):
        raise UpdateError(f"Versiunea {release['version']} nu este mai nouă decât cea instalată ({current_version}).")
    target = updates_dir(instance_dir)
    shutil.copyfile(package, target / "pending.zip")
    (target / "pending.json").write_text(json.dumps({**release, "from_version": current_version}, ensure_ascii=False),
                                         encoding="utf-8")
    return release


def pending(instance_dir: Path) -> dict | None:
    info = Path(instance_dir) / "updates" / "pending.json"
    if not info.exists():
        return None
    try:
        return json.loads(info.read_text(encoding="utf-8"))
    except ValueError:
        return None


def cancel_pending(instance_dir: Path):
    for name in ("pending.zip", "pending.json"):
        (Path(instance_dir) / "updates" / name).unlink(missing_ok=True)


def _program_files(program_dir: Path):
    for item in MANAGED:
        path = program_dir / item
        if path.is_file():
            yield path
        elif path.is_dir():
            for file in path.rglob("*"):
                if file.is_file() and not SKIP_PARTS & set(file.relative_to(program_dir).parts):
                    yield file


def _log(log, text):
    if log:
        log(text)


def apply_pending(program_dir: Path, instance_dir: Path, python=sys.executable, log=print) -> dict | None:
    """Aplică actualizarea pregătită. Întoarce informația despre ea, sau None dacă nu e nimic de aplicat."""
    program_dir, instance_dir = Path(program_dir), Path(instance_dir)
    info = pending(instance_dir)
    package = instance_dir / "updates" / "pending.zip"
    if info is None or not package.exists():
        return None
    old_version = info.get("from_version", "old")
    rollback_dir = instance_dir / "updates" / "rollback" / old_version
    work = instance_dir / "updates" / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    _log(log, f"Actualizare la versiunea {info['version']}...")
    with zipfile.ZipFile(package) as zf:
        zf.extract("payload.zip", work)
    if _sha256(work / "payload.zip") != info.get("sha256"):
        cancel_pending(instance_dir)
        raise UpdateError("Pachetul pregătit este deteriorat; actualizarea a fost anulată.")
    new_dir = work / "new"
    with zipfile.ZipFile(work / "payload.zip") as zf:
        for member in zf.namelist():
            # nicio cale în afara directorului programului
            if member.startswith(("/", "\\")) or ".." in Path(member).parts:
                raise UpdateError(f"Cale nepermisă în pachet: {member}")
        zf.extractall(new_dir)

    # 1. copia fișierelor actuale (pentru revenire)
    shutil.rmtree(rollback_dir, ignore_errors=True)
    old_files = list(_program_files(program_dir))
    for file in old_files:
        dest = rollback_dir / file.relative_to(program_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
    (rollback_dir / "rollback.json").write_text(json.dumps({"version": old_version}), encoding="utf-8")
    req = program_dir / "backend" / "requirements.txt"
    old_requirements = req.read_bytes() if req.exists() else b""
    try:
        # 2. fișierele noi peste cele vechi; cele care nu mai există în versiunea nouă se șterg
        new_files = {f.relative_to(new_dir) for f in new_dir.rglob("*") if f.is_file()}
        for rel in new_files:
            if rel.parts[0] == "wheels":
                continue
            dest = program_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(new_dir / rel, dest)
        for file in old_files:
            if file.relative_to(program_dir) not in new_files:
                file.unlink(missing_ok=True)
        # 3. dependențele Python, doar dacă s-au schimbat
        if req.exists() and req.read_bytes() != old_requirements:
            cmd = [python, "-m", "pip", "install", "-r", str(req)]
            if (new_dir / "wheels").exists():
                cmd += ["--no-index", "--find-links", str(new_dir / "wheels")]
            _log(log, "Se instalează bibliotecile noi...")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise UpdateError("Bibliotecile nu s-au instalat:\n" + proc.stdout[-2000:] + proc.stderr[-2000:])
    except Exception:
        rollback(program_dir, instance_dir, old_version, log=log)
        cancel_pending(instance_dir)
        raise
    cancel_pending(instance_dir)
    shutil.rmtree(work, ignore_errors=True)
    (instance_dir / "updates" / "last.json").write_text(json.dumps({"version": info["version"], "from_version": old_version}),
                                                        encoding="utf-8")
    _log(log, f"Fișierele versiunii {info['version']} sunt la locul lor.")
    return info


def rollback(program_dir: Path, instance_dir: Path, version: str, log=print) -> bool:
    """Readuce fișierele versiunii `version` (păstrate la actualizare)."""
    program_dir, instance_dir = Path(program_dir), Path(instance_dir)
    source = instance_dir / "updates" / "rollback" / version
    if not source.exists():
        return False
    saved = {f.relative_to(source) for f in source.rglob("*") if f.is_file() and f.name != "rollback.json"}
    for file in list(_program_files(program_dir)):
        if file.relative_to(program_dir) not in saved:
            file.unlink(missing_ok=True)
    for rel in saved:
        dest = program_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, dest)
    _log(log, f"S-a revenit la versiunea {version}.")
    return True
