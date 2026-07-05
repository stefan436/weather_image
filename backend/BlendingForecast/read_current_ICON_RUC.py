from datetime import datetime, timezone, timedelta
import netCDF4 as nc
import numpy as np
from pathlib import Path
from tqdm import tqdm
import requests
import eccodes
import xarray as xr
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import step_size, grid_file, base_url_ruc, num_workers, download_dir_ruc

# General info: steps_into_future contains the T+0 step. --> if forcast legth = 60 min --> steps_into_future = 13

def get_ruc_urls(set_past_date, RV_time, steps_into_future):
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
    # Berechne Zeitdifferenz zwischen RUC und RV Daten um sie zeitlich zu alignen
    diff = RV_time - today.replace(minute=0, second=0, microsecond=0)
    base_minutes = int(diff.total_seconds() / 60)
    url_list = []

    # + 1 und - step_size da der Vorherige Schritt zu T+0 benötigt wird um T+0 zu berechnen (differenz)
    for i in range(steps_into_future +1):
        total_minutes = base_minutes - step_size + (i * step_size)
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        filename = f"PT{hours:03d}H{minutes:02d}M.grib2"
        bu = f"{base_url_ruc}/{current_run_str}/s/{filename}"
        url_list.append(bu)
    return url_list
    
def _download_single_ruc(url, output_dir):
    """Hilfsfunktion für den parallelen Download einer einzelnen Datei."""
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

def download_ruc(url_list):
    output_dir = Path(download_dir_ruc)
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


def create_prediction(download_folder, steps_into_future):
    no_rain = None
    # Lade Metadaten von ICON D2 RUC
    projection_RUC = extract_icon_grid_essentials(grid_file)
    n_cells = len(projection_RUC['cell_lon'])
    pred = np.empty((steps_into_future, n_cells))
    # pred = np.empty((steps_into_future-1, 542040))
    folder_path = Path(download_folder)
    # sort
    files = sorted([f for f in folder_path.iterdir() if f.is_file()])
    
    previous_frame_mm = None
    
    for idx, element in enumerate(files):
        # + 1 da die Vorhersage von RUC für T-5 benötigt wird um T+0 zu berechnen
        if idx >= steps_into_future + 1:
            break # Sicherheitshalber abbrechen, falls mehr Dateien existieren
            
        current_frame_mm = process_grib_file(element)
        
        if idx == 0:
            # pass erstes file, da dieses 5 minuten vor dem Vorhersagezeitpunkt ist.
            # wird benötigt um die richtige Differenz zu T+0 zu berechnen
            pass
        else:
            # 2. Differenz bilden (Menge der letzten 5 Minuten)
            diff_mm = current_frame_mm - previous_frame_mm
            
            # Sicherheitsnetz: Rundungsfehler des Modells abfangen (vermeidet negative Raten)
            diff_mm = np.clip(diff_mm, 0, None)
            
            # 3. Umrechnung auf mm/h (5 min * 12 = 60 min)
            rate_mmh = diff_mm * 12.0
            
            # -1 da das erste file (idx=0) die Vorhersage für T-5 war und T+0 an Position 0 im pred array liegen soll 
            pred[idx-1, :] = rate_mmh
            
        previous_frame_mm = current_frame_mm
    
    if pred.max() <= 0.1:
        no_rain = True

    return pred, projection_RUC, no_rain




def save_pred_to_netcdf(pred, projection_dict, outfile="temp_model_data.nc"):
    """
    Wandelt das Vorhersage-Array in eine NetCDF-Datei um und fügt die 
    Polygon-Eckpunkte (Bounds) CF-konform hinzu, damit CDO's gencon funktioniert.
    """
    time_steps = pred.shape[0]
    
    # 1. Eckpunkte (Bounds) für CDO vorbereiten
    conn = projection_dict['connectivity'] # Shape: (n_cells, 3)
    vlon = projection_dict['vertex_lon']
    vlat = projection_dict['vertex_lat']
    
    # Mappe die Vertex-Koordinaten auf die Zellen. 
    # Ergebnis ist ein Array der Form (n_cells, 3)
    clon_bnds = vlon[conn]
    clat_bnds = vlat[conn]
    
    # 2. CF-konformes Dataset erstellen
    ds = xr.Dataset(
        {
            'precip_rate': (
                ['time', 'cell'], 
                pred, 
                {'units': 'mm/h', 'long_name': 'Precipitation Rate'}
            ),
            # CDO sucht nach Variablen für die Eckpunkte
            'clon_bnds': (['cell', 'vertices'], clon_bnds),
            'clat_bnds': (['cell', 'vertices'], clat_bnds)
        },
        coords={
            'time': np.arange(time_steps),
            'clon': (
                ['cell'], 
                projection_dict['cell_lon'], 
                # WICHTIG: Das bounds-Attribut sagt CDO, wo die Ecken liegen!
                {'standard_name': 'longitude', 'units': 'degrees_east', 'bounds': 'clon_bnds'}
            ),
            'clat': (
                ['cell'], 
                projection_dict['cell_lat'], 
                {'standard_name': 'latitude', 'units': 'degrees_north', 'bounds': 'clat_bnds'}
            )
        }
    )
    
    ds.to_netcdf(outfile)
    print(f"Temporäre Eingabedatei {outfile} (inkl. Zell-Eckpunkten) erstellt.")
    return outfile


    
# urls = get_ruc_urls(set_past_date)
# download_folder = download_ruc(urls)
# prediction = create_prediction(download_folder, steps_into_future)
# print(prediction[0].max(), prediction[0].min())

