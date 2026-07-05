import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt

def animate_blended_forecast(blended_data, lat2d, lon2d, target_minutes, save_ani=True, save_path="blended_forecast.gif"):
    """
    Erstellt eine georeferenzierte Animation der Blending-Vorhersage.
    """
    print("\n--- Visualisierung ---")
    print("Bereite Karte und Farbskalen vor...")

    # 1. Colormap definieren (wie im DWD-Radar-Komposit)
    levels = [0.25, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 40.0, 60.0, 100.0, 200.0]
    colors = [
        "#8CBDFF", "#4E8CFF", "#105CFF", "#00A0A0", "#00D000", 
        "#80FF00", "#FFFF00", "#FFC800", "#FF8C00", "#FF5000", 
        "#E60000", "#A00040", "#7A007A"
    ]
    cmap = mcolors.ListedColormap(colors)
    cmap.set_bad(color='none') # Setzt NaN-Werte (klares Wetter) auf transparent
    norm = mcolors.BoundaryNorm(levels, cmap.N)

    # 2. Geografische Grenzen für Cartopy ermitteln
    lon_min, lon_max = np.min(lon2d), np.max(lon2d)
    lat_min, lat_max = np.min(lat2d), np.max(lat2d)

    # 3. Plot initialisieren (OpenStreetMap als Hintergrund)
    osm_tiles = cimgt.OSM()
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(1, 1, 1, projection=osm_tiles.crs)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    ax.add_image(osm_tiles, 7)

    # 4. Leeres Mesh für Performance initialisieren
    # pcolormesh ist exakter für Gitterdaten als imshow
    mesh = ax.pcolormesh(
        lon2d, lat2d, np.full(lat2d.shape, np.nan), 
        transform=ccrs.PlateCarree(),
        cmap=cmap, norm=norm, shading='nearest', alpha=0.7, zorder=50
    )

    cbar = plt.colorbar(mesh, ax=ax, shrink=0.7, pad=0.05)
    cbar.set_label('Niederschlagsintensität [mm/h]')
    title_obj = plt.title('Lade Blending-Daten...')

    # 5. Update-Logik für die Frames
    def update(frame_idx):
        print(f"Rendere Vorhersage-Frame {frame_idx + 1}/{len(blended_data)} (+{target_minutes[frame_idx]} Min)...")
        
        # .copy() verhindert, dass wir das Original-Array im Speicher mit NaNs überschreiben
        data = blended_data[frame_idx].copy()
        data[data < 0.25] = np.nan 
        
        mesh.set_array(data.ravel())
        title_obj.set_text(f"Blended Forecast (Radar + ICON-D2)\nVorhersage: +{target_minutes[frame_idx]} Minuten")
        
        return mesh, title_obj

    # 6. Animation generieren und speichern
    print("Starte Rendering der Animation (das kann bei Ganz Deutschland etwas dauern)...")
    ani = animation.FuncAnimation(fig, update, frames=len(blended_data), blit=False, repeat=True)

    if save_ani:
        print(f"Speichere Animation als '{save_path}' ...")
        ani.save(save_path, fps=4)
        print("Animation erfolgreich erstellt!")
    
    plt.show()
    
    return ani


def check_radar_animation(radar_film, interval=2000):
    """
    Spielt den 3D-Tensor als Animation ab.
    interval: Zeit zwischen den Frames in Millisekunden (200ms = 5 Frames/Sekunde)
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Erste Matrix als Startbild anzeigen
    # 'viridis' oder 'inferno' eignen sich gut für Radar-Intensitäten
    im = ax.imshow(radar_film[0], cmap='viridis', origin='upper')
    ax.set_title("Frame 0")
    fig.colorbar(im, label="Intensität")

    # Update-Funktion für jeden Zeitschritt
    def update(frame_index):
        im.set_array(radar_film[frame_index])
        ax.set_title(f"Frame {frame_index}")
        return [im]

    # Animation erstellen
    ani = animation.FuncAnimation(
        fig, 
        update, 
        frames=len(radar_film), 
        interval=interval, 
        blit=True
    )

    plt.show()
    


def run_alignment_qa(radar_dbr, nwp_dbr_original, nwp_dbr_aligned, alignment_field, stride=40):
    """
    Führt die visuelle Quality Assurance für das NWP-Radar Alignment durch.
    
    radar_dbr: Das Radar-Ground-Truth Bild [Y, X]
    nwp_dbr_original: Das unkorrigierte NWP-Bild [Y, X]
    nwp_dbr_aligned: Das via VET & cv2 gewarpte NWP-Bild [Y, X]
    alignment_field: Das DVF von VET [2, Y, X] (Index 0: X-Verschiebung, Index 1: Y-Verschiebung)
    stride: Ausdünnungsfaktor für die Vektorpfeile (40 bedeutet: nur jeden 40. Pixel plotten)
    """
    # Vorbereitung der Vektoren für den Quiver-Plot (Ausdünnung via Slicing)
    u = alignment_field[0, ::stride, ::stride]
    v = alignment_field[1, ::stride, ::stride]
    
    # Koordinatengitter für den Quiver-Plot erstellen
    y_shape, x_shape = radar_dbr.shape
    x_coords, y_coords = np.meshgrid(np.arange(0, x_shape, stride), 
                                     np.arange(0, y_shape, stride))

    # Plot Setup (2x2 Grid)
    fig, axs = plt.subplots(2, 2, figsize=(18, 14))
    
    # Einheitliche Farbskala (vmin, vmax) für fairen visuellen Vergleich
    # Angenommen die Daten sind in dBZ. Passe diese an, falls du lineare Regenraten nutzt.
    vmin, vmax = -10, 50 
    cmap = 'turbo' # Gute SOTA Colormap für Radar/Niederschlag
    
    # 1. Oben Links: Original Radar (Die Realität / Ground Truth)
    ax = axs[0, 0]
    im1 = ax.imshow(radar_dbr, cmap=cmap, vmin=vmin, vmax=vmax, origin='upper')
    ax.set_title("1. Ground Truth (Radar $T_0$)", fontsize=14, fontweight='bold')
    fig.colorbar(im1, ax=ax, fraction=0.046, pad=0.04, label="Intensität")

    # 2. Oben Rechts: Original NWP (Der unkorrigierte Vorhersage-Run)
    ax = axs[0, 1]
    im2 = ax.imshow(nwp_dbr_original, cmap=cmap, vmin=vmin, vmax=vmax, origin='upper')
    ax.set_title("2. Unkorrigiertes NWP (mit Phasenfehler)", fontsize=14, fontweight='bold')
    fig.colorbar(im2, ax=ax, fraction=0.046, pad=0.04, label="Intensität")

    # 3. Unten Links: Displacement Vector Field (Das Warping-Feld)
    ax = axs[1, 0]
    # Wir legen das unkorrigierte NWP leicht transparent in den Hintergrund
    ax.imshow(nwp_dbr_original, cmap='Greys', alpha=0.4, origin='upper')
    # Quiver plottet die Pfeile. angles='xy', scale_units='xy', scale=1 sorgt für maßstabsgetreue Pfeile
    q = ax.quiver(x_coords, y_coords, u, v, color='red', angles='xy', scale_units='xy', scale=1, width=0.003)
    ax.set_title(f"3. VET Vektorfeld (Ausdünnung: {stride}px)", fontsize=14, fontweight='bold')
    ax.quiverkey(q, X=0.9, Y=1.05, U=20, label='Versatz = 20 Pixel', labelpos='E')

    # 4. Unten Rechts: Das Aligned NWP (Dein Resultat nach cv2.remap)
    ax = axs[1, 1]
    im4 = ax.imshow(nwp_dbr_aligned, cmap=cmap, vmin=vmin, vmax=vmax, origin='upper')
    ax.set_title("4. Aligned NWP (Ready for Blending)", fontsize=14, fontweight='bold')
    fig.colorbar(im4, ax=ax, fraction=0.046, pad=0.04, label="Intensität")

    plt.tight_layout()
    plt.show()






