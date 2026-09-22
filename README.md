# LaTablée — Home Assistant connector

[LaTablée](https://github.com/simpleace15/latablee) is a self-hosted recipe &
meal-planning app. This repo connects it to **Home Assistant**: sidebar access,
voice over Assist, and entities for automations.

One repo, two components (the Frigate pattern):

| Component | What it is | Where |
|-----------|-----------|-------|
| **Add-on** (`/latablee_proxy`) | Thin ingress proxy → the LaTablée sidebar panel. You log into the app UI through HA. | Supervisor add-on |
| **Integration** (`/custom_components/latablee`) | The real functionality: shopping-list & meal-plan entities, custom voice intents, services, and a freeform "ask LaTablée" conversation agent. | HACS / `custom_components` |

## Quick start

1. **Point the add-on at your LaTablée instance** — install *LaTablée Proxy*,
   set the instance URL (e.g. `https://latablee.example.com`) and paste an API
   token from LaTablée → Settings → Device tokens. Start it: a **LaTablée**
   panel appears in the HA sidebar.
2. **Set up the integration** — Settings → Devices & Services → *LaTablée*.
   If the add-on is installed and running, Supervisor discovery pre-fills the
   URL and token — confirm once and you're done. (HACS installs skip discovery;
   enter the URL + token manually.)
3. **Talk to it** —
   - *"Hey HA, add milk to the shopping list"* (built-in todo intent, no setup)
   - *"Hey HA, add tacos for dinner Wednesday"* / *"what's for dinner tonight"*
     (custom intent, fast local match)
   - Anything else: *"ask LaTablée, can we make something with the chicken
     tomorrow?"* → the app's LLM NLU answers.

## Entities & services

- `todo.latablee_shopping_list` — two-way mirror of the active shopping list.
- `calendar.latablee_meal_plan` — dinner/breakfast/lunch entries for the week.
- Services: `latablee.add_to_list`, `latablee.plan_meal`, `latablee.query_plan`,
  `latablee.voice_command`.
- Conversation agent: *Ask LaTablée* (freeform, uses the app's LLM).

## Requirements

- **LaTablée app, v0.4.1+**, reachable from HA over the network — this is the
  [app repo](https://github.com/simpleace15/latablee); deploy it anywhere with
  `docker compose up -d` (see its README prerequisites).
- **A device token** from that instance — LaTablée → Settings → Device tokens →
  name it (e.g. "Home Assistant") → copy the `lat_…` value once.
- **Home Assistant 2024.6+** (for the modern `todo` + conversation agent APIs).
- For the sidebar add-on: Home Assistant **OS or Supervised** (Supervisor).
  For container/Docker-Core HA installs, skip the add-on and use the
  integration alone (HACS) — it carries all the functionality.
- AI features through the connector (freeform voice) additionally need the
  app's LLM endpoint configured — Tier 1/2 voice (list + plan intents) works
  without any LLM.

## License

AGPL-3.0 — same as LaTablée.