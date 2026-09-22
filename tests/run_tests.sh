#!/bin/bash
# Pre-push validation for the LaTablée HA connector repo.
set -e
cd "$(dirname "$0")/.."
FAIL=0

echo "== Python syntax =="
for f in custom_components/latablee/*.py; do
    python3 -c "import ast; ast.parse(open('$f').read())" || FAIL=1
done
echo "python files parsed"

echo "== YAML validity =="
for f in repository.yaml latablee_proxy/config.yaml custom_components/latablee/custom_sentences/en.yaml custom_components/latablee/services.yaml; do
    python3 - "$f" <<'EOF'
import sys, yaml
yaml.safe_load(open(sys.argv[1]))
print(f"  ok: {sys.argv[1]}")
EOF
    [ $? -ne 0 ] && FAIL=1
done

echo "== JSON validity =="
for f in custom_components/latablee/manifest.json custom_components/latablee/strings.json; do
    python3 -c "import json; json.load(open('$f'))" || FAIL=1
done
echo "json files parsed"

echo "== Add-on manifest sanity =="
python3 - <<'EOF'
import yaml
c = yaml.safe_load(open("latablee_proxy/config.yaml"))
assert c["ingress"] is True, "ingress required for sidebar"
assert c["ingress_port"] == 8099
assert set(c["schema"]) == set(c["options"]), "schema/options keys must match exactly"
assert isinstance(c["arch"], list) and c["arch"]
print("  config.yaml ok")
EOF
[ $? -ne 0 ] && FAIL=1

echo "== Dockerfile checks (per skill pitfalls) =="
grep -q 'ARG BUILD_FROM' latablee_proxy/Dockerfile || { echo "FAIL: BUILD_FROM ARG missing"; FAIL=1; }
grep -q 'io.hass.type' latablee_proxy/Dockerfile || { echo "FAIL: io.hass labels missing"; FAIL=1; }
grep -q 'CMD \[ "/run.sh" \]' latablee_proxy/Dockerfile || { echo "FAIL: CMD missing (container would exit)"; FAIL=1; }
grep -q 'apk add --no-cache nginx jq' latablee_proxy/Dockerfile || { echo "FAIL: nginx/jq not installed"; FAIL=1; }

echo "== run.sh checks =="
grep -q 'jq -r' latablee_proxy/run.sh || { echo "FAIL: must use jq (not bashio) for options"; FAIL=1; }
grep -q 'daemon off;' latablee_proxy/run.sh || { echo "FAIL: nginx must run foreground"; FAIL=1; }

echo "== Integration manifest sanity =="
python3 - <<'EOF'
import json
m = json.load(open("custom_components/latablee/manifest.json"))
assert m["domain"] == "latablee"
assert m["config_flow"] is True
assert "aiohttp" in str(m["requirements"])
print("  manifest.json ok")
EOF
[ $? -ne 0 ] && FAIL=1

echo "== No real domains/secrets committed =="
if grep -rE 'dogzilla|10\.0\.|192\.168\.|lat_[a-f0-9]{20}' --include='*.py' --include='*.yaml' --include='*.json' --include='*.md' --include='*.sh' . | grep -v test | grep -v CHANGELOG; then
    echo "FAIL: potential real host/secret in committed files"
    FAIL=1
fi

echo "== Version match (config.yaml ↔ CHANGELOG) =="
V=$(grep '^version:' latablee_proxy/config.yaml | sed 's/version: *"\(.*\)"/\1/')
grep -q "## $V" latablee_proxy/CHANGELOG.md || { echo "FAIL: CHANGELOG missing entry for $V"; FAIL=1; }
V2=$(python3 -c "import json; print(json.load(open('custom_components/latablee/manifest.json'))['version'])")
[ "$V" = "$V2" ] || { echo "FAIL: add-on ($V) and integration ($V2) versions drift — one repo, one version"; FAIL=1; }

echo
[ $FAIL -eq 0 ] && echo "ALL CHECKS PASSED" || { echo "CHECKS FAILED"; exit 1; }