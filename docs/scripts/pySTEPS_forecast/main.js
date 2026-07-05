import { setupUI } from "./ui.js";
import { preloadFrames, renderFrame } from "./renderer.js";
import { meta_path, radarLevels } from "./config.js";
import { getLocation } from "./geoService.js";
import { fetchMetaData, fetchAndProcessKonrad } from "./dataFetcher.js";

// Zentraler State
const appState = {
  bounds: null,
  frames: [], // Speichert {time, url, overlay}
  currentFrame: 0,
  konradData: null,
  konradLayerGroup: null,
  currentFrame: 0,
  isPlaying: false,
  animationTimer: null,
};

// --- Initialisierung der Karte ---
const map = L.map("map").setView([48.137208, 11.575525], 10);
getLocation((lat, lon, is_real) => {
  map.setView([lat, lon], 10);
});

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap-Mitwirkende",
  crossOrigin: true,
  maxZoom: 18,
  className: "muted-osm",
}).addTo(map);

// Pane für Regenradar (stellt sicher, dass es über der Karte liegt)
map.createPane("radarPane");
map.getPane("radarPane").style.zIndex = 450;

map.createPane("konradPane");
map.getPane("konradPane").style.zIndex = 460;
appState.konradLayerGroup = L.layerGroup().addTo(map);

const mapEl = document.getElementById("map");
new ResizeObserver(() => map.invalidateSize()).observe(mapEl);

// Legende einblenden
document.getElementById("legend").style.display = "block";

// --- UI & Logik verbinden ---
setupUI(appState, {
  onStart: async () => {
    const startBtn = document.getElementById("start");
    const statusText = document.getElementById("status_output");

    startBtn.style.display = "none";
    statusText.style.display = "inline";
    statusText.textContent = "Lade Metadaten...";

    try {
      // 1. JSON abrufen
      const meta = await fetchMetaData(meta_path);
      appState.bounds = meta.bounds;
      appState.frames = meta.frames;

      // Ermittle den Index für T0 (falls er nicht schon fest im Backend verankert ist)
      const t0Idx = appState.frames.findIndex(f => f.relative_time === "T0");
      appState.t0Index = t0Idx !== -1 ? t0Idx : 0;

      // Platziere den T0-Marker exakt an der berechneten Prozent-Stelle
      const maxFrames = appState.frames.length - 1;
      if (maxFrames > 0) {
        const t0Percent = (appState.t0Index / maxFrames) * 100;
        const marker = document.getElementById("t0-marker");
        if (marker) {
          // Korrekturformel für die Breite des Slider-Thumbs (18px)
          marker.style.left = `calc(${t0Percent}% + (${9 - t0Percent * 0.18}px))`;
        }
      }

      // 3. Bilder in Leaflet vorladen
      statusText.textContent = "Lade Radarbilder...";
      await preloadFrames(appState, map);

      statusText.textContent = "Lade KONRAD3D...";
      await fetchAndProcessKonrad(appState);

      // 4. UI freischalten
      const slider = document.getElementById("frameSlider");
      slider.max = appState.frames.length - 1;
      // Setze Startwert direkt auf T0 anstatt auf 0
      appState.currentFrame = appState.t0Index || 0;
      slider.value = appState.currentFrame;
      
      slider.disabled = false;
      document.getElementById("playPause").disabled = false;

      statusText.style.display = "none";

      // 5. Erstes Frame anzeigen
      renderFrame(appState);
    } catch (error) {
      statusText.textContent = "Fehler: " + error.message;
      startBtn.style.display = "inline";
      startBtn.disabled = false;
    }
  },
  onRenderFrame: () => {
    renderFrame(appState);
  },
});

// Hilfsfunktion: Konvertiert HEX-Farbe zu RGB für den Farbabgleich
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

// Klick-Event auf der Karte für die Radar-Legende
map.on("click", (e) => {
  const legendHint = document.getElementById("legend-hint");
  const legendClick = document.getElementById("legend-click");

  function resetLegend() {
    if (legendHint) legendHint.style.display = "block";
    if (legendClick) legendClick.style.display = "none";
  }

  // Abbruch, wenn noch keine Bilder geladen wurden
  if (!appState.frames || appState.frames.length === 0 || !appState.bounds) {
    return;
  }

  const bounds = L.latLngBounds(appState.bounds);

  // Wenn außerhalb des Radar-Rechtecks geklickt wird -> Legende zurücksetzen
  if (!bounds.contains(e.latlng)) {
    resetLegend();
    return;
  }

  const currentFrameObj = appState.frames[appState.currentFrame];
  if (!currentFrameObj || !currentFrameObj.overlay) return;

  const imgEl = currentFrameObj.overlay.getElement();
  if (!imgEl) return;

  // NEU: Berechnung über tatsächliche Bildschirmkoordinaten (DOM).
  // Dies umgeht die Projektionsverzerrung der Karte vollständig.
  const imgRect = imgEl.getBoundingClientRect();
  const clickX = e.originalEvent.clientX - imgRect.left;
  const clickY = e.originalEvent.clientY - imgRect.top;

  const xRatio = clickX / imgRect.width;
  const yRatio = clickY / imgRect.height;

  const canvas = document.createElement("canvas");
  canvas.width = imgEl.naturalWidth || imgEl.width;
  canvas.height = imgEl.naturalHeight || imgEl.height;
  const ctx = canvas.getContext("2d");

  ctx.drawImage(imgEl, 0, 0, canvas.width, canvas.height);

  const x = Math.floor(xRatio * canvas.width);
  const y = Math.floor(yRatio * canvas.height);

  let pixel;
  try {
    pixel = ctx.getImageData(x, y, 1, 1).data;
  } catch (err) {
    console.error("Fehler beim Auslesen des Pixels (evtl. CORS):", err);
    return;
  }

  const alpha = pixel[3];

  // Diagnose-Ausgabe in der Konsole: Zeigt an, welche Farbe tatsächlich geklickt wurde
  console.log(
    `Geklickter Pixel X:${x}, Y:${y} | RGBA: ${pixel[0]}, ${pixel[1]}, ${pixel[2]}, ${alpha}`,
  );

  // Wenn der Bereich komplett transparent ist (kein Regen)
  if (alpha === 0) {
    resetLegend();
    return;
  }

  let minDistance = Infinity;
  let closestLevel = null;

  for (const level of radarLevels) {
    const rgb = hexToRgb(level.color);
    if (rgb) {
      const dist = Math.sqrt(
        Math.pow(pixel[0] - rgb.r, 2) +
          Math.pow(pixel[1] - rgb.g, 2) +
          Math.pow(pixel[2] - rgb.b, 2),
      );
      if (dist < minDistance) {
        minDistance = dist;
        closestLevel = level;
      }
    }
  }

  console.log(
    `Kürzeste Distanz zur Konfigurations-Palette: ${minDistance.toFixed(1)} (Zugeordnet: ≥ ${closestLevel?.min} mm/h)`,
  );

  // Toleranz deutlich erhöht (100 statt 50), um weiche Kanten abzufangen
  if (closestLevel && minDistance < 100) {
    if (legendHint) legendHint.style.display = "none";
    if (legendClick) legendClick.style.display = "block";

    const colorBox = document.getElementById("clickColorBox");
    const valueText = document.getElementById("clickValue");

    if (colorBox) colorBox.style.backgroundColor = closestLevel.color;
    if (valueText) valueText.textContent = `≥ ${closestLevel.min} mm/h`;
  } else {
    console.log("Farbe wich zu stark von der hinterlegten Palette ab.");
    resetLegend();
  }
});
