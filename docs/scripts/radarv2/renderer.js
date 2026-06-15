// renderer.js

// Berechnet die korrekte Zeit für den WMS-Server
export function getWmsIsoTime(frameIndex) {
    const now = luxon.DateTime.utc();
    // DWD Radar updatet alle 5 Minuten. Wir runden auf die letzten 5 Minuten ab.
    const minute = Math.floor(now.minute / 5) * 5;
    const baseTime = now.set({ minute: minute, second: 0, millisecond: 0 });
    
    // Frame 0 = Jetzt, Frame 1 = +5 Min, Frame 24 = +120 Min
    const targetTime = baseTime.plus({ minutes: frameIndex * 5 });
    
    // WMS erwartet ISO 8601 Format (z.B. 2023-10-25T12:05:00Z)
    return targetTime.toISO({ suppressMilliseconds: true });
}

export function updateForecastTimeDisplay(appState) {
    const timeIso = getWmsIsoTime(appState.currentFrame);
    const localTime = luxon.DateTime.fromISO(timeIso).toLocal();
    document.getElementById("frameLabel").textContent = localTime.toFormat("HH:mm") + " Uhr";
}

/**
 * Stellt die KONRAD3D-Daten für den gegebenen Frame-Index dar.
 * @param {number} idx - Der Index des darzustellenden Frames (0 = T+0, 1 = T+5, etc.)
 */
export function renderKonradData(appState, map) {
  appState.konradLayerGroup.clearLayers();
  if (!appState.konradData) return;

  // Frame 0: Aktuelle Positionen anzeigen
  if (appState.currentFrame === 0) {
    appState.konradData.forEach((cell) => {
      const popupContent = createPopupContent(cell);

      // Zellpolygon (jetzt mit unsichtbarer, klickbarer Füllung)
      if (cell.polygon_latitudes && cell.polygon_longitudes) {
        const lats = cell.polygon_latitudes.split(" ").map(Number);
        const lons = cell.polygon_longitudes.split(" ").map(Number);
        if (lats.length > 2) {
          const latlngs = lats.map((lat, i) => [lat, lons[i]]);
          L.polygon(latlngs, {
            color: "cyan",
            weight: 2,
            fill: true,
            fillOpacity: 0,
            pane: "konradPane", // GEÄNDERT: Korrekte Ebene zuweisen
          })
            .bindPopup(popupContent)
            .addTo(appState.konradLayerGroup);
        }
      }
      // Aktuelle Unsicherheitsellipse
      if (cell.lat_centroid && cell.major_axis) {
        L.ellipse(
          [cell.lat_centroid, cell.lon_centroid],
          [cell.major_axis * 1000, cell.minor_axis * 1000],
          90 - cell.angle,
          {
            color: "cyan",
            weight: 1.5,
            dashArray: "5, 5",
            fillColor: "#00FFFF",
            fillOpacity: 0.2,
            pane: "konradPane", // GEÄNDERT: Korrekte Ebene zuweisen
          },
        )
          .bindPopup(popupContent)
          .addTo(appState.konradLayerGroup);
      }
    });
  }

  // Frame 1: Vorhersage für T+5 Minuten anzeigen
  if (appState.currentFrame === 1) {
    appState.konradData.forEach((cell) => {
      // Vorhersage-Ellipse
      if (cell.lat_centroid_forecast && cell.major_axis_forecast) {
        L.ellipse(
          [cell.lat_centroid_forecast, cell.lon_centroid_forecast],
          [cell.major_axis_forecast * 1000, cell.minor_axis_forecast * 1000],
          90 - cell.angle_forecast,
          {
            color: "cyan",
            weight: 1.5,
            dashArray: "5, 5",
            fillColor: "#00FFFF",
            fillOpacity: 0.2,
            pane: "konradPane", // GEÄNDERT: Korrekte Ebene zuweisen
          },
        )
          .bindPopup(createPopupContent(cell))
          .addTo(appState.konradLayerGroup);
      }
    });
  }
}

/**
 * Erstellt den HTML-Inhalt für das Pop-up einer Zelle.
 * @param {object} cell - Das Zell-Datenobjekt.
 * @returns {string} Ein HTML-String für das Pop-up.
 */
export function createPopupContent(cell) {
  const format = (value, unit = "", decimals = 1) => {
    if (value === null || typeof value === "undefined" || isNaN(value)) {
      return "N/A";
    }
    return `${value.toFixed(decimals)} ${unit}`;
  };

  const severityTrendText =
    cell.severity_trend_cat === -2
      ? "⬇\uFE0F"
      : cell.severity_trend_cat === -1
        ? "↘\uFE0F"
        : cell.severity_trend_cat === 0
          ? "➡\uFE0F"
          : cell.severity_trend_cat === 1
            ? "↗\uFE0F"
            : cell.severity_trend_cat === 2
              ? "⬆\uFE0F"
              : "";
  const rain_data_quality_text =
    cell.heavy_rain_data_quality === 0
      ? "Schlecht. Keine Daten"
      : cell.heavy_rain_data_quality === 1
        ? "Beschränkt. <20% Valider Pixel "
        : "Gut";
  const hailText =
    cell.hail_flag === 0
      ? "Unwahrscheinlich"
      : cell.hail_flag === 1
        ? "Wahrscheinlich"
        : "Sehr wahrscheinlich";
  let growthText;
  if (cell.area_growth_rate !== null && !isNaN(cell.area_growth_rate)) {
    const growthPercent = (cell.area_growth_rate - 1) * 100;
    growthText = format(growthPercent, "%/5min", 0);
  } else {
    growthText = "Neue Zelle";
  }

  /* Wegen übersicht herausgenommenes element:
    <strong>Zelluntergrenze:</strong> ${format(cell.bottom_of_cell, 'm ü. M.', 0)}<br> 
    das war noch bei max regensumme hinten dran:
    in ${format(cell.heavy_rain_time, 'min', 0)} */
  return `
        <div style="font-family: sans-serif; font-size: 12px; line-height: 1.5; min-width: 200px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                <b>Stärke: ${severityTrendText}</b> 
                <span>${format(cell.severity, "", 2)}</span>
            </div>
            <meter 
                min="0" max="3" 
                low="1.5" high="3" optimum="0" 
                value="${cell.severity || 0}" 
                style="width: 100%; height: 12px; margin-bottom: 4px;"
                title="Skala von 0 bis 3">
            </meter>
            <hr style="margin: 4px 0;">
            <strong>Vert. Ausdehnung:</strong> ${format(cell.vertical_extent, "m", 0)}<br>
            <strong>Wachstumsrate:</strong> ${growthText}<br>
            <strong>Hagel:</strong> ${hailText}<br>
            <strong>Max. Böen:</strong> ${format(cell.max_wind_gusts, "km/h", 1)}<br>
            <strong>Max. Regensumme:</strong> ${format(cell.heavy_rain, "mm", 1)}<br>
            <strong>Datenqual. Regensumme:</strong> ${rain_data_quality_text}
        </div>
    `;
}
