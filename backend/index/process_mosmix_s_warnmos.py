import warnings
warnings.filterwarnings(
    "ignore", category=FutureWarning, message=".*default value for compat will change.*"
)
import os
import bz2
import requests
import cfgrib
import json
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from scipy.spatial import cKDTree
import urllib.request
import zipfile
import io
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor

# ==========================================
# WARNMOS FUNKTIONEN
# ==========================================

def clear_directory_pathlib(dir_path):
    path = Path(dir_path)
    if path.exists() and path.is_dir():
        print(f"Leere Ordner: {path}...")
        for item in path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
    else:
        path.mkdir(parents=True, exist_ok=True)

def get_warnmos_url(base_url, date):
    found_long_url = None
    found_short_url = None
    max_attempts = 8 
    attempts = 0

    while attempts < max_attempts:
        date_str = date.strftime('%Y%m%d%H00')
        target_url_long = base_url + f"WarnMOSLong{date_str}.grb2.bz2"
        target_url_short = base_url + f"WarnMOS{date_str}.grb2.bz2"
        
        if not found_long_url:
            try:
                if requests.head(target_url_long).status_code == 200:
                    found_long_url = target_url_long
                    if not found_short_url:
                        break 
                    else:
                        break
            except requests.exceptions.RequestException:
                pass

        if not found_short_url:
            try:
                if requests.head(target_url_short).status_code == 200:
                    found_short_url = target_url_short
            except requests.exceptions.RequestException:
                pass

        date -= timedelta(hours=1)
        attempts += 1

    return found_long_url, found_short_url

def download_bz2(url, output_dir="."):
    local_filename = Path(output_dir) / url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    return str(local_filename)

def extract_grib_from_bz2(bz2_path, output_dir=None):
    if output_dir:
        filename = os.path.basename(bz2_path).replace(".bz2", "")
        output_path = os.path.join(output_dir, filename)
    else:
        output_path = bz2_path.replace(".bz2", "")
        
    with bz2.open(bz2_path, "rb") as source, open(output_path, "wb") as dest:
        for chunk in iter(lambda: source.read(10 * 1024 * 1024), b""):
            dest.write(chunk)
    return output_path

def read_dataset(path, archive=False):
    if archive:
        path = extract_grib_from_bz2(path)
        
    backend_args = {
        "filter_by_keys": {"typeOfLevel": "surface"}, 
        "errors": "ignore",
    }
    return cfgrib.open_dataset(path, backend_kwargs=backend_args)

def extract_data(ds, target_vars, valid_times):
    data_dict = {}
    available_vars = list(ds.data_vars)
    
    for var in target_vars:
        if var not in available_vars:
            continue
            
        data_dict[var] = {
            "data": ds[var].values,
            "lats": ds["latitude"].values,
            "lons": ds["longitude"].values,
            "nodata1": ds[var].attrs.get("GRIB_missingValue", "N/A"), 
            "nodata2": -9,
            "unit": ds[var].attrs.get("units", "N/A"),
            "times": valid_times
        }
    return data_dict

def run_warnmos_workflow(base_url, date, target_vars, temp_dir="."):
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    print(f"Suche nach WarnMOS-Dateien für {date}...")
    long_url, short_url = get_warnmos_url(base_url, date)
    
    ds_short, ds_long = None, None
    valid_times = None
    
    # 1. SHORT einlesen und Basiszeit bestimmen
    if short_url:
        print(f"[SHORT] Lade herunter: {short_url}")
        ds_short = read_dataset(download_bz2(short_url, temp_dir), archive=True)
        
        # Basiszeit (time) und reale Vorhersagezeiten sichern
        short_base_time = ds_short["time"].values
        if "valid_time" in ds_short.coords:
            valid_times = ds_short.coords["valid_time"].values
        else:
            valid_times = (ds_short["time"] + ds_short["step"]).values

    # 2. LONG einlesen
    if long_url:
        print(f"[LONG] Lade herunter: {long_url}")
        ds_long = read_dataset(download_bz2(long_url, temp_dir), archive=True)
        
        # --- VERSATZ-KORREKTUR ---
        if ds_short is not None:
            long_base_time = ds_long["time"].values
            # Berechne den Zeitunterschied in Stunden (z.B. 18:00 - 16:00 = 2 Stunden)
            hours_diff = int((short_base_time - long_base_time) / np.timedelta64(1, 'h'))
            
            if hours_diff > 0:
                print(f"[KORREKTUR] Schneide die ersten {hours_diff} Stunden von LONG ab, um Versatz zu verhindern.")
                # Verschiebe die 'step'-Achse von LONG so, dass sie zu SHORT passt
                ds_long = ds_long.assign_coords(step=ds_long.step - np.timedelta64(hours_diff, 'h'))
                # Entferne negative Steps (die jetzt in der Vergangenheit von SHORT liegen)
                ds_long = ds_long.sel(step=ds_long.step >= np.timedelta64(0, 'ns'))
        
        if valid_times is None:
            if "valid_time" in ds_long.coords:
                valid_times = ds_long.coords["valid_time"].values
            else:
                valid_times = (ds_long["time"] + ds_long["step"]).values
        
    # 3. Jetzt ist der Merge absolut sicher!
    if ds_short is not None and ds_long is not None:
        print("Führe Datensätze zusammen (Short priorisiert, zeitlich synchron)...")
        ds_merged = ds_short.combine_first(ds_long)
    elif ds_short is not None:
        ds_merged = ds_short
    elif ds_long is not None:
        ds_merged = ds_long
    else:
        print("Warnung: Keine WarnMOS-Daten gefunden.")
        return {}
        
    print("Extrahiere WarnMOS-Zieldaten...")
    data_dict = extract_data(ds_merged, target_vars, valid_times)
    
    if ds_short: ds_short.close()
    if ds_long: ds_long.close()
    if ds_short is not None and ds_long is not None: ds_merged.close()
    clear_directory_pathlib(temp_dir)
    return data_dict

# ==========================================
# INTEGRIERTE VERARBEITUNG (MOSMIX + WARNMOS)
# ==========================================

def prepare_warnmos_for_stations(coords_json_path, warnmos_data_dict, mosmix_times):
    """
    Berechnet die KD-Tree Zuweisung VOR dem Multiprocessing.
    Gibt ein Dict zurück: { 'station_id': { 'var_name': [aligned_values] } }
    """
    warnmos_by_station = {}
    if not warnmos_data_dict:
        return warnmos_by_station

    with open(coords_json_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)

    first_var = list(warnmos_data_dict.keys())[0]
    lats_2d = warnmos_data_dict[first_var]['lats']
    lons_2d = warnmos_data_dict[first_var]['lons']
    warnmos_times_str = pd.to_datetime(warnmos_data_dict[first_var]['times']).strftime('%Y-%m-%dT%H:%M:%S.000Z').tolist()

    print("Baue KD-Tree für räumliche Zuordnung...")
    grid_points = np.column_stack((lats_2d.flatten(), lons_2d.flatten()))
    tree = cKDTree(grid_points)

    print("Richte WarnMOS-Zeitreihen an MOSMIX-Zeitachse aus...")
    for station in stations:
        station_id = station['station_id']
        station_lat, station_lon = float(station['lat']), float(station['lon'])
        
        # KD-Tree Abfrage
        dist, idx_1d = tree.query([station_lat, station_lon])
        y, x = np.unravel_index(idx_1d, lats_2d.shape)

        station_data = {}
        for var_name, var_data in warnmos_data_dict.items():
            nodata1, nodata2 = var_data['nodata1'], var_data['nodata2']
            local_time_series = var_data['data'][:, y, x]
            
            val_map = {t: val for t, val in zip(warnmos_times_str, local_time_series)}
            aligned_values = []
            
            for mt in mosmix_times:
                val = val_map.get(mt, None)
                if val is not None and val != nodata2 and val != nodata1 and not np.isnan(val):
                    aligned_values.append(round(float(val), 2))
                else:
                    aligned_values.append(None)
                    
            station_data[var_name] = aligned_values
            
        warnmos_by_station[station_id] = station_data

    return warnmos_by_station

def process_and_save_station(station_id, raw_forecasts, timesteps, targets, warnmos_station_data, out_dir):
    """ Worker-Funktion: Parst MOSMIX, mergt WarnMOS und schreibt JSON einmalig """
    data_dict = {'t': timesteps, 'd': {}}
    
    # 1. MOSMIX Daten parsen
    for el_name, val_text in raw_forecasts:
        if el_name in targets:
            vals = [float(v) if v != '-' else None for v in val_text.split()]
            data_dict['d'][el_name] = vals

    # 2. WarnMOS Daten mergen (bereits auf Zeitskala ausgerichtet)
    if warnmos_station_data:
        for var_name, aligned_values in warnmos_station_data.items():
            data_dict['d'][var_name] = aligned_values

    # 3. Speichern (Nur ein Write-Vorgang!)
    file_path = os.path.join(out_dir, f"{station_id}.json")
    with open(file_path, "w") as jf:
        json.dump(data_dict, jf, indent=2)

def build_unified_api(mosmix_url, out_dir, coords_json, warnmos_args, target_params):
    os.makedirs(out_dir, exist_ok=True)
    
    # Schritt 1: WarnMOS Daten laden
    warnmos_dict = run_warnmos_workflow(*warnmos_args)
    
    # Schritt 2: MOSMIX KMZ Stream starten
    print("Starte MOSMIX Download und Parsing...")
    req = urllib.request.urlopen(mosmix_url)
    tasks = []
    
    with zipfile.ZipFile(io.BytesIO(req.read())) as z:
        kml_filename = [f for f in z.namelist() if f.endswith('.kml')][0]
        
        with z.open(kml_filename) as f:
            context = ET.iterparse(f, events=('start', 'end'))
            ns = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'dwd': 'https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd'
            }
            
            timesteps = []
            warnmos_prepared = None
            
            for event, elem in context:
                if event == 'end':
                    if elem.tag == f"{{{ns['dwd']}}}TimeStep":
                        timesteps.append(elem.text)
                        elem.clear()
                    
                    elif elem.tag == f"{{{ns['kml']}}}Placemark":
                        # Sobald der erste Placemark kommt, sind alle TimeSteps gelesen.
                        # Jetzt können wir die WarnMOS-Daten zentral für alle Stationen vorbereiten.
                        if warnmos_prepared is None:
                            warnmos_prepared = prepare_warnmos_for_stations(coords_json, warnmos_dict, timesteps)
                            print("Sammle und konvertiere Stationen (Multiprocessing-Vorbereitung)...")
                            
                        name_node = elem.find('kml:name', ns)
                        if name_node is not None:
                            station_id = name_node.text
                            
                            raw_forecasts = []
                            ext_data = elem.find('kml:ExtendedData', ns)
                            if ext_data is not None:
                                for fc in ext_data.findall('dwd:Forecast', ns):
                                    el_name = fc.get(f"{{{ns['dwd']}}}elementName")
                                    if el_name in target_params:
                                        val_node = fc.find('dwd:value', ns)
                                        if val_node is not None and val_node.text:
                                            raw_forecasts.append((el_name, val_node.text))
                            
                            # Nur die spezifischen Daten dieser Station übergeben
                            station_warnmos_data = warnmos_prepared.get(station_id, {})
                            tasks.append((station_id, raw_forecasts, timesteps, target_params, station_warnmos_data, out_dir))
                        
                        elem.clear()    

    print(f"Starte paralleles Schreiben für {len(tasks)} Stationen...")
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_and_save_station, *task)
            for task in tasks
        ]
        for future in futures:
            future.result()
            
    print("✅ Unified API erfolgreich aufgebaut!")

# ==========================================
# AUSFÜHRUNG
# ==========================================
if __name__ == "__main__":
    # Pfade und Konfiguration
    MOSMIX_URL = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz"
    
    # OUT_DIR = "/WWW/users/TUMid/weather_data/index/Forecast/mosmix_s/"
    OUT_DIR = "./data/Forecast/mosmix_s/"

    # COORDS_JSON = "/WWW/users/TUMid/weather_data/mosmix_stationen_coords.json"
    COORDS_JSON = "./data/mosmix_stationen_coords.json"
    
    # WARNMOS_DOWNLOAD_PATH = "/WWW/users/TUMid/weather_data/index/WarnMOS"
    WARNMOS_DOWNLOAD_PATH = "./data/download/WarnMOS"
    
    WARNMOS_BASE_URL = "https://opendata.dwd.de/weather/local_forecasts/warnmos/"
    TARGET_DATE = datetime.now()
    
    # Variablen Definitionen
    MOSMIX_TARGETS = {'TTT', 'Td', 'RR1c', 'Neff', 'DD', 'FF', 'FX1', 'wwM', 'ww', 'Rad1h'}
    WARNMOS_TARGETS = ["cp", "lsp", "asnow", "W_GEW_01", "W_GEWSK_01", "U_GEWSW_01", "FZ", "FZRA", "FZRAX"]
    
    warnmos_arguments = (WARNMOS_BASE_URL, TARGET_DATE, WARNMOS_TARGETS, WARNMOS_DOWNLOAD_PATH)

    # Hauptprozess starten
    build_unified_api(MOSMIX_URL, OUT_DIR, COORDS_JSON, warnmos_arguments, MOSMIX_TARGETS)