import { getLocation } from "./geoService.js";

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

document.addEventListener("DOMContentLoaded", () => {
  // 1. Karte initialisieren (Fokus auf Mitteleuropa)
  const map = L.map("map").setView([48.137208, 11.575525], 8);
  getLocation((lat, lon, is_real) => {
    map.setView([lat, lon], 8)
  });
  // 2. OpenStreetMap Tiles laden
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
  }).addTo(map);

  // 3. MOSMIX JSON-Daten laden
  fetch(
    "https://users.ph.nat.tum.de/ge47fab/weather_data/mosmix_stationen_coords.json",
  )
    .then((response) => {
      if (!response.ok) {
        throw new Error("Netzwerkantwort war nicht ok");
      }
      return response.json();
    })
    .then((stations) => {
      // 4. Für jeden Eintrag im JSON einen Marker setzen
      stations.forEach((station) => {
        const lat = parseFloat(station.lat);
        const lon = parseFloat(station.lon);

        if (!isNaN(lat) && !isNaN(lon)) {
          const marker = L.circleMarker([lat, lon], {
            radius: 6,
            fillColor: "#3388ff",
            color: "#fff",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
          }).addTo(map);

          // NEU: Ein Link, der als Button gestylt ist und die Koordinaten via URL übergibt
          const popupContent = `
                        <strong>${station.description}</strong><br>
                        <div style="margin-top: 5px; font-size: 0.9em; margin-bottom: 10px;">
                            Höhe: ${station.height} m<br>
                        </div>
                        <a href="./../index.html?lat=${lat}&lon=${lon}&stationId=${station.station_id}&stationName=${encodeURIComponent(station.description)}"
                        style="display: block; text-align: center; background-color: #4f4f4f; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 0.85em; font-weight: bold;">
                        Diese Station auswählen
                        </a>
                    `;

          marker.bindPopup(popupContent);
        }
      });
    })
    .catch((error) => {
      console.error("Fehler beim Laden der Stationsdaten:", error);
    });
});
