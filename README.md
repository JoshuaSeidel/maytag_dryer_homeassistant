# Maytag Dryer — Home Assistant Integration

Monitor your Maytag/Whirlpool washer and dryer from Home Assistant via the Whirlpool cloud API.

> **Note:** An official integration by mkmer exists in Home Assistant core (2023.2+). That version uses GUI discovery and names states differently. This integration is maintained separately for users who prefer the state naming and attribute layout used here.

---

## What's new in v2.0

- **GUI setup** — configure via Settings → Integrations, no more `configuration.yaml` editing
- **Single shared coordinator** — one OAuth2 token and one API poll per account (not per appliance)
- **Robust error handling** — missing API fields no longer crash the entire update
- **Device registry** — dryer and washer entities are grouped under a device card
- **Reauth flow** — Home Assistant will prompt you to re-enter credentials if they expire
- **Reconfigure** — update credentials or SAIDs without removing and re-adding the integration
- **Consistent attribute naming** — all attributes use `snake_case`

---

## Requirements

- Home Assistant 2024.1.0 or later
- A Maytag/Whirlpool account
- The SAID(s) for your appliances (found in the Maytag app under appliance details)

---

## Installation

### HACS (recommended)

1. Add this repository to HACS as a custom integration: `https://github.com/JoshuaSeidel/maytag_dryer_homeassistant`
2. Install **Maytag Dryer** from HACS
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for **Maytag Dryer**
5. Enter your email, password, and SAID(s)

### Manual

1. Copy `custom_components/maytag_dryer/` into your `<config>/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration** and search for **Maytag Dryer**

---

## Finding your SAID

1. Open the Maytag app on your phone
2. Select your appliance
3. Go to **Settings** or **Appliance Info**
4. The SAID is the alphanumeric identifier shown (use uppercase letters as displayed)

---

## Entities

After setup, you will have:

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.maytag_dryer_<said>` | Sensor | Dryer state (Ready, Running, Paused, Cycle Complete, Wrinkle Prevent, Not Running) |
| `sensor.maytag_washer_<said>` | Sensor | Washer state |
| `binary_sensor.maytag_dryer_door_<said>` | Binary Sensor | Dryer door open/closed |
| `binary_sensor.maytag_washer_door_<said>` | Binary Sensor | Washer door open/closed |

Entity IDs use the SAID in lowercase, matching the previous naming convention so existing automations continue to work.

---

## Sensor attributes

### Dryer

| Attribute | Description |
|-----------|-------------|
| `appliance_id` | Whirlpool appliance ID |
| `model_number` | Model number |
| `serial_number` | Serial number |
| `last_synced` | Last full sync time |
| `last_modified` | Last modified time |
| `door_open` | Door open status (raw value) |
| `status` | Raw machine state code |
| `cycle_name` | Current cycle name |
| `cycle_id` | Current cycle ID |
| `temperature` | Temperature setting |
| `manual_dry_time` | Manual dry time setting |
| `dryness_level` | Dryness level setting |
| `airflow` | Airflow status |
| `drying` | Drying status |
| `damp` | Damp status |
| `steaming` | Steaming status |
| `sensing` | Sensing status |
| `cooldown` | Cool-down status |
| `operations` | Operations setting |
| `power_on_hours` | Total power-on hours (odometer) |
| `hours_in_use` | Running hours (odometer) |
| `total_cycles` | Total cycle count (odometer) |
| `remote_enabled` | Remote control enabled |
| `time_remaining` | Estimated time remaining (seconds) |
| `online` | Online status |
| `end_time` | Estimated end time (for timer-bar-card) |

### Washer

All dryer attributes plus:

| Attribute | Description |
|-----------|-------------|
| `door_locked` | Door locked status |
| `drawer_open` | Dispenser drawer open status |
| `need_clean` | Clean reminder status |
| `delay_time` | Delay time setting |
| `delay_remaining` | Delay time remaining |
| `rinsing` | Rinsing status |
| `draining` | Draining status |
| `filling` | Filling status |
| `spinning` | Spinning status |
| `soaking` | Soaking status |
| `sensing` | Sensing status |
| `washing` | Washing status |
| `add_garment` | Add garment status |
| `spin_speed` | Spin speed setting |
| `soil_level` | Soil level setting |
| `dispense_enable` | Bulk dispenser enabled |
| `dispense_level` | Bulk dispenser level |
| `dispense_concentration` | Bulk dispenser concentration |

---

## Usage examples

### Timer bar card

Compatible with [timer-bar-card](https://github.com/rianadon/timer-bar-card):

```yaml
type: custom:timer-bar-card
entity: sensor.maytag_dryer_xxxxxxx
bar_width: 35%
active_state:
  - Running
```

### Automation — notify when dryer is done

```yaml
alias: Dryer Done
description: Notify when the dryer finishes
trigger:
  - platform: state
    entity_id: sensor.maytag_dryer_xxxxx
    to:
      - Cycle Complete
      - Wrinkle Prevent
condition: []
action:
  - service: notify.mobile_app_xxxxx
    data:
      message: Dryer is done!
mode: single
```

### Template sensor for an attribute

```yaml
template:
  - sensor:
      - name: "Dryer Temperature Setting"
        state: "{{ state_attr('sensor.maytag_dryer_xxxx', 'temperature') }}"
```

### Entities card showing attributes

```yaml
type: entities
entities:
  - type: attribute
    entity: sensor.maytag_dryer_xxx
    attribute: cycle_name
    name: Cycle
  - type: attribute
    entity: sensor.maytag_dryer_xxx
    attribute: time_remaining
    name: Time Remaining
```

---

## Troubleshooting

**"Data Update Failed" or missing attributes**

Some models do not report all fields. The integration now handles missing fields gracefully — they will appear as `null` in the attributes rather than crashing the update. If you see a specific attribute always null, your model may not support it.

**Authentication errors**

If your credentials expire, Home Assistant will show a notification prompting you to re-authenticate. Click it and enter your updated credentials.

**Reconfiguring SAIDs**

Go to **Settings → Devices & Services → Maytag Dryer → Configure** to update your SAIDs or credentials without removing the integration.

---

## Migrating from v1.x

v2.0 switches from YAML platform configuration to config entries (GUI setup). To migrate:

1. Update the integration via HACS
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → Maytag Dryer**
4. Enter your credentials and SAIDs
5. Remove the old `platform: maytag_dryer` block from your `configuration.yaml`

**Attribute name changes from v1.x:**

| Old name | New name |
|----------|----------|
| `modelNumber` | `model_number` |
| `applianceid` | `appliance_id` |
| `lastsynced` | `last_synced` |
| `lastmodified` | `last_modified` |
| `dooropen` | `door_open` |
| `cyclename` | `cycle_name` |
| `cycleid` | `cycle_id` |
| `manualdrytime` | `manual_dry_time` |
| `drynesslevel` | `dryness_level` |
| `poweronhours` | `power_on_hours` |
| `hoursinuse` | `hours_in_use` |
| `totalcycles` | `total_cycles` |
| `remoteenabled` | `remote_enabled` |
| `timeremaining` | `time_remaining` |
| `doorlocked` | `door_locked` |
| `draweropen` | `drawer_open` |
| `needclean` | `need_clean` |
| `delaytime` | `delay_time` |
| `delayremaining` | `delay_remaining` |
| `addgarmet` | `add_garment` |
| `spinspeed` | `spin_speed` |
| `soillevel` | `soil_level` |
| `oweronhours` | `power_on_hours` (also fixed the typo) |
