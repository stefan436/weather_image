import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

# ------------------ Konfiguration ------------------
STATION_ID = "P755"  # Beispiel: Aschheim P755 Muenchen Stadt 10865
BASE_URL = f"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{STATION_ID}/kml/MOSMIX_L_LATEST_{STATION_ID}.kmz"

PERIODS = [
    {"name": "Früh", "startHour": 6, "endHour": 10},
    {"name": "Mittag", "startHour": 10, "endHour": 14},
    {"name": "Nachmittag", "startHour": 14, "endHour": 18},
    {"name": "Abend", "startHour": 18, "endHour": 22},
    {"name": "Spät Abends", "startHour": 22, "endHour": 2},
    {"name": "Nacht", "startHour": 2, "endHour": 6},
]

PERIOD_ORDER = ["Nacht", "Früh", "Mittag", "Nachmittag", "Abend", "Spät Abends"]

# Mapping Wettercode → Label + Icon-URL (Platzhalter)
WW_ICON_MAP = {
    # Gewitter
    95: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/thunderstorm.png", "label": "Gewitter mit Regen/Schnee"},

    # gefrierender Sprühregen/Regen
    57: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy freeting rain.png", "label": "Starker gefrierender Sprühregen"},
    56: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light freezing rain.png", "label": "Leichter gefrierender Sprühregen"},
    67: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy freeting rain.png", "label": "Starker gefrierender Regen"},
    66: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light freezing rain.png", "label": "Leichter gefrierender Regen"},

    # Schnee/Schneeschauer
    86: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy snow.png", "label": "Starker Schneeschauer"},
    85: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light snow.png", "label": "Leichter Schneeschauer"},
    84: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy sleet.png", "label": "Starker Schneeregenschauer"},
    83: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light sleet.png", "label": "Leichter Schneeregenschauer"},
    75: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy snow.png", "label": "Starker Schneefall"},
    73: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/moderate snow.png", "label": "Mäßiger Schneefall"},
    71: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light snow.png", "label": "Leichter Schneefall"},
    69: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy sleet.png", "label": "Starker Schneeregen"},
    68: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light sleet.png", "label": "Leichter Schneeregen"},

    # Regen/Schauer
    82: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy rain.png", "label": "Heftiger Regenschauer"},
    81: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/moderate rain.png", "label": "Starker Regenschauer"},
    80: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light rain.png", "label": "Leichter Regenschauer"},
    65: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy rain.png", "label": "Starker Regen"},
    63: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/moderate rain.png", "label": "Mäßiger Regen"},
    61: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light rain.png", "label": "Leichter Regen"},

    # Sprühregen
    55: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/heavy rain.png", "label": "Starker Sprühregen"},
    53: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/moderate rain.png", "label": "Mäßiger Sprühregen"},
    51: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/light rain.png", "label": "Leichter Sprühregen"},

    # Nebel
    49: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/fog.png", "label": "Nebel mit Reif"},
    45: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/fog.png", "label": "Nebel"},

    # Bewölkung
    3: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/total cloud cover.png", "label": "Bewölkung zunehmend"},
    2: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/medium cloud cover.png", "label": "Bewölkung unverändert"},
    1: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/low cloud cover.png", "label": "Bewölkung abnehmend"},
    0: {"icon": "https://raw.githubusercontent.com/stefan436/weather_image/main/docs/icons/clear-day-night.png", "label": "Klarer Himmel"}
}

def load_kmz(url):
    r = requests.get(url)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    kml_file = [f for f in z.namelist() if f.endswith(".kml")][0]
    return z.read(kml_file).decode("utf-8")


def parse_kml(kml_text):
    DWDNS = "{https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd}"
    xml_root = ET.fromstring(kml_text)
    timeSteps = [t.text.strip() for t in xml_root.findall(f".//{DWDNS}TimeStep")]
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    for placemark in xml_root.findall(".//kml:Placemark", ns):
        name_el = placemark.find("kml:name", ns)
        description_el = placemark.find("kml:description", ns)
        name = name_el.text.strip() if name_el is not None else ""
        description = description_el.text.strip() if description_el is not None else ""

    forecasts = {}
    for fc in xml_root.findall(f".//{DWDNS}Forecast"):
        elName = fc.attrib.get(f"{DWDNS}elementName") or fc.attrib.get("elementName")
        raw_values = [v.text for v in fc.findall(f"{DWDNS}value")]
        values = raw_values[0].split() if len(raw_values) == 1 else raw_values
        forecasts[elName] = values

    return timeSteps, forecasts, name, description


def build_summary(timeSteps, forecasts, name, description):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    entries = []
    for i, ts in enumerate(timeSteps):
        dateObj = datetime.fromisoformat(ts)
        code_raw = forecasts.get("ww", [None] * len(timeSteps))[i]
        try:
            code = int(float(code_raw)) if code_raw and code_raw != "-" else None
        except ValueError:
            code = None
        entries.append({"timestamp": dateObj, "hour": dateObj.hour, "code": code, "index": i})

    future_entries = [e for e in entries if e["timestamp"] >= now]

    daysMap = {}
    for entry in future_entries:
        period = None
        for p in PERIODS:
            if p["startHour"] < p["endHour"]:
                if p["startHour"] <= entry["hour"] < p["endHour"]:
                    period = p
                    break
            else:
                if entry["hour"] >= p["startHour"] or entry["hour"] < p["endHour"]:
                    period = p
                    break
        if not period:
            continue

        groupDate = entry["timestamp"]
        if period["startHour"] > period["endHour"] and entry["hour"] < period["endHour"]:
            groupDate -= timedelta(days=1)

        dayIso = groupDate.strftime("%Y-%m-%d")
        today = datetime.now().date()
        diffDays = (groupDate.date() - today).days
        displayDate = "Heute" if diffDays == 0 else "Morgen" if diffDays == 1 else "Übermorgen" if diffDays == 2 else groupDate.strftime("%a, %d.%m.")

        if dayIso not in daysMap:
            daysMap[dayIso] = {"displayDate": displayDate, "groups": {}}
        if period["name"] not in daysMap[dayIso]["groups"]:
            daysMap[dayIso]["groups"][period["name"]] = []
        daysMap[dayIso]["groups"][period["name"]].append(entry)

    result = {
        "name": name,
        "description": description,
        "days": {}
    }

    for dayIso, dayData in daysMap.items():
        result["days"][dayData["displayDate"]] = []
        for periodName in PERIOD_ORDER:
            entries = dayData["groups"].get(periodName, [])
            if not entries:
                continue

            ww_values_in_period = [e["code"] for e in entries if e["code"] is not None]
            if not ww_values_in_period:
                continue

            dominantCode = max(ww_values_in_period)

            # Speziallogik für Bewölkung (Codes 0–3)
            if dominantCode in [0, 1, 2, 3]:
                # Berechne durchschnittliche Bewölkung (Neff)
                cloud_vals = []
                for e in entries:
                    idx = e["index"]
                    neff = forecasts.get("Neff", [None])[idx]
                    try:
                        if neff and neff != "-":
                            cloud_vals.append(float(neff))
                    except ValueError:
                        continue

                if cloud_vals:
                    avg_cloud = sum(cloud_vals) / len(cloud_vals)
                    # Mapping wie im JS
                    if avg_cloud <= 20:
                        dominantCode = 0
                    elif avg_cloud <= 50:
                        dominantCode = 1
                    elif avg_cloud <= 80:
                        dominantCode = 2
                    else:
                        dominantCode = 3

            info = WW_ICON_MAP.get(dominantCode, {"icon": "URL/unknown.png", "label": "unbekannt"})

            timestep_entries = []
            ww_vals, ttt_vals, rr1_vals, neff_vals = [], [], [], []

            for e in entries:
                idx = e["index"]
                ww = forecasts.get("ww", [None])[idx]
                ttt = forecasts.get("TTT", [None])[idx]
                rr1 = forecasts.get("RR1c", [None])[idx]
                neff = forecasts.get("Neff", [None])[idx]

                try:
                    if ww and ww != "-": ww_vals.append(float(ww))
                    if ttt and ttt != "-": ttt_vals.append(float(ttt))
                    if rr1 and rr1 != "-": rr1_vals.append(float(rr1))
                    if neff and neff != "-": neff_vals.append(float(neff))
                except ValueError:
                    pass
                
                try:
                    ttt_c = round(float(ttt) - 273.15, 1) if ttt and ttt != "-" else None
                except ValueError:
                    ttt_c = None


                timestep_entries.append({
                    "timestamp": e["timestamp"].isoformat(),
                    "WW": ww,
                    "TTT": ttt_c,
                    "RR1c": rr1,
                    "Neff": neff
                })

            def avg(lst):
                return round(sum(lst) / len(lst), 1) if lst else None

            avg_data = {
                "WW": avg(ww_vals),
                "TTT": round(avg(ttt_vals) - 273.15, 1) if ttt_vals else None,
                "RR1c": round(sum(rr1_vals), 1) if rr1_vals else None,  # kumulierte Niederschlagsmenge
                "Neff": avg(neff_vals)
            }



            result["days"][dayData["displayDate"]].append({
                "period": periodName,
                "icon": info["icon"],
                "label": info["label"],
                "avg": avg_data,
                "details": timestep_entries
            })

    # Zusätzliche Daten im Ergebnis ergänzen
    result["timeSteps"] = [datetime.fromisoformat(ts).isoformat() for ts in timeSteps]
    result["parameters"] = {
        "WW": forecasts.get("ww", []),
        "TTT": forecasts.get("TTT", []),
        "RR1c": forecasts.get("RR1c", []),
        "Neff": forecasts.get("Neff", [])
    }

    return result


def main():
    kml_text = load_kmz(BASE_URL)
    timeSteps, forecasts, name, description = parse_kml(kml_text)
    summary = build_summary(timeSteps, forecasts, name, description)

    with open("docs/data/weather-summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
