import numpy as np
import netCDF4 as nc
from scipy.sparse import coo_matrix

from visualisation import check_radar_animation

def align_ruc_like_cdo_remap(weights_file, data_array):
    """
    Führt ein konservatives Remapping In-Memory direkt auf einem NumPy-Array durch.
    Geht davon aus, dass die letzte Dimension des Arrays die räumlichen Zellen (ncells) des Quellgitters sind.
    """
    
    # --- 1. Gewichte und Indizes aus dem SCRIP NetCDF extrahieren ---
    with nc.Dataset(weights_file, 'r') as w_nc:
        # 1-basierte Indizes aus CDO in 0-basierte Python-Indizes umwandeln
        src_address = w_nc.variables['src_address'][:] - 1
        dst_address = w_nc.variables['dst_address'][:] - 1
        
        remap_matrix = w_nc.variables['remap_matrix'][:, 0]
        
        src_grid_size = w_nc.dimensions['src_grid_size'].size
        dst_grid_size = w_nc.dimensions['dst_grid_size'].size
        
        # Zielgitter-Dimensionen (xsize, ysize) auslesen
        dst_grid_dims = w_nc.variables['dst_grid_dims'][:]
        xsize, ysize = dst_grid_dims[0], dst_grid_dims[1]

    # --- 2. Dünnbesetzte Projektionsmatrix aufbauen ---
    W = coo_matrix(
        (remap_matrix, (dst_address, src_address)), 
        shape=(dst_grid_size, src_grid_size)
    ).tocsr()

    # --- 3. Dimensionen prüfen und vorbereiten ---
    original_shape = data_array.shape
    
    # Sicherheitsprüfung: Entspricht die letzte Dimension der Anzahl der Zellen im ICON-Gitter?
    if original_shape[-1] != src_grid_size:
        raise ValueError(f"Shape-Mismatch: Die letzte Dimension des Arrays ({original_shape[-1]}) "
                         f"muss der Quellgitter-Größe im Weightsfile ({src_grid_size}) entsprechen.")

    # Alle führenden Dimensionen (z.B. Zeit, Level) flachklopfen
    # data_flat bekommt die Form (N, src_grid_size)
    data_flat = data_array.reshape(-1, src_grid_size) 
    
    # --- 4. Matrix-Multiplikation (SpMV) ---
    # W hat Shape (dst_size, src_size). 
    # Wir multiplizieren W mit der Transponierten von data_flat und transponieren zurück.
    res_flat = W.dot(data_flat.T).T
    
    # --- 5. Auf das stereografische 2D-Zielgitter (ysize, xsize) reshapen ---
    shape_prefix = original_shape[:-1] 
    res_reshaped = res_flat.reshape(*shape_prefix, ysize, xsize)
    return res_reshaped