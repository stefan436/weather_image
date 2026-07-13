import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tqdm import tqdm
import tarfile
import io
import h5py
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import base_url_rv, product_rv, download_dir_rv, num_workers

def get_radar_urls(hist_time_steps, set_past_date):
    if set_past_date is not None:
        today = set_past_date
    else:
        today = datetime.now(timezone.utc)
    rounded_min = (today.minute // 5) * 5
    time_now = today.replace(minute=rounded_min, second=0, microsecond=0)

    # look for the newest data
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        test_datum = time_now.strftime("%Y%m%d")
        test_uhrzeit = time_now.strftime("%H%M")
        test_url = f"{base_url_rv}composite_{product_rv}_{test_datum}_{test_uhrzeit}.tar"

        try:
            response = requests.head(test_url)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass

        time_now -= timedelta(minutes=5)
        attempts += 1
    else:
        print(
            "Warnung: Konnte kein aktuelles Bild finden. Nutze theoretischen Zeitstempel."
        )

    url_list = []

    for i in range(hist_time_steps):
        t = time_now - timedelta(minutes=5 * i)
        
        schritt_datum = t.strftime('%Y%m%d')
        schritt_uhrzeit = t.strftime('%H%M')
        
        bu = f"{base_url_rv}composite_{product_rv}_{schritt_datum}_{schritt_uhrzeit}.tar"
        url_list.append(bu)
    return url_list, time_now



def _download_single_radar(url, output_dir):
    """Hilfsfunktion für den Radar-Download."""
    file_name = url.split("/")[-1]
    file_path = output_dir / file_name
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True, url
    except requests.exceptions.RequestException as error:
        return False, f"Failed to download {url}. Error: {error}"


def _check_url_and_del_file(output_dir, url_list):
    # check if files are already downloaded and delete unused files                
    for element in output_dir.iterdir():
        if element.is_file():
            treffer_index = None
            for index, url in enumerate(url_list):
                # Path(url).name holt den Dateinamen aus der URL (z.B. "datei.zip")
                if not isinstance(url, str):
                    continue        # falls vorheriges file vorhanden ist und mit nan ersetzt wurde
                if Path(url).name == element.name:
                    treffer_index = index
                    break
            if treffer_index is not None:
                url_list[treffer_index] = np.nan
                print(f"Bereits vorhanden (wird übersprungen): {element.name}")
            else:
                print(f"Ungenutzte Datei wird gelöscht: {element.name}")
                element.unlink()    
    return url_list

def download_radar(url_list):
    output_dir = Path(download_dir_rv)
    output_dir.mkdir(parents=True, exist_ok=True)

    url_list = _check_url_and_del_file(output_dir, url_list)
    if any(isinstance(url, str) for url in url_list):
        print(f"Starting parallel downloads to: {output_dir.resolve()}\n")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(_download_single_radar, url, output_dir): url for url in url_list if isinstance(url, str)}
            for future in tqdm(as_completed(futures), total=len(url_list), desc="Downloading Radar Files"):
                success, message = future.result()
                if not success:
                    print(message)
    else:
        print("Alle Dateien sind bereits lokal vorhanden. Kein Download notwendig.")
            
    return output_dir

def get_rv_forecast(data_path, steps_into_future):
    """
    Liest die Vorhersage-Zeitschritte (T+5, T+10...) aus den einzelnen HDF5-Dateien
    innerhalb des RV-Tar-Archivs.
    """
    data_path = Path(data_path)
    forecast_frames = []
    
    with tarfile.open(data_path, 'r') as tar:
        # Alle Dateien im Archiv finden und alphabetisch sortieren
        # Dadurch ergibt sich die Reihenfolge: 000, 005, 010, 015...
        members = sorted([m for m in tar.getmembers() if m.isfile()], key=lambda x: x.name)
        
        # Wir starten zwingend bei Index 0 (T+0), da PySteps 
        # den Startzustand (t=0) für die Initialisierung der Blending-Gewichte braucht!
        for i in range(0, steps_into_future + 1):
            if i >= len(members):
                print(f"Warnung: Nicht genug Vorhersage-Dateien im Archiv. Erwarte {steps_into_future}, gefunden {len(members)-1}.")
                break
                
            member = members[i]
            f_obj = tar.extractfile(member)
            file_bytes = io.BytesIO(f_obj.read())
            
            with h5py.File(file_bytes, 'r') as h5:
                # Struktur ist in jeder Datei gleich
                dataset = h5['/dataset1/data1/data']
                what = h5['/dataset1/data1/what']
                
                # Attribute auslesen (Dein Output zeigt, dass nodata 4294967295 ist)
                nodata = what.attrs.get('nodata', [4294967295.0])[0] if isinstance(what.attrs.get('nodata'), np.ndarray) else what.attrs.get('nodata', 4294967295.0)
                gain = what.attrs.get('gain', [0.01])[0] if isinstance(what.attrs.get('gain'), np.ndarray) else what.attrs.get('gain', 0.01)
                offset = what.attrs.get('offset', [0.0])[0] if isinstance(what.attrs.get('offset'), np.ndarray) else what.attrs.get('offset', 0.0)
                
                raw = dataset[:]
                
                # Umrechnung in mm/h und Maskierung
                processed = np.where(
                    raw == nodata, 
                    np.nan, 
                    (raw.astype(np.float32) * gain + offset) * 12.0
                )
                forecast_frames.append(processed)
                
    return np.array(forecast_frames)


def read_radar_composite(data_path):
    data_path = Path(data_path)
    
    with tarfile.open(data_path, 'r') as tar:
        # only look at files in the tar archive and sort them
        members = sorted(
            [m for m in tar.getmembers() if m.isfile()],
            key=lambda x: x.name
            )

        # select first frame T+0 from archive
        member = members[0]

        # HDF5-Datei in den RAM laden (BytesIO)
        f_obj = tar.extractfile(member)
        file_bytes = io.BytesIO(f_obj.read())
        
        with h5py.File(file_bytes, 'r') as h5:
            dataset = h5['/dataset1/data1/data']
            what = h5['/dataset1/data1/what']
            where = h5['where']
            
            # Attribute sicher auslesen (HDF5 liefert oft Arrays mit einem Element zurück)
            nodata = what.attrs.get('nodata', [255.0])[0] if isinstance(what.attrs.get('nodata'), np.ndarray) else what.attrs.get('nodata', 255.0)
            gain = what.attrs.get('gain', [0.01])[0] if isinstance(what.attrs.get('gain'), np.ndarray) else what.attrs.get('gain', 0.01)
            offset = what.attrs.get('offset', [0.0])[0] if isinstance(what.attrs.get('offset'), np.ndarray) else what.attrs.get('offset', 0.0)
                            
            LL_lat = where.attrs.get('LL_lat', [45.696425377390064])[0] if isinstance(where.attrs.get('LL_lat'), np.ndarray) else where.attrs.get('LL_lat', 45.696425377390064)
            LL_lon = where.attrs.get('LL_lon', [3.5669946350078914])[0] if isinstance(where.attrs.get('LL_lon'), np.ndarray) else where.attrs.get('LL_lon', 3.5669946350078914)
            
            LR_lat = where.attrs.get('LR_lat', [45.68460578137082])[0] if isinstance(where.attrs.get('LR_lat'), np.ndarray) else where.attrs.get('LR_lat', 45.68460578137082)
            LR_lon = where.attrs.get('LR_lon', [16.580869348598274])[0] if isinstance(where.attrs.get('LR_lon'), np.ndarray) else where.attrs.get('LR_lon', 16.580869348598274)
            
            UL_lat = where.attrs.get('UL_lat', [55.862087108249824])[0] if isinstance(where.attrs.get('UL_lat'), np.ndarray) else where.attrs.get('UL_lat', 55.862087108249824)
            UL_lon = where.attrs.get('UL_lon', [1.463301510256666])[0] if isinstance(where.attrs.get('UL_lon'), np.ndarray) else where.attrs.get('UL_lon', 1.463301510256666)
            
            UR_lat = where.attrs.get('UR_lat', [55.845438563255755])[0] if isinstance(where.attrs.get('UR_lat'), np.ndarray) else where.attrs.get('UR_lat', 55.845438563255755)
            UR_lon = where.attrs.get('UR_lon', [18.73161645466747])[0] if isinstance(where.attrs.get('UR_lon'), np.ndarray) else where.attrs.get('UR_lon', 18.73161645466747)
            
            xscale = where.attrs.get('xscale', [1000.0])[0] if isinstance(where.attrs.get('xscale'), np.ndarray) else where.attrs.get('xscale', 1000.0)
            xsize = where.attrs.get('xsize', [1100])[0] if isinstance(where.attrs.get('xsize'), np.ndarray) else where.attrs.get('xsize', 1100)
            
            yscale = where.attrs.get('yscale', [1000.0])[0] if isinstance(where.attrs.get('yscale'), np.ndarray) else where.attrs.get('yscale', 1000.0)
            ysize = where.attrs.get('ysize', [1200])[0] if isinstance(where.attrs.get('ysize'), np.ndarray) else where.attrs.get('ysize', 1200)
            
            # Projektion und Gittergröße 
            projdef = where.attrs.get('projdef', [b'+proj=stere ...'])[0] if isinstance(where.attrs.get('projdef'), np.ndarray) else where.attrs.get('projdef', b'+proj=stere ...')
            # Falls projdef als Byte-String kommt, bei Bedarf zu normalem String decodieren:
            if isinstance(projdef, bytes):
                projdef = projdef.decode('utf-8')                
            
            # Daten Array einlesen und schneiden
            raw = dataset[:]

            # Konvertierung und Maskierung (v * gain + offset) * 12 für mm/h
            processed = np.where(
                raw == nodata, 
                np.nan, 
                (raw.astype(np.float32) * gain + offset) * 12.0
            )
            
            projection_dict = {
                'LL_lat': float(LL_lat),
                'LL_lon': float(LL_lon),
                'LR_lat': float(LR_lat),
                'LR_lon': float(LR_lon),
                'UL_lat': float(UL_lat),
                'UL_lon': float(UL_lon),
                'UR_lat': float(UR_lat),
                'UR_lon': float(UR_lon),
                'projdef': str(projdef),
                'xscale': float(xscale),
                'xsize': int(xsize),
                'yscale': float(yscale),
                'ysize': int(ysize)
            }
    return processed, projection_dict




def create_radar(download_folder, hist_time_steps):
    no_rain = False
    radar_film = np.empty((hist_time_steps, 1200, 1100))
    folder_path = Path(download_folder)
    file_list = sorted([element for element in folder_path.iterdir() if element.is_file()])
    for idx, element in enumerate(file_list):
        if element.is_file():
            frame, projection_dict = read_radar_composite(element)
            radar_film[idx, :, :] = frame
    if radar_film.max() <= 0.1:
        no_rain = True
    return radar_film, projection_dict, no_rain


# url_list = get_radar_urls(hist_time_steps, set_past_date)
# download_folder = download_radar(url_list)
# frames, projection_dict = create_radar(download_folder, hist_time_steps)
# print(projection_dict)

