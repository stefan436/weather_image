# config.py
from datetime import datetime
set_past_date = None # datetime(2026, 7, 27, 16, 0)

# include wind as dampening (especially wind shear)? WSHEAR_U, WSHEAR_V     $$BRN = \frac{CAPE}{0.5 \cdot (\Delta U^2 + \Delta V^2)}$$  warum durch 0.5 teilen? BRN zur klassifikation

step_size = 60          # in min
steps_into_future = 16

# grid_file = './data/icon_grid_0047_R19B07_L.nc'
grid_file = '/WWW/users/ge47fab/weather_data/pySTEPS_data/icon_grid_0047_R19B07_L.nc'
num_workers = 6

CAPE_MU_ref = 1000
CIN_MU_ref = 45

# Dynamische Konfiguration für alle herunterzuladenden Produkte
PRODUCTS = {
    "CAPE_MU": {
        "nodata": 9999.0,
        # "download_dir": "./data/CAPE_MU/",
        "download_dir": "/scratch/ge47fab/Wetter-data/TSindex_data/CAPE_MU/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/CAPE_MU/r/"
    },
    "CIN_MU": {
        "nodata": 9999.0,
        # "download_dir": "./data/CIN_MU/",
        "download_dir": "/scratch/ge47fab/Wetter-data/TSindex_data/CIN_MU/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/CIN_MU/r/"
    },
    "WSHEAR_V": {
        "nodata": 9999.0,
        # "download_dir": "./data/WSHEAR_V",
        "download_dir": "/scratch/ge47fab/Wetter-data/TSindex_data/WSHEAR_V/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/WSHEAR_V/lvt1/103/lv1/6000/r/"
    },
    "WSHEAR_U": {
        "nodata": 9999.0,
        # "download_dir": "./data/WSHEAR_U",
        "download_dir": "/scratch/ge47fab/Wetter-data/TSindex_data/WSHEAR_U/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/WSHEAR_U/lvt1/103/lv1/6000/r/"
    }
}

# export data
# Format: (Untergrenze_Wert, (R, G, B))
# Alles unter dem ersten Wert (hier 0.25) wird automatisch komplett transparent.
indexColorLevels = [
    (0.10, (140, 189, 255)),  # #8CBDFF
    (0.20, (16,  92,  255)),  # #105CFF
    (0.30, (0,   144, 192)),  # #0090C0
    (0.40, (0,   176, 106)),  # #00B06A
    (0.50, (0,   208, 0)),    # #00D000
    (0.60, (128, 255, 0)),    # #80FF00
    (0.70, (227, 227, 0)),    # #E3E300
    (0.80, (255, 200, 0)),    # #FFC800
    (0.90, (255, 170, 0)),    # #FFAA00
    (1.00, (255, 140, 0)),    # #FF8C00
    (1.10, (255, 134, 0)),    # #FF8600
    (1.20, (255, 128, 0)),    # #FF8000
    (1.30, (255, 122, 0)),    # #FF7A00
    (1.40, (255, 116, 0)),    # #FF7400
    (1.50, (255, 110, 0)),    # #FF6E00
    (1.60, (255, 104, 0)),    # #FF6800
    (1.70, (255, 98,  0)),    # #FF6200
    (1.80, (255, 92,  0)),    # #FF5C00
    (1.90, (255, 86,  0)),    # #FF5600
    (2.00, (255, 80,  0)),    # #FF5000
    (2.10, (253, 76,  0)),    # #FD4C00
    (2.20, (250, 67,  0)),    # #FA4300
    (2.30, (248, 59,  0)),    # #F83B00
    (2.40, (245, 48,  0)),    # #F53000
    (2.50, (243, 40,  0)),    # #F32800
    (2.75, (236, 20,  0)),    # #EC1400
    (3.00, (230, 0,   0)),    # #E60000
    (3.25, (203, 0,   38)),   # #CB0026
    (3.50, (176, 0,   66)),   # #B00042
    (3.75, (149, 0,   94)),   # #95005E
    (4.00, (122, 0,   122)),  # #7A007A
]

# save_path_webp = "./data/Forecast/frames/radar_frame_"
# url_webp = "/backend/TSindex/data/Forecast/frames/radar_frame_"
# meta_json_path = "./data/Forecast/meta.json"

save_path_webp = "/WWW/users/ge47fab/weather_data/TSindex_data/Forecast/frames/radar_frame_"
url_webp = "https://users.ph.nat.tum.de/ge47fab/weather_data/TSindex_data/Forecast/frames/radar_frame_"
meta_json_path = "/WWW/users/ge47fab/weather_data/TSindex_data/Forecast/meta.json"
