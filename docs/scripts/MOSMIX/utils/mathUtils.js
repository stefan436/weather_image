import { elementNamesMap } from "../config/elementNamesMap.js";

export function toRadians(deg) {
  return (deg * Math.PI) / 180;
}

export function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Erdradius in Metern
  const φ1 = toRadians(lat1),
    φ2 = toRadians(lat2);
  const Δφ = toRadians(lat2 - lat1),
    Δλ = toRadians(lon2 - lon1);
  const a =
    Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Wurde aus dem dataParser extrahiert, um diesen übersichtlich zu halten
export function calculateRelativeHumidity(seriesMap, timeStepsLength) {
  const tdKey = elementNamesMap["Td"] || "Td";
  const finalTemp = seriesMap["Temperatur (°C)"];
  const finalTd = seriesMap[tdKey];
  const finalErrT = seriesMap["Temperatur (°C)_error"];
  const finalErrTd = seriesMap[tdKey + "_error"];

  if (finalTemp && finalTd && finalTemp.length > 0) {
    const rhValues = [];
    const rhErrorValues = [];

    const a = 17.625;
    const b = 243.04;
    const ab = a * b;

    for (let i = 0; i < timeStepsLength; i++) {
      const T = finalTemp[i];
      const Td = finalTd[i];

      const errT = finalErrT && finalErrT[i] ? finalErrT[i] : 0;
      const errTd = finalErrTd && finalErrTd[i] ? finalErrTd[i] : 0;

      if (T !== null && Td !== null) {
        const e = Math.exp((a * Td) / (b + Td));
        const es = Math.exp((a * T) / (b + T));
        let rh = (e / es) * 100;

        let rh_err =
          rh *
          ab *
          Math.sqrt(
            Math.pow(errTd / Math.pow(b + Td, 2), 2) +
              Math.pow(errT / Math.pow(b + T, 2), 2),
          );

        rh = Math.round(rh * 10) / 10;
        rh_err = Math.ceil(rh_err * 10) / 10;

        rhValues.push(rh);
        rhErrorValues.push(rh_err);
      } else {
        rhValues.push(null);
        rhErrorValues.push(null);
      }
    }

    seriesMap["Relative Luftfeuchtigkeit (%)"] = rhValues;
    seriesMap["Relative Luftfeuchtigkeit (%)_error"] = rhErrorValues;
  }
}