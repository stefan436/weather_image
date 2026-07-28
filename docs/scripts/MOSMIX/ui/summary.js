import {
  cloudCoverThresholds,
  periods,
  periodOrder,
  wwIconMap,
  wwIconMapNight,
} from "../config/constants.js";
import { getStationTime } from "../utils/timeUtils.js";

export function buildSummary(seriesMap, timeSteps, timeZoneId) {
  if (!seriesMap || !seriesMap["Significant Weather"]) {
    console.warn("Kein Wettercode (ww) verfügbar – keine Zusammenfassung möglich");
    return;
  }

  const container = document.getElementById("scroll-container");
  const oldSelector = document.getElementById("day-selector");
  const selector = oldSelector.cloneNode(false);
  oldSelector.parentNode.replaceChild(selector, oldSelector);

  container.innerHTML = "";
  selector.innerHTML = "";

  const now = new Date();
  now.setMinutes(0, 0, 0);

  const entries = timeSteps.map((ts, i) => {
    const originalDate = new Date(ts);
    const realDateObj = new Date(originalDate.getTime() - 60 * 60 * 1000);
    const stTime = getStationTime(realDateObj, timeZoneId);
    return {
      timestamp: realDateObj,
      stTime: stTime,
      hour: stTime.hour,
      code: parseInt(seriesMap["Significant Weather"][i]),
      index: i,
    };
  });

  const futureEntries = entries.filter((e) => e.timestamp >= now);

  const daysMap = {};
  const todayIso = getStationTime(now, timeZoneId).dayIso;
  const tomorrowIso = getStationTime(new Date(now.getTime() + 86400000), timeZoneId).dayIso;
  const dayAfterTomorrowIso = getStationTime(new Date(now.getTime() + 2 * 86400000), timeZoneId).dayIso;

  for (const entry of futureEntries) {
    const period = periods.find((p) => {
      if (p.startHour < p.endHour) {
        return entry.hour >= p.startHour && entry.hour < p.endHour;
      } else {
        return entry.hour >= p.startHour || entry.hour < p.endHour;
      }
    });
    if (!period) continue;

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

  const sortedKeys = Object.keys(daysMap).sort();
  if (sortedKeys.length === 0) {
    container.innerHTML = `<div class="no-data">Keine zukünftigen Vorhersagen vorhanden.</div>`;
    return;
  }

  let currentIndex = sortedKeys.findIndex((k) => k === todayIso);
  if (currentIndex === -1) currentIndex = 0;

  let animating = false;

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
      document.getElementById("day-right").disabled = index >= sortedKeys.length - 1;
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
    document.getElementById("day-right").disabled = index >= sortedKeys.length - 1;
  }

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
          const prevIndex = i - 1;
          if (prevIndex >= 0 && seriesMap["Bewölkung"]?.[prevIndex] != null) {
            cloud_covers.push(seriesMap["Bewölkung"][prevIndex]);
          }
        }

        const avg_cloud_cover =
          cloud_covers.length > 0
            ? cloud_covers.reduce((acc, val) => acc + val, 0) / cloud_covers.length
            : null;

        if (avg_cloud_cover === null) {
          dominantCode = null;
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
      const isNightPeriod = ["Abend", "Spät Abends", "Nacht"].includes(periodName);

      if (dominantCode === null || dominantCode === undefined) {
        info = { icon: "unknown.png", label: "unbekannt" };
      } else if (isNightPeriod && dominantCode <= 2) {
        info = wwIconMapNight[dominantCode] || { icon: "unknown.png", label: "unbekannt" };
      } else {
        info = wwIconMap[dominantCode] || { icon: "unknown.png", label: "unbekannt" };
      }

      const temps = entries
        .map((e) => {
          const prevIndex = e.index - 1;
          return prevIndex >= 0 ? seriesMap["Temperatur (°C)"]?.[prevIndex] : null;
        })
        .filter((t) => t !== null && t !== undefined && !isNaN(t));

      const avgTemp = temps.length > 0
          ? Math.round(temps.reduce((a, b) => a + b, 0) / temps.length)
          : "--";
      const tempStr = `🌡️${avgTemp}°C`;

      let precipStr = "";
      if (dominantCode >= 50) {
        const probs = entries
          .map((e) => seriesMap["Niederschlagswahrscheinlichkeit"]?.[e.index])
          .filter((p) => p !== null && p !== undefined && !isNaN(p));
        const maxProb = probs.length > 0 ? Math.max(...probs) : 0;
        precipStr = `☔ ${Math.round(maxProb)}%`;
      }

      let windStr = "";
      const winds = entries
        .map((e) => {
          const prevIndex = e.index - 1;
          return prevIndex >= 0 ? seriesMap["Windgeschwindigkeit (km/h)"]?.[prevIndex] : null;
        })
        .filter((w) => w !== null && w !== undefined && !isNaN(w));

      if (winds.some((w) => w >= 15)) {
        windStr = "💨";
      }

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

  const oldLeftBtn = document.getElementById("day-left");
  const oldRightBtn = document.getElementById("day-right");
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

  updateDaySelector(currentIndex);

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