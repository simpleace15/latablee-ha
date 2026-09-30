# Changelog for LaTablée Proxy

## 2026.09.30.8 (2026-09-30)

### Fixed
- **Proxy never actually served**: Alpine's nginx puts `server{}` files in
  `/etc/nginx/http.d/`, not `conf.d/` — the rendered config was written to a
  directory that didn't exist (and the shipped template was never loaded).
  Now renders into `http.d/`, removes stock `default.conf`, uses the image's
  own main nginx.conf.

### Added
- **Startup self-diagnostics** in the add-on log: it probes
  `GET /api/health` (DNS/TLS/routing leg) and the device token via
  `GET /api/v1/auth/me`, then prints exactly which leg failed and how to
  fix it (bad URL vs unreachable app vs TLS vs invalid token). Run
  once at startup; look for the `DIAG` lines in the Supervisor log.

## 2026.09.30 (2026-09-30)

### Fixed
- **Add-on wouldn't build/install**: Dockerfile pinned
  `ghcr.io/home-assistant/base:3.19`, which no longer exists on ghcr
  (repo now keeps 3.21–3.24). Bumped to `base:3.23`.

## 2026.09.21 (2026-09-21)

### Added
- Initial release: ingress proxy to a hosted LaTablée instance.
- Options: instance URL, API device token, TLS-verify toggle.