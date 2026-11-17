#!/bin/sh
# Verifică comportamentul deploy/nginx pe un nginx de unică folosință, cu o
# aplicație-ecou în locul lui `app` (răspunde 200 cu calea și antetele primite):
# ce se închide din internet, segmentele „..”, CSP, X-Forwarded-For, limita de
# autentificare. Nu atinge stiva `cai-cadre`; rulează în CI și local, înainte de
# `nginx -s reload` pe server:
#   ./deploy/nginx-test.sh
# „Din internet” = cu antetul CF-Connecting-IP, ca cererile venite prin tunel.
# NGINX_CONF_DIR = alt folder de configurație (implicit deploy/nginx).
set -eu
cd "$(dirname "$0")/.."
CONF_DIR=$(cd "${NGINX_CONF_DIR:-deploy/nginx}" && pwd)

NAME=cai-cadre-nginx-test-$$
cleanup() {
    docker rm -f "$NAME-app" "$NAME-web" > /dev/null 2>&1 || true
    docker network rm "$NAME" > /dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# subrețea dată: plajele implicite ale Docker de pe server sunt epuizate
# (vezi `networks` în docker-compose.yml)
docker network create --subnet 10.219.0.32/29 "$NAME" > /dev/null
docker run -d --name "$NAME-app" --network "$NAME" --network-alias app python:3.13-slim python -c '
import http.server, json
class Echo(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = json.dumps({"path": self.path, "xff": self.headers.get("X-Forwarded-For")}).encode()
        html = self.path == "/" or self.path.startswith("/__platform")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_POST = do_GET
    def log_message(self, *args):
        pass
http.server.ThreadingHTTPServer(("0.0.0.0", 8000), Echo).serve_forever()
' > /dev/null
docker run -d --name "$NAME-web" --network "$NAME" -p 127.0.0.1::80 \
    -v "$CONF_DIR:/etc/nginx/conf.d:ro" nginx:1.30-alpine > /dev/null
URL="http://$(docker port "$NAME-web" 80/tcp | head -n 1)"

code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
header() {
    name=$1
    shift
    curl -s -D - -o /dev/null "$@" | tr -d '\r' | sed -n "s/^$name: //Ip"
}
i=0
until [ "$(code "$URL/health")" = 200 ]; do
    i=$((i + 1))
    if [ $i -ge 30 ]; then
        docker logs "$NAME-web" >&2
        echo "nginx nu răspunde" >&2
        exit 1
    fi
    sleep 1
done

FAILED=0
check() {
    if [ "$2" = "$3" ]; then
        echo "ok    $1"
    else
        echo "FAIL  $1: așteptat «$2», primit «$3»"
        FAILED=1
    fi
}
EDGE="-H CF-Connecting-IP:203.0.113.10"
LOGIN='{"username":"x","password":"y"}'

check "internet: /__platform/console închis" 404 "$(code $EDGE "$URL/__platform/console")"
check "internet: /__platform/current închis" 404 "$(code $EDGE "$URL/__platform/current")"
check "internet: /%5F%5Fplatform/console închis" 404 "$(code $EDGE "$URL/%5F%5Fplatform/console")"
check "internet: //__platform/console închis" 404 "$(code --path-as-is $EDGE "$URL//__platform/console")"
check "local: /__platform/console deschis" 200 "$(code "$URL/__platform/console")"
check "segment .. refuzat" 400 "$(code --path-as-is $EDGE "$URL/__platform/console/../../")"
check "segment %2e%2e refuzat" 400 "$(code --path-as-is "$URL/x/%2E%2e/y")"
check "internet: /api/setup/status/ deschis" 200 "$(code $EDGE "$URL/api/setup/status/")"
check "internet: /api/setup/install/ închis" 404 "$(code $EDGE -X POST "$URL/api/setup/install/")"
check "local: /api/setup/install/ deschis" 200 "$(code -X POST "$URL/api/setup/install/")"
check "http prin Cloudflare → https" 301 "$(code $EDGE -H X-Forwarded-Proto:http "$URL/x")"
check "HSTS doar pe https" "max-age=31536000" "$(header strict-transport-security "$URL/" -H X-Forwarded-Proto:https)"

csp=$(header content-security-policy "$URL/")
check "CSP pe HTML: scripturi doar proprii" yes "$(echo "$csp" | grep -q "script-src 'self';" && echo yes || echo no)"
check "CSP lipsește pe JSON" "" "$(header content-security-policy "$URL/api/x")"
csp=$(header content-security-policy "$URL/__platform/console")
check "CSP pe platformă (local): scripturi inline" yes "$(echo "$csp" | grep -q "script-src 'self' 'unsafe-inline'" && echo yes || echo no)"

xff=$(curl -s $EDGE -H "X-Forwarded-For: 6.6.6.6" "$URL/x" | sed -n 's/.*"xff": "\([^"]*\)".*/\1/p')
check "X-Forwarded-For = doar IP-ul real" 203.0.113.10 "$xff"

ok=0
n=0
while [ $n -lt 21 ]; do
    [ "$(code -H CF-Connecting-IP:203.0.113.50 -d "$LOGIN" "$URL/api/auth/login/")" = 200 ] && ok=$((ok + 1))
    n=$((n + 1))
done
check "autentificare: 21 de încercări trec (rafala)" 21 "$ok"
check "autentificare: a 22-a → 429" 429 "$(code -H CF-Connecting-IP:203.0.113.50 -d "$LOGIN" "$URL/api/auth/login/")"
check "autentificare: 429 are {\"detail\"}" yes \
    "$(curl -s -H CF-Connecting-IP:203.0.113.50 -d "$LOGIN" "$URL/api/auth/login/" | grep -q '"detail"' && echo yes || echo no)"
check "autentificare: alt IP nu e afectat" 200 "$(code -H CF-Connecting-IP:203.0.113.51 -d "$LOGIN" "$URL/api/auth/login/")"
check "GET pe login nu se numără" 200 "$(code -H CF-Connecting-IP:203.0.113.50 "$URL/api/auth/login/")"

if [ "$FAILED" != 0 ]; then
    echo "deploy/nginx: verificările au eșuat" >&2
    exit 1
fi
echo "deploy/nginx: toate verificările au trecut"
