// dataFetcher.js

import { ROWS_TO_KEEP } from './config.js';


export async function createCoords() {
  const response = await fetch("./../data/coords_radarcomposite_rv.bin");
  const buffer = await response.arrayBuffer();
  const view = new DataView(buffer);

  let offset = 0;
  const height = view.getUint32(offset, true);
  offset += 4;
  const width = view.getUint32(offset, true);
  offset += 4;
  const numValues = height * width;

  const lat1D = new Float32Array(buffer, offset, numValues);
  offset += numValues * 4;
  const lon1D = new Float32Array(buffer, offset, numValues);

  const startRow = height - ROWS_TO_KEEP;
  const lat2D = [],
    lon2D = [];
  for (let y = startRow; y < height; y++) {
    const latRow = [],
      lonRow = [];
    for (let x = 0; x < width; x++) {
      const idx = y * width + x;
      latRow.push(lat1D[idx]);
      lonRow.push(lon1D[idx]);
    }
    lat2D.push(latRow);
    lon2D.push(lonRow);
  }
  return { lat: lat2D, lon: lon2D };
}

// --- Hauptlogik zum Laden der Daten ---
export async function fetchAndProcessComposite(appState, map, lat_pos, lon_pos, isRealLocation, onComplete) {
  map.setView([lat_pos, lon_pos], 10);
  if (isRealLocation) {
    if (appState.userLocationMarker) {
      // Falls der Marker schon existiert, nur die Position updaten
      appState.userLocationMarker.setLatLng([lat_pos, lon_pos]);
    } else {
      // Neuen, blauen GPS-Punkt erstellen
      appState.userLocationMarker = L.circleMarker([lat_pos, lon_pos], {
        radius: 6, // Größe des Punkts
        fillColor: "#0078ff", // GPS-Blau
        color: "#ffffff", // Weißer Rand zur besseren Sichtbarkeit
        weight: 2, // Dicke des Rands
        opacity: 0.8,
        fillOpacity: 0.66,
        pane: "markerPane", // Standard Leaflet-Pane für Marker (ganz oben)
      }).addTo(map);

      // Ein kleines Pop-up beim Anklicken
      appState.userLocationMarker.bindPopup("<b>Dein Standort</b>");
    }
  }

  try {
    const konradPromise = fetchAndProcessKonrad(appState);

    const proxy =
      "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev?url=";
    const tarUrl = `${proxy}https://opendata.dwd.de/weather/radar/composite/rv/composite_rv_LATEST.tar?nocache=${Date.now()}`;
    const resp = await fetch(tarUrl);
    if (!resp.ok) throw new Error("RV-Download fehlgeschlagen");
    const arrayBuffer = await resp.arrayBuffer();

    const entries = await untar(arrayBuffer);
    entries.sort((a, b) => a.name.localeCompare(b.name));

    for (let i = 0; i < entries.length; i++) {
      await new Promise(requestAnimationFrame);
      const parsed = await parseH5File(entries[i].buffer, appState);
      appState.frames.push(parsed.data);
      const percent = Math.round(((i + 1) / entries.length) * 100);
      document.getElementById("loadProgress").value = percent;
      document.getElementById("loadProgressText").textContent = percent + "%";
    }

    const coords = await createCoords();
    appState.lat = coords.lat; 
    appState.lon = coords.lon;

    await konradPromise;

    document.getElementById("frameSlider").max = appState.frames.length - 1;
    document.getElementById("frameSlider").disabled = false;
    document.getElementById("playPause").disabled = false;
    document.getElementById("legend").style.display = "block";

    setTimeout(() => {
      document.getElementById("start").style.display = "none";
      document.getElementById("loadProgressLabel").style.display = "none";
      document.getElementById("loadProgress").style.display = "none";
      document.getElementById("loadProgressText").style.display = "none";
      document.getElementById("location_output").style.display = "none";
      // document.getElementById("renderProgressLabel").style.display = "none";
      // document.getElementById("renderProgress").style.display = "none";
      // document.getElementById("renderProgressText").style.display = "none";
      document.getElementById("controls").style.padding = "6px";
      document.getElementById("controls").style.gap = "6px";
      requestAnimationFrame(() => map.invalidateSize());
    }, 0);

    onComplete(); // Callback rufen, wenn alles geladen ist (startet Renderer)

  } catch (e) {
    console.error("Fehler: ", e);
    document.getElementById("location_output").textContent =
      "Fehler: " + e.message;
  }
}

// --- KONRAD3D Datenverarbeitung ---
export async function fetchAndProcessKonrad(appState) {
  const now_utc = luxon.DateTime.utc().minus({ minutes: 5 });
  const minute = Math.floor(now_utc.minute / 5) * 5;
  const rounded_time = now_utc.set({
    minute: minute,
    second: 0,
    millisecond: 0,
  });
  const timestamp_str = rounded_time.toFormat("yyyyMMdd'T'HHmm'00'");

  const proxy =
    "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev?url=";
  const url = `${proxy}https://opendata.dwd.de/weather/radar/konrad3d/KONRAD3D_${timestamp_str}.xml`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Fehler beim Abrufen der KONRAD3D-Datei: ${response.statusText} (Status: ${response.status})`,
      );
    }
    const xmlText = await response.text();

    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "application/xml");

    const getText = (element, selector) => {
      const node = element.querySelector(selector);
      return node ? node.textContent.trim() : null;
    };

    const data = [];
    const features = xmlDoc.querySelectorAll("feature");
    /* pdf mit infos über features von konrad: 
        https://www.dwd.de/EN/ourservices/radar_products/format_konrad3d.pdf?__blob=publicationFile
        pdf name ist KONRAD3D XML file format description
        */
    features.forEach((feature, index) => {
      try {
        const row = { cell_id: index + 1 };

        row.area_growth_rate = parseFloat(
          getText(feature, "geometry > area_growth_rate"),
        );
        row.bottom_of_cell = parseFloat(
          getText(feature, "geometry > echo_bottom_msl"),
        );
        row.vertical_extent = parseFloat(
          getText(feature, "geometry > vertical_extent"),
        );
        row.lat_centroid = parseFloat(
          getText(feature, "centroid_3d geodetic_coordinate > latitude"),
        );
        row.lon_centroid = parseFloat(
          getText(feature, "centroid_3d geodetic_coordinate > longitude"),
        );
        row.major_axis = parseFloat(
          getText(feature, "centroid_3d uncertainty_ellipse > major_axis"),
        );
        row.minor_axis = parseFloat(
          getText(feature, "centroid_3d uncertainty_ellipse > minor_axis"),
        );
        row.angle = parseFloat(
          getText(feature, "centroid_3d uncertainty_ellipse > angle"),
        );
        row.polygon_latitudes = getText(
          feature,
          "polygons_projected geodetic_coordinates polygon > latitudes",
        );
        row.polygon_longitudes = getText(
          feature,
          "polygons_projected geodetic_coordinates polygon > longitudes",
        );
        row.severity = parseFloat(
          getText(feature, "intensity > severity_decimal"),
        );
        row.severity_trend_cat = parseInt(
          getText(feature, "intensity > trends > severity_trend_category"),
        );
        row.hail_flag = parseInt(getText(feature, "intensity > hail_flag"));
        row.max_wind_gusts = parseFloat(
          getText(feature, "intensity > maximum_estimated_wind_gust"),
        );
        row.heavy_rain = parseFloat(
          getText(feature, "intensity > heavy_rain_potential"),
        );
        row.heavy_rain_time = parseFloat(
          getText(
            feature,
            "intensity > heavy_rain_potential_accumulation_time",
          ),
        );
        row.heavy_rain_data_quality = parseFloat(
          getText(feature, "intensity > heavy_rain_potential_quality"),
        );

        const forecastNode = feature.querySelector(
          "centroid_forecasts > centroid_forecast",
        );
        if (forecastNode) {
          row.forecast_time = forecastNode.getAttribute("forecast_time");
          row.lat_centroid_forecast = parseFloat(
            getText(forecastNode, "geodetic_coordinate > latitude"),
          );
          row.lon_centroid_forecast = parseFloat(
            getText(forecastNode, "geodetic_coordinate > longitude"),
          );
          row.major_axis_forecast = parseFloat(
            getText(forecastNode, "uncertainty_ellipse > major_axis"),
          );
          row.minor_axis_forecast = parseFloat(
            getText(forecastNode, "uncertainty_ellipse > minor_axis"),
          );
          row.angle_forecast = parseFloat(
            getText(forecastNode, "uncertainty_ellipse > angle"),
          );
        }

        for (const key in row) {
          if (row[key] === -1000000000.0) {
            row[key] = null;
          }
        }
        data.push(row);
      } catch (e) {
        console.error(`Fehler beim Parsen von Zelle ${index + 1}:`, e);
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

export async function parseH5File(buffer, appState) {
  await h5wasm.ready;
  const filename = "/tmp.h5";
  h5wasm.FS.writeFile(filename, new Uint8Array(buffer));
  const file = new h5wasm.File(filename, "r");

  const dataSet = file.get("/dataset1/data1/data");
  const shape = dataSet.shape;
  const raw = dataSet.to_array();

  // Metadaten-Gruppe laden
  const what = file.get("/dataset1/data1/what");
  const nodata = what.attrs["nodata"].value;

  // --- DYNAMISCHES AUSLESEN AUS DEM HEADER ---
  // Holt den 'gain'-Wert (PR / Datengenauigkeit) aus der Datei. Fallback: 0.01. Wert aus Dokumentation
  const gain = what.attrs["gain"] ? what.attrs["gain"].value : 0.01;
  // Holt den 'offset'-Wert aus der Datei (falls vorhanden, sonst 0)
  const offset = what.attrs["offset"] ? what.attrs["offset"].value : 0;

  appState.forecastTime = file.get("what").attrs["time"].value;

  file.close();

  const startRow = shape[0] - ROWS_TO_KEEP;
  const sliced = raw.slice(startRow).map((row) =>
    row.map((v) => {
      if (v === nodata) {
        return 0;
      }
      return (v * gain + offset) * 12;
    }),
  );

  return { data: sliced };
}

