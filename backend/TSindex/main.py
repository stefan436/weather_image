import numpy as np
from datetime import datetime, timezone

import config
from read_current_ICON_RUC import download_ruc, get_ruc_urls, create_prediction
from convert_to_mobile_format import generate_time_arrays_ruc, prepare_data_icon, export_data


def calculate_TSindex(cape, cin, cape_ref, cin_ref):
    """
    Berechnet die Kombination von a und b über die Formel:
    (cape / a_rcape_refef) * exp(-cin / cin_ref)
    
    Shapes:
    - cape, cin: (timestep, lat, lon)
    - cape_ref, cin_ref: Entweder Skalare, oder Arrays die zum Broadcasting passen 
                    (z. B. gleiches Shape oder (lat, lon))
    """
    # Vektoriierte Berechnung über alle Dimensionen hinweg
    result = (cape / cape_ref) * np.exp(-cin / cin_ref)
    
    return result


today = datetime.now(timezone.utc)
time_now = today.replace(minute=0, second=0, microsecond=0)

urls1 = get_ruc_urls(set_past_date=None, steps_into_future=config.steps_into_future, base_url_ruc=config.base_url_ruc1)
download_dir1 = download_ruc(urls1, config.download_dir_ruc1)
pred_cape_raw, projection_ruc = create_prediction(download_dir1, config.steps_into_future)
pred_cape = np.where(pred_cape_raw == 9999.0, np.nan, pred_cape_raw)

urls2 = get_ruc_urls(set_past_date=None, steps_into_future=config.steps_into_future, base_url_ruc=config.base_url_ruc2)
download_dir2 = download_ruc(urls2, config.download_dir_ruc2)
pred_cin_raw, projection_ruc = create_prediction(download_dir2, config.steps_into_future)
pred_cin = np.where(pred_cin_raw == 999.0, np.nan, pred_cin_raw)

final_pred = calculate_TSindex(pred_cape, pred_cin, config.cape_ref, config.cin_ref)

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