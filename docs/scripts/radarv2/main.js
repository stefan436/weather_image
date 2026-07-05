import { setupUI } from './ui.js';
import { fetchAndProcessKonrad } from './dataFetcher.js';
import { updateForecastTimeDisplay, renderKonradData, getWmsIsoTime } from './renderer.js';
import { getLocation } from './geoService.js';

const appState = {
    konradData: null,
    currentFrame: 0,
    isPlaying: false,
    animationTimer: null,
    konradLayerGroup: null 
};

const map = L.map("map").setView([48.1373, 11.57577], 10);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; OpenStreetMap',
  maxZoom: 18,
  className: "muted-osm",
}).addTo(map);

// Panes erstellen für saubere Ebenen-Trennung
map.createPane("contourPane");
map.getPane("contourPane").style.zIndex = 450;
map.getPane("contourPane").style.mixBlendMode = "multiply";

map.createPane("konradPane");
map.getPane("konradPane").style.zIndex = 460;

// Der neue WMS Layer vom DWD
const radarWmsLayer = L.tileLayer.wms("https://maps.dwd.de/geoserver/dwd/wms", {
  layers: 'dwd:Radar_rv_product_1x1km_ger',
  format: 'image/png',
  transparent: true,
  version: '1.3.0', // Für das Bild rendern nutzen wir 1.3.0
  opacity: 0.7,
  pane: "contourPane",
  attribution: '© Deutscher Wetterdienst'
}).addTo(map);

appState.konradLayerGroup = L.layerGroup().addTo(map);

// GetFeatureInfo für das Anklicken des Regens
map.on('click', function(e) {
    const hint = document.getElementById("legend-hint");
    const clickPanel = document.getElementById("legend-click");
    
    // UI zurücksetzen
    clickPanel.style.display = "none";
    if (hint) hint.style.display = "block";

    const point = map.latLngToContainerPoint(e.latlng);
    const size = map.getSize();
    const bounds = map.getBounds();
    const currentIsoTime = getWmsIsoTime(appState.currentFrame);
    
    // WMS 1.1.1 GetFeatureInfo Request (nutzt X und Y statt I und J)
    const url = "https://maps.dwd.de/geoserver/dwd/wms" +
        "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo" +
        "&LAYERS=dwd:Radar_rv_product_1x1km_ger" +
        "&QUERY_LAYERS=dwd:Radar_rv_product_1x1km_ger" +
        "&INFO_FORMAT=application/json" + 
        "&SRS=EPSG:4326" +
        "&BBOX=" + bounds.toBBoxString() +
        "&WIDTH=" + size.x + "&HEIGHT=" + size.y +
        "&X=" + Math.round(point.x) + "&Y=" + Math.round(point.y) + 
        "&TIME=" + currentIsoTime;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.features && data.features.length > 0) {
                // Bei DWD heißt das Feld oft GRAY_INDEX
                const value = data.features[0].properties.GRAY_INDEX; 
                if(value !== null && value !== undefined && value > 0) {
                    if (hint) hint.style.display = "none";
                    document.getElementById("clickValue").textContent = `${value} mm/h`;
                    clickPanel.style.display = "block";
                }
            }
        }).catch(err => console.error("Fehler beim Abrufen der Regenwerte:", err));
});

// UI und Animation steuern
setupUI(appState, {
  onStart: async () => {
    // 1. Ort abfragen (optional, falls du reinzoomen willst, ansonsten nur initialisieren)
    getLocation((lat, lon, isReal) => {
        if(isReal) map.setView([lat, lon], 10);
    });

    // 2. Konrad Daten laden
    await fetchAndProcessKonrad(appState);
    
    // 3. UI freischalten
    document.getElementById("frameSlider").disabled = false;
    document.getElementById("playPause").disabled = false;
    
    // 4. Initiales Rendern anstoßen
    appState.currentFrame = 0;
    updateFrame();
  },
  onRenderFrame: (idx) => {
    appState.currentFrame = idx;
    updateFrame();
  }
});

function updateFrame() {
    const isoTime = getWmsIsoTime(appState.currentFrame);
    // Das Bild auf der Karte updaten, ohne die Karte neu zu laden
    radarWmsLayer.setParams({ time: isoTime }, false); 
    
    updateForecastTimeDisplay(appState);
    renderKonradData(appState, map);
}