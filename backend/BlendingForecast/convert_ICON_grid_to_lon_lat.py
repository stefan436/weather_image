import numpy as np
import xarray as xr
import pyproj
import os
from cdo import Cdo

cdo = Cdo()

# --- Dateipfade definieren (analog zur Arbeitsweise im DWD-Skript) ---
TARGET_GRID_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/ICON_grid_conversion/transformed_icon_grid.txt'   # Entspricht der TARGET_GRID_DESCRIPTION im PDF
WEIGHTS_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/ICON_grid_conversion/weights_icon2stere_con.nc'  # Die zu berechnenden Interpolationsgewichte
IN_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/temp_model_data.nc'         # Die eigentlichen Modelldaten

# =========================================================
# VORBEREITUNG: Zielgitter-Datei erstellen (Ersetzt die Textdatei aus dem PDF)
# =========================================================
# Da CDO bei stereografischen Projektionen mit einer simplen Textdatei 
# wie im PDF (S. 5) scheitert, erstellen wir das Zielgitter als NetCDF.
if not os.path.exists(TARGET_GRID_FILE):
    proj_dict = {
        'projdef': '+proj=stere +lat_ts=60 +lat_0=90 +lon_0=10 +x_0=543196.83521776402 +y_0=3622588.8619310022 +units=m +a=6378137 +b=6356752.3142451802 +no_defs',
        'xscale': 1000.0, 'xsize': 1100, 'yscale': 1000.0, 'ysize': 1200
    }
    projdef = proj_dict['projdef']
    p = pyproj.Proj(projdef)
    
    # Berechne den X/Y Startpunkt (Untere linke Ecke, LL)
    x_start, y_start = p(3.566994635, 45.696425377)
    
    # CDO Grid Description Format
    grid_desc = f"""gridtype  = projection
    xsize     = {int(proj_dict['xsize'])}
    ysize     = {int(proj_dict['ysize'])}
    xfirst    = {x_start:.4f}
    xinc      = {proj_dict['xscale']:.4f}
    yfirst    = {y_start:.4f}
    yinc      = {proj_dict['yscale']:.4f}
    grid_mapping_name = polar_stereographic
    proj_params = "{projdef}"
    """
    
    with open(TARGET_GRID_FILE, "w") as f:
        f.write(grid_desc)
    
    print(f"{TARGET_GRID_FILE} erstellt.")


# =========================================================
# SCHRITT 1: Gewichte einmalig berechnen
# =========================================================
if not os.path.exists(WEIGHTS_FILE):
    print("Berechne konservative Interpolationsgewichte (kann etwas dauern)...")
    
    # Wir übergeben nun direkt die IN_FILE, da diese alle Gitter-Metadaten enthält!
    cdo.gencon(TARGET_GRID_FILE, input=IN_FILE, output=WEIGHTS_FILE)
    print(f"Gewichte erfolgreich in {WEIGHTS_FILE} gespeichert.")


