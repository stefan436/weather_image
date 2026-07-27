import numpy as np
from datetime import datetime, timezone

import config
from read_current_ICON_RUC import download_ruc, get_ruc_urls, create_prediction
from convert_to_mobile_format import generate_time_arrays_ruc, prepare_data_icon, export_data


def calculate_TSindex(cape, cin, cape_ref, cin_ref):
    """
    Berechnet die Kombination von a und b über die Formel:
    (cape / cape_ref) * exp(-cin / cin_ref)
    """
    return (cape / cape_ref) * np.exp(-cin / cin_ref)


today = datetime.now(timezone.utc)
time_now = today.replace(minute=0, second=0, microsecond=0)

# 1. Dynamischer Download und Verarbeitung in einer Schleife
predictions = {}

for product_name, params in config.PRODUCTS.items():
    # URL dynamisch aus dem Produktnamen bauen
    base_url = f"https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/{product_name}/r/"
    
    urls = get_ruc_urls(set_past_date=None, steps_into_future=config.steps_into_future, base_url_ruc=base_url)
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

# 3. Export der Daten
total_frames = final_pred.shape[0]
absolute_time_array, relative_time_array = generate_time_arrays_ruc(total_frames, time_now)

da_web, leaflet_bounds, da_mask_web = prepare_data_icon(
    final_pred=final_pred, 
    projection_ruc=projection_ruc, 
    time_array=absolute_time_array
)

export_data(
    da_web=da_web, 
    leaflet_bounds=leaflet_bounds, 
    da_mask_web=da_mask_web, 
    relative_time_array=relative_time_array
)

















# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

# # 1. Geografische Ausdehnung (Bounding Box) aus den Metadaten extrahieren
# lons = projection_ruc['cell_lon']
# lats = projection_ruc['cell_lat']
# extent = [lons.min(), lons.max(), lats.min(), lats.max()]

# # 2. Daten für imshow vorbereiten
# # np.mgrid generiert die Daten im Format (lon, lat) bzw. (x, y). 
# # plt.imshow erwartet Bilddaten aber im Format (Zeilen, Spalten) bzw. (y, x).
# # Daher müssen wir die Matrix mit .T (Transpose) stürzen.
# data_to_plot = final_pred[0].T

# # 3. Karten-Leinwand mit PlateCarree-Projektion erstellen
# fig = plt.figure(figsize=(12, 10))
# ax = plt.axes(projection=ccrs.PlateCarree())

# # 4. Geografische Merkmale hinzufügen
# ax.set_extent(extent, crs=ccrs.PlateCarree())
# ax.add_feature(cfeature.BORDERS, linewidth=0.8, edgecolor='black')
# ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='black')

# # 5. Daten plotten
# # origin='lower' ist essenziell, da Breitengrade von Süd nach Nord (unten nach oben) ansteigen
# im = ax.imshow(
#     data_to_plot, 
#     origin='lower',
#     extent=extent, 
#     transform=ccrs.PlateCarree(),
#     cmap='viridis',  # Eine Standard-Colormap, die gut für Metriken skaliert
#     alpha=0.8        # Leichte Transparenz, damit die Kartengrenzen sichtbar bleiben
# )

# # 6. Beschriftungen und Farbskala
# plt.colorbar(im, ax=ax, label="Werte für TSindex", shrink=0.7)
# plt.title(f"ICON-D2 RUC Vorhersage: TSindex (T+0)\nZeitpunkt: {time_now.strftime('%Y-%m-%d %H:%M')} UTC", fontsize=14)

# plt.show()