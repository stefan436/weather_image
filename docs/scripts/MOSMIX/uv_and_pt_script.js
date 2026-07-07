// uv_and_pt_script.js

async function loadTimeStamps() {
    const [response_gft, response_uvi] = await Promise.all([
        fetch("https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/gft_forecast_times.json"),
        fetch("https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/uvi_forecast_times.json")
    ]);

    const gft_times_raw = await response_gft.json();
    const uvi_times_raw = await response_uvi.json();

    const gft_times = gft_times_raw.map(iso => {
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1') + 'Z'; 
        return new Date(trimmed);
    });

    const uvi_times = uvi_times_raw.map(iso => {
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1') + 'Z'; 
        return new Date(trimmed);
    });

    return { gft_times, uvi_times };
}

/**
 * Holt die vorberechneten UV- und PT-Daten für eine spezifische MOSMIX-Station.
 * @param {string} stationId - Die ID der aktiven MOSMIX-Station
 * @returns {Object|null} Kombiniertes Objekt mit Daten und Zeitstempeln oder null, falls außerhalb des Rasters.
 */
export async function runForecastUvAndPt(stationId) {
    try {
        const response = await fetch(`https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/uv_gft/${stationId}.json`);
        
        // Status 404 (Not Found) bedeutet, die Station liegt außerhalb des Abdeckungsbereichs (z.B. Südafrika)
        if (!response.ok) {
            console.warn(`Station ${stationId} liegt außerhalb der GFT/UV-Abdeckung.`);
            return null; 
        }

        const results = await response.json();
        const { gft_times, uvi_times } = await loadTimeStamps();
        
        // Kombiniere alles in einem Ergebnisobjekt
        return { ...results, gft_times, uvi_times };

    } catch (err) {
        console.error("Fehler beim Abrufen der UV/GFT-Daten:", err);
        return null;
    }
}