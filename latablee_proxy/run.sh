#!/bin/bash
# LaTablée Proxy entrypoint — renders nginx config from /data/options.json and starts nginx.
set -e

OPTIONS_FILE="/data/options.json"
INSTANCE_URL="$(jq -r '.instance_url // empty' "$OPTIONS_FILE")"
API_TOKEN="$(jq -r '.api_token // empty' "$OPTIONS_FILE")"
VERIFY_TLS="$(jq -r '.verify_tls // true' "$OPTIONS_FILE")"

if [ -z "$INSTANCE_URL" ]; then
    echo "FATAL: instance_url is not set. Add-on → Configuration → LaTablée instance URL (e.g. https://latablee.example.com)"
    exit 1
fi

# normalize: strip trailing slash
INSTANCE_URL="${INSTANCE_URL%/}"
echo "Proxying to: ${INSTANCE_URL} (TLS verify: ${VERIFY_TLS})"

TLS_FLAGS=""
if [ "$VERIFY_TLS" != "true" ]; then
    TLS_FLAGS="proxy_ssl_verify off;"
fi

# Render config: static assets + API go upstream; everything else → upstream too
# (LaTablée is a SPA — the nginx on the other side handles the index.html fallback).
mkdir -p /etc/nginx/http.d
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

# upstream TLS verification for self-signed certs
if [ "$VERIFY_TLS" != "true" ]; then
    echo "proxy_ssl_verify off;" > /etc/nginx/http.d/latablee-verify.conf.disabled
else
    echo "" > /etc/nginx/http.d/latablee-verify.conf.disabled
fi

# drop the copied template — only the rendered one should load
rm -f /etc/nginx/latablee.conf

nginx -t
exec nginx -g "daemon off;"