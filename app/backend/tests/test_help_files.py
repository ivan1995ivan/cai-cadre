"""Fișierele instrucțiunilor (docs/files/): Word-ul se descarcă, video-ul rulează în browser, cu derularea (Range)."""
from django.test import override_settings
from rest_framework.test import APIClient


def test_guide_files_download_and_video_ranges(tmp_path):
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "ghid.docx").write_bytes(b"PK-word")
    (tmp_path / "files" / "ghid.webm").write_bytes(bytes(range(100)))
    api = APIClient()  # public, ca instrucțiunile: legătura se deschide într-o filă nouă, fără jeton
    with override_settings(DOCS_DIR=tmp_path):
        r = api.get("/api/help/files/ghid.docx")
        assert r.status_code == 200 and "attachment" in r["Content-Disposition"] and b"".join(r.streaming_content) == b"PK-word"
        r = api.get("/api/help/files/ghid.webm")
        assert r.status_code == 200 and r["Content-Type"] == "video/webm" and "attachment" not in r.get("Content-Disposition", "")
        r = api.get("/api/help/files/ghid.webm", HTTP_RANGE="bytes=10-19")
        assert r.status_code == 206 and r.content == bytes(range(10, 20)) and r["Content-Range"] == "bytes 10-19/100"
        r = api.get("/api/help/files/ghid.webm", HTTP_RANGE="bytes=-5")
        assert r.status_code == 206 and r.content == bytes(range(95, 100))
        assert api.get("/api/help/files/ghid.webm", HTTP_RANGE="bytes=200-").status_code == 416
        assert api.get("/api/help/files/lipsa.webm").status_code == 404
        assert api.get("/api/help/files/x.py").status_code == 404
        assert api.get("/api/help/files/..%2Fsettings.docx").status_code == 404
