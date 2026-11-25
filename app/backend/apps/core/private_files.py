"""Fișierele încărcate cu date personale (fotografia și scanările actelor angajatului, certificatele de concediu medical,
semnătura și ștampila întreprinderii): stau în `media/private/` și se dau doar prin API — cu autentificarea și drepturile
endpoint-ului (modulul, subdiviziunile văzute), niciodată prin `/media/`. Public rămân doar logo-urile (pagina de login).

În răspunsurile API câmpul fișierului e adresa endpoint-ului care îl dă (relativă la `/api`, cu `?v=` după numele fișierului,
ca să nu rămână în cache cel vechi); interfața îl cere cu sesiunea utilizatorului."""
import hashlib
import mimetypes
import os
from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import serializers

PREFIX = "private/"
# se deschid în browser; restul (SVG, HTML, orice alt tip) doar se descarcă — un SVG deschis ar rula scripturi
INLINE_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"}


def api_url(route: str, field) -> str | None:
    if not field:
        return None
    return f"{route}?v={hashlib.sha1(field.name.encode()).hexdigest()[:10]}"


class PrivateFileField(serializers.FileField):
    """Câmpul de fișier al cărui conținut se dă doar prin API: în răspuns — adresa endpoint-ului (`route` cu `{pk}`)."""

    def __init__(self, route: str, **kwargs):
        self.route = route
        super().__init__(**kwargs)

    def to_representation(self, value):
        return api_url(self.route.format(pk=getattr(value.instance, "pk", "")), value) if value else None


def serve(field, name: str = ""):
    """Fișierul (FileField) ca răspuns: PDF-urile și imaginile obișnuite în browser, restul ca descărcare."""
    if not field:
        raise Http404
    try:
        handle = field.open("rb")
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Http404 from exc
    ctype = mimetypes.guess_type(field.name)[0] or "application/octet-stream"
    inline = ctype in INLINE_TYPES
    response = FileResponse(handle, content_type=ctype if inline else "application/octet-stream", as_attachment=not inline,
                            filename=name or Path(field.name).name.split("-", 1)[-1])
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    response["Cache-Control"] = "private, max-age=3600"
    return response


def relocate(model, fields, media_root):
    """Pentru migrații: fișierele vechi din afara `private/` se mută acolo (pe disc și în bază). Fișierul lipsă de pe disc —
    doar numele se schimbă. Se poate rula de mai multe ori."""
    root = Path(media_root)
    for obj in model.objects.all():
        changed = []
        for name in fields:
            current = getattr(obj, name).name if getattr(obj, name) else ""
            if not current or current.startswith(PREFIX):
                continue
            new = PREFIX + current
            src, dst = root / current, root / new
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.replace(src, dst)
            setattr(obj, name, new)
            changed.append(name)
        if changed:
            obj.save(update_fields=changed)
