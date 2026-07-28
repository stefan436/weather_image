import { loadMosmixData } from "./api/weatherParser.js";
import { renderPlot } from "./ui/plot.js";
import { setStatus, renderStationChoices } from "./ui/domUtils.js";
import { buildSummary } from "./ui/summary.js";
import { fetchCoordinates, getNearestStations } from "./api/geoApi.js";

let userLat = null;
let userLon = null;
let currentGeocodeData = null; 

const appState = {
  seriesMap: {},
  timeSteps: [],
  result_uv_and_pt: null,
  minDistance: Infinity,
  timeZoneId: "UTC", 
};

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

async function findAndRenderStations() {
  setStatus("Lade Stationsliste …");

  try {
    const response = await fetch(
      "https://users.ph.nat.tum.de/ge47fab/weather_data/mosmix_stationen_coords.json",
    );
    if (!response.ok) throw new Error("JSON konnte nicht geladen werden.");
    const stationData = await response.json();

    if (userLat === null || userLon === null) {
      if (!navigator.geolocation) {
        setStatus("Geolocation wird nicht unterstützt.");
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          userLat = position.coords.latitude;
          userLon = position.coords.longitude;
          const nearestStations = getNearestStations(userLat, userLon, stationData);
          renderStationChoices(nearestStations, handleStationSelection);
          setStatus("Wähle Ort der Vorhersage");
        },
        (error) => {
          setStatus("Nutze Suchfeld für manuelle Eingabe. Fehler beim Standortzugriff: " + error.message);
        },
      );
    } else {
      const nearestStations = getNearestStations(userLat, userLon, stationData);
      renderStationChoices(nearestStations, handleStationSelection);
      setStatus("Wähle Ort der Vorhersage");
    }
  } catch (err) {
    setStatus("Fehler: " + err.message);
  }
}

async function handleStationSelection(stationId, distance) {
  try {
    appState.minDistance = distance;
    setStatus(`Station ${stationId} gewählt – lade KMZ …`);

    // (Global verfügbar durch index.html imports)
    appState.timeZoneId = tzlookup(userLat, userLon);
    console.log("Lokale Zeitzone der Station:", appState.timeZoneId);

    const data = await loadMosmixData(stationId, userLat, userLon);
    setStatus("Erstelle Grafiken...");

    appState.seriesMap = data.seriesMap;
    appState.timeSteps = data.timeSteps;
    appState.result_uv_and_pt = data.result_uv_and_pt;

    const metadataEl = document.getElementById("station-metadata-container");
    metadataEl.innerHTML = `<b>Station:</b> ${data.stationDesc} &nbsp; <b>Höhe:</b> ${data.stationHeight} m ü. M. &nbsp; <b>Entfernung:</b> ${Math.round(appState.minDistance)} m`;
    metadataEl.style.display = "block";

    let availableColumns = data.plotColumns;

    if (!appState.result_uv_and_pt) {
      availableColumns = availableColumns.filter((c) => !c.includes("UV-Index"));
    }

    const plotSel = document.getElementById("plotSelect");
    plotSel.innerHTML = availableColumns
      .map((c) => {
        const selected = c === "Temperatur (°C)" ? "selected" : "";
        return `<option value="${c}" ${selected}>${c}</option>`;
      })
      .join("");
    plotSel.disabled = false;

    const defaultParam = data.plotColumns.includes("Temperatur (°C)")
      ? "Temperatur (°C)"
      : data.plotColumns[0];
    if (defaultParam) {
      renderPlot(defaultParam, appState.seriesMap, appState.timeSteps, appState.result_uv_and_pt, appState.timeZoneId);
    }

    buildSummary(appState.seriesMap, appState.timeSteps, appState.timeZoneId);
    
    document.getElementById("search-section").style.display = "none";
    document.getElementById("station-choices-container").style.display = "none";
    document.getElementById("search-section").style.display = "none";
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus("Fehler: " + err.message);
  }
}

document.getElementById("loadButton").addEventListener("click", findAndRenderStations);
document.getElementById("addressButton").addEventListener("click", handleGeocodeRequest);
document.getElementById("confirmButton").addEventListener("click", handleConfirmResult);

document.getElementById("plotSelect").addEventListener("change", (e) => {
  renderPlot(e.target.value, appState.seriesMap, appState.timeSteps, appState.result_uv_and_pt, appState.timeZoneId);
});

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const latParam = urlParams.get("lat");
  const lonParam = urlParams.get("lon");
  const stationId = urlParams.get("stationId");
  const stationName = urlParams.get("stationName");

  if (stationId && latParam && lonParam) {
    userLat = parseFloat(latParam);
    userLon = parseFloat(lonParam);

    const searchSection = document.getElementById("search-section");
    if (searchSection) searchSection.style.display = "none";

    window.history.replaceState({}, document.title, window.location.pathname);
    handleStationSelection(stationId, 0);

  } else if (latParam && lonParam) {
    const searchSection = document.getElementById("search-section");
    const addressInput = document.getElementById("address");
    const addressBtn = document.getElementById("addressButton");

    if (addressInput && addressBtn) {
      addressInput.value = `${latParam}, ${lonParam}`;
      addressBtn.click();

      const resultDiv = document.getElementById("result");
      if (resultDiv) {
        resultDiv.style.display = "none";
      }

      window.history.replaceState({}, document.title, window.location.pathname);

      const automatedFlowInterval = setInterval(() => {
        const confirmBtn = document.getElementById("confirmButton");
        const stationContainer = document.getElementById("station-choices-container");
        const firstStationBtn = stationContainer
          ? stationContainer.querySelector(".station-btn")
          : null;

        if (confirmBtn && confirmBtn.style.display !== "none" && !firstStationBtn) {
          confirmBtn.style.display = "none"; 
          confirmBtn.click();
          return; 
        }

        if (firstStationBtn) {
          firstStationBtn.click();
          clearInterval(automatedFlowInterval);
        }
      }, 100);

      setTimeout(() => clearInterval(automatedFlowInterval), 7000);
    }
  }
});