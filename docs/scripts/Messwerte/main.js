//main.js

import { fetchWeatherData } from './dataFetcher.js';
import { renderWeather, setStatusMessage, showError } from './ui.js';

function handleLocationRequest() {
  if (!navigator.geolocation) {
    setStatusMessage("Geolocation wird von deinem Browser nicht unterstützt.");
    return;
  }


  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        const fields = await fetchWeatherData(pos.coords.latitude, pos.coords.longitude);
        renderWeather(fields);
      } catch (err) {
        console.error("Ein kritischer Fehler ist aufgetreten:", err);
        setStatusMessage(err.message || "Fehler beim Laden der Haupt-Wetterdaten.");
      }
    },
    showError
  );
}

// Event Listener registrieren, sobald das DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
  const loadBtn = document.getElementById('loadWeatherBtn');
  if (loadBtn) {
    loadBtn.addEventListener('click', handleLocationRequest);
  }
});