from datetime import datetime, timezone
# RUC Data
hist_time_steps = 4      # wie viele radarbilder aus der vergangenheit genutzt werden um pySTEPS vorhersage zu machen. 5 min schritte --> 3 = T-10, T-5, T+0
hist_radar_film_steps = 24     # Für das Frontend (Letzte 2 Stunden inkl. T0)
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

# COORD_BIN_PATH = r'../../../docs/data/coords_radarcomposite_rv.bin'
# ICON_GRID_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/icon_grid_0047_R19B07_L.nc'      # Dein unstrukturiertes Quellgitter
# TARGET_GRID_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/ICON_grid_conversion/transformed_icon_grid.txt'   # Entspricht der TARGET_GRID_DESCRIPTION im PDF
WEIGHTS_FILE = r'./data/ICON_grid_conversion/weights_icon2stere_con.nc'  # Die zu berechnenden Interpolationsgewichte
# IN_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/temp_model_data.nc'         # Die eigentlichen Modelldaten
# OUT_FILE = r'/home/stefan/Schreibtisch/Coding/Wetterinfo/Wetterinfo/advanced_radar/pysteps/Blending/data/regridded_ICON_data.nc'           # Das finale Ergebnis


# export data
# Format: (Untergrenze_Wert, (R, G, B))
# Alles unter dem ersten Wert (hier 0.25) wird automatisch komplett transparent.
radarColorLevels = [
    (0.25,  (140, 189, 255)),  # #8CBDFF (0.25 - 0.5 mm/h)
    (0.5,   (16,  92,  255)),  # #105CFF (0.5 - 1.0 mm/h)
    (1.0,   (0,   144, 192)),  # #0090C0 (1.0 - 2.5 mm/h)
    (2.5,   (0,   176, 106)),  # #00B06A (2.5 - 5.0 mm/h)
    (5.0,   (0,   208, 0)),    # #00D000 (5.0 - 7.5 mm/h)   - Anker Grün
    (7.5,   (128, 255, 0)),    # #80FF00 (7.5 - 10.0 mm/h)
    (10.0,  (227, 227, 0)),    # #E3E300 (10 - 15 mm/h)     - Anker Gelb
    (15.0,  (255, 200, 0)),    # #FFC800 (15 - 20 mm/h)
    (20.0,  (255, 170, 0)),    # #FFAA00 (20 - 25 mm/h)     - Start Orange
    (25.0,  (255, 140, 0)),    # #FF8C00 (25 - 30 mm/h)
    (30.0,  (255, 134, 0)),    # #FF8600 (30 - 35 mm/h)
    (35.0,  (255, 128, 0)),    # #FF8000 (35 - 40 mm/h)
    (40.0,  (255, 122, 0)),    # #FF7A00 (40 - 45 mm/h)
    (45.0,  (255, 116, 0)),    # #FF7400 (45 - 50 mm/h)
    (50.0,  (255, 110, 0)),    # #FF6E00 (50 - 55 mm/h)     <-- Ab hier: Werte > 50
    (55.0,  (255, 104, 0)),    # #FF6800 (55 - 60 mm/h)
    (60.0,  (255, 98,  0)),    # #FF6200 (60 - 65 mm/h)
    (65.0,  (255, 92,  0)),    # #FF5C00 (65 - 70 mm/h)
    (70.0,  (255, 86,  0)),    # #FF5600 (70 - 75 mm/h)
    (75.0,  (255, 80,  0)),    # #FF5000 (75 - 80 mm/h)
    (80.0,  (253, 76,  0)),    # #FD4C00 (80 - 85 mm/h)
    (85.0,  (250, 67,  0)),    # #FA4300 (85 - 90 mm/h)
    (90.0,  (248, 59,  0)),    # #F83B00 (90 - 95 mm/h)
    (95.0,  (245, 48,  0)),    # #F53000 (95 - 100 mm/h)
    (100.0, (243, 40,  0)),    # #F32800 (100 - 105 mm/h)   - Dunkelorange/Rot
    (105.0, (236, 20,  0)),    # #EC1400 (105 - 110 mm/h)
    (110.0, (230, 0,   0)),    # #E60000 (110 - 115 mm/h)   - Anker Rot
    (115.0, (203, 0,   38)),   # #CB0026 (115 - 120 mm/h)
    (120.0, (176, 0,   66)),   # #B00042 (120 - 130 mm/h)
    (130.0, (149, 0,   94)),   # #95005E (130 - 140 mm/h)
    (140.0, (122, 0,   122)),  # #7A007A (> 140 mm/h)       - Anker Violett
]

save_path_webp = "./data/Forecast/frames/radar_frame_"
url_webp = "/backend/BlendingForecast/data/Forecast/frames/radar_frame_"
meta_json_path = "./data/Forecast/meta.json"


