import warnings
warnings.filterwarnings(
    "ignore", category=FutureWarning, message=".*default value for compat will change.*"
)
import os
import requests
import cfgrib
import xarray as xr
from datetime import timedelta
from pathlib import Path
from utils import clear_directory_pathlib, download_bz2, extract_grib_from_bz2

def get_warnmos_url(base_url, date):
    found_long_url = None
    found_short_url = None
    max_attempts = 12 
    attempts = 0

    while attempts < max_attempts:
        date_str = date.strftime('%Y%m%d%H00')
        target_url_long = base_url + f"WarnMOSLong{date_str}.grb2.bz2"
        target_url_short = base_url + f"WarnMOS{date_str}.grb2.bz2"
        
        if not found_long_url:
            try:
                if requests.head(target_url_long).status_code == 200:
                    found_long_url = target_url_long
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
    
    def align_to_valid_time(ds):
        if "valid_time" not in ds.coords:
            ds = ds.assign_coords(valid_time=ds.time + ds.step)
        ds = ds.swap_dims({"step": "valid_time"})
        return ds.drop_vars(["time", "step"], errors="ignore")

    if short_url:
        print(f"[SHORT] Lade herunter: {short_url}")
        ds_short = read_dataset(download_bz2(short_url, temp_dir), archive=True)
        ds_short = align_to_valid_time(ds_short)

    if long_url:
        print(f"[LONG] Lade herunter: {long_url}")
        ds_long = read_dataset(download_bz2(long_url, temp_dir), archive=True)
        ds_long = align_to_valid_time(ds_long)
        
    if ds_short is not None and ds_long is not None:
        print("Führe Datensätze zusammen...")
        ds_merged = ds_short.combine_first(ds_long)
    elif ds_short is not None:
        ds_merged = ds_short
    elif ds_long is not None:
        ds_merged = ds_long
    else:
        print("Warnung: Keine WarnMOS-Daten gefunden.")
        return {}
        
    valid_times = ds_merged.coords["valid_time"].values
    print("Extrahiere WarnMOS-Zieldaten...")
    data_dict = extract_data(ds_merged, target_vars, valid_times)
    
    if ds_short: ds_short.close()
    if ds_long: ds_long.close()
    if ds_short is not None and ds_long is not None: ds_merged.close()
    clear_directory_pathlib(temp_dir)
    
    return data_dict
