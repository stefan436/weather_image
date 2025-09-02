import json
import os
from datetime import datetime, timedelta
import requests
import re
import xarray as xr

def download_latest_dwd_file(target_folder, date=None, typ="uvi"):
    if date is None:
        date_obj = datetime.utcnow()
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
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
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



def main():
    download_folder = "./downloads"
    os.makedirs(download_folder, exist_ok=True)

    # Dateien herunterladen
    file_paths = download_all_dwd_types(download_folder)





    if all(file_paths.values()):
        # Dateien mit xarray öffnen
        gft = xr.open_dataset(file_paths["gft"], engine='cfgrib')
        uvh = xr.open_dataset(file_paths["uvh"], engine='cfgrib')
        uvi = xr.open_dataset(file_paths["uvi"], engine='cfgrib')

    else:
        print("error: Nicht alle Dateien konnten heruntergeladen werden.", f"files: {file_paths}")


    # Daten speichern 
    with open("docs/data/latitudes_uv_and_pt.json", "w") as f:
        json.dump(gft['latitude'].values.tolist(), f)
        
    with open("docs/data/longitudes_uv_and_pt.json", "w") as f:
        json.dump(gft['longitude'].values.tolist(), f)
        
    with open("docs/data/data_gft.bin", "wb") as f:
        f.write(gft['PT1M'].values[:, 75:-157, 200:-477].tobytes())
        
    with open("docs/data/data_uvi.bin", "wb") as f:
        f.write(uvi['UVI_MAX_CL'].values.tobytes())
        
    with open("docs/data/data_uvh.bin", "wb") as f:
        f.write(uvh['UVI_MAX_H'].values.tobytes())
        
        
    # Konvertiere numpy datetime64-Array in Liste von ISO-Strings
    times_str_gft = [str(t) for t in gft['valid_time'].values]
    with open("docs/data/gft_forecast_times.json", "w") as f:
        json.dump(times_str_gft, f)


    # Konvertiere numpy datetime64-Array in Liste von ISO-Strings
    times_str_uvi = [str(t) for t in uvi['valid_time'].values]
    with open("docs/data/uvi_forecast_times.json", "w") as f:
        json.dump(times_str_uvi, f)

if __name__ == "__main__":
    main()

