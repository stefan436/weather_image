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

# ---------------------------------------------------------
# Adaptierte Funktionen für ICON-D2 RUC
# ---------------------------------------------------------

def _apply_custom_colormap(data_matrix, valid_mask):
    """Verwandelt eine 2D-Matrix in ein RGBA-Bild basierend auf Farb-Leveln."""
    r = np.zeros_like(data_matrix, dtype=np.uint8)
    g = np.zeros_like(data_matrix, dtype=np.uint8)
    b = np.zeros_like(data_matrix, dtype=np.uint8)
    alpha = np.zeros_like(data_matrix, dtype=np.uint8)
    
    eroded_mask = binary_erosion(valid_mask, iterations=2)
    border_mask = valid_mask & ~eroded_mask
    
    for threshold, color in sorted(config.indexColorLevels, key=lambda x: x[0]):
        mask = data_matrix >= threshold
        r[mask] = color[0]
        g[mask] = color[1]
        b[mask] = color[2]
        alpha[mask] = 255 
        
    nan_mask = np.isnan(data_matrix)
    alpha[nan_mask] = 0
    
    r[border_mask] = 80
    g[border_mask] = 80
    b[border_mask] = 80
    alpha[border_mask] = 255
    
    return np.stack([r, g, b, alpha], axis=-1)

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
    x_coords = np.linspace(lons.min(), lons.max(), 794)
    y_coords = np.linspace(lats.min(), lats.max(), 753)

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
    
    return da_web, leaflet_bounds, da_mask_web

def export_data(da_web, leaflet_bounds, da_mask_web, relative_time_array):
    meta_json_dir = Path(config.meta_json_path).parent
    meta_json_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(config.save_path_webp).parent
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    for element in meta_json_dir.iterdir():
        if element.is_file():
            element.unlink()
    for element in frames_dir.iterdir():
        if element.is_file():
            element.unlink()

    mask_2d = da_mask_web.values > 0.5
    
    meta_json = {
        "bounds": leaflet_bounds,
        "frames": []
    }
    
    for t in range(len(da_web.time)):
        frame_data = da_web.isel(time=t).values
        rgba_array = _apply_custom_colormap(frame_data, mask_2d)
        
        uhrzeit_string = da_web.time.isel(time=t).dt.strftime("%Y%m%d_%H%M").item()
        iso_time_string = da_web.time.isel(time=t).dt.strftime("%Y-%m-%dT%H:%M:%SZ").item()
        konrad_timestamp = da_web.time.isel(time=t).dt.strftime("%Y%m%dT%H%M00").item()
        
        img = Image.fromarray(rgba_array, mode='RGBA')
        save_path = config.save_path_webp + uhrzeit_string + ".webp"
        final_url_webp = config.url_webp + uhrzeit_string + ".webp"
        
        meta_json["frames"].append({
            "iso_time": iso_time_string,
            "url": final_url_webp,
            "relative_time": relative_time_array[t],
            "konrad_url_time": konrad_timestamp
        })
        
        img.save(save_path, "WEBP", lossless=True)
        
    with open(config.meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2, ensure_ascii=False)
        
    print("Alle zeitgestempelten Frames für TSindex erfolgreich exportiert!")

