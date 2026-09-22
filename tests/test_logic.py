"""Unit tests for the pure logic in the LaTablée integration (no HA runtime needed)."""
import importlib.util
import sys
from pathlib import Path

COMP = Path(__file__).resolve().parent.parent / "custom_components" / "latablee"


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# conversation.py imports homeassistant — extract _resolve_date without HA by
# exec'ing only the helper (guards the regex/date logic, our actual logic)
def _resolve_date():
    src = (COMP / "conversation.py").read_text()
    start = src.index("def _resolve_date")
    end = src.index("def _extract_hint")
    ns = {"DATE_WORDS": {
        "tonight": 0, "today": 0, "tomorrow": 1,
        "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH",
        "friday": "FR", "saturday": "SA", "sunday": "SU",
    }}
    exec("import re\nfrom datetime import date as d, timedelta\n" + src[start:end], ns)
    return ns["_resolve_date"]


def test_resolve_tonight_and_tomorrow():
    r = _resolve_date()
    from datetime import date, timedelta

    assert r("tonight") == date.today().isoformat()
    assert r("today") == date.today().isoformat()
    assert r("tomorrow") == (date.today() + timedelta(days=1)).isoformat()
    assert r(None) == date.today().isoformat()


def test_resolve_weekday_is_next_occurrence_not_today():
    r = _resolve_date()
    from datetime import date, timedelta

    today = date.today()
    for name, idx in (("monday", 0), ("wednesday", 2), ("sunday", 6)):
        got = date.fromisoformat(r(name))
        delta = (got - today).days
        assert 1 <= delta <= 7, f"{name} should be in the future, got {delta}"
        assert got.weekday() == idx


def test_resolve_iso_passthrough():
    r = _resolve_date()
    assert r("2026-12-25") == "2026-12-25"


def test_quantity_splitter():
    src = (COMP / "todo.py").read_text()
    start = src.index("def _as_number")
    ns = {}
    exec(src[start:], ns)
    f = ns["_as_number"]
    assert f("2") == 2.0
    assert f("0.5") == 0.5
    assert f("½") == 0.5
    assert f("milk") is None


def test_api_client_url_join():
    src = (COMP / "api.py").read_text()
    assert 'base_url.rstrip("/")' in src, "trailing slash must be normalized"
    assert "/api/v1" in src, "client must target /api/v1"