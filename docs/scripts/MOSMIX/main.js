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
  timeZoneId: "UTC", // Standard-Fallback
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
  setStatus("Bestätigen der Adresse ...");

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
    const response = await fetch("https://users.ph.nat.tum.de/ge47fab/weather_data/mosmix_stationen_coords.json");
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
          setStatus("Wähle Ort der Vorhersage");
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
      setStatus("Wähle Ort der Vorhersage");
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

    // Zeitzone aus den genutzten Koordinaten ermitteln
    appState.timeZoneId = tzlookup(userLat, userLon);
    console.log("Lokale Zeitzone der Station:", appState.timeZoneId);

    // 1. Daten asynchron parsen lassen
    const data = await loadMosmixData(stationId, userLat, userLon);
    setStatus("Erstelle Grafiken...");

    // 2. Zustand ablegen
    appState.seriesMap = data.seriesMap;
    appState.timeSteps = data.timeSteps;
    appState.result_uv_and_pt = data.result_uv_and_pt;

    // 3. Metadaten anzeigen
    const metadataEl = document.getElementById("station-metadata-container");
    metadataEl.innerHTML = `<b>Station:</b> ${data.stationDesc} &nbsp; <b>Höhe:</b> ${data.stationHeight} m ü. M. &nbsp; <b>Entfernung:</b> ${Math.round(appState.minDistance)} m`;
    metadataEl.style.display = "block";

    // 4. Dropdown befüllen
    let availableColumns = data.plotColumns;
    
    // UV-Index herausfiltern, falls result_uv_and_pt null ist
    if (!appState.result_uv_and_pt) {
      availableColumns = availableColumns.filter(c => !c.includes("UV-Index"));
    }

    const plotSel = document.getElementById("plotSelect");
    plotSel.innerHTML = availableColumns
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
        appState.timeZoneId,
      );
    }

    // 6. Wetterzusammenfassung generieren
    buildSummary(appState.seriesMap, appState.timeSteps, appState.timeZoneId);
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
    appState.timeZoneId,
  );
});

document.addEventListener('DOMContentLoaded', () => {
    // NEU: Automatische Auswertung der URL-Parameter für die Stationskarte
    const urlParams = new URLSearchParams(window.location.search);
    const latParam = urlParams.get('lat');
    const lonParam = urlParams.get('lon');

    if (latParam && lonParam) {
        const addressInput = document.getElementById('address');
        const addressBtn = document.getElementById('addressButton');
        
        if (addressInput && addressBtn) {
            // 1. Koordinaten formatiert in das Suchfeld schreiben
            addressInput.value = `${latParam}, ${lonParam}`;
            
            // 2. Suche automatisch auslösen
            addressBtn.click();
            // Parameter sofort nach dem Trigger aus der Adresszeile löschen!
            // Macht im Hintergrund aus "index.html?lat=XX&lon=YY" einfach wieder "index.html"
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // 3. Optionale automatische Bestätigung:
            // Da das Laden der Stationen asynchron per API geschieht, taucht der Bestätigen-Button erst kurz danach auf.
            // Wenn deine Such-Logik bei exakten Koordinaten-Treffern automatisch den "confirmButton" klickt,
            // musst du hier nichts weiter tun. Falls nicht, kannst du einen kleinen Observer oder Timeout nutzen,
            // um den confirmButton automatisch zu klicken, sobald er sichtbar wird:
            const checkConfirmInterval = setInterval(() => {
                const confirmBtn = document.getElementById('confirmButton');
                if (confirmBtn && confirmBtn.style.display !== 'none') {
                    confirmBtn.click();
                    clearInterval(checkConfirmInterval); // Intervall stoppen, sobald bestätigt wurde
                }
            }, 100);

            // Nach 5 Sekunden die Suche abbrechen, falls nichts gefunden wurde (Sicherheitshalber)
            setTimeout(() => clearInterval(checkConfirmInterval), 5000);
        }
    }
});
