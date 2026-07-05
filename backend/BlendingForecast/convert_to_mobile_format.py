import numpy as np
import xarray as xr
import rioxarray
from pyproj import Transformer
from PIL import Image
from pathlib import Path
from datetime import datetime, timedelta
import json
from scipy.ndimage import binary_erosion

from config import radarColorLevels, step_size, save_path_webp, meta_json_path, url_webp

def _apply_custom_colormap(data_matrix, valid_mask):
    """Verwandelt eine 2D-Matrix in ein RGBA-Bild basierend auf radarColorLevels."""
    # Erstelle leere Arrays für R, G, B und Alpha (Standardmäßig alles 0 = transparent)
    r = np.zeros_like(data_matrix, dtype=np.uint8)
    g = np.zeros_like(data_matrix, dtype=np.uint8)
    b = np.zeros_like(data_matrix, dtype=np.uint8)
    alpha = np.zeros_like(data_matrix, dtype=np.uint8)
    
    # Erosion zieht den "gültigen" Bereich zusammen. 
    # Die Differenz zwischen Original und erodiertem Bereich ist exakt der 2-Pixel-Rand.
    eroded_mask = binary_erosion(valid_mask, iterations=2)
    border_mask = valid_mask & ~eroded_mask
    
    # Loope rückwärts durch die Regeln, damit höhere Werte niedrigere überschreiben
    for threshold, color in sorted(radarColorLevels, key=lambda x: x[0]):
        mask = data_matrix >= threshold
        r[mask] = color[0]
        g[mask] = color[1]
        b[mask] = color[2]
        alpha[mask] = 255  # Volle Sichtbarkeit, wenn der Schwellenwert erreicht ist
        
    # NaNs explizit transparent machen (falls rioxarray beim Warpen Ränder auffüllt)
    nan_mask = np.isnan(data_matrix)
    alpha[nan_mask] = 0
    
    r[border_mask] = 80
    g[border_mask] = 80
    b[border_mask] = 80
    alpha[border_mask] = 255
    
    # Zu einem 3D RGBA-Array zusammenfügen
    return np.stack([r, g, b, alpha], axis=-1)



def prepare_data(radar_forecast, projection_dict, current_time, valid_RV_mask):
    num_time_steps = radar_forecast.shape[0]
    dates = [
        current_time + timedelta(minutes=i * step_size)
        for i in range(num_time_steps)
    ]
    
    # 2. Die obere linke Ecke (UL) von Lat/Lon in Projektionsmeter umrechnen
    # EPSG:4326 ist Standard WGS84 (Lat/Lon)
    transformer = Transformer.from_crs("EPSG:4326", projection_dict['projdef'], always_xy=True)
    x_min, y_max = transformer.transform(projection_dict['UL_lon'], projection_dict['UL_lat'])

    # 3. Die Koordinaten-Achsen in Metern berechnen
    # x startet bei x_min und geht nach rechts (+ xscale)
    # y startet bei y_max und geht nach unten (- yscale)
    x_coords = np.arange(x_min, x_min + (projection_dict['xsize'] * projection_dict['xscale']), projection_dict['xscale'])
    y_coords = np.arange(y_max, y_max - (projection_dict['ysize'] * projection_dict['yscale']), -projection_dict['yscale'])

    # 4. Erstellen des xarray DataArrays
    da = xr.DataArray(
        data=radar_forecast,
        dims=["time", "y", "x"],
        coords={"time": dates, "y": y_coords, "x": x_coords}
    )

    # 5. CRS zuweisen und Dimensionen für rioxarray deklarieren
    da = da.rio.write_crs(projection_dict['projdef'])
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")

    # 6. In Web Mercator (EPSG:3857) für Leaflet reprojizieren
    # rioxarray biegt das Bild hier automatisch gerade und glättet die Krümmung aus!
    da_web = da.rio.reproject("EPSG:3857")
    
    da_mask = xr.DataArray(
        data=valid_RV_mask.astype(np.float32), 
        dims=["y", "x"],
        coords={"y": y_coords, "x": x_coords}
    )
    da_mask = da_mask.rio.write_crs(projection_dict['projdef'])
    da_mask = da_mask.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da_mask_web = da_mask.rio.reproject("EPSG:3857")

    # 7. Die neuen, perfekt rechteckigen Leaflet-Bounds berechnen
    bounds_4326 = da_web.rio.transform_bounds("EPSG:4326")

    # Leaflet Format: [[min_lat, min_lon], [max_lat, max_lon]]
    leaflet_bounds = [[bounds_4326[1], bounds_4326[0]], [bounds_4326[3], bounds_4326[2]]]
    return da_web, leaflet_bounds, da_mask_web


def export_data(da_web, leaflet_bounds, da_mask_web):
    meta_json_dir = Path(meta_json_path).parent
    meta_json_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(save_path_webp).parent
    frames_dir.mkdir(parents=True, exist_ok=True)
    for element in meta_json_dir.iterdir():
        if element.is_file():
            element.unlink()
    for element in frames_dir.iterdir():
        if element.is_file():
            element.unlink()

    # Wert > 0.5 fängt Interpolationsunschärfen durch die Reprojektion sauber ab
    mask_2d = da_mask_web.values > 0.5
    
    meta_json = {
        "bounds": leaflet_bounds,
        "frames": []
    }
    for t in range(len(da_web.time)):
        frame_data = da_web.isel(time=t).values
        rgba_array = _apply_custom_colormap(frame_data, mask_2d)
        
        # Das datetime-Objekt aus dem aktuellen xarray-Schritt ziehen
        # .dt.strftime formatiert das xarray-numpy-datetime-Objekt sauber zu Text
        uhrzeit_string = da_web.time.isel(time=t).dt.strftime("%Y%m%d_%H%M").item()
        uhrzeit_anzeige = da_web.time.isel(time=t).dt.strftime("%H:%M").item()
        
        img = Image.fromarray(rgba_array, mode='RGBA')
        # Datei wird z.B. als "radar_frame_20260703_2025.webp" gespeichert
        save_path = save_path_webp + uhrzeit_string + ".webp"
        final_url_webp = url_webp + uhrzeit_string + ".webp"
        
        meta_json["frames"].append({
            "time": uhrzeit_anzeige,
            "url": final_url_webp
        })
        
        img.save(save_path, "WEBP", lossless=True)
        
    # 3. Das gesamte Dictionary als JSON-Datei speichern
    # 'indent=2' sorgt dafür, dass das JSON schön formatiert und lesbar ist
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2, ensure_ascii=False)
        
    print("Alle zeitgestempelten Frames erfolgreich exportiert!")

        
        
        
        
        
        
        
        
        
        
        