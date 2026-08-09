import os
from datetime import datetime
import numpy as np

# ==========================================
# CONFIGURATION MOSMIX & WARNMOS
# ==========================================

MOSMIX_URL = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz"
OUT_DIR = "./data/Forecast/mosmix_s/"
# OUT_DIR = "/WWW/users/ge47fab/weather_data/index/Forecast/mosmix_s/"
COORDS_JSON = "./data/mosmix_stationen_coords.json"
# COORDS_JSON = "/WWW/users/ge47fab/weather_data/mosmix_stationen_coords.json"

WARNMOS_DOWNLOAD_PATH = "./data/WarnMOS"
# WARNMOS_DOWNLOAD_PATH = "/scratch/ge47fab/Wetter-data/index-MCP/WarnMOS"
WARNMOS_BASE_URL = "https://opendata.dwd.de/weather/local_forecasts/warnmos/"

MOSMIX_TARGETS = {'TTT', 'Td', 'RR1c', 'Neff', 'DD', 'FF', 'FX1', 'wwM', 'ww', 'Rad1h'}
WARNMOS_TARGETS = ["cp", "lsp", "asnow", "W_GEW_01", "W_GEWSK_01", "U_GEWSW_01", "FZ", "FZRA", "FZRAX"]


# ==========================================
# CONFIGURATION Modified Convection Potential
# ==========================================

set_past_date = None # datetime(2026, 8, 8, 20, 0)

step_size = 60          # in min
steps_into_future = 16

grid_file = './data/icon_grid_0047_R19B07_L.nc'
# grid_file = '/WWW/users/ge47fab/weather_data/pySTEPS_data/icon_grid_0047_R19B07_L.nc'
num_workers = 6

CAPE_MU_ref = np.load('./data/cape_ref_2d.npy')
# CAPE_MU_ref = np.load('/WWW/users/ge47fab/weather_data/index/cape_ref_2d.npy')
CIN_MU_ref = np.load('./data/cin_ref_2d.npy')
# CIN_MU_ref = np.load('/WWW/users/ge47fab/weather_data/index/cin_ref_2d.npy')

# Dynamische Konfiguration für alle herunterzuladenden Produkte
PRODUCTS = {
    "CAPE_MU": {
        "nodata": 9999.0,
        "download_dir": "./data/CAPE_MU/",
        # "download_dir": "/scratch/ge47fab/Wetter-data/index-MCP/CAPE_MU/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/CAPE_MU/r/"
    },
    "CIN_MU": {
        "nodata": [9999.0, -999.9],
        "download_dir": "./data/CIN_MU/",
        # "download_dir": "/scratch/ge47fab/Wetter-data/index-MCP/CIN_MU/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/CIN_MU/r/"
    },
    "WSHEAR_V": {
        "nodata": 9999.0,
        "download_dir": "./data/WSHEAR_V",
        # "download_dir": "/scratch/ge47fab/Wetter-data/index-MCP/WSHEAR_V/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/WSHEAR_V/lvt1/103/lv1/6000/r/"
    },
    "WSHEAR_U": {
        "nodata": 9999.0,
        "download_dir": "./data/WSHEAR_U",
        # "download_dir": "/scratch/ge47fab/Wetter-data/index-MCP/WSHEAR_U/",
        "base_url": "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/WSHEAR_U/lvt1/103/lv1/6000/r/"
    }
}

# export data
# Format: (Untergrenze_Wert, (R, G, B))
# Alles unter dem ersten Wert (hier 0.25) wird automatisch komplett transparent.
indexColorLevels = [
    # (Prozent %, RGB-Tupel)
    (12.94, (140, 189, 255)),  # #8CBDFF 
    (24.21, (16,  92,  255)),  # #105CFF 
    (34.03, (0,   144, 192)),  # #0090C0 
    (42.57, (0,   176, 106)),  # #00B06A 
    (50.00, (0,   208, 0)),    # #00D000 
    (56.47, (128, 255, 0)),    # #80FF00 
    (62.10, (227, 227, 0)),    # #E3E300 
    (67.00, (255, 200, 0)),    # #FFC800 
    (71.27, (255, 170, 0)),    # #FFAA00 
    (75.00, (255, 140, 0)),    # #FF8C00 
    (78.24, (255, 134, 0)),    # #FF8600 
    (81.06, (255, 128, 0)),    # #FF8000 
    (83.52, (255, 122, 0)),    # #FF7A00 
    (85.66, (255, 116, 0)),    # #FF7400 
    (87.52, (255, 110, 0)),    # #FF6E00 
    (89.14, (255, 104, 0)),    # #FF6800 
    (90.55, (255, 98,  0)),    # #FF6200 
    (91.77, (255, 92,  0)),    # #FF5C00 
    (92.84, (255, 86,  0)),    # #FF5600 
    (93.75, (255, 80,  0)),    # #FF5000 
    (94.56, (253, 76,  0)),    # #FD4C00 
    (95.26, (250, 67,  0)),    # #FA4300 
    (95.87, (248, 59,  0)),    # #F83B00 
    (96.41, (245, 48,  0)),    # #F53000 
    (96.88, (243, 40,  0)),    # #F32800 
    (97.80, (236, 20,  0)),    # #EC1400 
    (98.44, (230, 0,   0)),    # #E60000 
    (98.89, (203, 0,   38)),   # #CB0026 
    (99.22, (176, 0,   66)),   # #B00042 
    (99.45, (149, 0,   94)),   # #95005E 
    (99.61, (122, 0,   122)),  # #7A007A 
]

save_path_webp = "./data/Forecast/frames/radar_frame_"
url_webp = "/backend/index-MCP/data/Forecast/frames/radar_frame_"
meta_json_path = "./data/Forecast/meta.json"

# save_path_webp = "/WWW/users/ge47fab/weather_data/index/Forecast/frames/radar_frame_"
# url_webp = "https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/frames/radar_frame_"
# meta_json_path = "/WWW/users/ge47fab/weather_data/index/Forecast/meta.json"
