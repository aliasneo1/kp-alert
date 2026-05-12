# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

Two independent push-notification systems running on free GitHub Actions + ntfy.sh. No server, no database — state lives in `state.json` (for the Kp alert) and is committed back to the repo after each alert.

1. **Kp Alert** — polls NOAA every 15 minutes; notifies when geomagnetic Kp crosses thresholds (`kp_alert.py` + `.github/workflows/kp.yml`)
2. **Panchanga Alert** — daily 7 AM IST; notifies on Sashthi, Ekadashi, Pushya Nakshatra, or Chandrashtama (`panchanga_alert.py` + `.github/workflows/panchanga.yml`)

## Running locally

```bash
# Kp Alert
pip install requests
NTFY_TOPIC=your-topic python kp_alert.py

# Panchanga Alert
pip install requests pyswisseph
NTFY_TOPIC=your-topic python panchanga_alert.py
```

To simulate a Kp storm transition without waiting for real activity, edit `state.json` by hand and/or set `KP_THRESHOLD` below the current Kp.

## Architecture

### `kp_alert.py`

Single-file script, runs top to bottom:
1. Fetches the 1-minute Kp feed from `https://services.swpc.noaa.gov/json/planetary_k_index_1m.json` (list of dicts).
2. **Uses `estimated_kp` (float, 0.33 steps), NOT `kp_index` (rounded int)**. The integer field flips at every boundary and is noisy.
3. **Returns the max over the last 30 minutes**, not the latest single reading. This is critical — NOAA resets `estimated_kp` to 0 at the start of every 3-hour window (00, 03, 06, 09, 12, 15, 18, 21 UTC). A naive read at the boundary would fire a false all-clear.
4. Reads `state.json` for `last_alert_band` (int, 0 = quiet).
5. `kp_to_band()`: 0 if Kp ≤ `KP_THRESHOLD` (default 3.5, configurable), else `floor(Kp)`.
6. Compares current band vs last band → up-alert, escalation, all-clear, or silent.
7. POSTs to `https://ntfy.sh/<NTFY_TOPIC>` with `Title`, `Priority`, `Tags`, `Click` headers. **Headers must be ASCII** — use `-`, not em-dash `—` (HTTP headers reject non-latin-1).
8. Writes updated `state.json` only when an alert fires.

### `panchanga_alert.py`

Single-file script using `pyswisseph` (Swiss Ephemeris) with Lahiri ayanamsa:
1. Computes today's local sunrise at configured (lat, lon) using `swe.rise_trans`.
2. At that sunrise moment, computes sun and moon sidereal longitudes (`FLG_SIDEREAL`).
3. **Tithi** = `floor((moon_lon - sun_lon) % 360 / 12) + 1` → 1-30. Tithi 1-15 = Shukla Paksha, 16-30 = Krishna Paksha.
4. **Nakshatra** = `floor(moon_lon / (360/27)) + 1` → 1-27.
5. Fires alert if any match: Sashthi (tithi 6/21), Ekadashi (tithi 11/26), Pushya (nakshatra 8), or Chandrashtama (nakshatra == 8th-from-janma, inclusive, for any configured janma).
6. **pyswisseph 2.x API quirk**: `swe.rise_trans(jd, body, rsmi_flags, (lon, lat, alt))` — flags is 3rd arg, geopos is a tuple. The pre-2.x positional form `rise_trans(jd, body, lon, lat, alt, ...)` raises `TypeError: float cannot be interpreted as integer`.

### `state.json`

Single key `last_alert_band`. The only persistence between runs (Kp only — panchanga is stateless). Gets committed back to the repo by the Kp workflow after each alert.

### `.github/workflows/kp.yml`

- Cron: `7-59/15 * * * *` (runs at :07, :22, :37, :52 — offset from `*/15` to dodge GitHub's documented high-load periods at the top of the hour).
- Permissions: `contents: write` so the workflow can commit `state.json` updates.
- Final step: `git diff --quiet state.json || (git add state.json && git commit && git push)` — only commits when state actually changed.

### `.github/workflows/panchanga.yml`

- Cron: `30 1 * * *` (= 07:00 IST). GitHub may drift; typically fires by 07:10-07:30 IST.
- No state, no commit step. Stateless idempotent check.

## Alert logic — Kp

| Condition | Action |
|---|---|
| `current_band > last_band` and `last_band == 0` | First alert — "activity rising" |
| `current_band > last_band` and `last_band > 0` | Escalation alert |
| `current_band == 0` and `last_band > 0` | All-clear |
| Otherwise | Silent |

Band → storm level: 3=pre-storm watch, 4=elevated/G0, 5=G1, 6=G2, 7=G3, 8=G4, 9=G5. Priority/tags escalate at band ≥ 7.

## Alert logic — Panchanga

All checks run independently; multiple matches on the same day produce one notification listing all of them.

| Trigger | Match condition |
|---|---|
| Sashthi | tithi ∈ {6, 21} |
| Ekadashi | tithi ∈ {11, 26} |
| Pushya Nakshatra | nakshatra == 8 |
| Chandrashtama | nakshatra == `((janma - 1 + 7) % 27) + 1` for any janma in `JANMA_NAKSHATRA` |

## Required secret

`NTFY_TOPIC` must be set as a GitHub Actions repository **Secret** (Settings → Secrets and variables → Actions → Secrets). The ntfy topic string acts as the auth token — keep it private.

## Optional variables (Settings → Variables)

| Variable | Default | Used by |
|---|---|---|
| `KP_THRESHOLD` | `3.5` | kp_alert.py |
| `PANCHANGA_LAT` | `13.0827` (Chennai) | panchanga_alert.py |
| `PANCHANGA_LON` | `80.2707` (Chennai) | panchanga_alert.py |
| `PANCHANGA_TZ` | `5.5` (IST) | panchanga_alert.py |
| `JANMA_NAKSHATRA` | `22,17` (Shravana, Anuradha) | panchanga_alert.py |

Workflow files reference these as `${{ vars.NAME || 'default' }}` so unset variables fall back gracefully.

## Gotchas worth knowing

- **GitHub cron is best-effort**, especially on the hour. Already mitigated via offset cron `7-59/15`.
- **ntfy headers must be latin-1** — non-ASCII characters like `—` (em-dash) cause `UnicodeEncodeError`. Use plain `-`.
- **`vars.X` vs `secrets.X`** — repo Variables (non-sensitive) are separate from Secrets in the GitHub UI. `KP_THRESHOLD` is a Variable, not a Secret.
- **Editing the workflow file resets GitHub's internal cron registration timer.** A brand-new scheduled workflow can take up to ~1 hour before the first auto-run; every push to `kp.yml`/`panchanga.yml` may delay the next scheduled fire.
- **Public repos have scheduled workflows auto-disabled after 60 days of repo inactivity.** Any commit resets the clock.
