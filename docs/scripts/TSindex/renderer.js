// renderer.js

import { cross_fade_time } from './config.js'


/**
 * Lädt alle Frames als versteckte ImageOverlays in die Karte.
 */
export async function preloadFrames(appState, map) {
    const promises = appState.frames.map((frame, index) => {
        return new Promise((resolve) => {
            const img = new Image();
            img.crossOrigin = "Anonymous";
            img.onload = () => {
                // Leaflet Overlay erstellen, aber unsichtbar machen
                const overlay = L.imageOverlay(frame.url, appState.bounds, {
                    opacity: 0,
                    interactive: false, // Bilder fangen keine Klicks ab
                    pane: 'radarPane',
                    crossOrigin: true
                }).addTo(map);

                // CSS Transition auf das HTML-Bildelement anwenden
                // Frames beginnen gleichzeitig ein und ausgeblendet zu werden
                const imgEl = overlay.getElement();
                if (imgEl) {
                    imgEl.style.transition = `opacity ${cross_fade_time}s ease-in-out`;
                }

                // Overlay im State speichern, um es später ein/auszublenden
                appState.frames[index].overlay = overlay;
                resolve();
            };
            img.onerror = () => {
                console.error(`Fehler beim Laden von: ${frame.url}`);
                resolve(); // Trotzdem auflösen, damit andere Frames laden
            };
            img.src = frame.url;
        });
    });

    // Warten, bis alle Bilder im Browser-Cache und in Leaflet initialisiert sind
    await Promise.all(promises);
}


export function renderFrame(appState) {
    const currentFrameObj = appState.frames[appState.currentFrame];
    
    appState.frames.forEach((frame, idx) => {
        if (frame.overlay) {
            frame.overlay.setOpacity(idx === appState.currentFrame ? 0.7 : 0);
        }
    });

    // --- ZEIT-KONVERTIERUNG MIT LUXON ---
    const dateTimeUtc = luxon.DateTime.fromISO(currentFrameObj.iso_time);
    
    // Fix auf deutsche Zeit zwingen (da Radar nur über DE) 
    const displayTime = dateTimeUtc.setZone("Europe/Berlin").toFormat("HH:mm");
    
    document.getElementById("frameLabel").textContent = `${displayTime} Uhr`;
    
    // Status-Label anhand der relativen Zeit (aus dem Backend) einfärben
    const statusLabel = document.getElementById("timeStatusLabel");
    if (statusLabel && currentFrameObj.relative_time) {
        if (currentFrameObj.relative_time.startsWith("T-")) {
            statusLabel.textContent = "Historie";
            statusLabel.style.color = "#4f4f4f"; // Dunkelgrau statt vorher hellem Grau
        } else if (currentFrameObj.relative_time === "T0") {
            statusLabel.textContent = "Aktuell";
            statusLabel.style.color = "#4f4f4f"; // Auch Dunkelgrau als Baseline
        } else if (currentFrameObj.relative_time.startsWith("T+")) {
            statusLabel.textContent = "Vorhersage";
            statusLabel.style.color = "#e67e22"; // Passendes Orange zur neuen Slider-Farbe
        }
    }
    
}

