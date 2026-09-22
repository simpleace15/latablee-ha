"""Constants for the LaTablée integration."""
DOMAIN = "latablee"

CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"

PLATFORMS = ["todo", "calendar", "conversation"]

# voice device hints from Assist satellites (helps the app's fuzzy wake-word matching)
WAKE_HINTS = ["LaTablée", "la table", "latable", "the table"]