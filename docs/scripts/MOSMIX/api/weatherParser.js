import {
  unitProcessingConfig,
  combinedParams,
  preferredOrder,
  includedDropdownElements,
  USE_MOSMIX_S,
} from "../config/constants.js";
import { elementNamesMap } from "../config/elementNamesMap.js";
import { runForecastUvAndPt } from "./uvPtApi.js";
import { calculateRelativeHumidity } from "../utils/mathUtils.js";
import { setStatus } from "../ui/domUtils.js";

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

  try {
    setStatus("Lade UV-Index und gefühlte Temperatur...");
    result_uv_and_pt = await runForecastUvAndPt(stationId);

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
    console.warn("Unerwarteter Fehler beim Verarbeiten der UV/GFT-Daten:", e);
  }

  for (const fc of forecasts) {
    const elName =
      fc.getAttributeNS(DWDNS, "elementName") || fc.getAttribute("elementName");
    const valueNode = fc.getElementsByTagNameNS(DWDNS, "value")[0];
    if (!elName || !valueNode) continue;

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

  for (const { value, error } of combinedParams) {
    if (seriesMap[value] && seriesMap[error]) {
      seriesMap[value + "_error"] = seriesMap[error];
      delete seriesMap[error];
    }
  }

  if (USE_MOSMIX_S) {
    try {
      setStatus("Integriere stündliche Vorhersagedaten...");
      const sResp = await fetch(`https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/mosmix_s/${stationId}.json`);
      //   const sResp = await fetch(`./../backend/index-MCP/data/Forecast/mosmix_s/${stationId}.json`);

      if (sResp.ok) { 
        const sData = await sResp.json();
        const sTimeMap = {};
        sData.t.forEach((ts, index) => {
          sTimeMap[new Date(ts).getTime()] = index;
        });

        for (const jsonKey in sData.d) {
          const readableName = elementNamesMap[jsonKey] || jsonKey;
          const processingRule = unitProcessingConfig[jsonKey];
          const converter = processingRule ? processingRule.convert : (v) => v;

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
      console.warn("Konnte MOSMIX-S JSON nicht laden. Nutze reine MOSMIX-L Daten als Fallback.", e);
    }
  }

  // Modulare Auslagerung
  calculateRelativeHumidity(seriesMap, timeSteps.length);

  if (
    seriesMap["Convective Available Potential Energy"] || 
    seriesMap["Convective Inhibition"] || 
    seriesMap["Modified Convective Potential"] || 
    seriesMap["Bulk Richardson Number"]
  ) {
    seriesMap["Konvektionspotential"] = []; 
  }
  
  console.log("=== KOMPLETTE EXTRAHIERTE DATEN (seriesMap) ===");
  console.log("Time series:", timeSteps);
  console.log("Parsed series:", seriesMap);

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
    return includedDropdownElements.includes(c);
  });

  return {
    timeSteps: timeSteps,
    seriesMap: seriesMap,
    result_uv_and_pt: result_uv_and_pt,
    plotColumns: plotColumns,
    stationDesc: stationDesc,
    stationHeight: stationHeight,
  };
}