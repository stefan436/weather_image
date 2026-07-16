import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# =====================================================================
# ------------------------- KONFIGURATION -----------------------------
# =====================================================================

STATION_ID = "P755"  # DWD Stations-ID (z.B. P755 für Aschheim)

# URLs wie im Frontend: Erst L vom DWD, dann S vom eigenen Backend
MOSMIX_L_URL = f"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{STATION_ID}/kml/MOSMIX_L_LATEST_{STATION_ID}.kmz"
MOSMIX_S_JSON_PATH = f"./../index/data/Forecast/mosmix_s/{STATION_ID}.json"
OUTPUT_FILE = "./data/weather-summary.json"

# MOSMIX_S_JSON_PATH = f"/WWW/users/TUMid/weather_data/index/Forecast/mosmix_s/{STATION_ID}.json"
# OUTPUT_FILE = "/WWW/users/TUMid/weather_data/widget/weather-summary.json"

ICON_BASE_URL = "https://raw.githubusercontent.com/stefan436/Wetterinfo/main/docs/icons/"

# Schwellenwerte für die Bewölkung (unter 30 wolkenlos, bis 60 leicht, bis 80 mittel, drüber stark)
CLOUD_COVER_THRESHOLDS = [30, 60, 80]

PERIODS = [
    {"name": "Früh", "startHour": 6, "endHour": 10},
    {"name": "Mittag", "startHour": 10, "endHour": 14},
    {"name": "Nachmittag", "startHour": 14, "endHour": 18},
    {"name": "Abend", "startHour": 18, "endHour": 22},
    {"name": "Spät Abends", "startHour": 22, "endHour": 2},
    {"name": "Nacht", "startHour": 2, "endHour": 6},
]

PERIOD_ORDER = ["Nacht", "Früh", "Mittag", "Nachmittag", "Abend", "Spät Abends"]

WW_ICON_MAP = {
    95: "thunderstorm.png", 57: "heavy freeting rain.png", 56: "light freezing rain.png",
    67: "heavy freezing rain.png", 66: "light freezing rain.png", 86: "heavy snow.png",
    85: "light snow.png", 84: "heavy sleet.png", 83: "light sleet.png",
    75: "heavy snow.png", 73: "moderate snow.png", 71: "light snow.png",
    69: "heavy sleet.png", 68: "light sleet.png", 82: "heavy rain.png",
    81: "moderate rain.png", 80: "light rain.png", 65: "heavy rain.png",
    63: "moderate rain.png", 61: "light rain.png", 55: "heavy rain.png",
    53: "moderate rain.png", 51: "light rain.png", 49: "fog.png",
    45: "fog.png", 3: "total cloud cover.png", 2: "medium cloud cover.png",
    1: "low cloud cover.png", 0: "clear day.png",
}

WW_ICON_MAP_NIGHT = {
    0: "clear night.png",
    1: "low cloud cover night.png",
    2: "medium cloud cover night.png",
}

# =====================================================================
# ------------------------- LOGIK & PARSING ---------------------------
# =====================================================================

def load_mosmix_l():
    r = requests.get(MOSMIX_L_URL)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    kml_file = [f for f in z.namelist() if f.endswith(".kml")][0]
    return z.read(kml_file).decode("iso-8859-1")

def parse_kml_l(kml_text):
    DWDNS = "{https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd}"
    xml_root = ET.fromstring(kml_text)
    timeSteps = [t.text.strip() for t in xml_root.findall(f".//{DWDNS}TimeStep")]
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    placemark = xml_root.find(".//kml:Placemark", ns)
    if placemark is None:
        raise ValueError("Kein Placemark in der KML gefunden.")

    name = placemark.find("kml:name", ns).text.strip()
    description = placemark.find("kml:description", ns).text.strip()

    forecasts = {}
    needed_elements = ["ww", "Neff", "TTT", "wwP", "FF"]
    
    for fc in xml_root.findall(f".//{DWDNS}Forecast"):
        elName = fc.attrib.get(f"{DWDNS}elementName") or fc.attrib.get("elementName")
        if elName in needed_elements:
            raw_values = [v.text for v in fc.findall(f"{DWDNS}value")]
            values = raw_values[0].split() if len(raw_values) == 1 else raw_values
            # Leere Werte sicher zu None umwandeln
            forecasts[elName] = [float(v) if v != "-" else None for v in values]

    return timeSteps, forecasts, name, description

def merge_mosmix_s(timeSteps, forecasts):
    """Lädt die lokale MOSMIX S JSON und überschreibt die KML-Daten."""
    try:
        # Lokale Datei öffnen und JSON parsen
        with open(MOSMIX_S_JSON_PATH, "r", encoding="utf-8") as f:
            s_data = json.load(f)
        
        # Mapping der JSON-Zeitstempel (Index pro Timestamp)
        s_time_map = {}
        for idx, ts_str in enumerate(s_data.get("t", [])):
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            dt_s = datetime.fromisoformat(ts_str).astimezone(ZoneInfo("UTC"))
            s_time_map[int(dt_s.timestamp())] = idx

        # Überschreiben der existierenden L-Parameter mit S-Werten
        for param in forecasts.keys():
            if param in s_data.get("d", {}):
                s_values = s_data["d"][param]
                
                for l_idx, kml_ts in enumerate(timeSteps):
                    dt_l = datetime.strptime(kml_ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.000").replace(tzinfo=ZoneInfo("UTC"))
                    timestamp_l = int(dt_l.timestamp())
                    
                    s_idx = s_time_map.get(timestamp_l)
                    if s_idx is not None and s_idx < len(s_values) and s_values[s_idx] is not None:
                        forecasts[param][l_idx] = float(s_values[s_idx])
                        
        log("Lokale MOSMIX S Daten erfolgreich integriert.")
    except Exception as e:
        log(f"Konnte lokale MOSMIX S JSON nicht laden/mergen, nutze reine MOSMIX L Daten als Fallback. Grund: {e}")

def get_value(forecasts, param, index, convert_func=lambda x: x):
    """Hilfsfunktion zum sicheren Auslesen der vorbereiteten Arrays."""
    try:
        val = forecasts.get(param, [])[index]
        if val is not None:
            return convert_func(val)
    except IndexError:
        pass
    return None

def build_summary(timeSteps, forecasts, name, description):
    tz = ZoneInfo("Europe/Berlin")
    now = datetime.now(tz)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = []
    for i, ts in enumerate(timeSteps):
        dt_utc = datetime.strptime(ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.000").replace(tzinfo=ZoneInfo("UTC"))
        dt_local = dt_utc.astimezone(tz)
        
        # Shift um 1h zurück für Zeitraum-Beginn-Parameter
        shifted_dt = dt_local - timedelta(hours=1)

        if shifted_dt >= current_hour:
            code = get_value(forecasts, "ww", i, int)
            entries.append({
                "timestamp": shifted_dt,
                "hour": shifted_dt.hour,
                "code": code,
                "index": i
            })

    daysMap = {}
    for entry in entries:
        period = next((p for p in PERIODS if (
            (p["startHour"] <= entry["hour"] < p["endHour"]) if p["startHour"] < p["endHour"] 
            else (entry["hour"] >= p["startHour"] or entry["hour"] < p["endHour"])
        )), None)
        
        if not period: continue

        group_date = entry["timestamp"]
        if period["startHour"] > period["endHour"] and entry["hour"] < period["endHour"]:
            group_date -= timedelta(days=1)

        day_iso = group_date.strftime("%Y-%m-%d")
        group_midnight = group_date.replace(hour=0, minute=0, second=0, microsecond=0)
        diff_days = (group_midnight - today_midnight).days

        if diff_days == 0:
            display_date = "Heute"
        elif diff_days == 1:
            display_date = "Morgen"
        elif diff_days == 2:
            display_date = "Übermorgen"
        else:
            weekdays = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
            display_date = f"{weekdays[group_date.weekday()]} {group_date.strftime('%d.%m.')}"

        if day_iso not in daysMap:
            daysMap[day_iso] = {"displayDate": display_date, "groups": {}}
        if period["name"] not in daysMap[day_iso]["groups"]:
            daysMap[day_iso]["groups"][period["name"]] = []
        daysMap[day_iso]["groups"][period["name"]].append(entry)

    result = {
        "name": name,
        "description": description,
        "days": {}
    }

    for day_iso in sorted(daysMap.keys()):
        day_data = daysMap[day_iso]
        display_date = day_data["displayDate"]
        result["days"][display_date] = []

        for period_name in PERIOD_ORDER:
            period_entries = day_data["groups"].get(period_name, [])
            if not period_entries: continue

            valid_codes = [e["code"] for e in period_entries if e["code"] is not None]
            if not valid_codes: continue
            
            dominant_code = max(valid_codes)

            if dominant_code in [0, 1, 2, 3]:
                cloud_covers = []
                for e in period_entries:
                    prev_idx = e["index"] - 1
                    if prev_idx >= 0:
                        neff = get_value(forecasts, "Neff", prev_idx)
                        if neff is not None: cloud_covers.append(neff)
                
                if cloud_covers:
                    avg_cloud = sum(cloud_covers) / len(cloud_covers)
                    if avg_cloud <= CLOUD_COVER_THRESHOLDS[0]: dominant_code = 0
                    elif avg_cloud <= CLOUD_COVER_THRESHOLDS[1]: dominant_code = 1
                    elif avg_cloud <= CLOUD_COVER_THRESHOLDS[2]: dominant_code = 2
                    else: dominant_code = 3
                else:
                    dominant_code = None

            is_night = period_name in ["Abend", "Spät Abends", "Nacht"]
            if dominant_code is None:
                icon_file = "unknown.png"
            elif is_night and dominant_code <= 2:
                icon_file = WW_ICON_MAP_NIGHT.get(dominant_code, "unknown.png")
            else:
                icon_file = WW_ICON_MAP.get(dominant_code, "unknown.png")
            
            full_icon_url = f"{ICON_BASE_URL}{icon_file}"

            temps = []
            for e in period_entries:
                prev_idx = e["index"] - 1
                if prev_idx >= 0:
                    t = get_value(forecasts, "TTT", prev_idx, lambda x: x - 273.15)
                    if t is not None: temps.append(t)
            avg_temp = round(sum(temps) / len(temps)) if temps else None

            precip_prob = None
            if dominant_code is not None and dominant_code >= 50:
                probs = []
                for e in period_entries:
                    p = get_value(forecasts, "wwP", e["index"])
                    if p is not None: probs.append(p)
                precip_prob = round(max(probs)) if probs else 0

            is_windy = False
            for e in period_entries:
                prev_idx = e["index"] - 1
                if prev_idx >= 0:
                    ff = get_value(forecasts, "FF", prev_idx, lambda x: x * 3.6)
                    if ff is not None and ff >= 15:
                        is_windy = True
                        break

            result["days"][display_date].append({
                "period": period_name,
                "icon": full_icon_url,
                "avgTemp": avg_temp,
                "precipProb": precip_prob,
                "isWindy": is_windy
            })

    return result

def main():
    log("Start: Lade MOSMIX L KMZ vom DWD")
    kml_text = load_mosmix_l()
    
    log("KML geladen, beginne mit dem Parsing")
    timeSteps, forecasts, name, description = parse_kml_l(kml_text)
    
    log("Integriere hochauflösende MOSMIX S Daten vom Backend...")
    merge_mosmix_s(timeSteps, forecasts)
    
    log(f"Daten zusammengeführt. {len(timeSteps)} Timesteps gefunden. Baue Zusammenfassung...")
    summary = build_summary(timeSteps, forecasts, name, description)
    
    log(f"Zusammenfassung erstellt, schreibe JSON-Datei in {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    log("Vorgang erfolgreich beendet.")

if __name__ == "__main__":
    main()