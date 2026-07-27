# config.py

# include wind as dampening (especially wind shear)? WSHEAR_U, WSHEAR_V     $$BRN = \frac{CAPE}{0.5 \cdot (\Delta U^2 + \Delta V^2)}$$  warum durch 0.5 teilen? BRN zur klassifikation

step_size = 60          # in min
steps_into_future = 27

grid_file = './data/icon_grid_0047_R19B07_L.nc'
num_workers = 6

CAPE_MU_ref = 1000
CIN_MU_ref = 35

# Dynamische Konfiguration für alle herunterzuladenden Produkte
PRODUCTS = {
    "CAPE_MU": {
        "nodata": 9999.0,
        "download_dir": "./data/CAPE_MU/"
    },
    "CIN_MU": {
        "nodata": 999.0,
        "download_dir": "./data/CIN_MU/"
    }
}

# export data
# Format: (Untergrenze_Wert, (R, G, B))
# Alles unter dem ersten Wert (hier 0.25) wird automatisch komplett transparent.
indexColorLevels = [
    (0.05, (140, 189, 255)),  # #8CBDFF
    (0.10, (78,  140, 255)),  # #4E8CFF
    (0.20, (16,  92,  255)),  # #105CFF
    (0.35, (0,   160, 160)),  # #00A0A0
    (0.50, (0,   208, 0)),    # #00D000
    (0.65, (128, 255, 0)),    # #80FF00
    (0.80, (255, 255, 0)),    # #FFFF00
    (1.00, (255, 200, 0)),    # #FFC800
    (2.00, (255, 140, 0)),    # #FF8C00
    (3.00, (255, 80,  0)),    # #FF5000
    (4.00, (230, 0,   0)),    # #E60000
    (4.50, (160, 0,   64)),   # #A00040
    (5.00, (122, 0,   122)),  # #7A007A
]

save_path_webp = "./data/Forecast/frames/radar_frame_"
url_webp = "/backend/TSindex/data/Forecast/frames/radar_frame_"
meta_json_path = "./data/Forecast/meta.json"