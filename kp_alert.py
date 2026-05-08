import json
import math
import os
import sys
from pathlib import Path

import requests

NOAA_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
STATE_FILE = Path(__file__).parent / "state.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")


def fetch_latest_kp() -> float:
    resp = requests.get(NOAA_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Each entry is [time_tag, kp_index, ...]; last entry is most recent
    return float(data[-1][1])


def read_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_alert_band": 0}


def write_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def kp_to_band(kp: float) -> int:
    """0 when kp <= 3.5, else floor(kp). So 3.67->3, 4.33->4, 5.67->5, 9->9."""
    if kp <= 3.5:
        return 0
    return math.floor(kp)


def noaa_storm_level(band: int) -> str:
    levels = {3: "pre-storm watch", 4: "elevated/G0", 5: "G1 Minor", 6: "G2 Moderate", 7: "G3 Strong", 8: "G4 Severe", 9: "G5 Extreme"}
    return levels.get(band, f"Kp {band}")


def send_ntfy(topic: str, title: str, message: str, priority: int = 4, tags: str = "rotating_light") -> None:
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": tags,
        "Click": "https://www.spaceweatherlive.com/en/solar-activity/k-index.html",
    }
    resp = requests.post(url, data=message.encode(), headers=headers, timeout=10)
    resp.raise_for_status()
    print(f"Sent: {title}")


def main() -> None:
    if not NTFY_TOPIC:
        print("ERROR: NTFY_TOPIC environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    kp = fetch_latest_kp()
    print(f"Latest Kp: {kp}")

    state = read_state()
    last_band = state["last_alert_band"]
    current_band = kp_to_band(kp)

    print(f"Current band: {current_band}, Last alerted band: {last_band}")

    if current_band > last_band:
        storm = noaa_storm_level(current_band)
        if last_band == 0:
            title = f"Geomagnetic activity rising — Kp {kp:.2f}"
            msg = f"Kp index has crossed 3.5. Current level: {kp:.2f} ({storm}). Aurora possible at high latitudes."
        else:
            title = f"Storm escalating — Kp {kp:.2f} ({storm})"
            msg = f"Kp index rising. Now at {kp:.2f} — {storm}. Check sky conditions."

        # Use louder tags for severe storms
        tags = "rotating_light" if current_band < 7 else "rotating_light,boom"
        priority = 4 if current_band < 7 else 5

        send_ntfy(NTFY_TOPIC, title, msg, priority=priority, tags=tags)
        state["last_alert_band"] = current_band
        write_state(state)

    elif current_band == 0 and last_band > 0:
        title = "Geomagnetic storm over — All clear"
        msg = f"Kp index has dropped back to {kp:.2f}. Storm has ended."
        send_ntfy(NTFY_TOPIC, title, msg, priority=3, tags="white_check_mark")
        state["last_alert_band"] = 0
        write_state(state)

    else:
        print("No alert needed.")


if __name__ == "__main__":
    main()
