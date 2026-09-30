#!/bin/bash
# LaTablee Proxy entrypoint — renders nginx config from /data/options.json and starts nginx.
# Startup runs a self-diagnostic against the configured instance so Supervisor logs tell
# you exactly which leg is broken (config → DNS → TLS → app → token) instead of a proxy 502.
set -e

OPTIONS_FILE="/data/options.json"
INSTANCE_URL="$(jq -r '.instance_url // empty' "$OPTIONS_FILE")"
API_TOKEN="$(jq -r '.api_token // empty' "$OPTIONS_FILE")"
VERIFY_TLS="$(jq -r '.verify_tls // true' "$OPTIONS_FILE")"

if [ -z "$INSTANCE_URL" ]; then
    echo "FATAL: instance_url is not set. Add-on → Configuration → LaTablee instance URL (e.g. https://latablee.example.com)"
    exit 1
fi

# normalize: strip trailing slash
INSTANCE_URL="${INSTANCE_URL%/}"
echo "Proxying to: ${INSTANCE_URL} (TLS verify: ${VERIFY_TLS})"

# ---------- Startup self-diagnostics (visible in the Supervisor add-on log) ----------
probe() {
    # $1 = description, $2 = curl args...
    local desc="$1"; shift
    local out rc body http_code
    out=$(curl -sS -m 8 -w '\n%{http_code}' "$@" 2>&1) && rc=0 || rc=$?
    http_code=$(echo "$out" | tail -n1)
    body=$(echo "$out" | head -n -1 | head -c 200)
    if [ "$rc" -eq 0 ] && [ "$http_code" = "200" ]; then
        echo "DIAG OK   : ${desc} (200)"
        return 0
    fi
    echo "DIAG FAIL : ${desc} (curl_rc=${rc} http=${http_code:-none})"
    case "$out" in *curl*6*) echo "            -> could not resolve/connect: check the URL and that the instance is reachable from HA";; esac
    case "$out" in *SSL*) echo "            -> TLS problem: wrong cert or self-signed (try toggle 'Verify TLS' off or fix the cert)";; esac
    [ -n "$body" ] && echo "            -> body: ${body}"
    return 1
}

echo "--- LaTablee proxy diagnostics ---"
# leg 1: DNS/TLS/routing — is the app up?
if probe "instance reachable (${INSTANCE_URL}/api/health)" "${INSTANCE_URL}/api/health"; then
    # leg 2: is the device token valid? (only if one was configured)
    if [ -n "$API_TOKEN" ]; then
        probe "device token valid (/api/v1/auth/me)" -H "Authorization: Bearer ${API_TOKEN}" \
            "${INSTANCE_URL}/api/v1/auth/me" \
        || echo "            -> mint a fresh token: LaTablee → Settings → Device tokens"
    else
        echo "DIAG WARN : no api_token configured — the integration and voice will not work until one is set"
    fi
else
    echo "DIAG      : skipping token check (app unreachable) — fix reachability first"
fi
echo "--- end diagnostics ---"

TLS_FLAGS=""
if [ "$VERIFY_TLS" != "true" ]; then
    TLS_FLAGS="proxy_ssl_verify off;"
fi

# Render config: static assets + API go upstream; everything else → upstream too
# (LaTablée is a SPA — the nginx on the other side handles the index.html fallback).
# Alpine nginx puts server{} files in /etc/nginx/http.d/ (stock nginx.conf includes
# http.d/*.conf inside http{}); this image has no conf.d dir.
# NOTE: proxy_ssl_verify is only valid inside server/location.
mkdir -p /etc/nginx/http.d
rm -f /etc/nginx/http.d/default.conf
rm -f /etc/nginx/latablee.conf  # legacy: template from old COPY, never auto-loaded
cat > /etc/nginx/http.d/latablee.conf <<EOF
# cookies must be scoped under the ingress prefix or the browser drops them
map \$http_x_ingress_path \$cookie_path {
    default  "/";
    ~.+      "\$http_x_ingress_path/";
}

server {
    listen 8099;
    server_name _;

    # Ingress support: HA sends X-Ingress-Path (e.g. /api/hassio_ingress/<token>).
    # The app uses absolute paths (/_next/, /api/), so rewrite refs in responses
    # to live under the ingress prefix; direct (non-ingress) access passes through
    # unchanged because the header is absent and the var resolves empty.
    sub_filter_once off;
    sub_filter_types text/javascript application/javascript application/json;
    set \$ingress_prefix "";
    if (\$http_x_ingress_path) {
        set \$ingress_prefix \$http_x_ingress_path;
    }
    sub_filter 'src="/' 'src="\$ingress_prefix/';
    sub_filter 'href="/' 'href="\$ingress_prefix/';
    sub_filter '"\/_next/' '"\$ingress_prefix\/_next/';
    sub_filter '"\/_next/' '"\$ingress_prefix/_next/';
    sub_filter '"/_next/' '"\$ingress_prefix/_next/';
    sub_filter '"\\/api/' '"\$ingress_prefix\\/api/';
    sub_filter '"/api/' '"\$ingress_prefix/api/';
    sub_filter "'/_next/" "'\$ingress_prefix/_next/";
    sub_filter "'/api/" "'\$ingress_prefix/api/";

    location / {
        error_page 418 = @ingress;
        if (\$http_x_ingress_path) {
            return 418;
        }
        proxy_pass ${INSTANCE_URL};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_connect_timeout 15s;
        ${TLS_FLAGS}
    }

    # Ingress path: strip the X-Ingress-Path prefix so the app sees clean URIs.
    # Static proxy_pass (no resolver needed); the rewrite pattern itself carries
    # the per-request prefix from the header.
    location @ingress {
        rewrite ^/api/hassio_ingress/[^/]+/?\$ / break;
        rewrite ^/api/hassio_ingress/[^/]+(/.*)\$ \$1 break;
        proxy_pass ${INSTANCE_URL};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_cookie_path / "\$cookie_path";
        ${TLS_FLAGS}
    }
}
EOF

rm -f /etc/nginx/latablee.conf 2>/dev/null          # legacy template copy, never loaded
rm -f /etc/nginx/conf.d/latablee-verify.conf 2>/dev/null  # legacy verify snippet
rm -f /etc/nginx/http.d/latablee-verify.conf 2>/dev/null  # legacy verify snippet (http.d paths)

nginx -t
exec nginx -g "daemon off;"