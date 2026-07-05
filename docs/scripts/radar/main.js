import { setupUI } from './ui.js';
import { fetchAndProcessComposite } from './dataFetcher.js';
import { renderAllFrames, renderFrame } from './renderer.js';
import { getLocation } from './geoService.js';

// Zentraler State der Anwendung (Single Source of Truth)
const appState = {
    frames: [],
    lat: [],
    lon: [],
    konradData: null,
    contourLayers: [],
    preRenderedFrames: [],
    currentFrame: 0,
    forecastTime: 0,
    isPlaying: false,
    animationTimer: null,
    userLocationMarker: null,
    konradLayerGroup: null // Wird nach Map-Init gesetzt
};

// Ein einzelner Canvas-Renderer für das gesamte Radar (Der Performance-Boost!)
const canvasRenderer = L.canvas({ pane: "contourPane" });

// --- Initialisierung der Karte ---
const map = L.map("map").setView([48.1373, 11.57577], 10);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>-Mitwirkende',
  maxZoom: 18,
  className: "muted-osm",
}).addTo(map);


// --- Problem 1: Layering-Problem lösen ---
// Pane für Regenradar-Konturen (unten)
map.createPane("contourPane");
map.getPane("contourPane").style.zIndex = 450;
map.getPane("contourPane").style.mixBlendMode = "multiply";

// Pane für benutzerstandort
map.createPane("markerPane");
map.getPane("markerPane").style.zIndex = 470;

// Pane für KONRAD-Daten (oben)
map.createPane("konradPane");
map.getPane("konradPane").style.zIndex = 460;

appState.konradLayerGroup = L.layerGroup().addTo(map);

const mapEl = document.getElementById("map");
new ResizeObserver(() => map.invalidateSize()).observe(mapEl);

// Schließt die Intensitätsanzeige, wenn auf eine freie Kartenfläche geklickt wird
map.on("click", () => {
  document.getElementById("legend-click").style.display = "none";
});

// Setzt die Legende zurück, wenn auf eine freie Kartenfläche geklickt wird
map.on("click", () => {
  const hint = document.getElementById("legend-hint");
  const clickPanel = document.getElementById("legend-click");

  if (hint && clickPanel) {
    hint.style.display = "block";
    clickPanel.style.display = "none";
  }
});

function convertIndicesToLatLon(line, latGrid, lonGrid) {
  return line
    .map(([x, y]) => {
      const xi = Math.round(x),
        yi = Math.round(y);
      if (yi >= 0 && yi < latGrid.length && xi >= 0 && xi < latGrid[0].length)
        return [latGrid[yi][xi], lonGrid[yi][xi]];
      return null;
    })
    .filter((pt) => pt !== null);
}


// --- Problem 2: Legenden-Interaktivität lösen ---
// Implementierung der Funktion
function attachContourEvents(polygon, value) {
  const legendHover = document.getElementById("legend-hover");
  const hoverColorBox = document.getElementById("hoverColorBox");
  const hoverValue = document.getElementById("hoverValue");

  const showHoverInfo = () => {
    const color = colorScale(value).hex();
    hoverColorBox.style.backgroundColor = color;
    hoverValue.textContent = `${value.toFixed(1)} mm/h`;
    legendHover.style.display = "block";
  };

  const hideHoverInfo = () => {
    legendHover.style.display = "none";
  };

  polygon.on("mouseover", showHoverInfo);
  polygon.on("mouseout", hideHoverInfo);
  polygon.on("click", showHoverInfo); // Für Touch-Geräte
}


// 3. UI Setup mit Callbacks
setupUI(appState, {
  onStart: () => {
    // Wenn "Start" geklickt wird -> Ort abfragen -> Daten laden
    getLocation((lat, lon, isReal) => {
      fetchAndProcessComposite(appState, map, lat, lon, isReal, async () => {
        // Callback: Wird gerufen, wenn Download fertig ist
        await renderAllFrames(appState, map, canvasRenderer, convertIndicesToLatLon);
        renderFrame(appState, map);
      });
    });
  },
  onRenderFrame: (idx) => {
    renderFrame(appState, map);
  }
});