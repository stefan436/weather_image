# main.py

import numpy as np
from datetime import datetime, timezone

import config
from read_current_ICON_RUC import download_ruc, get_ruc_urls, create_prediction
from convert_to_mobile_format import generate_time_arrays_ruc, prepare_data_icon, export_data
from calculation import calculate_TSindex, calculate_BRN


today = datetime.now(timezone.utc)
time_now = today.replace(minute=0, second=0, microsecond=0)

# 1. Dynamischer Download und Verarbeitung in einer Schleife
predictions = {}

for product_name, params in config.PRODUCTS.items():
    urls = get_ruc_urls(set_past_date=config.set_past_date, steps_into_future=config.steps_into_future, base_url_ruc=params["base_url"])
    download_dir = download_ruc(urls, params["download_dir"])
    pred_raw, projection_ruc = create_prediction(download_dir, config.steps_into_future)
    
    # produktspezifischen NoData-Wert maskieren
    pred_masked = np.where(pred_raw == params["nodata"], np.nan, pred_raw)
    
    # Resultat im Dictionary unter dem Produktnamen speichern
    predictions[product_name] = pred_masked

# 2. Spezifische Index-Berechnung mit den gesammelten Daten
final_pred = calculate_TSindex(
    cape=predictions["CAPE_MU"], 
    cin=predictions["CIN_MU"], 
    cape_ref=config.CAPE_MU_ref, 
    cin_ref=config.CIN_MU_ref
)

# BRN berechnen (nutzt die Arrays direkt aus dem predictions-Dictionary)
brn_pred = calculate_BRN(
    cape=predictions["CAPE_MU"],
    wshear_u=predictions["WSHEAR_U"],
    wshear_v=predictions["WSHEAR_V"]
)

# 3. Export der Daten
total_frames = final_pred.shape[0]
absolute_time_array, relative_time_array = generate_time_arrays_ruc(total_frames, time_now)

# TS-Index für das Rasterbild
da_web_ts, leaflet_bounds, da_mask_web, _ = prepare_data_icon(
    final_pred=final_pred, 
    projection_ruc=projection_ruc, 
    time_array=absolute_time_array
)

# BRN-Daten verarbeiten. Wir brauchen hier das 4326-Array (Rückgabewert 4)
_, _, _, da_brn_4326 = prepare_data_icon(
    final_pred=brn_pred, 
    projection_ruc=projection_ruc, 
    time_array=absolute_time_array
)

export_data(
    da_web=da_web_ts, 
    da_brn_4326=da_brn_4326, 
    leaflet_bounds=leaflet_bounds, 
    da_mask_web=da_mask_web, 
    relative_time_array=relative_time_array
)

