import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

# Korrigierte PySTEPS Importe: Direkter Import der Kalkulationsfunktionen
from pysteps.verification.detcatscores import det_cat_fct
from pysteps.verification.detcontscores import det_cont_fct
from pysteps.verification.spatialscores import fss

from read_past_radar import download_radar, create_radar
from config import base_url_rv, product_rv

def get_ground_truth_urls(base_time, target_minutes):
    """
    Generiert die Radar-URLs für die tatsächliche Zukunft (Ground Truth).
    Wichtig: base_time ist die Zeit des letzten Radarbildes (T0).
    """
    url_list = []
    for minutes in target_minutes:
        t_future = base_time + timedelta(minutes=int(minutes))
        schritt_datum = t_future.strftime('%Y%m%d')
        schritt_uhrzeit = t_future.strftime('%H%M')
        
        bu = f"{base_url_rv}composite_{product_rv}_{schritt_datum}_{schritt_uhrzeit}.tar"
        url_list.append(bu)
        
    return url_list

def calculate_validation_scores(forecast_mmh, ground_truth_mmh, target_minutes, threshold=0.1, spatial_scale=10):
    """
    Berechnet deterministische, kategoriale und räumliche QPF-Scores.
    spatial_scale: Die Größe des Fensters für den FSS in Pixeln (10 Pixel = 10 km bei RV).
    """
    results = {
        'CSI': [], 'FAR': [], 'POD': [], 
        'RMSE': [], 'MAE': [], 'FSS': []
    }
    
    print("\n--- Validiere Vorhersage gegen Ground Truth (Dynamische Maskierung) ---")
    
    for i, lead_time in enumerate(target_minutes):
        fct = forecast_mmh[i]
        obs = ground_truth_mmh[i]
        
        # 1. Dynamische Radar-Maske generieren
        # Jeder Pixel, der im Ground-Truth-Radarbild einen gültigen Wert hat
        valid_radar_mask = ~np.isnan(obs)
        
        # 2. Pixelgenaue Scores: Nur exakt die validen Pixel betrachten (1D-Arrays extrahieren)
        # Verhindert True-Negative-Inflation und künstliche False-Alarms durch Out-of-Bounds-RUC-Daten
        fct_valid_1d = fct[valid_radar_mask]
        obs_valid_1d = obs[valid_radar_mask]
        
        # Sicherheitsnetz: Eventuelle NaNs im Vorhersagefeld (z.B. am Rand des Warping-Feldes) auf 0 setzen
        fct_valid_1d = np.nan_to_num(fct_valid_1d, nan=0.0)
        
        # Kategoriale Scores (Punktgenau)
        cat_scores = det_cat_fct(fct_valid_1d, obs_valid_1d, thr=threshold)
        results['CSI'].append(cat_scores['CSI'])
        results['FAR'].append(cat_scores['FAR'])
        results['POD'].append(cat_scores['POD'])
        
        # Kontinuierliche Scores (Punktgenau)
        cont_scores = det_cont_fct(fct_valid_1d, obs_valid_1d)
        results['RMSE'].append(cont_scores['RMSE'])
        results['MAE'].append(cont_scores['MAE'])
        
        # 3. Fractions Skill Score (Räumlich / 2D)
        # FSS braucht die 2D-Struktur. Damit PySTEPS bei der Faltung (FFT/Uniform Filter) nicht über NaNs stolpert,
        # setzen wir außerhalb des gültigen Radarbereichs BEIDE Felder strikt auf 0.
        fct_fss = np.nan_to_num(fct, nan=0.0)
        obs_fss = np.nan_to_num(obs, nan=0.0)
        
        fct_fss[~valid_radar_mask] = 0.0
        obs_fss[~valid_radar_mask] = 0.0
        
        fss_score = fss(fct_fss, obs_fss, thr=threshold, scale=spatial_scale)
        results['FSS'].append(fss_score)
        
        print(f"+{lead_time} Min: CSI={cat_scores['CSI']:.3f}, FAR={cat_scores['FAR']:.3f}, RMSE={cont_scores['RMSE']:.2f}, FSS({spatial_scale}km)={fss_score:.3f}")
        
    return results

def plot_validation_results(results, target_minutes, save_path="validation_scores.png"):
    """Visualisiert die Performance der Vorhersage über die Lead-Time."""
    fig, axs = plt.subplots(1, 3, figsize=(18, 5))
    
    # Kategoriale Scores
    axs[0].plot(target_minutes, results['CSI'], marker='o', label='CSI (Critical Success Index)', color='blue')
    axs[0].plot(target_minutes, results['POD'], marker='s', label='POD (Probability of Detection)', color='green')
    axs[0].plot(target_minutes, results['FAR'], marker='^', label='FAR (False Alarm Ratio)', color='red')
    axs[0].set_ylim([0, 1])
    axs[0].set_title('Pixelgenaue kategoriale Scores (> 0.1 mm/h)')
    axs[0].set_xlabel('Lead Time (Minuten)')
    axs[0].legend()
    axs[0].grid(True)
    
    # Fractions Skill Score
    axs[1].plot(target_minutes, results['FSS'], marker='d', color='purple', linewidth=2)
    axs[1].set_ylim([0, 1])
    axs[1].set_title('Fractions Skill Score (FSS)\n(Höher ist besser)')
    axs[1].set_xlabel('Lead Time (Minuten)')
    axs[1].grid(True)
    
    # Kontinuierliche Scores (Fehler)
    axs[2].plot(target_minutes, results['RMSE'], marker='o', color='darkred', label='RMSE')
    axs[2].plot(target_minutes, results['MAE'], marker='s', color='orange', label='MAE')
    axs[2].set_title('Vorhersagefehler [mm/h]')
    axs[2].set_xlabel('Lead Time (Minuten)')
    axs[2].legend()
    axs[2].grid(True)
    
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"\nValidierungsplot gespeichert unter: {save_path}")
    plt.show()