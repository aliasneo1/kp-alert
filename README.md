# Kp Alert

Sends push notifications to your phone when the geomagnetic Kp index rises above 3.5. Built on NOAA's real-time data, GitHub Actions (free), and ntfy.sh (free, no account needed).

## How it works

- Polls [NOAA's 1-minute Kp feed](https://services.swpc.noaa.gov/json/planetary_k_index_1m.json) every 15 minutes via GitHub Actions
- Sends a push notification on the first crossing above Kp 3.5, then escalates at each integer band (4, 5, 6, 7, 8, 9)
- Sends an all-clear when Kp drops back below 3.5
- One notification per transition — no spam during sustained storms

## Alert levels

| Kp range | Band | Level |
|---|---|---|
| ≤ 3.5 | 0 | Quiet — no alert |
| 3.5–4 | 3 | Pre-storm watch |
| 4–5 | 4 | Elevated / G0 |
| 5–6 | 5 | G1 Minor storm |
| 6–7 | 6 | G2 Moderate storm |
| 7–8 | 7 | G3 Strong storm |
| 8–9 | 8 | G4 Severe storm |
| 9 | 9 | G5 Extreme storm |

## Setup

### 1. Phone — install ntfy

1. Install the **ntfy** app ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))
2. Subscribe to a topic — make up a long random string e.g. `kp-alerts-abc123xyz`
3. Test: open `https://ntfy.sh/<your-topic>` in a browser, send a message, your phone should ding

The topic name is your only credential on the free tier — treat it like a password.

### 2. GitHub — add the secret

1. Fork or clone this repo
2. Go to **Settings → Secrets and variables → Actions**
3. Add a secret named `NTFY_TOPIC` with your topic string as the value

### 3. Verify

Go to **Actions → Kp Alert → Run workflow** to trigger a manual run. Check the logs — you should see the current Kp printed and either "No alert needed" or a notification fired.

## Running locally

```bash
pip install requests
NTFY_TOPIC=your-topic python kp_alert.py
```

To simulate a storm without waiting for real activity, set `last_alert_band` to `0` in `state.json` and temporarily lower the threshold in `kp_to_band()`.

## Files

| File | Purpose |
|---|---|
| `kp_alert.py` | Main script — fetch, decide, notify |
| `state.json` | Persists last alerted band between runs |
| `.github/workflows/kp.yml` | Runs every 15 min, commits state changes |

## Cost

$0. GitHub Actions gives unlimited free minutes on public repos. ntfy.sh free tier handles this volume easily.
