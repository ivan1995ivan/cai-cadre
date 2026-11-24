"""Instrucțiunile de lucru: fișiere Markdown din docs/<limbă>/, afișate în sistem la butonul „?”."""
import re

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

KEY = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}(/[a-z0-9][a-z0-9-]{0,60}){0,2}$")


def _read(lang: str, key: str):
    """Articolul ecranului; dacă ecranul (obiectul) n-are articol propriu — al părintelui: „universal/sales” →
    „universal”, „delivery-notes/new” → „delivery-notes”. Întoarce (textul, limba, cheia găsită)."""
    if lang not in ("ro", "ru", "en") or not KEY.match(key):
        return None
    parts = key.split("/")
    for size in range(len(parts), 0, -1):
        found_key = "/".join(parts[:size])
        for candidate in (lang, "ro"):  # dacă lipsește traducerea, se arată versiunea în română
            path = settings.DOCS_DIR / candidate / f"{found_key}.md"
            if path.is_file():
                return path.read_text(encoding="utf-8"), candidate, found_key
    return None


class HelpArticleView(APIView):
    public = True
    authentication_classes = []

    def get(self, request, lang, key):
        found = _read(lang, key)
        if not found:
            return Response({"detail": "Instrucțiunea pentru acest ecran va fi adăugată în curând."}, status=404)
        text, used_lang, found_key = found
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), found_key)
        return Response({"key": found_key, "lang": used_lang, "title": title, "content": text})


class HelpIndexView(APIView):
    public = True
    authentication_classes = []

    def get(self, request, lang):
        if lang not in ("ro", "ru", "en"):
            lang = "ro"
        root = settings.DOCS_DIR / lang
        if not root.exists():
            root = settings.DOCS_DIR / "ro"  # fără instrucțiuni în limba aleasă (EN) se arată cele în română
        articles = []
        for path in sorted(root.rglob("*.md")) if root.exists() else []:
            key = path.relative_to(root).with_suffix("").as_posix()
            first = path.read_text(encoding="utf-8").splitlines()[:1]
            title = first[0][2:].strip() if first and first[0].startswith("# ") else key
            articles.append({"key": key, "title": title})
        return Response(articles)


FILE_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "webm": "video/webm",
    "mp4": "video/mp4",
}


class HelpFileView(APIView):
    """Fișierele instrucțiunilor (docs/files/): documentul Word se descarcă, video-ul se deschide în browser și rulează, cu
    derularea (cererile Range). Publice, ca instrucțiunile: legăturile din Ajutor se deschid într-o filă nouă, fără jeton."""

    public = True
    authentication_classes = []

    def get(self, request, name):
        from django.http import FileResponse, Http404, HttpResponse

        path = settings.DOCS_DIR / "files" / name
        if not path.is_file():
            raise Http404
        ext = name.rsplit(".", 1)[1]
        size = path.stat().st_size
        rng = re.match(r"^bytes=(\d*)-(\d*)$", request.headers.get("Range", ""))
        if rng and ext != "docx" and (rng.group(1) or rng.group(2)):
            if rng.group(1):
                start = int(rng.group(1))
                end = min(int(rng.group(2)), size - 1) if rng.group(2) else size - 1
            else:  # ultimii N octeți
                start, end = max(size - int(rng.group(2)), 0), size - 1
            if start >= size or start > end:
                response = HttpResponse(status=416)
                response["Content-Range"] = f"bytes */{size}"
                return response
            with path.open("rb") as fh:
                fh.seek(start)
                body = fh.read(end - start + 1)
            response = HttpResponse(body, status=206, content_type=FILE_TYPES[ext])
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        else:
            response = FileResponse(path.open("rb"), content_type=FILE_TYPES[ext], as_attachment=ext == "docx", filename=name)
        response["Accept-Ranges"] = "bytes"
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "public, max-age=3600"
        return response
