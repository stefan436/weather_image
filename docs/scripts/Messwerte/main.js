//main.js

import { fetchWeatherData } from './dataFetcher.js';
import { renderWeather, setStatusMessage, showError } from './ui.js';

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