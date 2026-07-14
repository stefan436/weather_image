// config.js

export const USE_MOSMIX_S = true;

/* Schwellenwerte für die Summary cards nach denen die Bewölkung klassifiziert wird
unter 30 wolkenlos, zwischen 30 und 60 leicht bewölkt,
zwischen 60 und 80 mittel bewölkt, über 80 stark bewölkt */
export const cloudCoverThresholds = [30, 60, 80];

export const previewHours = 48; // Anzahl Stunden, die anfangs im Plot angezeigt werden

export const periodOrder = [
  "Nacht",
  "Früh",
  "Mittag",
  "Nachmittag",
  "Abend",
  "Spät Abends",
];

export const periods = [
  { name: "Früh", startHour: 6, endHour: 10 },
  { name: "Mittag", startHour: 10, endHour: 14 },
  { name: "Nachmittag", startHour: 14, endHour: 18 },
  { name: "Abend", startHour: 18, endHour: 22 },
  { name: "Spät Abends", startHour: 22, endHour: 2 },
  { name: "Nacht", startHour: 2, endHour: 6 },
];

export const combinedParams = [
  {
    value: "Temperatur (°C)",
    error: "Absolute error temperature 2m above surface",
  },
  {
    value: "Windgeschwindigkeit (km/h)",
    error: "Absolute error wind speed 10m above surface",
  },
  { value: "Windrichtung", error: "Absolute error wind direction" },
];

/**
 * Die preferredOrder bestimmt die Reihenfolge der Elemente, wie sie im 
 * Dropdown-Menü der Benutzeroberfläche erscheinen sollen.
 * Elemente, die hier weiter oben stehen, werden zuerst angezeigt.
 * Elemente, die nicht in dieser Liste stehen, werden im Dropdown 
 * alphabetisch an das Ende angehängt.
 */
export const preferredOrder = [
  "Temperatur (°C)",
  "Niederschlagswahrscheinlichkeit",
  "Gewitterwahrscheinlichkeit (WarnMOS)",
  "Glättewahrscheinlichkeit",
  "Totale Niederschlagsmenge (mm)",
  "Bewölkung",
  "Windgeschwindigkeit (km/h)",
  "Maximale Windböe",
  "Windrichtung",
  "Sichtweite",
  "Nebelwahrscheinlichkeit",
  "Relative Luftfeuchtigkeit (%)",
  "Sonnenstunden-stündlich",
  "Sonnenstunden",
  "UV-Index",
  "Strahlungsintensität (W/m^2)",
  "reduzierter Oberflächendruck",
];

// Definiert explizit, welche Parameter im UI-Dropdown auswählbar sein sollen.
// Ersetzt das alte "excludedElements"-Array für mehr Kontrolle.
export const includedDropdownElements = [
  "Temperatur (°C)",
  "Niederschlagswahrscheinlichkeit",
  "Gewitterwahrscheinlichkeit (WarnMOS)",
  "Totale Niederschlagsmenge (mm)",
  "Bewölkung",
  "Windgeschwindigkeit (km/h)",
  "Windrichtung",
  "Nebelwahrscheinlichkeit",
  "Relative Luftfeuchtigkeit (%)",
  "Sonnenstunden",
  "UV-Index",
  "Strahlungsintensität (W/m^2)"
]; 

/**
 * unitProcessingConfig fasst die Einheitenzuweisung und Umrechnung zusammen.
 * Jeder Schlüssel entspricht dem rohen DWD-Kürzel.
 * Wenn ein Kürzel hier nicht gelistet ist, wird der Wert 1:1 übernommen.
 */
export const unitProcessingConfig = {
  // --- Temperatur (Kelvin zu Celsius) ---
  TTT: { unit: "°C", convert: (v) => v - 273.15 },
  Td: { unit: "°C", convert: (v) => v - 273.15 },
  TX: { unit: "°C", convert: (v) => v - 273.15 },
  TN: { unit: "°C", convert: (v) => v - 273.15 },
  T5cm: { unit: "°C", convert: (v) => v - 273.15 },
  TM: { unit: "°C", convert: (v) => v - 273.15 },
  TG: { unit: "°C", convert: (v) => v - 273.15 },

  // --- Fehlerbereiche Temperatur (bleiben K, da Differenzen in K und °C identisch sind) ---
  E_TTT: { unit: "K", convert: (v) => v },
  E_Td: { unit: "K", convert: (v) => v },

  // --- Windgeschwindigkeit (m/s zu km/h) ---
  FF: { unit: "km/h", convert: (v) => v * 3.6 },
  FX1: { unit: "km/h", convert: (v) => v * 3.6 },
  FX3: { unit: "km/h", convert: (v) => v * 3.6 },
  FXh: { unit: "km/h", convert: (v) => v * 3.6 },
  E_FF: { unit: "km/h", convert: (v) => v * 3.6 }, 

  // --- Windrichtung ---
  DD: { unit: "°", convert: (v) => v },
  E_DD: { unit: "°", convert: (v) => v },

  // --- Luftdruck (Pa zu hPa) ---
  PPPP: { unit: "hPa", convert: (v) => v / 100 },
  QNH: { unit: "hPa", convert: (v) => v / 100 },
  E_PPP: { unit: "hPa", convert: (v) => v / 100 },

  // --- Niederschlag (kg/m² entspricht 1:1 mm) ---
  RR1: { unit: "mm", convert: (v) => v },
  RR3: { unit: "mm", convert: (v) => v },
  RR6: { unit: "mm", convert: (v) => v },
  RR6c: { unit: "mm", convert: (v) => v },
  RR1c: { unit: "mm", convert: (v) => v },
  RR3c: { unit: "mm", convert: (v) => v },
  RRh: { unit: "mm", convert: (v) => v },
  RRhc: { unit: "mm", convert: (v) => v },
  RRd: { unit: "mm", convert: (v) => v },
  RRdc: { unit: "mm", convert: (v) => v },

  // --- Strahlung (Umrechnung in W/m²) ---
  Rad1h: { unit: "W/m²", convert: (v) => v / 3.6 }, // 1std kJ/m² -> W/m²
  RadS3: { unit: "W/m²", convert: (v) => v / 10.8 }, // 3std kJ/m² -> W/m²
  RadL3: { unit: "W/m²", convert: (v) => v / 10.8 }, // 3std kJ/m² -> W/m²

  // --- Sichtweite (m zu km) ---
  VV: { unit: "km", convert: (v) => v / 1000 },

  // --- Wolkenhöhe ---
  H_BsC: { unit: "m", convert: (v) => v },

  // --- Zeiten/Dauern (Sekunden zu Minuten) ---
  SunD1: { unit: "min", convert: (v) => v / 60 },
  SunD3: { unit: "min", convert: (v) => v / 60 },
  SunD: { unit: "min", convert: (v) => v / 60 },
  DRR1: { unit: "min", convert: (v) => v / 60 }
};

export const wwIconMap = {
  // Gewitter
  95: { icon: "thunderstorm.png", label: "Gewitter mit Regen/Schnee" }, // gefrierender Sprühregen/Regen

  57: { icon: "heavy freeting rain.png", label: "Starker gefrierender Sprühregen" },
  56: { icon: "light freezing rain.png", label: "Leichter gefrierender Sprühregen" },
  67: { icon: "heavy freezing rain.png", label: "Starker gefrierender Regen" },
  66: { icon: "light freezing rain.png", label: "Leichter gefrierender Regen" }, // Schnee/Schneeschauer

  86: { icon: "heavy snow.png", label: "Starker Schneeschauer" },
  85: { icon: "light snow.png", label: "Leichter Schneeschauer" },
  84: { icon: "heavy sleet.png", label: "Starker Schneeregenschauer" },
  83: { icon: "light sleet.png", label: "Leichter Schneeregenschauer" },
  75: { icon: "heavy snow.png", label: "Starker Schneefall" },
  73: { icon: "moderate snow.png", label: "Mäßiger Schneefall" },
  71: { icon: "light snow.png", label: "Leichter Schneefall" },
  69: { icon: "heavy sleet.png", label: "Starker Schneeregen" },
  68: { icon: "light sleet.png", label: "Leichter Schneeregen" }, // Regen/Schauer

  82: { icon: "heavy rain.png", label: "Heftiger Regenschauer" },
  81: { icon: "moderate rain.png", label: "Starker Regenschauer" },
  80: { icon: "light rain.png", label: "Leichter Regenschauer" },
  65: { icon: "heavy rain.png", label: "Starker Regen" },
  63: { icon: "moderate rain.png", label: "Mäßiger Regen" },
  61: { icon: "light rain.png", label: "Leichter Regen" }, // Sprühregen

  55: { icon: "heavy rain.png", label: "Starker Sprühregen" },
  53: { icon: "moderate rain.png", label: "Mäßiger Sprühregen" },
  51: { icon: "light rain.png", label: "Leichter Sprühregen" }, // Nebel

  49: { icon: "fog.png", label: "Nebel mit Reif" },
  45: { icon: "fog.png", label: "Nebel" }, // Bewölkung

  3: { icon: "total cloud cover.png", label: "Bewölkung zunehmend" },
  2: { icon: "medium cloud cover.png", label: "Bewölkung unverändert" },
  1: { icon: "low cloud cover.png", label: "Bewölkung abnehmend" },
  0: { icon: "clear day.png", label: "Klarer Himmel" },
};

export const wwIconMapNight = {
  0: { icon: "clear night.png", label: "Klarer Himmel" },
  1: { icon: "low cloud cover night.png", label: "Bewölkung abnehmend" },
  2: { icon: "medium cloud cover night.png", label: "Bewölkung unverändert" },
};