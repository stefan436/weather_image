// geoService.js - Kapselung von API-Anfragen und mathematischen Berechnungen

const cache = new Map();
let lastRequestTime = 0;

/**
 * Führt das Geocoding für eine Adresse via Nominatim durch.
 * Kapselt das Rate-Limiting und Caching intern.
 * Gibt entweder die Daten oder eine Fehlermeldung zurück.
 */
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

// Mathematische Hilfsfunktionen zur Distanzberechnung
function toRadians(deg) {
  return (deg * Math.PI) / 180;
}

function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Erdradius in Metern
  const φ1 = toRadians(lat1),
    φ2 = toRadians(lat2);
  const Δφ = toRadians(lat2 - lat1),
    Δλ = toRadians(lon2 - lon1);
  const a =
    Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Filtert aus der Gesamtliste aller Stationen die 5 nächstgelegenen heraus
 * und gibt sie sortiert nach Entfernung zurück.
 */
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



export function getStationTime(dateInput, timeZoneId) {
  // Dynamische Instanziierung mit der Zeitzone der Station
  const formatter = new Intl.DateTimeFormat('de-DE', {
    timeZone: timeZoneId,
    year: 'numeric', month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: 'numeric', second: 'numeric',
    hour12: false
  });
  
  const d = new Date(dateInput);
  const parts = formatter.formatToParts(d);
  
  const getP = (type) => parseInt(parts.find(p => p.type === type).value, 10);
  
  const year = getP('year');
  const month = getP('month');
  const day = getP('day');
  const hour = getP('hour');
  
  const pad = (n) => String(n).padStart(2, '0');
  
  return {
    d, 
    year, month, day, hour,
    dayIso: `${year}-${pad(month)}-${pad(day)}`, // YYYY-MM-DD
    plotlyString: `${year}-${pad(month)}-${pad(day)} ${pad(hour)}:00:00`
  };
}
