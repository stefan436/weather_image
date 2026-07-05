import numpy as np
import glob
import os
import xarray as xr
from datetime import datetime, timezone
from cdo import Cdo
from time import time

# Deine eigenen Module
from blending_engine import run_steps_blending
from visualisation import animate_blended_forecast
from read_past_radar import get_radar_urls, download_radar, create_radar, load_coordinates
from read_current_ICON_RUC import get_ruc_urls, download_ruc, create_prediction, save_pred_to_netcdf
from alignment import align_ruc_like_cdo_remap
from config import *
from validation import get_ground_truth_urls, calculate_validation_scores, plot_validation_results
from convert_to_mobile_format import prepare_data, export_data

cdo = Cdo()

def main():
    total_start_time = time()
    print(f"--- 1. Lade Radar Historie (Letzte {hist_time_steps * 5} Minuten) ---")
    
    radar_urls, latest_RV_time = get_radar_urls(hist_time_steps, set_past_date=set_past_date)
    radar_folder = download_radar(radar_urls)
    
    # radar_history hat nun Shape (9, 1200, 1100)
    radar_history, projection_dict_rv, no_rain_rv= create_radar(radar_folder, hist_time_steps)
    
    print("\n--- 2. Lade NWP (ICON-D2 RUC) Vorhersagen ---")
    ruc_urls = get_ruc_urls(set_past_date=set_past_date, RV_time=latest_RV_time, steps_into_future=(forecast_length // step_size) + 1)
    ruc_folder = download_ruc(ruc_urls)
    prediction_ruc, projection_ruc, no_rain_ruc = create_prediction(ruc_folder, steps_into_future=(forecast_length // step_size) + 1)
    print(f"Download and extract data time: {time()-total_start_time}")
    
    if not (no_rain_rv and no_rain_ruc):
        final_prediction_ruc = align_ruc_like_cdo_remap(WEIGHTS_FILE, prediction_ruc)
        
        # Zielminuten definieren: 5, 10, 15, ..., 120
        target_minutes = np.arange(forecast_step_size, forecast_length + forecast_step_size, forecast_step_size)

        print("\n--- 3. Finales STEPS Blending ---")
        # pySTEPS Vorhersage startet (index 0) bei T+5
        blended_forecast_mmh, valid_RV_mask = run_steps_blending(radar_history, final_prediction_ruc, target_minutes, pase_correction_nwp_rv)
        blended_forecast_mmh = np.concatenate(
            [radar_history[-1][np.newaxis, ...], blended_forecast_mmh],
            axis=0,
        )
        forecast_minutes = np.arange(0, forecast_length + forecast_step_size, forecast_step_size)
        print(f"Shape des Blended Outputs: {blended_forecast_mmh.shape} (Zeitpunkte, Y, X)")
        print(f"Totale Dauer der Erstellung der Vorhersage: {time()-total_start_time}")
        
    else:
        print("\n--- Kein Regen erwartet. Generiere leere Vorhersage-Frames ---")
        n_timesteps = (forecast_length // step_size) + 1
        blended_forecast_mmh = np.zeros((n_timesteps, 1200, 1100), dtype=np.float32)
        # Radar-Maske trotzdem aus dem letzten Frame ableiten
        valid_RV_mask = ~np.isnan(radar_history[-1, :, :])

    print("\n--- 4. Export Forecast ---")
    xr_dataset, leaflet_bounds, reprojected_mask = prepare_data(blended_forecast_mmh, projection_dict_rv, latest_RV_time, valid_RV_mask)
    export_data(xr_dataset, leaflet_bounds, reprojected_mask)
    
    print("\n--- 5. Visualisierung ---")
    # animate_blended_forecast(blended_forecast_mmh, lat2d, lon2d, forecast_minutes, save_ani=save_final_animation, save_path="steps_forecast.gif")

    if validate:
        print("\n--- 6. Validierung (Hindcast) ---")
        # Validierung ergibt nur Sinn, wenn wir ein historisches Datum haben 
        # ODER wenn in Echtzeit bereits genügend Zeit vergangen ist (was beim Live-Run nicht der Fall ist)
        if set_past_date is not None:
            print(f"Hole Ground Truth Radardaten ab T0 ({latest_RV_time})...")
            
            # 1. URLs für die Zukunft generieren (passend zu forecast_minutes)
            gt_urls = get_ground_truth_urls(latest_RV_time, forecast_minutes)
            
            # 2. Download und Einlesen (Nutzt deine bestehenden Funktionen)
            gt_folder = download_radar(gt_urls)
            # Wir übergeben len(forecast_minutes) an hist_time_steps, da wir genauso viele Frames wie Zielminuten haben
            ground_truth_film, _, _ = create_radar(gt_folder, hist_time_steps=len(forecast_minutes))
            
            # 3. Metriken berechnen
            # Threshold 0.1 mm/h trennt "Regen" von "Kein Regen"
            scores = calculate_validation_scores(blended_forecast_mmh, ground_truth_film, forecast_minutes, threshold=0.1, spatial_scale=10)
            
            # 4. Plotten
            plot_validation_results(scores, forecast_minutes, save_path="blending_validation.png")
                
        else:
            print("Live-Modus aktiv ('set_past_date = None'). Ground-Truth für Validierung noch nicht verfügbar.")

if __name__ == "__main__":
    main()