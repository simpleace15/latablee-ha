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
cat > /etc/nginx/conf.d/latablee.conf <<EOF
server {
    listen 8099;
    server_name _;

    location / {
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
}
EOF

# upstream TLS verification for self-signed certs
if [ "$VERIFY_TLS" != "true" ]; then
    echo "proxy_ssl_verify off;" > /etc/nginx/conf.d/latablee-verify.conf
else
    echo "" > /etc/nginx/conf.d/latablee-verify.conf
fi

# drop the copied template — only the rendered one should load
rm -f /etc/nginx/latablee.conf

nginx -t
exec nginx -g "daemon off;"