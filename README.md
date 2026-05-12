# Solar & Panchanga Alerts

Two independent push-notification systems running on the same free GitHub Actions + ntfy.sh stack:

1. **Kp Alert** — geomagnetic storm notifications (polls every 15 min)
2. **Panchanga Alert** — daily 7 AM IST notification on Sashthi, Ekadashi, Pushya Nakshatra, or Chandrashtama for configured janma nakshatras

No server, no database, no recurring cost.

---

## 1. Kp Alert

Sends push notifications when the geomagnetic Kp index rises above a configurable threshold (default 3.5).

### How it works

- Polls [NOAA's 1-minute Kp feed](https://services.swpc.noaa.gov/json/planetary_k_index_1m.json) every 15 minutes
- Uses `estimated_kp` (the smoother 0.33-step float) and takes the **max over the last 30 minutes** to ride through NOAA's 3-hour boundary resets
- First crossing above threshold → "activity rising" alert
- Each integer band crossing (4, 5, 6, 7, 8, 9) → escalation alert
- Drops back below threshold → all-clear
- One notification per transition — no spam during sustained storms

### Alert levels

| Kp range | Band | Level |
|---|---|---|
| ≤ threshold | 0 | Quiet — no alert |
| 3.5–4 | 3 | Pre-storm watch |
| 4–5 | 4 | Elevated / G0 |
| 5–6 | 5 | G1 Minor storm |
| 6–7 | 6 | G2 Moderate storm |
| 7–8 | 7 | G3 Strong storm |
| 8–9 | 8 | G4 Severe storm |
| 9 | 9 | G5 Extreme storm |

### Running locally

```bash
pip install requests
NTFY_TOPIC=your-topic python kp_alert.py

# Override the threshold
NTFY_TOPIC=your-topic KP_THRESHOLD=4.0 python kp_alert.py
```

To simulate a storm without waiting for real activity, set `last_alert_band` to `0` in `state.json` and set `KP_THRESHOLD` to a value below the current Kp.

---

## 2. Panchanga Alert

Daily 7 AM IST notification when the day is auspicious (Sashthi/Ekadashi/Pushya) or significant for your janma nakshatra (Chandrashtama).

### What it computes

Using Swiss Ephemeris + Lahiri ayanamsa, evaluates **tithi and nakshatra at local sunrise**, then alerts if any of the following match:

| Match | Trigger |
|---|---|
| Sashthi | Tithi 6 (Shukla) or 21 (Krishna) |
| Ekadashi | Tithi 11 (Shukla) or 26 (Krishna) |
| Pushya Nakshatra | Nakshatra #8 |
| Chandrashtama | Moon in the 8th nakshatra (inclusive) from each configured janma nakshatra |

Defaults: janma nakshatras = **Shravana (22), Anuradha (17)** → fires Chandrashtama on **Bharani (#2)** and **Shatabhisha (#24)** respectively.

Silent days send no notification.

### Running locally

```bash
pip install requests pyswisseph
NTFY_TOPIC=your-topic python panchanga_alert.py

# Override defaults
NTFY_TOPIC=your-topic JANMA_NAKSHATRA=22,17,4 PANCHANGA_LAT=12.97 PANCHANGA_LON=77.59 python panchanga_alert.py
```

---

## Setup (one-time)

### 1. Phone — install ntfy

1. Install the **ntfy** app ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))
2. Subscribe to a topic — pick a long random string, e.g. `kp-alerts-abc123xyz`
3. Test: open `https://ntfy.sh/<your-topic>` in a browser, send a message, your phone should ding

The topic name is your only credential on the free tier — treat it like a password.

### 2. GitHub — add the secret

1. Fork or clone this repo
2. Go to **Settings → Secrets and variables → Actions**
3. Under the **Secrets** tab, add `NTFY_TOPIC` with your ntfy topic string as the value

### 3. (Optional) Override defaults via Variables

Same screen, **Variables** tab. None are required — defaults work out of the box.

| Variable | Default | Purpose |
|---|---|---|
| `KP_THRESHOLD` | `3.5` | Minimum Kp to trigger first alert |
| `PANCHANGA_LAT` | `13.0827` | Latitude for sunrise calc (Chennai) |
| `PANCHANGA_LON` | `80.2707` | Longitude for sunrise calc (Chennai) |
| `PANCHANGA_TZ` | `5.5` | Local timezone offset in hours (IST) |
| `JANMA_NAKSHATRA` | `22,17` | Comma-separated nakshatra IDs for Chandrashtama (1=Ashwini, 22=Shravana, 17=Anuradha, …) |

### 4. Verify

- **Actions → Kp Alert → Run workflow** — should print current Kp and either fire an alert or say "No alert needed"
- **Actions → Panchanga Alert → Run workflow** — should print today's tithi and nakshatra, alert if any match

## Files

| File | Purpose |
|---|---|
| `kp_alert.py` | Geomagnetic Kp script — fetch, decide, notify |
| `state.json` | Persists last alerted Kp band between runs |
| `panchanga_alert.py` | Daily panchanga script — compute tithi/nakshatra at sunrise, notify on match |
| `.github/workflows/kp.yml` | Kp workflow, runs every 15 min, commits state changes |
| `.github/workflows/panchanga.yml` | Panchanga workflow, runs daily at 01:30 UTC (07:00 IST) |

## Cost

$0. GitHub Actions gives unlimited free minutes on public repos. ntfy.sh free tier handles this volume easily.
