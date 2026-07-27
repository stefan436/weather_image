from datetime import datetime, timezone, timedelta
import netCDF4 as nc
import numpy as np
from pathlib import Path
from tqdm import tqdm
from scipy.interpolate import griddata
import requests
import re
import eccodes
import xarray as xr
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import step_size, num_workers, grid_file

# General info: steps_into_future contains the T+0 step. --> if forcast legth = 60 min --> steps_into_future = 13

def get_ruc_urls(set_past_date, steps_into_future, base_url_ruc):
    if set_past_date is not None:
        today = set_past_date
    else:
        today = datetime.now(timezone.utc)

    # look for the newest data
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        test_datum = today.strftime('%Y-%m-%dT%H:00')
        test_url = f"{base_url_ruc}/{test_datum}/s/PT000H00M.grib2"

        try:
            response = requests.head(test_url)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass

        today -= timedelta(hours=1)
        attempts += 1
    else:
        print(
            "Warnung: Konnte kein aktuelles Bild finden. Nutze theoretischen Zeitstempel."
        )
    
    current_run_str = today.strftime('%Y-%m-%dT%H:00')
    url_list = []

    # + 1 und - step_size da der Vorherige Schritt zu T+0 benötigt wird um T+0 zu berechnen (differenz)
    for i in range(steps_into_future +1):
        hours = (i * step_size) // 60
        
        filename = f"PT{hours:03d}H00M.grib2"
        bu = f"{base_url_ruc}/{current_run_str}/s/{filename}"
        url_list.append(bu)
    return url_list
    
    
def _format_dwd_url(url: str) -> str:
    """
    Erwartetes Input-Format:
    .../2026-07-05T19:00/s/PT001H20M.grib2
    
    Erwartetes Output-Format:
    RUC_20260705_R19_001H20M.grib2
    """
    # Das Regex-Muster sucht gezielt nach den Bausteinen:
    # Gruppe 1-3: Jahr, Monat, Tag (\d{4}, \d{2}, \d{2})
    # Gruppe 4: Stunde (\d{2}) - ignoriert die Minuten (:\d{2})
    # Gruppe 5: Der Dateiname nach 'PT' (.*\.grib2)
    pattern = r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):\d{2}/s/PT(.*\.grib2)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Die URL entspricht nicht dem erwarteten DWD-Format: {url}")
    year, month, day, hour, step_file = match.groups()
    return f"RUC_{year}{month}{day}_R{hour}_{step_file}"
    
    
def _download_single_ruc(url, output_dir):
    """Hilfsfunktion für den parallelen Download einer einzelnen Datei."""
    file_name = _format_dwd_url(url)
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
                if _format_dwd_url(url) == element.name:
                    treffer_index = index
                    break
            if treffer_index is not None:
                url_list[treffer_index] = np.nan
                print(f"Bereits vorhanden (wird übersprungen): {element.name}")
            else:
                print(f"Ungenutzte Datei wird gelöscht: {element.name}")
                element.unlink()    
    return url_list


def download_ruc(url_list, download_dir):
    output_dir = Path(download_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url_list = _check_url_and_del_file(output_dir, url_list)

    if any(isinstance(url, str) for url in url_list):
        print(f"Starting downloads to: {output_dir.resolve()}\n")
        # Parallelisieren der Downloads
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Erstelle eine Liste von auszuführenden Tasks
            futures = {executor.submit(_download_single_ruc, url, output_dir): url for url in url_list if isinstance(url, str)}
            
            # tqdm für den Fortschrittsbalken über die asynchronen Tasks
            for future in tqdm(as_completed(futures), total=len(url_list), desc="Downloading RUC Files"):
                success, message = future.result()
                if not success:
                    print(message)
    else:
        print("Alle Dateien sind bereits lokal vorhanden. Kein Download notwendig.")
            
    return output_dir

    
    
def process_grib_file(grib_file):
    with open(grib_file, 'rb') as f:
        gid = eccodes.codes_grib_new_from_file(f)
        values = np.array(eccodes.codes_get_values(gid))
        # date = eccodes.codes_get_string(gid, "dataDate")
        # time = eccodes.codes_get_string(gid, "dataTime")
        # Der step (Vorhersagestunde) ist oft wichtig für die Beschriftung
        # step = eccodes.codes_get_string(gid, "step") 
        eccodes.codes_release(gid)
    return values



def extract_icon_grid_essentials(grid_filepath):
    ds = xr.open_dataset(grid_filepath)
    
    # Zellzentren (clon, clat) in Grad umwandeln
    clon_deg = np.rad2deg(ds['clon'].values)
    clat_deg = np.rad2deg(ds['clat'].values)
    
    # Eckpunkte / Vertices (vlon, vlat) in Grad umwandeln
    # Diese werden benötigt, um die Umrisse der Dreiecke zu zeichnen
    vlon_deg = np.rad2deg(ds['vlon'].values)
    vlat_deg = np.rad2deg(ds['vlat'].values)
    
    # Konnektivität extrahieren (welche Vertices gehören zu welcher Zelle)
    # Die Variable ist 'vertex_of_cell' mit Dimensionen ('nv', 'cell'), also (3, 542040)
    # Wir transponieren sie, um die Form (cell, 3) zu bekommen, was die meisten Tools erwarten.
    vertex_of_cell = ds['vertex_of_cell'].values.T
    
    # WICHTIGER SCHRITT: Fortran-Index vs. Python-Index
    # ICON ist in Fortran geschrieben (1-basierter Index). 
    # Python ist 0-basiert. Wir müssen also 1 abziehen, damit der Index auf 
    # unsere vlon_deg / vlat_deg Arrays passt!
    # (Wir überprüfen vorher sicherheitshalber, ob die Werte 1-basiert sind, 
    #  indem wir schauen, ob es keine 0 im Array gibt).
    if vertex_of_cell.min() > 0:
        vertex_of_cell = vertex_of_cell - 1
        
    print(f"Extrahiert: {len(clon_deg)} Zellen und {len(vlon_deg)} Knotenpunkte (Vertices).")
    
    # Rückgabe als Dictionary für einfache Weiterverwendung
    return {
        'cell_lon': clon_deg,
        'cell_lat': clat_deg,
        'vertex_lon': vlon_deg,
        'vertex_lat': vlat_deg,
        'connectivity': vertex_of_cell
    }

def regrid_timeseries(pred, reprojection_ruc):
    """
    Interpoliert unstrukturierte Wetterdaten mit der Shape (time, coords) 
    auf ein regelmäßiges 2D-Gitter für jeden Zeitschritt.
    
    Parameter:
    - pred: numpy array der Shape (time, coords)
    - reprojection_ruc: Dictionary mit 'cell_lon' und 'cell_lat'
    
    Rückgabe:
    - grid_values_time: numpy array der Shape (time, 794, 753)
    """
    # 1. 1D-Koordinaten aus dem ICON-Grid extrahieren
    lons_1d = reprojection_ruc['cell_lon']
    lats_1d = reprojection_ruc['cell_lat']

    # 2. Regelmäßiges 2D-Gitter einmalig definieren
    grid_lon, grid_lat = np.mgrid[
        lons_1d.min():lons_1d.max():794j,
        lats_1d.min():lats_1d.max():753j
    ]

    # 3. Über alle Zeitschritte iterieren und interpolieren
    # Da sich das Quell- und Zielgitter nicht ändern, bleibt 'points' und 'xi' konstant.
    grid_values_list = [
        griddata(
            points=(lons_1d, lats_1d),
            values=pred[t, :],
            xi=(grid_lon, grid_lat),
            method='nearest'
        )
        for t in range(pred.shape[0])
    ]

    # In ein einzelnes NumPy-Array konvertieren: Shape wird (time, 794, 753)
    grid_values_time = np.array(grid_values_list)

    return grid_values_time

def create_prediction(download_folder, steps_into_future):
    no_rain = None
    # Lade Metadaten von ICON D2 RUC
    projection_RUC = extract_icon_grid_essentials(grid_file)
    n_cells = len(projection_RUC['cell_lon'])
    pred = np.empty((steps_into_future+1, n_cells))
    # pred = np.empty((steps_into_future-1, 542040))
    folder_path = Path(download_folder)
    # sort
    files = sorted([f for f in folder_path.iterdir() if f.is_file()])
    
    for idx, element in enumerate(files):
        # + 1 da die Vorhersage von RUC für T-5 benötigt wird um T+0 zu berechnen
        if idx >= steps_into_future + 1:
            break # Sicherheitshalber abbrechen, falls mehr Dateien existieren
            
        current_frame = process_grib_file(element)
        
        pred[idx, :] = current_frame
    pred = regrid_timeseries(pred, projection_RUC)
    return pred, projection_RUC
