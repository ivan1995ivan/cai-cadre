"""Iconițele programului din logo-ul firmei (PNG / JPG / ICO):

    .venv\\Scripts\\python.exe tools\\make_icon.py C:\\cale\\logo.png

- installer/crm.ico — scurtătura „CRM” de pe desktop și din meniul Start (mărimile cerute de Windows, 16 … 256 px);
- frontend/public/icons/*.png — iconița ferestrei programului (favicon), a aplicației pe telefon (manifest) și cea de pe
  ecranul iPhone-ului; `maskable-512.png` are sigla mai mică, pe fundalul ei, pentru măștile rotunde de pe Android.

Logo-ul se pune pe un pătrat transparent (fără să se deformeze). Cere Pillow (pip install pillow) — doar la producător,
installer-ul și interfața primesc fișierele gata făcute.
"""
import sys
from pathlib import Path

from PIL import Image

SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "installer" / "crm.ico"
ICONS_DIR = ROOT / "frontend" / "public" / "icons"
WEB_ICONS = {"icon-192.png": 192, "icon-512.png": 512, "apple-touch-icon.png": 180}


def square_logo(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    box = image.getbbox()  # fără marginile complet transparente
    if box:
        image = image.crop(box)
    side = max(image.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return square


def make(source: Path, target: Path = TARGET, icons_dir: Path = ICONS_DIR) -> list:
    logo = square_logo(source)
    logo.resize((256, 256), Image.LANCZOS).save(target, format="ICO", sizes=SIZES)
    done = [target]
    icons_dir.mkdir(parents=True, exist_ok=True)
    for name, size in WEB_ICONS.items():
        path = icons_dir / name
        logo.resize((size, size), Image.LANCZOS).save(path, format="PNG", optimize=True)
        done.append(path)
    # maskable: sigla pe 70 % din pătrat, fundalul în culoarea din colțul siglei (zona sigură a măștilor Android)
    background = logo.resize((1, 1), Image.LANCZOS).getpixel((0, 0))[:3]
    canvas = Image.new("RGBA", (512, 512), (*background, 255))
    inner = logo.resize((358, 358), Image.LANCZOS)
    canvas.alpha_composite(inner, ((512 - 358) // 2, (512 - 358) // 2))
    path = icons_dir / "maskable-512.png"
    canvas.save(path, format="PNG", optimize=True)
    done.append(path)
    return done


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for file in make(Path(sys.argv[1])):
        print(f"Gata: {file}")
