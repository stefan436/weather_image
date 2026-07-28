import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

def prepare_icon_for_stations(coords_json_path, icon_data_dict, icon_times, mosmix_times, x_coords, y_coords):
    """
    Räumliche Zuordnung der ICON-Parameter zu den Stationen per KD-Tree und 
    zeitliche Ausrichtung an der MOSMIX-Zeitachse.
    """
    icon_by_station = {}
    if not icon_data_dict:
        return icon_by_station

    with open(coords_json_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)

    # Die absoluten datetime-Zeiten in das MOSMIX ISO-Format überführen
    icon_times_str = [t.strftime('%Y-%m-%dT%H:%M:%S.000Z') for t in icon_times]

    print("Baue KD-Tree für ICON Zuordnung...")
    lons_2d, lats_2d = np.meshgrid(x_coords, y_coords)
    grid_points = np.column_stack((lats_2d.flatten(), lons_2d.flatten()))
    tree = cKDTree(grid_points)

    print("Richte ICON-Zeitreihen an MOSMIX-Zeitachse aus...")
    for station in stations:
        station_id = station['station_id']
        station_lat = float(station['lat'])
        station_lon = float(station['lon'])
        
        dist, idx_1d = tree.query([station_lat, station_lon])
        MAX_DISTANCE_DEG = 0.1
        
        if dist > MAX_DISTANCE_DEG:
            icon_by_station[station_id] = {} 
            continue 

        # 1D Index zurück ins 2D-Grid übersetzen
        y, x = np.unravel_index(idx_1d, lats_2d.shape)

        station_data = {}
        for var_name, var_data in icon_data_dict.items():
            # var_data ist ein 3D-Array: (time, y, x)
            local_time_series = var_data[:, y, x]
            
            val_map = {t: val for t, val in zip(icon_times_str, local_time_series)}
            aligned_values = []
            
            for mt in mosmix_times:
                val = val_map.get(mt, None)
                if val is not None and not np.isnan(val):
                    aligned_values.append(round(float(val), 2))
                else:
                    aligned_values.append(None)
                    
            station_data[var_name] = aligned_values
            
        icon_by_station[station_id] = station_data

    return icon_by_station


def prepare_warnmos_for_stations(coords_json_path, warnmos_data_dict, mosmix_times):
    warnmos_by_station = {}
    if not warnmos_data_dict:
        return warnmos_by_station

    with open(coords_json_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)

    first_var = list(warnmos_data_dict.keys())[0]
    lats_2d = warnmos_data_dict[first_var]['lats']
    lons_2d = warnmos_data_dict[first_var]['lons']
    warnmos_times_str = pd.to_datetime(warnmos_data_dict[first_var]['times']).strftime('%Y-%m-%dT%H:%M:%S.000Z').tolist()

    print("Baue KD-Tree für räumliche Zuordnung...")
    grid_points = np.column_stack((lats_2d.flatten(), lons_2d.flatten()))
    tree = cKDTree(grid_points)

    print("Richte WarnMOS-Zeitreihen an MOSMIX-Zeitachse aus...")
    for station in stations:
        station_id = station['station_id']
        station_lat, station_lon = float(station['lat']), float(station['lon'])
        
        dist, idx_1d = tree.query([station_lat, station_lon])
        MAX_DISTANCE_DEG = 0.1
                
        if dist > MAX_DISTANCE_DEG:
            warnmos_by_station[station_id] = {} 
            continue 

        y, x = np.unravel_index(idx_1d, lats_2d.shape)

        station_data = {}
        for var_name, var_data in warnmos_data_dict.items():
            nodata1, nodata2 = var_data['nodata1'], var_data['nodata2']
            local_time_series = var_data['data'][:, y, x]
            
            val_map = {t: val for t, val in zip(warnmos_times_str, local_time_series)}
            aligned_values = []
            
            for mt in mosmix_times:
                val = val_map.get(mt, None)
                if val is not None and val != nodata2 and val != nodata1 and not np.isnan(val):
                    aligned_values.append(round(float(val), 2))
                else:
                    aligned_values.append(None)
                    
            station_data[var_name] = aligned_values
            
        warnmos_by_station[station_id] = station_data

    return warnmos_by_station
