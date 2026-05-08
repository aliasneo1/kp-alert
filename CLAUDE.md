# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

Polls NOAA's 1-minute Kp index every 15 minutes via GitHub Actions and sends push notifications to a phone via ntfy.sh when geomagnetic activity crosses thresholds. No server, no database — state is persisted by committing `state.json` back to the repo after each alert.

## Running locally

```bash
pip install requests
NTFY_TOPIC=your-topic python kp_alert.py
```

To simulate a storm transition without waiting for real Kp activity, edit `state.json` by hand before running:
- Set `last_alert_band` to `0` and temporarily lower the threshold in `kp_to_band()` to trigger an up-alert
- Set `last_alert_band` to `5` and lower Kp threshold to trigger an all-clear

## Architecture

**`kp_alert.py`** — single-file script, runs top to bottom:
1. Fetches latest Kp from `https://services.swpc.noaa.gov/json/planetary_k_index_1m.json` (list of dicts, `kp_index` key)
2. Reads `state.json` for `last_alert_band` (int, 0 = quiet)
3. `kp_to_band()` maps Kp float → integer band: 0 if Kp ≤ 3.5, else `floor(Kp)`
4. Compares current band vs last band to decide: up-alert, escalation, all-clear, or silent
5. POSTs to `https://ntfy.sh/<NTFY_TOPIC>` with ntfy headers (Title, Priority, Tags, Click)
6. Writes updated `state.json` only when an alert fires

**`state.json`** — single key `last_alert_band`. The only persistence between runs. Gets committed back to the repo by the workflow after each alert.

**`.github/workflows/kp.yml`** — runs on `*/15 * * * *` cron and `workflow_dispatch`. Checks out repo, runs script, commits `state.json` if changed.

## Alert logic

| Condition | Action |
|---|---|
| `current_band > last_band` and `last_band == 0` | First alert — "activity rising" |
| `current_band > last_band` and `last_band > 0` | Escalation alert |
| `current_band == 0` and `last_band > 0` | All-clear |
| Otherwise | Silent |

Band → storm level: 3=pre-storm watch, 4=elevated/G0, 5=G1, 6=G2, 7=G3, 8=G4, 9=G5. Priority and tags escalate at band ≥ 7.

## Required secret

`NTFY_TOPIC` must be set as a GitHub Actions repository secret (Settings → Secrets → Actions). The ntfy topic string acts as the auth token — keep it private.
