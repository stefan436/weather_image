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

export async function runForecastUvAndPt(stationId) {
    try {
        const response = await fetch(`https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/uv_gft/${stationId}.json`);
        
        if (!response.ok) {
            console.warn(`Station ${stationId} liegt außerhalb der GFT/UV-Abdeckung.`);
            return null; 
        }

        const results = await response.json();
        const { gft_times, uvi_times } = await loadTimeStamps();
        
        return { ...results, gft_times, uvi_times };

    } catch (err) {
        console.error("Fehler beim Abrufen der UV/GFT-Daten:", err);
        return null;
    }
}