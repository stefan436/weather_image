import { cross_fade_time } from './config.js'

/**
 * Lädt alle Bilder und Vektoren vorab in den Speicher.
 */
export async function preloadFrames(appState, map) {
    const promises = appState.frames.map((frame, index) => {
        return new Promise(async (resolve) => {
            try {
                // 1. Rasterbild laden (wie bisher)
                const imgPromise = new Promise((resImg) => {
                    const img = new Image();
                    img.crossOrigin = "Anonymous";
                    img.onload = () => {
                        const overlay = L.imageOverlay(frame.url, appState.bounds, {
                            opacity: 0,
                            interactive: false,
                            pane: 'indexPane',
                            crossOrigin: true
                        }).addTo(map);

                        const imgEl = overlay.getElement();
                        if (imgEl) {
                            imgEl.style.transition = `opacity ${cross_fade_time}s ease-in-out`;
                        }
                        appState.frames[index].overlay = overlay;
                        resImg();
                    };
                    img.onerror = () => {
                        console.error(`Fehler beim Laden des Bildes: ${frame.url}`);
                        resImg(); // Fortsetzen trotz Fehler
                    };
                    img.src = frame.url;
                });

                // 2. GeoJSON Vektoren laden (NEU)
                const geoPromise = new Promise(async (resGeo) => {
                    if (frame.url_vector) {
                        try {
                            const response = await fetch(frame.url_vector);
                            if (response.ok) {
                                const geojsonData = await response.json();
                                
                                const vectorLayer = L.geoJSON(geojsonData, {
                                    pane: 'vectorPane',
                                    interactive: false, // WICHTIG für iOS: Lässt alle Taps auf die Karte durch
                                    
                                    style: function(feature) {
                                        if (feature.properties.type === "supercell_risk_start") {
                                            // BRN >= 10: Gestrichelte, weiße Warnlinie
                                            return { color: "#ffffff", weight: 2.5, opacity: 0.9};
                                            
                                        } else if (feature.properties.type === "supercell_risk_end") {
                                            // BRN >= 50: Harte, rote Warnlinie
                                            return { color: "#ff0000", weight: 2.5, opacity: 0.9 };
                                            
                                        } else if (feature.properties.type === "data_boundary") {
                                            // Datenrand
                                            return { color: "#333333", weight: 4, opacity: 0.66 };
                                        }
                                    }
                                });
                                // Wir speichern den Layer, fügen ihn aber NOCH NICHT der Karte hinzu
                                appState.frames[index].vectorLayer = vectorLayer;
                            }
                        } catch (e) {
                            console.error(`Fehler beim Laden des Vektors: ${frame.url_vector}`, e);
                        }
                    }
                    resGeo();
                });

                // Warten, bis Bild UND Vektor für diesen Frame fertig geladen sind
                await Promise.all([imgPromise, geoPromise]);
                resolve();
            } catch (e) {
                resolve(); // Fallback, falls Promise.all abstürzt
            }
        });
    });

    await Promise.all(promises);
}


// map als zweiten Parameter hinzufügen!
export function renderFrame(appState, map) { 
    const currentFrameObj = appState.frames[appState.currentFrame];
    
    appState.frames.forEach((frame, idx) => {
        // 1. Raster-Deckkraft steuern
        if (frame.overlay) {
            frame.overlay.setOpacity(idx === appState.currentFrame ? 0.7 : 0);
        }
        
        // 2. Vektor-Layer auf die Karte legen oder entfernen
        if (frame.vectorLayer) {
            if (idx === appState.currentFrame) {
                if (!map.hasLayer(frame.vectorLayer)) {
                    frame.vectorLayer.addTo(map);
                }
            } else {
                if (map.hasLayer(frame.vectorLayer)) {
                    frame.vectorLayer.removeFrom(map);
                }
            }
        }
    });

    // --- ZEIT-KONVERTIERUNG MIT LUXON ---
    const dateTimeUtc = luxon.DateTime.fromISO(currentFrameObj.iso_time);
    const displayTime = dateTimeUtc.setZone("Europe/Berlin").toFormat("HH:mm");
    
    document.getElementById("frameLabel").textContent = `${displayTime} Uhr`;
}