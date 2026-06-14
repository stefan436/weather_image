// dataFetcher.js

const DateTime = luxon.DateTime;

function formatValue(value, unit = "") {
  if (value === null || value === undefined || value === "") {
    return "Keine Daten";
  }
  return `${value}${unit}`;
}

export async function fetchWeatherData(lat, lon) {
  const proxy =
    "https://cors-proxy-for-weather-app.stefan-wiedemann01.workers.dev";
  const targetUrlBrightsky = `https://api.brightsky.dev/weather?lat=${lat}&lon=${lon}&date=${DateTime.now().toFormat("yyyy-MM-dd")}`;
  const targetUrlUv = `https://currentuvindex.com/api/v1/uvi?latitude=${lat}&longitude=${lon}`;

  const url = `${proxy}?url=${encodeURIComponent(targetUrlBrightsky)}`;
  const url_uv = `${proxy}?url=${encodeURIComponent(targetUrlUv)}`;

  // --- TEIL 1: Sonnenaufgang/-untergang BERECHNEN (statt API) ---
  let sunriseFormatted = "Keine Daten";
  let sunsetFormatted = "Keine Daten";

  try {
    // SunCalc berechnet die Zeiten basierend auf Datum & Koordinaten
    const times = SunCalc.getTimes(new Date(), lat, lon);

    // Die Ergebnisse sind JavaScript Date-Objekte. Wir formatieren sie mit Luxon.
    if (times.sunrise && times.sunset) {
      sunriseFormatted = DateTime.fromJSDate(times.sunrise).toFormat("HH:mm");
      sunsetFormatted = DateTime.fromJSDate(times.sunset).toFormat("HH:mm");
    }
  } catch (e) {
    console.warn("Fehler bei der Sonnenstandsberechnung:", e);
  }

  // --- TEIL 2: Wetterdaten laden (Brightsky) ---
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("API-Fehler bei Brightsky: " + res.status);

    const data = await res.json();
    const now = DateTime.now();

    const currentHourData = data.weather.find(
      (entry) => DateTime.fromISO(entry.timestamp).hour === now.hour,
    );

    if (!currentHourData) {
      document.getElementById("location_output").innerText =
        "Keine Wetterdaten gefunden.";
      return;
    }

    const source_id = currentHourData.source_id;

    // --- TEIL 3: UV-Index laden ---
    let uvIndexValue = null;
    try {
      const res_uv = await fetch(url_uv, {
        headers: { Accept: "application/json" },
      });
      if (res_uv.ok) {
        const data_uv = await res_uv.json();
        uvIndexValue = data_uv?.now?.uvi ?? null;
      }
    } catch (e) {
      console.warn("Fehler beim Laden des UV-Index:", e);
    }

    // --- Zusammenstellen der Daten ---
    const fields = {
      Zeitpunkt: formatValue(
        DateTime.fromISO(currentHourData.timestamp, { zone: "utc" })
          .toLocal()
          .toFormat("ccc, dd.LLL, HH:mm 'Uhr'"),
      ),
      Temperatur: formatValue(currentHourData.temperature?.toFixed(1), "°C"),
      Niederschlag: formatValue(currentHourData.precipitation, " mm"),
      Sonnenaufgang: sunriseFormatted,
      Sonnenuntergang: sunsetFormatted,
      Sonnenscheindauer: formatValue(currentHourData.sunshine, " min"),
      "UV-Index": formatValue(uvIndexValue),
      Bewölkung: formatValue(currentHourData.cloud_cover, "%"),
      "Relative Luftfeuchtigkeit": formatValue(
        currentHourData.relative_humidity,
        "%",
      ),
      Sichtweite: formatValue(currentHourData.visibility, " m"),
      Niederschlagswahrscheinlichkeit: formatValue(
        currentHourData.precipitation_probability,
        "%",
      ),
      "Niederschlagswahrscheinlichkeit (6h)": formatValue(
        currentHourData.precipitation_probability_6h,
        "%",
      ),
    };

    const sourceData = data.sources.find((s) => s.id === source_id);
    if (sourceData) {
      fields["Stationsname"] = formatValue(sourceData.station_name);
      fields["Entfernung zur Station"] = formatValue(sourceData.distance, " m");
      fields["Höhe der Station"] = formatValue(sourceData.height, " m");
    }

    return fields;
  } catch (err) {
    console.error("Ein kritischer Fehler ist aufgetreten:", err);
    document.getElementById("location_output").innerText =
      "Fehler beim Laden der Haupt-Wetterdaten.";
  }
}
