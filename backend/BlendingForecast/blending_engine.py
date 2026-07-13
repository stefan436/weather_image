import matplotlib.pyplot as plt
import numpy as np
import re
from datetime import datetime
import os
import cv2
from scipy.ndimage import distance_transform_edt
from pysteps.motion.lucaskanade import dense_lucaskanade
from pysteps.motion.vet import vet
from pysteps.blending.steps import forecast
from pysteps.utils import transformation
from concurrent.futures import ProcessPoolExecutor
import time

from config import num_workers, step_size, decay_tau, forecast_step_size
from visualisation import run_alignment_qa

import multiprocessing as mp

# Zwingt Python, frische Prozesse zu starten statt den Speicher zu kopieren
if mp.get_start_method(allow_none=True) != 'spawn':
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        pass


def run_steps_blending(radar_history, nwp_cube, target_minutes, rv_forecast, pase_correction=True):
    """
    Führt das quasi-deterministische pysteps STEPS-Blending durch.
    radar_history: Shape (hist_time_steps, Y, X)
    nwp_cube: Shape (N_steps, Y, X)
    """
    print("\nBereite Daten für PySteps vor (NaNs entfernen, dBR Transformation)...")
    # 1. Gültigen Radarbereich ermitteln, bevor NaNs überschrieben werden
    valid_radar_mask = ~np.isnan(radar_history[-1, :, :])
    
    # 2. NaN-Handling
    np.nan_to_num(radar_history, copy=False, nan=0.0)
    np.nan_to_num(nwp_cube, copy=False, nan=0.0)
    np.nan_to_num(rv_forecast, copy=False, nan=0.0)
    nwp_cube = np.flip(nwp_cube, axis=1)
    
    # 3. Transformation in dBR
    radar_dbr, _ = transformation.dB_transform(radar_history, threshold=0.1, zerovalue=-15.0)
    nwp_dbr, _ = transformation.dB_transform(nwp_cube, threshold=0.1, zerovalue=-15.0)
    rv_forecast_dbr, _ = transformation.dB_transform(rv_forecast, threshold=0.1, zerovalue=-15.0)
    
    # 4. Bewegungsfelder berechnen
    print("Berechne Phase Correction (VET Bewegungsvektoren) ...")

    if pase_correction:  
        # Berechne verschiebung zwischen akteullem Radar Bild RV und Vorhersage des RUC für T+0
        s= time.time()
        # SCHRITT 1: Symmetrische Maskierung
        # NWP-Feld außerhalb des Radars ausblenden, um RUC Daten außerhalb von RV bereich zu beeinflussen
        nwp_dbr_for_vet = np.copy(nwp_dbr[0, :, :])
        nwp_dbr_for_vet[~valid_radar_mask] = -15.0
        radar_dbr_for_vet = radar_dbr[-1, :, :] # Ist außerhalb bereits -15.0
        
        alignment_field = vet(np.stack([nwp_dbr_for_vet, radar_dbr_for_vet], axis=0),
                              sectors=((32, 16, 4, 2), (32, 16, 4, 2)),
                              verbose=False)
        print(f"duration alignment field calculation with vet: {time.time()-s:.2f}s")

        # SCHRITT 2: Extrapolation der Vektoren
        # Wir übertragen die synoptische Verschiebung auf die Modellränder
        # alignment_field[0] = X-Komponenten, alignment_field[1] = Y-Komponenten
        align_x = alignment_field[0, :, :]
        align_y = alignment_field[1, :, :]
        
        # Setze Vektoren im Randbereich zurück, da sie künstlich null sind
        align_x[~valid_radar_mask] = np.nan
        align_y[~valid_radar_mask] = np.nan
        
        # invalid_mask ist True, wo Daten fehlen (~valid_radar_mask)
        _, indices = distance_transform_edt(~valid_radar_mask, return_indices=True)

        # indices[0] enthält die Y-Koordinaten der nächsten gültigen Pixel, indices[1] die X-Koordinaten
        align_x[~valid_radar_mask] = align_x[tuple(indices)][~valid_radar_mask]
        align_y[~valid_radar_mask] = align_y[tuple(indices)][~valid_radar_mask]
                    
        alignment_field[0, :, :] = align_x
        alignment_field[1, :, :] = align_y
        
        
        # Koordinatengitter erstellen (Form: Y, X)
        height, width = nwp_dbr.shape[1], nwp_dbr.shape[2]
        # y_grid ist eine matrix (array) der shape (height, width) und beinhaltet als einträge immer den zeilen index 
        # e.g. [[0, 0, 0, 0],
        #       [1, 1, 1, 1],
        #       [2, 2, 2, 2]]
        y_grid, x_grid = np.indices((height, width))

        # Jeden Zeitschritt des NWP-Modells einzeln verschieben
        nwp_dbr_aligned = np.empty_like(nwp_dbr)
        
        # Parameter für das exponentielle Abklingen
        # decay_tau ist die e-folding time in Minuten. 
        # Bei decay_tau Minuten ist das Gewicht bei ~0.37 (37% = 1/e) der ursprünglichen Verschiebung.

        for t_step in range(nwp_dbr.shape[0]):
            # Berechne die Lead-Time (time t) in Minuten für diesen NWP-Zeitschritt
            t = t_step * step_size
            
            # Berechne das Gewicht: w(t) = exp(-t / tau)
            weight = np.exp(-t / decay_tau)
            
            # Skaliere das Verschiebungsfeld für diesen spezifischen Zeitschritt
            current_align_y = alignment_field[1, :, :] * weight
            current_align_x = alignment_field[0, :, :] * weight
            
            # Quellkoordinaten berechnen (Backward Mapping)
            # y_grid gibt jeweils den index des Pixels (nur für y Komponente)
            # current_align_y (hat selbe shape wie y_grid) und gibt in jedem eintrag an wie weit dieser geshiftet (in y Komponente) wurde 
            # die Differenz gibt ein array bei dem jeder Pixel ein Index enthält welcher referenziert welcher Wert (aus dem verschobenen Bild) an den jeweiligen Pixel gehört
            src_y = (y_grid - current_align_y).astype(np.float32)
            src_x = (x_grid - current_align_x).astype(np.float32)
            # opencv needs float32
            
            nwp_dbr_aligned[t_step, :, :] = cv2.remap(
                nwp_dbr[t_step, :, :], src_x, src_y, 
                interpolation=cv2.INTER_LINEAR, 
                borderMode=cv2.BORDER_CONSTANT, 
                borderValue=-15.0               # für werte die aus dem/in das Bild geschoben werden --> werden auf zerovalue gesetzt --> kein Regen
            )
            
        # QA-Plot nur für T=0 ausführen (Gewicht ist hier 1.0)
        # run_alignment_qa(radar_dbr[-1, :, :], nwp_dbr[0, :, :], nwp_dbr_aligned[0, :, :], alignment_field, stride=40)

        nwp_dbr = nwp_dbr_aligned
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        # submit startet die Funktionen sofort asynchron im Hintergrund
        future_radar = executor.submit(dense_lucaskanade, radar_dbr)
        future_nwp = executor.submit(dense_lucaskanade, nwp_dbr[0:3])

        # .result() wartet, bis der jeweilige Kern fertig ist und holt das Ergebnis
        motion_radar = future_radar.result()
        motion_nwp = future_nwp.result()
    
    # 5. Dimensionen für PySteps anpassen
    precip_models_4d = nwp_dbr[np.newaxis, ...]
    # Das RV-Feld in 4D (n_ens_members, timesteps, Y, X) umwandeln
    precip_nowcast_4d = rv_forecast_dbr[np.newaxis, ...]
    
    n_timesteps = len(target_minutes)
    velocity_models_5d = np.repeat(motion_nwp[np.newaxis, np.newaxis, ...], n_timesteps + 1, axis=1)
    
    # Random Seed fixieren für Reproduzierbarkeit (entferne für ensemble Vorhersage)
    np.random.seed(42)
    
    # 6. STEPS Blending aufrufen
    print("Führe reproduzierbares STEPS Blending durch (mit Multithreading & optimierter FFT)...")
    s = time.time()
    blended_dbr = forecast(
        precip=radar_dbr,              
        precip_models=precip_models_4d,
        precip_nowcast=precip_nowcast_4d,          # Einspeisen der RV-Vorhersage
        nowcasting_method="external_nowcast",      # Überspringen der internen Extrapolation  
        velocity=motion_radar,              
        velocity_models=velocity_models_5d, 
        timesteps=n_timesteps,              
        timestep=forecast_step_size,                         
        issuetime=datetime.now(),           
        n_ens_members=1,
        n_cascade_levels=7,                    
        noise_method="nonparametric",       
        vel_pert_method=None,               
        kmperpixel=1.0,                     
        precip_thr=-15.0,
        num_workers=num_workers,                 # <-- Nutzt z.B. 4 CPU-Kerne für die FFT-Kaskaden
        fft_method="pyfftw"        # <-- Schnellere Fourier-Transformation
    )
    print(f"Forcast berechnung dauert: {time.time()-s}")
    
    # 7. Rücktransformation in mm/h
    blended_dbr = np.squeeze(blended_dbr, axis=0)
    blended_mmh, _ = transformation.dB_transform(blended_dbr, threshold=-15.0, inverse=True)
    return blended_mmh, valid_radar_mask




