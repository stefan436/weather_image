import xarray as xr
import rioxarray
from pyproj import Transformer
import numpy as np
from PIL import Image
from pathlib import Path
from datetime import timedelta
import json
from scipy.ndimage import binary_erosion
from rasterio.enums import Resampling
import config
from skimage import measure
import json


def _export_contours_to_geojson(data_matrix, x_coords, y_coords, thresholds, out_path, relative_time):
    """
    Findet Konturlinien (inkl. Datenrand) in einer 2D-Matrix und exportiert sie als GeoJSON.
    """
    features = []
    
    # 1. Datenrand (Data Boundary) extrahieren
    # Erzeugt eine Maske: 1.0 wo Daten existieren, 0.0 bei NaN
    valid_mask_float = (~np.isnan(data_matrix)).astype(float)
    
    # Finde die exakte Kante zwischen Daten (1) und Nicht-Daten (0) -> bei 0.5
    boundary_contours = measure.find_contours(valid_mask_float, 0.5)
    for contour in boundary_contours:
        c_lats = np.interp(contour[:, 0], np.arange(len(y_coords)), y_coords)
        c_lons = np.interp(contour[:, 1], np.arange(len(x_coords)), x_coords)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": np.column_stack((c_lons, c_lats)).tolist()
            },
            "properties": {
                "type": "data_boundary",
                "time": relative_time
            }
        })

    # 2. BRN Konturen extrahieren
    # NaNs temporär mit 0 füllen, damit die Kantenberechnung nicht abstürzt
    brn_filled = np.nan_to_num(data_matrix, nan=0.0)
    
    for threshold, prop_name in thresholds:
        contours = measure.find_contours(brn_filled, threshold)
        for contour in contours:
            c_lats = np.interp(contour[:, 0], np.arange(len(y_coords)), y_coords)
            c_lons = np.interp(contour[:, 1], np.arange(len(x_coords)), x_coords)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": np.column_stack((c_lons, c_lats)).tolist()
                },
                "properties": {
                    "type": prop_name,
                    "value": threshold,
                    "time": relative_time
                }
            })
            
    feature_collection = {"type": "FeatureCollection", "features": features}
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, ensure_ascii=False)


def _apply_custom_colormap(data_matrix, valid_mask):
    """Verwandelt eine 2D-Matrix in ein RGBA-Bild basierend auf Farb-Leveln."""
    r = np.zeros_like(data_matrix, dtype=np.uint8)
    g = np.zeros_like(data_matrix, dtype=np.uint8)
    b = np.zeros_like(data_matrix, dtype=np.uint8)
    alpha = np.zeros_like(data_matrix, dtype=np.uint8)
    
    # 1. Basis-Farben des TS-Index zuweisen
    for threshold, color in sorted(config.indexColorLevels, key=lambda x: x[0]):
        mask = data_matrix >= threshold
        r[mask] = color[0]
        g[mask] = color[1]
        b[mask] = color[2]
        alpha[mask] = 255 
        
    nan_mask = np.isnan(data_matrix)
    alpha[nan_mask] = 0

    return np.stack([r, g, b, alpha], axis=-1)


def export_data(da_web, da_brn_4326, leaflet_bounds, da_mask_web, relative_time_array):
    meta_json_dir = Path(config.meta_json_path).parent
    meta_json_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(config.save_path_webp).parent
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Nur die meta.json löschen
    meta_file = Path(config.meta_json_path)
    if meta_file.is_file():
        meta_file.unlink()
        
    # 2. Den Ordner für die Frames komplett leeren
    for element in frames_dir.iterdir():
        if element.is_file():
            element.unlink()

    mask_2d = da_mask_web.values > 0.5
    
    meta_json = {
        "bounds": leaflet_bounds,
        "frames": []
    }
    
    # x- und y-Koordinaten (Lon/Lat) für die Vektorisierung aus dem 4326-Array ziehen
    x_coords = da_brn_4326.x.values
    y_coords = da_brn_4326.y.values
    
    for t in range(len(da_web.time)):
        # 1. Rasterbild (TS-Index) erzeugen
        frame_data = da_web.isel(time=t).values
        rgba_array = _apply_custom_colormap(frame_data, mask_2d) # Nutzt wieder deine ursprüngliche Funktion ohne BRN
        
        uhrzeit_string = da_web.time.isel(time=t).dt.strftime("%Y%m%d_%H%M").item()
        iso_time_string = da_web.time.isel(time=t).dt.strftime("%Y-%m-%dT%H:%M:%SZ").item()
        
        # Pfade definieren
        save_path_img = config.save_path_webp + uhrzeit_string + ".webp"
        save_path_json = config.save_path_webp + uhrzeit_string + "_BRN.geojson"
        
        final_url_webp = config.url_webp + uhrzeit_string + ".webp"
        final_url_json = config.url_webp + uhrzeit_string + "_BRN.geojson"
        
        # 2. BRN Konturen (Vektoren) erzeugen
        brn_frame_data = da_brn_4326.isel(time=t).values
        _export_contours_to_geojson(
            data_matrix=brn_frame_data,
            x_coords=x_coords,
            y_coords=y_coords,
            thresholds=[(10, "supercell_risk_start"), (50, "supercell_risk_end")],
            out_path=save_path_json,
            relative_time=relative_time_array[t]
        )
        
        # Bild speichern
        img = Image.fromarray(rgba_array, mode='RGBA')
        img.save(save_path_img, "WEBP", lossless=True)
        
        # Metadaten ergänzen
        meta_json["frames"].append({
            "iso_time": iso_time_string,
            "url": final_url_webp,
            "url_vector": final_url_json, # Dem Frontend die passende GeoJSON URL mitgeben
            "relative_time": relative_time_array[t],
        })
        
    with open(config.meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2, ensure_ascii=False)
        
    print("Alle Bilder und GeoJSON-Vektoren erfolgreich exportiert!")
    
    
def generate_time_arrays_ruc(total_frames, start_time):
    # Im RUC-Skript blicken wir nur in die Zukunft (T+0 bis T+n), keine Radar-Historie
    absolute_time_array = [start_time + timedelta(minutes=i * config.step_size) for i in range(total_frames)]
    
    relative_time_array = []
    for i in range(total_frames):
        if i == 0:
            relative_time_array.append("T0")
        else:
            relative_time_array.append(f"T+{i * config.step_size}")

    return absolute_time_array, relative_time_array

def prepare_data_icon(final_pred, projection_ruc, time_array):
    # 1. 1D-Koordinaten aus den Originaldaten rekonstruieren
    lons = projection_ruc['cell_lon']
    lats = projection_ruc['cell_lat']
    
    # Exakte Pixelanzahl aus regrid_timeseries (794x753)
    x_coords = np.linspace(lons.min(), lons.max(), 1000)
    y_coords = np.linspace(lats.min(), lats.max(), 1000)

    # 2. Dimensionen transponieren: (time, lon, lat) -> (time, lat, lon) = (time, y, x)
    data_transposed = np.transpose(final_pred, (0, 2, 1))
    
    # 3. Maske direkt aus den NaN-Werten des aktuellen Vorhersage-Grids erzeugen
    valid_mask = ~np.isnan(data_transposed[0])

    # 4. xarray DataArray in WGS84 (EPSG:4326) initialisieren
    da = xr.DataArray(
        data=data_transposed,
        dims=["time", "y", "x"],
        coords={"time": time_array, "y": y_coords, "x": x_coords}
    )

    da = da.rio.write_crs("EPSG:4326")
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")

    # 5. In Web Mercator reprojizieren
    da_web = da.rio.reproject("EPSG:3857", resampling=Resampling.nearest)
    
    # Maske separat reprojizieren
    da_mask = xr.DataArray(
        data=valid_mask.astype(np.float32), 
        dims=["y", "x"],
        coords={"y": y_coords, "x": x_coords}
    )
    da_mask = da_mask.rio.write_crs("EPSG:4326")
    da_mask = da_mask.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da_mask_web = da_mask.rio.reproject("EPSG:3857")

    # 6. Leaflet-Bounds generieren
    bounds_4326 = da_web.rio.transform_bounds("EPSG:4326")
    leaflet_bounds = [[bounds_4326[1], bounds_4326[0]], [bounds_4326[3], bounds_4326[2]]]
    
    return da_web, leaflet_bounds, da_mask_web, da

