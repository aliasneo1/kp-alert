"""Daily panchanga alert: notify on Sashthi, Ekadashi, or Pushya Nakshatra.

Computes tithi (lunar day) and nakshatra at local sunrise using Swiss Ephemeris
with Lahiri ayanamsa (standard Indian convention). Sends ntfy alert only when
one of the target days is matched.
"""

import datetime
import os
import sys

import requests
import swisseph as swe

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
LATITUDE = float(os.environ.get("PANCHANGA_LAT", "13.0827"))   # Chennai default
LONGITUDE = float(os.environ.get("PANCHANGA_LON", "80.2707"))
TIMEZONE_HOURS = float(os.environ.get("PANCHANGA_TZ", "5.5"))  # IST default

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

TITHI_NAMES = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Sashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dvadashi",
    "Trayodashi", "Chaturdashi", "Purnima_or_Amavasya",
]


def sunrise_jd(local_date: datetime.date, lat: float, lon: float) -> float:
    """Julian Day (UT) of sunrise on local_date at (lat, lon)."""
    jd_start = swe.julday(local_date.year, local_date.month, local_date.day, 0.0)
    flags = swe.CALC_RISE | swe.BIT_DISC_CENTER
    res, tret = swe.rise_trans(jd_start, swe.SUN, lon, lat, 0.0, 0.0, flags)
    if res != 0:
        raise RuntimeError(f"swe.rise_trans failed (code {res})")
    return tret[0]


def tithi_at(jd: float):
    """Return (number 1-30, name, paksha) for the tithi prevailing at jd."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sun_lon = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0]
    moon_lon = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0]
    diff = (moon_lon - sun_lon) % 360.0
    tithi_num = int(diff / 12.0) + 1  # 1..30
    if tithi_num <= 15:
        return tithi_num, TITHI_NAMES[tithi_num - 1], "Shukla"
    return tithi_num, TITHI_NAMES[tithi_num - 16], "Krishna"


def nakshatra_at(jd: float):
    """Return (number 1-27, name) for the nakshatra at jd."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    moon_lon = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0]
    nak_num = int(moon_lon / (360.0 / 27.0)) + 1  # 1..27
    return nak_num, NAKSHATRAS[nak_num - 1]


def send_ntfy(topic: str, title: str, message: str) -> None:
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": "3",
        "Tags": "om,sparkles",
    }
    resp = requests.post(url, data=message.encode(), headers=headers, timeout=10)
    resp.raise_for_status()
    print(f"Sent: {title}")


def main() -> None:
    if not NTFY_TOPIC:
        print("ERROR: NTFY_TOPIC not set.", file=sys.stderr)
        sys.exit(1)

    tz = datetime.timezone(datetime.timedelta(hours=TIMEZONE_HOURS))
    today = datetime.datetime.now(tz).date()

    jd = sunrise_jd(today, LATITUDE, LONGITUDE)
    tithi_num, tithi_name, paksha = tithi_at(jd)
    nak_num, nak_name = nakshatra_at(jd)

    print(f"Date: {today}")
    print(f"Tithi: #{tithi_num} {paksha} {tithi_name}")
    print(f"Nakshatra: #{nak_num} {nak_name}")

    matches = []
    if tithi_num in (6, 21):
        matches.append(f"Sashthi ({paksha} Paksha)")
    if tithi_num in (11, 26):
        matches.append(f"Ekadashi ({paksha} Paksha)")
    if nak_num == 8:
        matches.append("Pushya Nakshatra")

    if not matches:
        print("No match today, no alert sent.")
        return

    title = "Panchanga: " + ", ".join(matches)
    msg = (
        f"{', '.join(matches)}\n\n"
        f"Tithi: {paksha} {tithi_name}\n"
        f"Nakshatra: {nak_name}\n"
        f"Date: {today.isoformat()}"
    )
    send_ntfy(NTFY_TOPIC, title, msg)


if __name__ == "__main__":
    main()
