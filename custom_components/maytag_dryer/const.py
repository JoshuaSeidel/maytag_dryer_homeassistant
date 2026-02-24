"""Constants for the Maytag Dryer integration."""
from datetime import timedelta

DOMAIN = "maytag_dryer"

# Config entry keys
CONF_USER = "user"
CONF_PASSWORD = "password"
CONF_DRYER_SAIDS = "dryersaids"
CONF_WASHER_SAIDS = "washersaids"

# API
API_AUTH_URL = "https://api.whrcloud.com/oauth/token"
API_APPLIANCE_URL = "https://api.whrcloud.com/api/v1/appliance/{said}"
API_CLIENT_ID = "maytag_android_v1"
API_CLIENT_SECRET = "f1XfYji_D9KfZGovyp8PMgRzrFKjhjY26TV0hu3Mt1-tCCNPl9s95z7QLUfB9UgB"
API_USER_AGENT = "okhttp/4.12.0"

# Polling
SCAN_INTERVAL = timedelta(minutes=2)

# Icons
ICON_DRYER = "mdi:tumble-dryer"
ICON_WASHER = "mdi:washing-machine"

# Machine state mapping (API numeric value -> human-readable string)
MACHINE_STATES: dict[str, str] = {
    "0": "Ready",
    "1": "Not Running",
    "6": "Paused",
    "7": "Running",
    "8": "Wrinkle Prevent",
    "10": "Cycle Complete",
}

# Appliance types
APPLIANCE_TYPE_DRYER = "dryer"
APPLIANCE_TYPE_WASHER = "washer"

# Platforms
PLATFORMS = ["sensor", "binary_sensor"]
