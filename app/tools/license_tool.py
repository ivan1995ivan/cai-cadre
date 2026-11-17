"""Instrumentul producătorului pentru licențe (NU se livrează clienților).

    python tools/license_tool.py genkey
        creează perechea de chei în ~/.crm-license/ (cheia privată rămâne doar la producător)
        și afișează cheia publică de pus în backend/apps/core/license.py (PUBLIC_KEY_B64)

    python tools/license_tool.py issue --company "Firma SRL" --idno 1003600000000 \
        --plan business --users 20 --until 2027-12-31 --modules cadre,payroll

    Treptele (după numărul de utilizatori activi): start 1–5, business 10–50, corporate 100, enterprise 500;
    fără --plan, treapta se alege după --users.
        afișează textul licenței, care se introduce în sistem la Administrare → Licență
"""
import argparse
import base64
import datetime
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

KEY_DIR = Path.home() / ".crm-license"
PRIVATE_KEY = KEY_DIR / "private_key.pem"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def genkey(_args):
    if PRIVATE_KEY.exists():
        raise SystemExit(f"Cheia există deja: {PRIVATE_KEY}. Nu o suprascriu.")
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    PRIVATE_KEY.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    print(f"Cheia privată: {PRIVATE_KEY}  (păstrați-o în siguranță, faceți copie!)")
    print(f"PUBLIC_KEY_B64 = \"{b64(public)}\"")


def issue(args):
    key = serialization.load_pem_private_key(PRIVATE_KEY.read_bytes(), password=None)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    from apps.core.license_plans import PlanError, check_plan, plan_for  # noqa: E402

    plan = args.plan or plan_for(args.users)
    try:
        check_plan(plan, args.users)
    except PlanError as exc:
        raise SystemExit(str(exc)) from None
    payload = {
        "company": args.company,
        "idno": args.idno,
        "plan": plan,
        "max_users": args.users,
        "modules": [m.strip() for m in args.modules.split(",") if m.strip()],
        "valid_until": args.until,
        "issued": datetime.date.today().isoformat(),
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    print(f"{b64(raw)}.{b64(key.sign(raw))}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(required=True)
    sub.add_parser("genkey").set_defaults(func=genkey)
    p = sub.add_parser("issue")
    p.add_argument("--company", required=True)
    p.add_argument("--idno", default="")
    p.add_argument("--users", type=int, default=5)
    p.add_argument("--plan", default=None, help="start (1–5) / business (10–50) / corporate (100) / enterprise (500)")
    p.add_argument("--until", default=None, help="AAAA-LL-ZZ; fără = nelimitat")
    p.add_argument("--modules", default="cadre,payroll")
    p.set_defaults(func=issue)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
