# calculate.py

import numpy as np

def calculate_TSindex(cape, cin, cape_ref, cin_ref):
    """
    Berechnet die Kombination von a und b über die Formel:
    (cape / cape_ref) * exp(-cin / cin_ref) * 10
    """
    # 1. Term berechnen: exp(-cin / cin_ref)
    cin_factor = np.exp(-cin / cin_ref)
    
    # 2. Wo CIN ein NaN war, setzen wir den Dämpfungsfaktor auf 1.0 (keine Hemmung)
    cin_factor = np.where(np.isnan(cin_factor), 1.0, cin_factor)
    
    # 3. TS-Index berechnen
    ts_index = (cape / cape_ref) * cin_factor * 100
    # * 100 für bessere lesbarkeit
    
    return ts_index

def calculate_BRN(cape, wshear_u, wshear_v):
    """
    Berechnet die Bulk Richardson Number (BRN).
    Setzt CAPE ins Verhältnis zur kinetischen Energie der vertikalen Windscherung.
    """
    epsilon = 1e-6
    
    # Berechnung der massenspezifischen kinetischen Energie der Scherung
    shear_kinetic_energy = 0.5 * (wshear_u**2 + wshear_v**2)
    
    # BRN berechnen
    brn_raw = cape / (shear_kinetic_energy + epsilon)

    # Werte kappen, um Singularitäten zu eliminieren
    brn_pred = np.clip(brn_raw, a_min=0, a_max=200)
        
    return brn_pred