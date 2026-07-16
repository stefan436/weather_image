// ui.js
import {
  cloudCoverThresholds,
  periods,
  periodOrder,
  wwIconMap,
  wwIconMapNight,
} from "./config.js";

import { getStationTime } from "./geoService.js";

export function setStatus(txt) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = txt;
  statusEl.style.display = txt ? "inline-block" : "none";
}

export function renderStationChoices(stations, onStationSelect) {
  const stationEl = document.getElementById("station-choices-container");
  stationEl.innerHTML = `
    <div class="station-info">
      <b>Nächstgelegene Stationen:</b>
      <div class="station-choices"></div>
    </div>
  `;

  const container = stationEl.querySelector(".station-choices");

  stations.forEach((st) => {
    const btn = document.createElement("button");
    btn.textContent = `${st.description} (${Math.round(st.distance)} m)`;
    btn.className = "btn station-btn";
    btn.onclick = () => {
      // Wir rufen den übergebenen Callback aus der main.js auf
      onStationSelect(st.station_id, st.distance);
    };
    container.appendChild(btn);
  });
}

/**
 * buildSummary: erstellt die Tag-Auswahl und rendert beim Klick die Summary-Karten
 * Benötigt global: timeSteps (Array), seriesMap["Significant Weather"] (Array gleicher Länge), wwIconMap (Objekt)
 */

export function buildSummary(seriesMap, timeSteps, timeZoneId) {
  if (!seriesMap || !seriesMap["Significant Weather"]) {
    console.warn(
      "Kein Wettercode (ww) verfügbar – keine Zusammenfassung möglich",
    );
    return;
  }

  const container = document.getElementById("scroll-container");
  // Um mehrfache Swipe-Listener bei wiederholtem Aufruf zu vermeiden, klonen wir den Selektor
  const oldSelector = document.getElementById("day-selector");
  const selector = oldSelector.cloneNode(false);
  oldSelector.parentNode.replaceChild(selector, oldSelector);

  container.innerHTML = "";
  selector.innerHTML = "";

  const now = new Date();
  now.setMinutes(0, 0, 0); // Minuten, Sekunden, Millisekunden auf 0 setzen

  // ********* Schritt 1: Roh-Einträge vorbereiten *********
  const entries = timeSteps.map((ts, i) => {
    const originalDate = new Date(ts);
    // SHIFT: 1 Stunde (60 Minuten * 60 Sekunden * 1000 Millisekunden) abziehen.
    // Ein Zeitstempel von 14:00 Uhr wird so zu 13:00 Uhr und repräsentiert
    // damit exakt die korrekte Stunde, in der das Wetter stattfand.
    // Der ww code um 14:00 Uhr beschreibt die Wetterbedingungen von 13:00-13:59 Uhr, daher dieser Shift.
    const realDateObj = new Date(originalDate.getTime() - 60 * 60 * 1000);

    // Wandle das bereinigte Datum in die korrekte Zeitzone um
    const stTime = getStationTime(realDateObj, timeZoneId);

    const code = parseInt(seriesMap["Significant Weather"][i]);
    return {
      timestamp: realDateObj,
      stTime: stTime,
      hour: stTime.hour, // Stunde in der Ziel-Zeitzone
      code: parseInt(seriesMap["Significant Weather"][i]),
      index: i,
    };
  });

  // ********* Schritt 2: nur zukünftige Einträge (ab jetzt) *********
  const futureEntries = entries.filter((e) => e.timestamp >= now);

  // ********* Schritt 3: nach Tag (ISO YYYY-MM-DD) und Periode gruppieren *********
  const daysMap = {};
  // Für die Referenztage (Heute, Morgen) nutzen wir nun auch die Stations-Zeitzone
  const todayIso = getStationTime(now, timeZoneId).dayIso;
  const tomorrowIso = getStationTime(
    new Date(now.getTime() + 86400000),
    timeZoneId,
  ).dayIso;
  const dayAfterTomorrowIso = getStationTime(
    new Date(now.getTime() + 2 * 86400000),
    timeZoneId,
  ).dayIso;

  for (const entry of futureEntries) {
    const period = periods.find((p) => {
      // Normalfall: Zeitraum innerhalb eines Tages
      if (p.startHour < p.endHour) {
        return entry.hour >= p.startHour && entry.hour < p.endHour;
        // Sonderfall: Zeitraum über Mitternacht (z.B. Spät Abend 22-02 Uhr)
      } else {
        return entry.hour >= p.startHour || entry.hour < p.endHour;
      }
    });
    if (!period) continue;

    const entryDate = new Date(entry.timestamp);
    let groupDate = new Date(entry.timestamp);
    if (period.startHour > period.endHour && entry.hour < period.endHour) {
      groupDate = new Date(groupDate.getTime() - 86400000);
    }

    const bGroup = getStationTime(groupDate, timeZoneId);
    const dayIso = bGroup.dayIso;

    let displayDate;
    if (dayIso === todayIso) {
      displayDate = "Heute";
    } else if (dayIso === tomorrowIso) {
      displayDate = "Morgen";
    } else if (dayIso === dayAfterTomorrowIso) {
      displayDate = "Übermorgen";
    } else {
      // Anzeige zwingend in Stations-Zeitzone formatieren
      displayDate = bGroup.d.toLocaleDateString("de-DE", {
        timeZone: timeZoneId,
        weekday: "short",
        day: "2-digit",
        month: "short",
      });
    }

    if (!daysMap[dayIso]) daysMap[dayIso] = { displayDate, groups: {} };
    if (!daysMap[dayIso].groups[period.name])
      daysMap[dayIso].groups[period.name] = [];
    daysMap[dayIso].groups[period.name].push(entry);
  }

  const dayKeys = Object.keys(daysMap).sort();
  if (dayKeys.length === 0) {
    container.innerHTML = `<div class="no-data">Keine zukünftigen Vorhersagen vorhanden.</div>`;
    return;
  }

  // ********* Schritt 4: Aktuellen Tag finden *********
  const sortedKeys = Object.keys(daysMap).sort();
  let currentIndex = sortedKeys.findIndex((k) => k === todayIso);
  if (currentIndex === -1) currentIndex = 0;

  let animating = false;

  // ********* Schritt 5: Rendering eines einzelnen Tages *********
  function updateDaySelector(index, direction = null) {
    if (animating) return;

    const iso = sortedKeys[index];
    const displayText = daysMap[iso].displayDate;

    const newWrapper = document.createElement("div");
    newWrapper.className = "day-slide-wrapper";
    newWrapper.innerHTML = `<strong>${displayText}</strong>`;

    if (direction === "left") {
      newWrapper.style.transform = "translateX(100%)";
    } else if (direction === "right") {
      newWrapper.style.transform = "translateX(-100%)";
    } else {
      newWrapper.style.transform = "translateX(0)";
    }

    const oldWrapper = selector.querySelector(".day-slide-wrapper");

    if (!oldWrapper) {
      selector.innerHTML = "";
      selector.appendChild(newWrapper);
      newWrapper.getBoundingClientRect();
      requestAnimationFrame(() => {
        newWrapper.style.transform = "translateX(0)";
      });
      renderDay(iso, direction);
      document.getElementById("day-left").disabled = index <= 0;
      document.getElementById("day-right").disabled =
        index >= sortedKeys.length - 1;
      return;
    }

    animating = true;
    selector.appendChild(newWrapper);

    oldWrapper.style.transition = "transform 0.3s ease";
    newWrapper.style.transition = "transform 0.3s ease";

    oldWrapper.style.transform = "translateX(0)";
    oldWrapper.getBoundingClientRect();
    newWrapper.getBoundingClientRect();

    const exitDir = direction === "left" ? "-100%" : "100%";
    oldWrapper.style.transform = `translateX(${exitDir})`;
    requestAnimationFrame(() => {
      newWrapper.style.transform = "translateX(0)";
    });

    const onNewEnd = () => {
      if (oldWrapper.parentNode === selector) selector.removeChild(oldWrapper);
      newWrapper.removeEventListener("transitionend", onNewEnd);
      animating = false;
    };
    newWrapper.addEventListener("transitionend", onNewEnd);

    renderDay(iso, direction);
    document.getElementById("day-left").disabled = index <= 0;
    document.getElementById("day-right").disabled =
      index >= sortedKeys.length - 1;
  }

  // ********* Schritt 6: Einzeltag-Rendering *********
  function renderDay(iso) {
    container.innerHTML = "";
    const day = daysMap[iso];

    if (!day) {
      container.innerHTML = `<div class="no-data">Keine Daten für den gewählten Tag.</div>`;
      return;
    }

    periodOrder.forEach((periodName) => {
      const entries = day.groups[periodName];
      if (!entries || entries.length === 0) return;

      const freq = {};
      for (const e of entries) {
        if (!isNaN(e.code)) freq[e.code] = (freq[e.code] || 0) + 1;
      }

      let dominantCode = Math.max(...entries.map((e) => Number(e.code)));

      if ([0, 1, 2, 3].includes(Number(dominantCode))) {
        const indices = [];
        for (const e of entries) {
          if (!isNaN(e.index)) indices.push(e.index);
        }

        const cloud_covers = [];
        for (const i of indices) {
          // SHIFT-AUSGLEICH: Wir ziehen 1 vom Index ab, um den
          // Bewölkungswert am ANFANG der jeweiligen Stunde zu bekommen.
          // Dadurch ist z.B. für Mittags der Durchschnitt durch den Bewölkungsgrad
          // um 10 Uhr, 11 Uhr, 12 Uhr und 13 Uhr (anstatt 11-14 Uhr) berechnet.
          const prevIndex = i - 1;

          // SICHERHEITSCHECK: Verhindert einen Fehler beim allerersten Eintrag
          // des Arrays (falls prevIndex -1 sein sollte).
          if (prevIndex >= 0 && seriesMap["Bewölkung"]?.[prevIndex] != null) {
            cloud_covers.push(seriesMap["Bewölkung"][prevIndex]);
          }
        }

        if (cloud_covers.length === 0) {
          console.warn(
            "Warnung: cloud_cover ist leer, Durchschnitt wird auf 0 gesetzt.",
          );
        }

        const avg_cloud_cover =
          cloud_covers.length > 0
            ? cloud_covers.reduce((acc, val) => acc + val, 0) /
              cloud_covers.length
            : null;

        if (avg_cloud_cover === null) {
          dominantCode = null; // oder ein eigener Code wie -1
        } else if (avg_cloud_cover <= cloudCoverThresholds[0]) {
          dominantCode = 0;
        } else if (avg_cloud_cover <= cloudCoverThresholds[1]) {
          dominantCode = 1;
        } else if (avg_cloud_cover <= cloudCoverThresholds[2]) {
          dominantCode = 2;
        } else {
          dominantCode = 3;
        }
      }

      let info;
      const isNightPeriod = ["Abend", "Spät Abends", "Nacht"].includes(
        periodName,
      );

      if (dominantCode === null || dominantCode === undefined) {
        info = {
          icon: "unknown.png",
          label: "unbekannt",
        };
      } else if (isNightPeriod && dominantCode <= 2) {
        info = wwIconMapNight[dominantCode] || {
          icon: "unknown.png",
          label: "unbekannt",
        };
      } else {
        info = wwIconMap[dominantCode] || {
          icon: "unknown.png",
          label: "unbekannt",
        };
      }

      // --- 1. Temperatur (Durchschnitt der Periode) ---
      // Punktueller Parameter: Wir nutzen e.index - 1, um die Werte am Anfang der Stunde
      // (z.B. 10, 11, 12, 13 Uhr für die Mittag-Periode) zu greifen.
      const temps = entries
        .map((e) => {
          const prevIndex = e.index - 1;
          return prevIndex >= 0
            ? seriesMap["Temperatur (°C)"]?.[prevIndex]
            : null;
        })
        .filter((t) => t !== null && t !== undefined && !isNaN(t));

      const avgTemp =
        temps.length > 0
          ? Math.round(temps.reduce((a, b) => a + b, 0) / temps.length)
          : "--";
      const tempStr = `🌡️${avgTemp}°C`;

      // --- 2. Niederschlagswahrscheinlichkeit ---
      // Zeitraumbezogener Parameter: e.index passt hier exakt, da es die Endzeitpunkte
      // der aufsummierten Stunden (z.B. 11, 12, 13, 14 Uhr) abbildet.
      let precipStr = "";
      if (dominantCode >= 50) {
        // Maximale Wahrscheinlichkeit in der Periode
        const probs = entries
          .map((e) => seriesMap["Niederschlagswahrscheinlichkeit"]?.[e.index])
          .filter((p) => p !== null && p !== undefined && !isNaN(p));
        const maxProb = probs.length > 0 ? Math.max(...probs) : 0;

        precipStr = `🌧️ ${Math.round(maxProb)}%`;
      }

      // --- 3. Windgeschwindigkeit (mindestens einmal >= 15 km/h) ---
      // Punktueller Parameter: e.index - 1 nutzen
      let windStr = "";
      const winds = entries
        .map((e) => {
          const prevIndex = e.index - 1;
          return prevIndex >= 0
            ? seriesMap["Windgeschwindigkeit (km/h)"]?.[prevIndex]
            : null;
        })
        .filter((w) => w !== null && w !== undefined && !isNaN(w));

      if (winds.some((w) => w >= 15)) {
        windStr = "💨";
      }

      // --- HTML der Karte zusammenbauen ---
      const card = document.createElement("div");
      card.className = "summary-card";

      card.innerHTML = `
            <div class="summary-text">
              <strong>${periodName}</strong>
              <img src="icons/${info.icon}" alt="${info.label}">
              <div class="summary-params">
                <span>${tempStr}</span>
                ${precipStr ? `<span>${precipStr}</span>` : ""}
                ${windStr ? `<span>${windStr}</span>` : ""}
              </div>
              <span class="label">${info.label}</span>
            </div>
        `;
      container.appendChild(card);
    });

    if (container.children.length === 0) {
      container.innerHTML = `<div class="no-data">Für diesen Tag liegen keine Vorhersagedaten vor.</div>`;
    }
  }

  // ********* Schritt 7: Event-Listener für Pfeile *********
  const oldLeftBtn = document.getElementById("day-left");
  const oldRightBtn = document.getElementById("day-right");

  // Knöpfe klonen, um alte Event-Listener von vorherigen Suchanfragen zu entfernen
  const leftBtn = oldLeftBtn.cloneNode(true);
  const rightBtn = oldRightBtn.cloneNode(true);
  oldLeftBtn.parentNode.replaceChild(leftBtn, oldLeftBtn);
  oldRightBtn.parentNode.replaceChild(rightBtn, oldRightBtn);

  leftBtn.addEventListener("click", () => {
    if (animating || currentIndex <= 0) return;
    currentIndex--;
    updateDaySelector(currentIndex, "right");
  });

  rightBtn.addEventListener("click", () => {
    if (animating || currentIndex >= sortedKeys.length - 1) return;
    currentIndex++;
    updateDaySelector(currentIndex, "left");
  });

  // ********* Initialisierung *********
  updateDaySelector(currentIndex);

  // ********* Schritt 8: Swipe-Gesten *********
  let touchStartX = null;
  let touchEndX = null;
  const swipeThreshold = 50;

  selector.addEventListener(
    "touchstart",
    function (e) {
      touchStartX = e.changedTouches[0].screenX;
    },
    { passive: true },
  );

  selector.addEventListener(
    "touchend",
    function (e) {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipeGesture();
    },
    { passive: true },
  );

  function handleSwipeGesture() {
    if (animating) return;
    if (touchStartX === null || touchEndX === null) return;
    const diffX = touchEndX - touchStartX;

    if (Math.abs(diffX) > swipeThreshold) {
      if (diffX < 0 && currentIndex < sortedKeys.length - 1) {
        currentIndex++;
        updateDaySelector(currentIndex, "left");
      } else if (diffX > 0 && currentIndex > 0) {
        currentIndex--;
        updateDaySelector(currentIndex, "right");
      }
    }
    touchStartX = null;
    touchEndX = null;
  }
}
