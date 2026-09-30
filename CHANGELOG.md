# Changelog for the LaTablée HA connector (add-on + integration, lockstep).

## 2026.09.30.8 (2026-09-30)

### Fixed
- **Add-on wouldn't build**: `latablee_proxy` Dockerfile pinned base image
  `ghcr.io/home-assistant/base:3.19`, which no longer exists on ghcr
  (only 3.21–3.24 remain; verified against the ghcr tags list). Bumped
  to `base:3.23`.
- Versions kept in lockstep across add-on + integration (2026.09.30).

## 2026.09.21 (2026-09-21)

### Added
- Initial release.
- **Add-on:** LaTablée Proxy — ingress proxy to your hosted instance; sidebar panel.
  Options: instance URL, API device token, TLS-verify toggle.
- **Integration (HACS):** config flow with Supervisor discovery pre-fill;
  `todo` entity (two-way shopping list mirror — add/check/delete); `calendar`
  entity (7-day meal plan); custom voice intents ("add tacos for dinner
  Wednesday", "what's for dinner tonight"); freeform *Ask LaTablée* conversation
  agent via the app's `/api/v1/voice/command` NLU; services `add_to_list`,
  `plan_meal`, `query_plan`, `voice_command`.