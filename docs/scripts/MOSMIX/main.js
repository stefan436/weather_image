// main.js - Der zentrale Orchestrator (Zuständig für Event-Handling und Koordination)

import { loadMosmixData } from "./dataParser.js";
import { renderPlot } from "./plot.js";
import { setStatus, buildSummary, renderStationChoices } from "./ui.js";
import { fetchCoordinates, getNearestStations } from "./geoService.js";

// Import NavBar
// 1. Navbar laden (Pfade ggf. korrigieren, z.B. /scripts/shared/navbar.html)
fetch('/docs/scripts/shared/navbar.html')
  .then(response => {
    if (!response.ok) {
      throw new Error(`Navbar konnte nicht geladen werden: ${response.status}`);
    }
    return response.text();
  })
  .then(data => {
    // 2. HTML in den Platzhalter einfügen
    const placeholder = document.getElementById('navbar-placeholder');
    if (placeholder) {
      placeholder.innerHTML = data;
    }

    // 3. Hamburger-Menü ERST HIER initialisieren, wenn das HTML wirklich da ist!
    const hamburger = document.getElementById('hamburger-icon');
    const menu = document.getElementById('nav-menu');

    if (hamburger && menu) {
      hamburger.addEventListener('click', () => {
        menu.classList.toggle('active'); // Wechselt die CSS-Klasse für das Menü
        hamburger.classList.toggle('open'); // Falls du das Icon selbst animierst
      });
    }
  })
  .catch(error => {
    console.error("Fehler beim Laden der Navigation:", error);
  });


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
    const response = await fetch(
      "https://users.ph.nat.tum.de/ge47fab/weather_data/mosmix_stationen_coords.json",
    );
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
      availableColumns = availableColumns.filter(
        (c) => !c.includes("UV-Index"),
      );
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
document.addEventListener("DOMContentLoaded", () => {
  // Automatische Auswertung der URL-Parameter für die Stationskarte
  const urlParams = new URLSearchParams(window.location.search);
  const latParam = urlParams.get("lat");
  const lonParam = urlParams.get("lon");
  const stationId = urlParams.get("stationId");
  const stationName = urlParams.get("stationName")
  // console.log(`lat: ${latParam}, lon: ${lonParam}, stationId: ${stationId}, stationName: ${stationName}`);

  // Wenn wir die Station-ID bereits aus der URL kennen!
  if (stationId && latParam && lonParam) {
    
    // 1. Globale Koordinaten setzen (wird für die Zeitzone und den API-Aufruf benötigt)
    userLat = parseFloat(latParam);
    userLon = parseFloat(lonParam);

    // 2. Suchbereich sofort ausblenden, da wir nicht suchen müssen
    const searchSection = document.getElementById("search-section");
    if (searchSection) searchSection.style.display = "none";

    // 3. Parameter aus der Adresszeile löschen (für saubere Reloads)
    window.history.replaceState({}, document.title, window.location.pathname);

    // 4. DIREKT den Ladeprozess starten! (Distanz ist 0, da wir exakt diese Station gewählt haben)
    handleStationSelection(stationId, 0);

  }
  else if (latParam && lonParam) {
    const searchSection = document.getElementById("search-section");
    const addressInput = document.getElementById("address");
    const addressBtn = document.getElementById("addressButton");

    if (addressInput && addressBtn) {
      // 1. Koordinaten formatiert in das Suchfeld schreiben
      addressInput.value = `${latParam}, ${lonParam}`;

      // 2. Suche automatisch auslösen
      addressBtn.click();

      // Das Result-Div sofort ausblenden
      const resultDiv = document.getElementById("result");
      if (resultDiv) {
        resultDiv.style.display = "none";
      }

      // Parameter sofort nach dem Trigger aus der Adresszeile löschen!
      window.history.replaceState({}, document.title, window.location.pathname);

      // 3. Automatischer Ablauf: Erst Bestätigen -> Dann Station wählen
      const automatedFlowInterval = setInterval(() => {
        const confirmBtn = document.getElementById("confirmButton");
        const stationContainer = document.getElementById(
          "station-choices-container",
        );
        const firstStationBtn = stationContainer
          ? stationContainer.querySelector(".station-btn")
          : null;

        // SCHRITT A: Der Bestätigen-Button ist da, aber die Stationen wurden noch nicht gerendert.
        // Wir klicken auf Bestätigen.
        if (
          confirmBtn &&
          confirmBtn.style.display !== "none" &&
          !firstStationBtn
        ) {
          confirmBtn.style.display = "none"; // Verstecken vor dem Klick
          confirmBtn.click();
          return; // Schleife verlassen und auf das Rendern der Stationen im nächsten Durchlauf warten
        }

        // SCHRITT B: Nach dem Bestätigen-Klick sind die Stations-Buttons nun endlich im HTML aufgetaucht.
        if (firstStationBtn) {
          // Die oberste Station anklicken (das löst dein onStationSelect aus)
          firstStationBtn.click();

          // Alles erledigt -> Intervall beenden!
          clearInterval(automatedFlowInterval);
        }
      }, 100);

      // Nach 7 Sekunden abbrechen (Sicherheitsanker, da wir jetzt zwei asynchrone Schritte haben)
      setTimeout(() => clearInterval(automatedFlowInterval), 7000);
    }
  }
});
