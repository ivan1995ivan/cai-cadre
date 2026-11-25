"""Adresa reală a omului ajunge în aplicație: waitress crede X-Forwarded-For / X-Forwarded-Proto doar de la proxy-ul declarat
(config.proxy — nginx în fața platformei, platforma în fața serverului bazei); de la oricine altcineva antetele se șterg.
Consola platformei nu ia drept „locală” o cerere venită printr-un proxy."""
import http.client
import json
import threading

from waitress import create_server

from config.proxy import waitress_options


def echo(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps({"ip": environ.get("REMOTE_ADDR"), "scheme": environ.get("wsgi.url_scheme"),
                        "xff": environ.get("HTTP_X_FORWARDED_FOR")}).encode()]


def ask(options, headers):
    srv = create_server(echo, host="127.0.0.1", port=0, **options)
    def run():
        try:
            srv.run()
        except OSError:  # serverul de probă e închis la sfârșitul cererii
            pass

    threading.Thread(target=run, daemon=True).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", srv.effective_port, timeout=5)
        conn.request("GET", "/", headers=headers)
        return json.loads(conn.getresponse().read())
    finally:
        srv.close()


def test_forwarded_address_only_from_the_trusted_proxy(monkeypatch):
    headers = {"X-Forwarded-For": "6.6.6.6, 81.180.0.7", "X-Forwarded-Proto": "https"}
    # proxy-ul de încredere: ultima adresă (pusă de proxy-ul nostru), https de la margine
    assert ask(waitress_options("127.0.0.1"), headers) == {"ip": "81.180.0.7", "scheme": "https", "xff": "81.180.0.7"}
    assert ask(waitress_options("*"), headers)["ip"] == "81.180.0.7"
    # fără proxy declarat (sau altul decât cel care se conectează): antetele nu se cred și se șterg
    assert ask(waitress_options(""), headers) == {"ip": "127.0.0.1", "scheme": "http", "xff": None}
    assert ask(waitress_options("10.219.0.2"), headers) == {"ip": "127.0.0.1", "scheme": "http", "xff": None}
    monkeypatch.setenv("CRM_TRUSTED_PROXY", "*")
    assert waitress_options()["trusted_proxy"] == "*"
    monkeypatch.delenv("CRM_TRUSTED_PROXY")
    assert waitress_options() == {}


def test_client_ip_is_remote_addr_not_the_header(rf):
    from apps.core.audit import client_ip

    req = rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="81.180.0.7")
    assert client_ip(req) == "81.180.0.7"


def test_platform_console_local_only_without_a_proxy():
    from launcher import Platform

    assert Platform._local({"REMOTE_ADDR": "127.0.0.1"})
    assert not Platform._local({"REMOTE_ADDR": "127.0.0.1", "HTTP_X_FORWARDED_FOR": "127.0.0.1"})
    assert not Platform._local({"REMOTE_ADDR": "10.219.0.3"})
