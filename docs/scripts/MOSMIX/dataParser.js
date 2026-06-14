// dataParser.js

import {
  elementUnitsMap,
  unitConversionMap,
  combinedParams,
  preferredOrder,
  excludedElements,
  USE_MOSMIX_S,
} from "./config.js";

import { elementNamesMap } from "./elementNamesMap.js";

import { runForecastUvAndPt } from "./uv_and_pt_script.js";

import { setStatus } from "./ui.js";

function fmtLocal(iso) {
  try {
    return new Date(iso).toLocaleString("de-DE", { timeZone: "Europe/Berlin" });
  } catch {
    return iso;
  }
}

export async function loadMosmixData(stationId, userLat, userLon) {
  setStatus("Lade Wetterdaten vom DWD herunter...");
  const proxy =
    "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev?url=";
  const baseUrl = `https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/${stationId}/kml/MOSMIX_L_LATEST_${stationId}.kmz`;

  const resp = await fetch(proxy + encodeURIComponent(baseUrl));
  if (!resp.ok)
    throw new Error(`KMZ konnte nicht geladen werden (${resp.status})`);
  setStatus("Entpacke Wetterdaten...");
  const blob = await resp.blob();
  const zip = await JSZip.loadAsync(blob);
  const kmlFile = Object.keys(zip.files).find((f) => f.endsWith(".kml"));
  setStatus("Analysiere Wetterdaten...");
  const kmlText = await zip.files[kmlFile].async("string");

  // Wir rufen parseKML auf und GEEBEN die Daten an die main.js ZURÜCK!
  return await parseKML(kmlText, userLat, userLon, stationId);
}

/**
 * Parst die KML-Daten, holt zusätzliche UV/PT sowie MOSMIX-S Daten und berechnet abgeleitete Werte.
 * WICHTIG: Diese Funktion manipuliert KEIN HTML/DOM. Sie gibt nur die geparsten Daten zurück.
 */
export async function parseKML(text, userLat, userLon, stationId) {
  const KMLNS = "http://www.opengis.net/kml/2.2";
  const DWDNS =
    "https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd";

  const parser = new DOMParser();
  const xml = parser.parseFromString(text, "application/xml");

  if (xml.getElementsByTagName("parsererror")[0]) {
    throw new Error("XML-Parsing-Fehler");
  }

  let timeSteps = Array.from(xml.getElementsByTagNameNS(DWDNS, "TimeStep")).map(
    (n) => n.textContent.trim(),
  );
  if (timeSteps.length === 0) {
    throw new Error("Keine dwd:TimeStep gefunden.");
  }

  const placemark = xml.getElementsByTagNameNS(KMLNS, "Placemark")[0];
  if (!placemark) {
    throw new Error("Kein kml:Placemark gefunden.");
  }

  // Stationsinfos auslesen
  const stationDesc =
    placemark.getElementsByTagNameNS(KMLNS, "description")[0]?.textContent ??
    "";
  const coords =
    placemark
      .getElementsByTagNameNS(KMLNS, "coordinates")[0]
      ?.textContent?.trim() ?? "";
  const coordParts = coords.split(",");
  const stationHeight = coordParts[2]?.trim() ?? "";

  const forecasts = Array.from(
    placemark.getElementsByTagNameNS(DWDNS, "Forecast"),
  );
  let seriesMap = {};
  let result_uv_and_pt = null;

  // 1. UV und PT Daten holen
  try {
    setStatus("Berechne UV-Index und gefühlte Temperatur...");
    // Es wird vorausgesetzt, dass runForecastUvAndPt importiert oder verfügbar ist
    result_uv_and_pt = await runForecastUvAndPt(userLat, userLon);
    console.log(result_uv_and_pt);

    seriesMap["Gefühlte Temperatur"] = result_uv_and_pt["GFT"].map((wert) => {
      const celsius = wert - 273.15;
      return Math.round(celsius * 10) / 10;
    });

    seriesMap["UV-Index"] = result_uv_and_pt["UVI"].map((wert) => {
      return Math.round(wert * 10) / 10;
    });
  } catch (e) {
    console.warn("Fehler beim Laden von UV-Index und Gefühlter Temperatur:", e);
  }

  // 2. KML Forecasts parsen
  for (const fc of forecasts) {
    const elName =
      fc.getAttributeNS(DWDNS, "elementName") || fc.getAttribute("elementName");
    const valueNode = fc.getElementsByTagNameNS(DWDNS, "value")[0];
    if (!elName || !valueNode) continue;

    const unit = elementUnitsMap[elName];
    const converter = unitConversionMap[unit];
    const values = valueNode.textContent
      .trim()
      .split(/\s+/)
      .map((v) => {
        if (v === "-" || v === "") return null;
        const num = Number(v);
        if (!Number.isFinite(num)) return v;
        const converted = converter ? converter(num) : num;
        return Math.round(converted * 100) / 100;
      });

    const readableName = elementNamesMap[elName] || elName;
    seriesMap[readableName] = values.slice(0, timeSteps.length);
  }

  // 3. Fehler kombinieren
  for (const { value, error } of combinedParams) {
    if (seriesMap[value] && seriesMap[error]) {
      seriesMap[value + "_error"] = seriesMap[error];
      delete seriesMap[error];
    }
  }

  // 4. MOSMIX-S JSON LADEN UND ÜBERSCHREIBEN
  if (USE_MOSMIX_S) {
    try {
      setStatus("Integriere stündliche Vorhersagedaten...");
      const sResp = await fetch(`data/mosmix_s/${stationId}.json`);

      if (sResp.ok) {
        const sData = await sResp.json();

        const sTimeMap = {};
        sData.t.forEach((ts, index) => {
          sTimeMap[new Date(ts).getTime()] = index;
        });

        const overrideSeries = (jsonKey, seriesName, converter) => {
          if (sData.d[jsonKey]) {
            // Alternative: Zwingendes Leeren des von "L" stammenden Arrays,
            // um eine Vermischung im Fall fehlender "S"-Zeitstempel unmöglich zu machen.
            seriesMap[seriesName] = new Array(timeSteps.length).fill(null);

            timeSteps.forEach((kmlTs, kmlIndex) => {
              const kmlTime = new Date(kmlTs).getTime();
              const sIndex = sTimeMap[kmlTime];

              if (sIndex !== undefined && sData.d[jsonKey][sIndex] !== null) {
                seriesMap[seriesName][kmlIndex] =
                  Math.round(converter(sData.d[jsonKey][sIndex]) * 100) / 100;
              }
            });
          }
        };

        overrideSeries("TTT", "Temperatur (°C)", (v) => v - 273.15);
        const tdKey = elementNamesMap["Td"] || "Td";
        overrideSeries("Td", tdKey, (v) => v - 273.15);
        overrideSeries("RR1c", "Totale Niederschlagsmenge (mm)", (v) => v);
        overrideSeries("Neff", "Bewölkung", (v) => v);
        overrideSeries("DD", "Windrichtung", (v) => v);
        overrideSeries("FF", "Windgeschwindigkeit (km/h)", (v) => v * 3.6);
        overrideSeries("FX1", "Maximale Windböe", (v) => v * 3.6);
        overrideSeries("Rad1h", "Strahlungsintensität (W/m^2)", (v) => v / 3.6);
        overrideSeries("wwM", "Nebelwahrscheinlichkeit", (v) => v);

        const wwArray = sData.d["ww"];
        if (wwArray) {
          // Bedingungsloses Leeren, um L-Daten zu vernichten
          seriesMap["Significant Weather"] = new Array(timeSteps.length).fill(
            null,
          );

          timeSteps.forEach((kmlTs, kmlIndex) => {
            const sIndex = sTimeMap[new Date(kmlTs).getTime()];
            if (sIndex !== undefined && wwArray[sIndex] !== null) {
              seriesMap["Significant Weather"][kmlIndex] = wwArray[sIndex];
            }
          });
        }
      }
    } catch (e) {
      console.warn(
        "Konnte MOSMIX-S JSON nicht laden. Nutze reine MOSMIX-L Daten als Fallback.",
        e,
      );
    }
  }

  // 5. Relative Luftfeuchtigkeit berechnen
  const tdKey = elementNamesMap["Td"] || "Td";
  const finalTemp = seriesMap["Temperatur (°C)"];
  const finalTd = seriesMap[tdKey];
  const finalErrT = seriesMap["Temperatur (°C)_error"];
  const finalErrTd = seriesMap[tdKey + "_error"];

  if (finalTemp && finalTd && finalTemp.length > 0) {
    const rhValues = [];
    const rhErrorValues = [];

    const a = 17.625;
    const b = 243.04;
    const ab = a * b;

    for (let i = 0; i < timeSteps.length; i++) {
      const T = finalTemp[i];
      const Td = finalTd[i];

      const errT = finalErrT && finalErrT[i] ? finalErrT[i] : 0;
      const errTd = finalErrTd && finalErrTd[i] ? finalErrTd[i] : 0;

      if (T !== null && Td !== null) {
        const e = Math.exp((a * Td) / (b + Td));
        const es = Math.exp((a * T) / (b + T));
        let rh = (e / es) * 100;

        let rh_err =
          rh *
          ab *
          Math.sqrt(
            Math.pow(errTd / Math.pow(b + Td, 2), 2) +
              Math.pow(errT / Math.pow(b + T, 2), 2),
          );

        rh = Math.round(rh * 10) / 10;
        rh_err = Math.ceil(rh_err * 10) / 10;

        rhValues.push(rh);
        rhErrorValues.push(rh_err);
      } else {
        rhValues.push(null);
        rhErrorValues.push(null);
      }
    }

    seriesMap["Relative Luftfeuchtigkeit (%)"] = rhValues;
    seriesMap["Relative Luftfeuchtigkeit (%)_error"] = rhErrorValues;
  }
  console.log("Time series:", timeSteps);
  console.log("Parsed series:", seriesMap);

  // 6. Sortieren und Filtern für das UI-Dropdown vorbereiten
  let cols = Object.keys(seriesMap);

  cols.sort((a, b) => {
    const ia = preferredOrder.indexOf(a);
    const ib = preferredOrder.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  const plotColumns = cols.filter((c) => {
    if (c.endsWith("_error")) return false;
    const originalKey = Object.keys(elementNamesMap).find(
      (k) => elementNamesMap[k] === c,
    );
    const key = originalKey || c;
    return !excludedElements.includes(key);
  });

  // 7. RÜCKGABE DER DATEN (Das Wichtigste an dieser Funktion)
  return {
    timeSteps: timeSteps,
    seriesMap: seriesMap,
    result_uv_and_pt: result_uv_and_pt,
    plotColumns: plotColumns,
    stationDesc: stationDesc,
    stationHeight: stationHeight,
  };
}
