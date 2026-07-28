import json
import os
from datetime import datetime, timedelta, timezone
import requests
import re
import xarray as xr
import numpy as np
import shutil

def download_latest_dwd_file(target_folder, date=None, typ="uvi"):
    if date is None:
        date_obj = datetime.now(timezone.utc)
    elif isinstance(date, str):
        date_obj = datetime.strptime(date, "%Y%m%d")
    else:
        date_obj = date

    base_url = "https://opendata.dwd.de/climate_environment/health/forecasts/"

    for i in range(2):
        current_date = date_obj - timedelta(days=i)
        full_date = current_date.strftime('%Y%m%d')
        short_date = current_date.strftime('%y%m%d')

        try:
            resp = requests.get(base_url)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error loading index page: {e}")
            return None

        html_text = resp.text

        pattern = re.compile(
            rf"(Z__C_EDZW_{full_date}\d{{6}}_grb02(?:,|%2C)icreu_{typ}_icreu__000048_999999_{short_date}0000_HPC\.bin)"
        )

        matches = pattern.findall(html_text)
        if matches:
            latest_file = sorted(matches)[-1]
            file_url = base_url + latest_file
            target_path = os.path.join(target_folder, latest_file)

            try:
                with requests.get(file_url, stream=True) as r:
                    r.raise_for_status()
                    with open(target_path, "wb") as f:
                        # write all chunks from the streaming response
                        f.writelines(r.iter_content(chunk_size=8192))
                return target_path
            except Exception as e:
                print(f"Error downloading file: {e}")
                return None
        else:
            print(f"No file found for {typ.upper()} on {full_date}.")

    return None

def download_all_dwd_types(target_folder, date=None):
    paths = {}
    for typ in ["uvi", "uvh", "gft"]:
        path = download_latest_dwd_file(target_folder=target_folder, date=date, typ=typ)
        paths[typ] = path
    return paths

def find_nearest_idx(array, value):
    return (np.abs(array - value)).argmin()

def clean_array(arr):
    # Wandelt NaN in JSON-kompatibles None (null) um und rundet die Werte
    return [round(float(x), 2) if not np.isnan(x) else None for x in arr]

def main():
    download_folder = "/scratch/ge47fab/tmp_download"
    os.makedirs(download_folder, exist_ok=True)

    file_paths = download_all_dwd_types(download_folder)

    if not all(file_paths.values()):
        print("error: Nicht alle Dateien konnten heruntergeladen werden.", f"files: {file_paths}")
        return

    # Dateien mit xarray öffnen
    gft = xr.open_dataset(file_paths["gft"], engine='cfgrib')
    uvh = xr.open_dataset(file_paths["uvh"], engine='cfgrib')
    uvi = xr.open_dataset(file_paths["uvi"], engine='cfgrib')

    # Arrays extrahieren (bei GFT mit deinen Crop-Indices)
    lat_gft = gft['latitude'].values[200:-232]
    lon_gft = gft['longitude'].values[450:-677]
    gft_data = gft['PT1M'].values[:, 200:-232, 450:-677]
    
    lat_uv = uvi['latitude'].values
    lon_uv = uvi['longitude'].values
    uvi_data = uvi['UVI_MAX_CL'].values
    uvh_data = uvh['UVI_MAX_H'].values

    # Bounding Boxes der Gitter definieren
    min_lat_gft, max_lat_gft = np.min(lat_gft), np.max(lat_gft)
    min_lon_gft, max_lon_gft = np.min(lon_gft), np.max(lon_gft)
    
    min_lat_uv, max_lat_uv = np.min(lat_uv), np.max(lat_uv)
    min_lon_uv, max_lon_uv = np.min(lon_uv), np.max(lon_uv)

    # Lade die bekannten MOSMIX-Stationen
    with open("/WWW/users/ge47fab/weather_data/mosmix_stationen_coords.json", "r", encoding="utf-8") as f:
        stations = json.load(f)

    # Zielverzeichnis für die vorverarbeiteten JSONs
    out_dir = "/WWW/users/ge47fab/weather_data/index/Forecast/uv_gft"
    os.makedirs(out_dir, exist_ok=True)
    
    for st in stations:
        st_id = st["station_id"]
        slat = float(st["lat"])
        slon = float(st["lon"])
        
        station_data = {}
        
        # GFT Check (ist die Station im GFT-Gitter?)
        if min_lat_gft <= slat <= max_lat_gft and min_lon_gft <= slon <= max_lon_gft:
            ilat = find_nearest_idx(lat_gft, slat)
            ilon = find_nearest_idx(lon_gft, slon)
            station_data["GFT"] = clean_array(gft_data[:, ilat, ilon])
            
        # UV Check (ist die Station im UV-Gitter?)
        if min_lat_uv <= slat <= max_lat_uv and min_lon_uv <= slon <= max_lon_uv:
            ilat = find_nearest_idx(lat_uv, slat)
            ilon = find_nearest_idx(lon_uv, slon)
            station_data["UVI"] = clean_array(uvi_data[:, ilat, ilon])
            station_data["UVH"] = clean_array(uvh_data[:, ilat, ilon])
            
        # Nur eine Datei schreiben, wenn die Station von mindestens einem Netz abgedeckt wird
        if station_data:
            with open(os.path.join(out_dir, f"{st_id}.json"), "w", encoding="utf-8") as f:
                json.dump(station_data, f, separators=(',', ':'))

    # Zeitstempel global abspeichern, da das Frontend diese weiterhin zur Zuordnung braucht
    times_str_gft = [str(t) for t in gft['valid_time'].values]
    with open("/WWW/users/ge47fab/weather_data/index/Forecast/gft_forecast_times.json", "w", encoding="utf-8") as f:
        json.dump(times_str_gft, f)

    times_str_uvi = [str(t) for t in uvi['valid_time'].values]
    with open("/WWW/users/ge47fab/weather_data/index/Forecast/uvi_forecast_times.json", "w", encoding="utf-8") as f:
        json.dump(times_str_uvi, f)

    gft.close()
    uvh.close()
    uvi.close()
    shutil.rmtree(download_folder)
    

if __name__ == "__main__":
    main()