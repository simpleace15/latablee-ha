# LaTablée Proxy

Thin ingress proxy that shows your hosted **LaTablée** meal planner in the
Home Assistant sidebar. No app code here — it forwards to your instance.

## Configuration

| Option | Required | Description |
|--------|----------|-------------|
| `instance_url` | yes | Your LaTablée instance, e.g. `https://latablee.example.com` |
| `api_token` | no | Device token from LaTablée → Settings → Device tokens (used by the integration's discovery pre-fill) |
| `verify_tls` | no | Verify upstream TLS (default `true`; turn off only for self-signed LAN certs) |

Start the add-on and the **LaTablée** panel appears in the sidebar. Log in with
your normal app credentials — the session persists in your browser.