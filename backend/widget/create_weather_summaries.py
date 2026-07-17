import os
import json
import urllib.request
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from concurrent.futures import ProcessPoolExecutor

tf_instance = None  # Für Performance in den Workern

def get_timezone_finder():
    global tf_instance
    if tf_instance is None:
        tf_instance = TimezoneFinder()
    return tf_instance

# =====================================================================
# ------------------------- KONFIGURATION -----------------------------
# =====================================================================

MOSMIX_L_ALL_URL = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/all_stations/kml/MOSMIX_L_LATEST.kmz"

# Ordner, in dem die MOSMIX_S JSON-Dateien aus deinem Backend liegen
MOSMIX_S_DIR = "/WWW/users/TUMid/weather_data/index/Forecast/mosmix_s"

# Zielordner für die generierten Wetter-Zusammenfassungen (pro Station eine Datei)
OUTPUT_DIR = "/WWW/users/TUMid/weather_data/widget"

ICON_BASE_URL = "https://raw.githubusercontent.com/stefan436/Wetterinfo/main/docs/icons/"

COORDS_JSON_PATH = "/WWW/users/TUMid/weather_data/mosmix_stationen_coords.json"

# Schwellenwerte für die Bewölkung
CLOUD_COVER_THRESHOLDS = [30, 60, 80]

WINDY_THRESHOLD = 15

PERIODS = [
    {"name": "Früh", "startHour": 6, "endHour": 10},
    {"name": "Mittag", "startHour": 10, "endHour": 14},
    {"name": "Nachmittag", "startHour": 14, "endHour": 18},
    {"name": "Abend", "startHour": 18, "endHour": 22},
    {"name": "Spät Abends", "startHour": 22, "endHour": 2},
    {"name": "Nacht", "startHour": 2, "endHour": 6},
]

PERIOD_ORDER = ["Nacht", "Früh", "Mittag", "Nachmittag", "Abend", "Spät Abends"]

NEEDED_ELEMENTS = {"ww", "Neff", "TTT", "wwP", "FF"}

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

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# =====================================================================
# ------------------------- LOGIK & PARSING ---------------------------
# =====================================================================

def get_value(forecasts, param, index, convert_func=lambda x: x):
    """Hilfsfunktion zum sicheren Auslesen der vorbereiteten Arrays."""
    try:
        val = forecasts.get(param, [])[index]
        if val is not None:
            return convert_func(val)
    except IndexError:
        pass
    return None

def merge_mosmix_s_local(station_id, timeSteps, forecasts):
    """Lädt die lokale MOSMIX S JSON der jeweiligen Station und überschreibt die KML-Daten."""
    s_file_path = os.path.join(MOSMIX_S_DIR, f"{station_id}.json")
    
    if not os.path.exists(s_file_path):
        return # Keine S-Daten für diese Station vorhanden
        
    try:
        with open(s_file_path, "r", encoding="utf-8") as f:
            s_data = json.load(f)
        
        s_time_map = {}
        for idx, ts_str in enumerate(s_data.get("t", [])):
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            dt_s = datetime.fromisoformat(ts_str).astimezone(ZoneInfo("UTC"))
            s_time_map[int(dt_s.timestamp())] = idx

        for param in forecasts.keys():
            if param in s_data.get("d", {}):
                s_values = s_data["d"][param]
                
                for l_idx, kml_ts in enumerate(timeSteps):
                    dt_l = datetime.strptime(kml_ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.000").replace(tzinfo=ZoneInfo("UTC"))
                    timestamp_l = int(dt_l.timestamp())
                    
                    s_idx = s_time_map.get(timestamp_l)
                    if s_idx is not None and s_idx < len(s_values) and s_values[s_idx] is not None:
                        forecasts[param][l_idx] = float(s_values[s_idx])
                        
    except Exception as e:
        # Fehltoleranz: Wenn S-Daten defekt sind, L-Daten als Fallback behalten
        pass

def build_summary(timeSteps, forecasts, name, description, tz_name):
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = []
    for i, ts in enumerate(timeSteps):
        dt_utc = datetime.strptime(ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.000").replace(tzinfo=ZoneInfo("UTC"))
        dt_local = dt_utc.astimezone(tz)
        
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
                    if ff is not None and ff >= WINDY_THRESHOLD:
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

def process_station_worker(station_id, name, description, lat, lon, raw_forecasts, timeSteps):
    """
    Worker-Funktion für das Multiprocessing. 
    Wandelt die raw_forecasts um, mergt MOSMIX_S rein und erstellt das Widget-Summary.
    """
    try:
        # NEU: Zeitzone dynamisch anhand der Koordinaten bestimmen
        tf = get_timezone_finder()
        tz_name = tf.timezone_at(lng=lon, lat=lat)
        if not tz_name:
            tz_name = "UTC"  # Fallback, falls Koordinaten ungültig (z.B. 0.0, 0.0)
            
        # 1. Rohdaten (Strings) in Listen von Floats umwandeln
        forecasts = {}
        for el_name, val_text in raw_forecasts:
            vals = [float(v) if v != '-' else None for v in val_text.split()]
            forecasts[el_name] = vals
        
        # 2. MOSMIX S Daten mergen (falls vorhanden)
        merge_mosmix_s_local(station_id, timeSteps, forecasts)
        
        # 3. Summary generieren - NEU: tz_name übergeben
        summary = build_summary(timeSteps, forecasts, name, description, tz_name)
        
        # 4. JSON schreiben
        out_file = os.path.join(OUTPUT_DIR, f"{station_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Fehler bei Station {station_id}: {e}")

# =====================================================================
# ------------------------- MAIN LOOP ---------------------------------
# =====================================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    log("Lade Koordinaten-Mapping aus JSON...")
    with open(COORDS_JSON_PATH, "r", encoding="utf-8") as f:
        coords_data = json.load(f)
    
    # Lookup-Table erstellen: {"station_id": (lat, lon)}
    coords_map = {}
    for item in coords_data:
        coords_map[item["station_id"]] = (float(item["lat"]), float(item["lon"]))
    
    log(f"Lade MOSMIX L All Stations von {MOSMIX_L_ALL_URL}")
    req = urllib.request.urlopen(MOSMIX_L_ALL_URL)
    
    tasks = []
    
    log("Entpacke und starte Streaming-Parsing...")
    with zipfile.ZipFile(io.BytesIO(req.read())) as z:
        kml_filename = [f for f in z.namelist() if f.endswith('.kml')][0]
        
        with z.open(kml_filename) as f:
            context = ET.iterparse(f, events=('start', 'end'))
            ns = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'dwd': 'https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd'
            }
            
            timeSteps = []
            
            for event, elem in context:
                if event == 'end':
                    # 1. TimeSteps sammeln
                    if elem.tag == f"{{{ns['dwd']}}}TimeStep":
                        timeSteps.append(elem.text)
                        elem.clear()
                    
                    # 2. Stationen (Placemarks) verarbeiten
                    elif elem.tag == f"{{{ns['kml']}}}Placemark":
                        name_node = elem.find('kml:name', ns)
                        desc_node = elem.find('kml:description', ns)
                        
                        if name_node is not None:
                            station_id = name_node.text.strip()
                            description = desc_node.text.strip() if desc_node is not None else ""
                            
                            # Koordinaten aus dem JSON-Mapping abfragen
                            lat, lon = coords_map.get(station_id, (0.0, 0.0))
                            
                            raw_forecasts = []
                            ext_data = elem.find('kml:ExtendedData', ns)
                            if ext_data is not None:
                                for fc in ext_data.findall('dwd:Forecast', ns):
                                    el_name = fc.get(f"{{{ns['dwd']}}}elementName")
                                    if el_name in NEEDED_ELEMENTS:
                                        val_node = fc.find('dwd:value', ns)
                                        if val_node is not None and val_node.text:
                                            raw_forecasts.append((el_name, val_node.text))
                            
                            # Wenn die Station Wetterdaten hat, packe sie in die Tasks
                            if raw_forecasts:
                                # lat und lon an den Worker übergeben
                                tasks.append((station_id, station_id, description, lat, lon, raw_forecasts, timeSteps))
                        
                        # RAM sofort freigeben
                        elem.clear()

    log(f"Starte parallele Verarbeitung für {len(tasks)} Stationen...")
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_station_worker, *task)
            for task in tasks
        ]
        for future in futures:
            future.result() # Fängt Exceptions der Worker ab
            
    log("Alle Stationen erfolgreich verarbeitet und gespeichert.")

if __name__ == "__main__":
    main()
    
    
