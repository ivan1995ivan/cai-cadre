"""Proxy-ul de încredere pentru waitress (platforma `launcher.py` și serverul bazei `run.py`).

Cererea ajunge la aplicație prin lanțul nginx → platformă → serverul bazei. Waitress șterge antetele X-Forwarded-* venite de la
un proxy nedeclarat (`clear_untrusted_proxy_headers`), așa că fără reglaj aplicația vede mereu adresa vecinului (127.0.0.1),
nu a omului: jurnalul de audit, sesiunile și consola arătau doar 127.0.0.1.

`CRM_TRUSTED_PROXY` — adresa proxy-ului din fața serverului (un IP sau `*` pentru „oricine poate ajunge la port”, potrivit doar
când portul e închis în rețeaua stivei, ca `app` în compose, unde singurul din față e nginx). Gol — fără proxy de încredere:
antetele se șterg, adresa e cea a conexiunii. Se ia doar ultima adresă din X-Forwarded-For (cea pusă de proxy-ul nostru; nginx
o scrie din nou cu adresa reală, nu o adaugă la cea trimisă de client) și X-Forwarded-Proto (https de la margine).
"""
import os


def waitress_options(trusted: str | None = None) -> dict:
    trusted = (os.environ.get("CRM_TRUSTED_PROXY", "") if trusted is None else trusted).strip()
    if not trusted:
        return {}
    return {"trusted_proxy": trusted, "trusted_proxy_count": 1,
            "trusted_proxy_headers": {"x-forwarded-for", "x-forwarded-proto"}, "clear_untrusted_proxy_headers": True}
