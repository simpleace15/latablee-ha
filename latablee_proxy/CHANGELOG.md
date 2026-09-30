# Changelog for LaTablée Proxy

## 2026.09.30 (2026-09-30)

### Fixed
- **Add-on wouldn't build/install**: Dockerfile pinned
  `ghcr.io/home-assistant/base:3.19`, which no longer exists on ghcr
  (repo now keeps 3.21–3.24). Bumped to `base:3.23`.

## 2026.09.21 (2026-09-21)

### Added
- Initial release: ingress proxy to a hosted LaTablée instance.
- Options: instance URL, API device token, TLS-verify toggle.