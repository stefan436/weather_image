import { haversineDistance } from "../utils/mathUtils.js";

const cache = new Map();
let lastRequestTime = 0;

export async function fetchCoordinates(address) {
  if (!address) return { error: "Bitte gib eine Adresse ein." };

  if (cache.has(address)) {
    const cachedData = cache.get(address);
    console.log("Aus dem Cache geladen:", address);
    return { data: cachedData[0] };
  }

  const now = Date.now();
  const timeSinceLast = now - lastRequestTime;
  const delay = Math.max(0, 1000 - timeSinceLast);

  await new Promise((resolve) => setTimeout(resolve, delay));
  lastRequestTime = Date.now();

  const proxy =
    "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev?url=";
  const baseUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${address}`;
  const url = proxy + encodeURIComponent(baseUrl);

  try {
    const response = await fetch(url, {
      headers: {
        "Accept-Language": "de",
        "User-Agent":
          "wetterprojekt-stefan-2025 (https://stefan436.github.io/)",
      },
    });

    if (!response.ok) throw new Error("Fehler bei der Geocoding-Anfrage.");

    const requestAdressData = await response.json();
    cache.set(address, requestAdressData);

    if (requestAdressData.length > 0) {
      return { data: requestAdressData[0] };
    } else {
      return { error: "Keine Ergebnisse gefunden." };
    }
  } catch (error) {
    return { error: error.message };
  }
}

export function getNearestStations(lat, lon, stationData) {
  const stationsWithDist = stationData
    .map((row) => {
      const stationLat = parseFloat(row.lat);
      const stationLon = parseFloat(row.lon);
      if (isNaN(stationLat) || isNaN(stationLon)) return null;
      const distance = haversineDistance(lat, lon, stationLat, stationLon);
      return { ...row, distance };
    })
    .filter(Boolean);

  stationsWithDist.sort((a, b) => a.distance - b.distance);
  return stationsWithDist.slice(0, 5);
}