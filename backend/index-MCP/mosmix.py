import os
import json
import urllib.request
import zipfile
import io
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor

from warnmos import run_warnmos_workflow
from spatial import prepare_warnmos_for_stations
from spatial import prepare_warnmos_for_stations, prepare_icon_for_stations

def process_and_save_station(station_id, raw_forecasts, timesteps, targets, warnmos_station_data, icon_station_data, out_dir):
    data_dict = {'t': timesteps, 'd': {}}
    
    for el_name, val_text in raw_forecasts:
        if el_name in targets:
            vals = [float(v) if v != '-' else None for v in val_text.split()]
            data_dict['d'][el_name] = vals

    if warnmos_station_data:
        for var_name, aligned_values in warnmos_station_data.items():
            data_dict['d'][var_name] = aligned_values
            
    # Hinzugefügt: ICON Daten ins JSON schreiben
    if icon_station_data:
        for var_name, aligned_values in icon_station_data.items():
            data_dict['d'][var_name] = aligned_values

    file_path = os.path.join(out_dir, f"{station_id}.json")
    with open(file_path, "w") as jf:
        json.dump(data_dict, jf, indent=2)

def build_unified_api(mosmix_url, out_dir, coords_json, warnmos_args, target_params, icon_data_dict=None, icon_times=None, x_coords=None, y_coords=None):
    os.makedirs(out_dir, exist_ok=True)
    
    try:
        print("Starte WarnMOS-Verarbeitung...")
        warnmos_dict = run_warnmos_workflow(*warnmos_args)
    except Exception as e:
        print(f"⚠️ FEHLER bei der WarnMOS-Verarbeitung: {e}")
        warnmos_dict = {} 
    
    print("Starte MOSMIX Download und Parsing...")
    try:
        req = urllib.request.urlopen(mosmix_url)
    except Exception as e:
        print(f"❌ KRITISCHER FEHLER: MOSMIX konnte nicht heruntergeladen werden: {e}")
        return 
        
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
            icon_prepared = None # Hinzugefügt
            
            for event, elem in context:
                if event == 'end':
                    if elem.tag == f"{{{ns['dwd']}}}TimeStep":
                        timesteps.append(elem.text)
                        elem.clear()
                    
                    elif elem.tag == f"{{{ns['kml']}}}Placemark":
                        if warnmos_prepared is None:
                            warnmos_prepared = prepare_warnmos_for_stations(coords_json, warnmos_dict, timesteps)
                            
                            # Hinzugefügt: ICON-Stationen aufbereiten
                            if icon_data_dict is not None:
                                icon_prepared = prepare_icon_for_stations(coords_json, icon_data_dict, icon_times, timesteps, x_coords, y_coords)
                            else:
                                icon_prepared = {}
                                
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
                            
                            station_warnmos_data = warnmos_prepared.get(station_id, {})
                            # Hinzugefügt: Holen der Stationsdaten aus dem ICON-Set
                            station_icon_data = icon_prepared.get(station_id, {}) if icon_prepared else {}
                            
                            # Die Tasks-Liste um station_icon_data erweitern
                            tasks.append((station_id, raw_forecasts, timesteps, target_params, station_warnmos_data, station_icon_data, out_dir))
                        
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
