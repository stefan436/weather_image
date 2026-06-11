// main.js - Der zentrale Orchestrator (Zuständig für Event-Handling und Koordination)

import { loadMosmixData } from "./dataParser.js";
import { renderPlot } from "./plot.js";
import { setStatus, buildSummary, renderStationChoices } from "./ui.js";
import { fetchCoordinates, getNearestStations } from "./geoService.js";

// --- Globaler Zustand (State) der Anwendung ---
// Nur noch Kernvariablen, die für die app-weite Koordination benötigt werden
let userLat = null;
let userLon = null;
let currentGeocodeData = null; // Speichert das gefundene Ergebnis vor der Bestätigung

const appState = {
  seriesMap: {},
  timeSteps: [],
  result_uv_and_pt: null,
  minDistance: Infinity,
};

// --- Geocoding Event-Handler ---
async function handleGeocodeRequest() {
  const address = document.getElementById("address").value;
  const resultDiv = document.getElementById("result");
  const confirmBtn = document.getElementById("confirmButton");

  confirmBtn.style.display = "none";
  currentGeocodeData = null;

  if (!address) {
    resultDiv.textContent = "Bitte gib eine Adresse ein.";
    return;
  }

  setStatus("Suche Adresse …");
  const result = await fetchCoordinates(address);
  setStatus("");

  if (result.error) {
    resultDiv.textContent = "Fehler: " + result.error;
    return;
  }

  // Erfolg: Daten zwischenspeichern und Bestätigung erlauben
  currentGeocodeData = result.data;
  resultDiv.innerHTML = `<strong>${currentGeocodeData.display_name}</strong>`;
  confirmBtn.style.display = "inline-block";
}

function handleConfirmResult() {
  if (!currentGeocodeData) return;

  userLat = parseFloat(currentGeocodeData.lat);
  userLon = parseFloat(currentGeocodeData.lon);

  findAndRenderStations();
}

// --- Stationssuche koordineren ---
async function findAndRenderStations() {
  setStatus("Lade Stationsliste …");

  try {
    const response = await fetch("data/mosmix_stationen_coords.json");
    if (!response.ok) throw new Error("JSON konnte nicht geladen werden.");
    const stationData = await response.json();

    // Falls der Button "Aktueller Standort" geklickt wurde und Koordinaten noch fehlen:
    if (userLat === null || userLon === null) {
      if (!navigator.geolocation) {
        setStatus("Geolocation wird nicht unterstützt.");
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          userLat = position.coords.latitude;
          userLon = position.coords.longitude;
          const nearestStations = getNearestStations(
            userLat,
            userLon,
            stationData,
          );
          renderStationChoices(nearestStations, handleStationSelection);
          setStatus("");
        },
        (error) => {
          setStatus(
            "Nutze Suchfeld für manuelle Eingabe. Fehler beim Standortzugriff: " +
              error.message,
          );
        },
      );
    } else {
      // Adresse wurde manuell eingegeben und bestätigt
      const nearestStations = getNearestStations(userLat, userLon, stationData);
      renderStationChoices(nearestStations, handleStationSelection);
      setStatus("");
    }
  } catch (err) {
    setStatus("Fehler: " + err.message);
  }
}

// --- Zentrale Koordination nach finaler Stationsauswahl ---
async function handleStationSelection(stationId, distance) {
  try {
    appState.minDistance = distance;
    setStatus(`Station ${stationId} gewählt – lade KMZ …`);

    // 1. Daten asynchron parsen lassen
    const data = await loadMosmixData(stationId, userLat, userLon);

    // 2. Zustand ablegen
    appState.seriesMap = data.seriesMap;
    appState.timeSteps = data.timeSteps;
    appState.result_uv_and_pt = data.result_uv_and_pt;

    // 3. Metadaten anzeigen
    const metadataEl = document.getElementById("station-metadata-container");
    metadataEl.innerHTML = `<b>Station:</b> ${data.stationDesc} &nbsp; <b>Höhe:</b> ${data.stationHeight} m ü. M. &nbsp; <b>Entfernung:</b> ${Math.round(appState.minDistance)} m`;
    metadataEl.style.display = "block";

    // 4. Dropdown befüllen
    const plotSel = document.getElementById("plotSelect");
    plotSel.innerHTML = data.plotColumns
      .map((c) => {
        const selected = c === "Temperatur (°C)" ? "selected" : "";
        return `<option value="${c}" ${selected}>${c}</option>`;
      })
      .join("");
    plotSel.disabled = false;

    // 5. Ersten Plot erzeugen
    const defaultParam = data.plotColumns.includes("Temperatur (°C)")
      ? "Temperatur (°C)"
      : data.plotColumns[0];
    if (defaultParam) {
      renderPlot(
        defaultParam,
        appState.seriesMap,
        appState.timeSteps,
        appState.result_uv_and_pt,
      );
    }

    // 6. Wetterzusammenfassung generieren
    buildSummary(appState.seriesMap, appState.timeSteps);
    document.getElementById("search-section").style.display = "none";
    document.getElementById("station-choices-container").style.display = "none";

    // 7. Gesamten Suchbereich ausblenden, sobald die Daten da sind
    document.getElementById("search-section").style.display = "none";

    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus("Fehler: " + err.message);
  }
}

// --- Registrierung der Event-Listener ---
document
  .getElementById("loadButton")
  .addEventListener("click", findAndRenderStations);
document
  .getElementById("addressButton")
  .addEventListener("click", handleGeocodeRequest);
document
  .getElementById("confirmButton")
  .addEventListener("click", handleConfirmResult);

document.getElementById("plotSelect").addEventListener("change", (e) => {
  renderPlot(
    e.target.value,
    appState.seriesMap,
    appState.timeSteps,
    appState.result_uv_and_pt,
  );
});
