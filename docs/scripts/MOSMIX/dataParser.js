// dataParser.js

import {
  unitProcessingConfig,
  combinedParams,
  preferredOrder,
  includedDropdownElements,
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
    setStatus("Lade UV-Index und gefühlte Temperatur...");
    result_uv_and_pt = await runForecastUvAndPt(stationId);

    // WICHTIG: Null-Check! Nur verarbeiten, wenn die Daten wirklich existieren
    if (result_uv_and_pt && result_uv_and_pt["GFT"] && result_uv_and_pt["UVI"]) {
      seriesMap["Gefühlte Temperatur"] = result_uv_and_pt["GFT"].map((wert) => {
        const celsius = wert - 273.15;
        return Math.round(celsius * 10) / 10;
      });

      seriesMap["UV-Index"] = result_uv_and_pt["UVI"].map((wert) => {
        return Math.round(wert * 10) / 10;
      });
    }
  } catch (e) {
    // Dieser Catch-Block greift nur noch bei echten unerwarteten Fehlern, 
    // nicht mehr bei regulären Stationen außerhalb des Rasters.
    console.warn("Unerwarteter Fehler beim Verarbeiten der UV/GFT-Daten:", e);
  }

  // 2. KML Forecasts parsen und direkt mit Names-Map übersetzen
  for (const fc of forecasts) {
    const elName =
      fc.getAttributeNS(DWDNS, "elementName") || fc.getAttribute("elementName");
    const valueNode = fc.getElementsByTagNameNS(DWDNS, "value")[0];
    if (!elName || !valueNode) continue;

    // Übersetzung und Einheitenverarbeitung
    const readableName = elementNamesMap[elName] || elName;
    const processingRule = unitProcessingConfig[elName];
    const converter = processingRule ? processingRule.convert : (v) => v;

    const values = valueNode.textContent
      .trim()
      .split(/\s+/)
      .map((v) => {
        if (v === "-" || v === "") return null;
        const num = Number(v);
        if (!Number.isFinite(num)) return v;
        const converted = converter(num);
        return Math.round(converted * 100) / 100;
      });

    seriesMap[readableName] = values.slice(0, timeSteps.length);
  }

  // 3. Fehler kombinieren
  for (const { value, error } of combinedParams) {
    if (seriesMap[value] && seriesMap[error]) {
      seriesMap[value + "_error"] = seriesMap[error];
      delete seriesMap[error];
    }
  }

  // 4. MOSMIX-S JSON LADEN UND ÜBERSCHREIBEN (Dynamisiert)
  if (USE_MOSMIX_S) {
    try {
      setStatus("Integriere stündliche Vorhersagedaten...");
      const sResp = await fetch(`https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/mosmix_s/${stationId}.json`);
      // const sResp = await fetch(`./../backend/WarnMOS/data/mosmix_s/${stationId}.json`);

      if (sResp.ok) { 
        const sData = await sResp.json();

        const sTimeMap = {};
        sData.t.forEach((ts, index) => {
          sTimeMap[new Date(ts).getTime()] = index;
        });

        // Wir iterieren über ALLE Elemente im MOSMIX-S, konvertieren sie und speichern sie, 
        // damit auch ungenutzte Parameter vollständig im seriesMap für die Konsole landen.
        for (const jsonKey in sData.d) {
          const readableName = elementNamesMap[jsonKey] || jsonKey;
          const processingRule = unitProcessingConfig[jsonKey];
          const converter = processingRule ? processingRule.convert : (v) => v;

          // Arrays bedingungslos leeren/initialisieren um L-Daten sauber zu überschreiben
          seriesMap[readableName] = new Array(timeSteps.length).fill(null);
          
          const sourceArray = sData.d[jsonKey];
          timeSteps.forEach((kmlTs, kmlIndex) => {
            const kmlTime = new Date(kmlTs).getTime();
            const sIndex = sTimeMap[kmlTime];

            if (sIndex !== undefined && sourceArray[sIndex] !== null) {
              seriesMap[readableName][kmlIndex] =
                Math.round(converter(sourceArray[sIndex]) * 100) / 100;
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
  
  // Alle Parameter ordentlich in die Konsole loggen (aufgeräumt und verständlich)
  console.log("=== KOMPLETTE EXTRAHIERTE DATEN (seriesMap) ===");
  console.log("Time series:", timeSteps);
  console.log("Parsed series:", seriesMap);

  // 6. Sortieren und Filtern für das UI-Dropdown (jetzt über Whitelist-Filter)
  let cols = Object.keys(seriesMap);

  cols.sort((a, b) => {
    const ia = preferredOrder.indexOf(a);
    const ib = preferredOrder.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  // Filtern mit der neuen includedDropdownElements (Whitelist)
  const plotColumns = cols.filter((c) => {
    if (c.endsWith("_error")) return false;
    return includedDropdownElements.includes(c);
  });

  // 7. RÜCKGABE DER DATEN 
  return {
    timeSteps: timeSteps,
    seriesMap: seriesMap,
    result_uv_and_pt: result_uv_and_pt,
    plotColumns: plotColumns,
    stationDesc: stationDesc,
    stationHeight: stationHeight,
  };
}