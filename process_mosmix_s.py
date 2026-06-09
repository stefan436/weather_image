import urllib.request
import zipfile
import io
import xml.etree.ElementTree as ET
import json
import os
import time

import os
import io
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
import json
from concurrent.futures import ProcessPoolExecutor

# Extrahierte parameter: (übersetzung in elementNamesMap.js)
target_params = {'TTT', 'Td', 'RR1c', 'Neff', 'DD', 'FF', 'FX1', 'wwM', 'ww', 'Rad1h'}



# Diese Funktion läuft parallel auf verschiedenen CPU-Kernen
def save_station_json(station_id, raw_forecasts, timesteps, targets, out_dir):
    data_dict = {'t': timesteps, 'd': {}}
    
    for el_name, val_text in raw_forecasts:
        if el_name in targets:
            # Konvertierung findet jetzt parallel statt
            vals = [float(v) if v != '-' else None for v in val_text.split()]
            data_dict['d'][el_name] = vals

    file_path = os.path.join(out_dir, f"{station_id}.json")
    with open(file_path, "w") as jf:
        json.dump(data_dict, jf, separators=(',', ':'))
        # Für bessere lesbarkeit der json
        # json.dump(data_dict, jf, indent=2)

def build_mosmix_static_api():
    start_time = time.time()
    url = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz"
    out_dir = "docs/data/mosmix_s"
    os.makedirs(out_dir, exist_ok=True)
    
    print("Lade MOSMIX-S herunter...")
    req = urllib.request.urlopen(url)
    
    print("Parse XML-Stream und bereite Parallelisierung vor...")
    
    # Hier sammeln wir die Aufgaben für die Worker
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
            targets = target_params
            
            for event, elem in context:
                if event == 'end':
                    if elem.tag == f"{{{ns['dwd']}}}TimeStep":
                        timesteps.append(elem.text)
                        elem.clear()
                    
                    elif elem.tag == f"{{{ns['kml']}}}Placemark":
                        name_node = elem.find('kml:name', ns)
                        if name_node is not None:
                            station_id = name_node.text
                            
                            # Extrahiere nur die rohen Strings aus dem XML (geht blitzschnell)
                            raw_forecasts = []
                            ext_data = elem.find('kml:ExtendedData', ns)
                            if ext_data is not None:
                                for fc in ext_data.findall('dwd:Forecast', ns):
                                    el_name = fc.get(f"{{{ns['dwd']}}}elementName")
                                    if el_name in targets:
                                        val_node = fc.find('dwd:value', ns)
                                        if val_node is not None and val_node.text:
                                            raw_forecasts.append((el_name, val_node.text))
                            
                            # Aufgabe für den Pool speichern
                            tasks.append((station_id, raw_forecasts))
                        
                        elem.clear()

    print(f"XML fertig gelesen. Starte parallele Verarbeitung von {len(tasks)} Stationen...")
    
    # Nutzt automatisch alle CPU-Kerne des GitHub-Runners (Standard: 2 Kerne)
    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(save_station_json, station_id, raw_forecasts, timesteps, targets, out_dir)
            for station_id, raw_forecasts in tasks
        ]
        # Warten, bis alle Worker fertig sind
        for future in futures:
            future.result()

    print(f"Erfolgreich beendet in {time.time() - start_time:.2f} Sekunden.")

if __name__ == "__main__":
    build_mosmix_static_api()