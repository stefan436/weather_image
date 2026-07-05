from datetime import datetime, timezone
# RUC Data
hist_time_steps = 4      # wie viele radarbilder aus der vergangenheit genutzt werden um pySTEPS vorhersage zu machen. 5 min schritte --> 3 = T-10, T-5, T+0
step_size = 5
product_ruc = 'TOT_PREC'
base_url_ruc = f'https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/{product_ruc}/r/'
grid_file = './data/icon_grid_0047_R19B07_L.nc'
download_dir_ruc = "./data/RUC"

# RV Data
product_rv = 'rv'
base_url_rv = f"https://opendata.dwd.de/weather/radar/composite/{product_rv}/"
download_dir_rv = "./data/RV"


# Main config
forecast_length = 60                    # length in min
forecast_step_size = 5                  # in min (nur 5 min funktioniert, da die RUC daten in 5 Min schritte sind; RUC Daten müssten auf zwischenschritte interpoliert werden)
pase_correction_nwp_rv = True

decay_tau = 60          # Was dieser Parameter macht --> blending_engine.py Zeile 96

save_final_animation = False
validate = True

num_workers = 6         # 10 oder 12 im backend (beobachte RAM)
set_past_date = None # datetime(2026, 7, 2, 23, 20, tzinfo=timezone.utc)    

COORD_BIN_PATH = r'../../../docs/data/coords_radarcomposite_rv.bin'
ICON_GRID_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/icon_grid_0047_R19B07_L.nc'      # Dein unstrukturiertes Quellgitter
TARGET_GRID_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/ICON_grid_conversion/transformed_icon_grid.txt'   # Entspricht der TARGET_GRID_DESCRIPTION im PDF
WEIGHTS_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/ICON_grid_conversion/weights_icon2stere_con.nc'  # Die zu berechnenden Interpolationsgewichte
IN_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/temp_model_data.nc'         # Die eigentlichen Modelldaten
OUT_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/regridded_ICON_data.nc'           # Das finale Ergebnis


# export data
# Format: (Untergrenze_Wert, (R, G, B))
# Alles unter dem ersten Wert (hier 0.25) wird automatisch komplett transparent.
radarColorLevels = [
    (0.25, (140, 189, 255)),  # #8CBDFF (0.25 - 0.5 mm/h)
    (0.5,  (78,  140, 255)),  # #4E8CFF (0.5 - 1 mm/h)
    (1.0,  (16,  92,  255)),  # #105CFF (1 - 2.5 mm/h)
    (2.5,  (0,   160, 160)),  # #00A0A0 (2.5 - 5 mm/h)
    (5.0,  (0,   208, 0)),    # #00D000 (5 - 7.5 mm/h)
    (7.5,  (128, 255, 0)),    # #80FF00 (7.5 - 10 mm/h)
    (10.0, (255, 255, 0)),    # #FFFF00 (10 - 15 mm/h)
    (15.0, (255, 200, 0)),    # #FFC800 (15 - 20 mm/h)
    (20.0, (255, 140, 0)),    # #FF8C00 (20 - 25 mm/h)
    (25.0, (255, 80,  0)),    # #FF5000 (25 - 40 mm/h)
    (40.0, (230, 0,   0)),    # #E60000 (40 - 60 mm/h)
    (60.0, (160, 0,   64)),    # #A00040 (60 - 100 mm/h)
    (100.0, (122, 0,   122)),  # #7A007A (> 100 mm/h)
]

save_path_webp = "./data/Forecast/frames/radar_frame_"
url_webp = "./../../../advanced_radar/pysteps/Blending/data/Forecast/frames/radar_frame_"
meta_json_path = "./data/Forecast/meta.json"


