// dataFetcher.js

/**
 * Lädt die meta.json vom Server
 * @param {string} url - Pfad zur meta.json
 * @returns {Promise<Object>} Das geparste JSON-Objekt
 */
export async function fetchMetaData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP Fehler! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Fehler beim Abrufen der meta.json:", error);
        throw error;
    }
}


// --- KONRAD3D Datenverarbeitung ---
export async function fetchAndProcessKonrad(appState) {
  // 1. T0 Index ermitteln (wie zuvor besprochen)
  appState.t0Index = appState.frames.findIndex(f => f.relative_time === "T0");
  if (appState.t0Index === -1) appState.t0Index = 0; 
  
  // 2. Den exakten Zeitstempel für dieses T0-Frame aus den Backend-Metadaten holen
  const t0Frame = appState.frames[appState.t0Index];
  const timestamp_str = t0Frame.konrad_url_time;
  
  // Zeit-Synchronitäts-Check entfällt, da wir zwingend dieselbe Zeit nutzen.
  const warningDiv = document.getElementById("time-warning");
  if (warningDiv) warningDiv.style.display = "none";

  // 3. URL bauen
  const proxy = "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev?url=";
  const url = `${proxy}https://opendata.dwd.de/weather/radar/konrad3d/KONRAD3D_${timestamp_str}.xml`;

  try {
    const response = await fetch(url);
    
    // Fehlerbehandlung, falls der DWD genau DIESES File (noch) nicht hat
    if (!response.ok) {
      console.warn(`KONRAD Daten für exaktes T0 (${t0Frame.time} Uhr) nicht verfügbar beim DWD. Code: ${response.status}`);
      appState.konradData = [];
      return; // Wir brechen sauber ab, ohne dass die App crasht
    }
    
    const xmlText = await response.text();
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "application/xml");

    const getText = (element, selector) => {
      const node = element.querySelector(selector);
      return node ? node.textContent.trim() : null;
    };

    /* pdf mit infos über features von konrad: 
        https://www.dwd.de/EN/ourservices/radar_products/format_konrad3d.pdf?__blob=publicationFile
        pdf name ist KONRAD3D XML file format description
        */
    const data = [];
    xmlDoc.querySelectorAll("feature").forEach((feature, index) => {
      try {
        const row = { cell_id: index + 1 };
        
        row.area_growth_rate = parseFloat(getText(feature, "geometry > area_growth_rate"));
        row.bottom_of_cell = parseFloat(getText(feature, "geometry > echo_bottom_msl"));
        row.vertical_extent = parseFloat(getText(feature, "geometry > vertical_extent"));
        row.lat_centroid = parseFloat(getText(feature, "centroid_3d geodetic_coordinate > latitude"));
        row.lon_centroid = parseFloat(getText(feature, "centroid_3d geodetic_coordinate > longitude"));
        row.major_axis = parseFloat(getText(feature, "centroid_3d uncertainty_ellipse > major_axis"));
        row.minor_axis = parseFloat(getText(feature, "centroid_3d uncertainty_ellipse > minor_axis"));
        row.angle = parseFloat(getText(feature, "centroid_3d uncertainty_ellipse > angle"));
        row.polygon_latitudes = getText(feature, "polygons_projected geodetic_coordinates polygon > latitudes");
        row.polygon_longitudes = getText(feature, "polygons_projected geodetic_coordinates polygon > longitudes");
        row.severity = parseFloat(getText(feature, "intensity > severity_decimal"));
        row.severity_trend_cat = parseInt(getText(feature, "intensity > trends > severity_trend_category"));
        row.hail_flag = parseInt(getText(feature, "intensity > hail_flag"));
        row.max_wind_gusts = parseFloat(getText(feature, "intensity > maximum_estimated_wind_gust"));
        row.heavy_rain = parseFloat(getText(feature, "intensity > heavy_rain_potential"));
        row.heavy_rain_time = parseFloat(getText(feature, "intensity > heavy_rain_potential_accumulation_time"));
        row.heavy_rain_data_quality = parseFloat(getText(feature, "intensity > heavy_rain_potential_quality"));

        // Holt den T+5 Vorhersageknoten
        const forecastNode = feature.querySelector("centroid_forecasts > centroid_forecast");
        if (forecastNode) {
          row.forecast_time = forecastNode.getAttribute("forecast_time");
          row.lat_centroid_forecast = parseFloat(getText(forecastNode, "geodetic_coordinate > latitude"));
          row.lon_centroid_forecast = parseFloat(getText(forecastNode, "geodetic_coordinate > longitude"));
          row.major_axis_forecast = parseFloat(getText(forecastNode, "uncertainty_ellipse > major_axis"));
          row.minor_axis_forecast = parseFloat(getText(forecastNode, "uncertainty_ellipse > minor_axis"));
          row.angle_forecast = parseFloat(getText(forecastNode, "uncertainty_ellipse > angle"));
        }

        for (const key in row) {
          if (row[key] === -1000000000.0) row[key] = null;
        }
        data.push(row);
      } catch (e) {
        console.warn(`Fehler beim Parsen von Zelle ${index + 1}:`, e);
      }
    });

    console.log("--- KONRAD3D Info Tabelle ---");
    console.table(data);

    appState.konradData = data;
  } catch (error) {
    console.error("Fehler bei der Verarbeitung der KONRAD3D-Daten:", error);
    document.getElementById("location_output").textContent +=
      ` | KONRAD3D: ${error.message}`;
    appState.konradData = [];
  }
}