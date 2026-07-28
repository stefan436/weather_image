import { elementNamesMap } from "../config/elementNamesMap.js";
import { previewHours } from "../config/constants.js";
import { getStationTime } from "../utils/timeUtils.js";

function getConfig() {
  return {
    responsive: true,
    displaylogo: false,
    displayModeBar: true,
    modeBarButtonsToRemove: [
      "toImage",
      "select2d",
      "lasso2d",
      "zoomIn2d",
      "zoomOut2d",
      "autoScale2d",
      "resetScale2d",
    ],
  };
}

function enforcePanAfterZoom(plotlyDiv) {
  if (plotlyDiv.removeAllListeners) {
    plotlyDiv.removeAllListeners("plotly_relayout");
  }

  plotlyDiv.on("plotly_relayout", function (eventData) {
    if (!eventData) return;

    const keys = Object.keys(eventData);
    const isZoom = keys.some(
      (k) =>
        k.includes("xaxis.range") ||
        k.includes("yaxis.range") ||
        k.includes("autorange"),
    );

    if (isZoom && plotlyDiv.layout && plotlyDiv.layout.dragmode !== "pan") {
      setTimeout(() => {
        Plotly.relayout(plotlyDiv, { dragmode: "pan" });
      }, 100);
    }
  });
}

function getLayout(param, timeSteps, timeZoneId) {
  const xData = timeSteps.map((ts) => getStationTime(ts, timeZoneId).plotlyString);
  let xRange = null;

  if (timeSteps.length > 0) {
    const startObj = new Date(timeSteps[0]);
    const endObj = new Date(startObj.getTime() + previewHours * 3600 * 1000);
    xRange = [
      getStationTime(startObj, timeZoneId).plotlyString,
      getStationTime(endObj, timeZoneId).plotlyString,
    ];
  }
  
  const layout = {
    margin: { l: 50, r: 20, t: 30, b: 70 },
    xaxis: {
      automargin: true,
      range: xRange,
      gridcolor: "rgba(17, 24, 39, 0.2)",
      hoverformat: "%a, %d.%b, %H:%M",
      tickformat: "%H:%M \n%d.%b",
    },
    yaxis: { 
      title: param, 
      gridcolor: "rgba(17, 24, 39, 0.2)",
      automargin: true,
      fixedrange: true 
    },
    hovermode: "x",
    autosize: true,
    showlegend: false,
    dragmode: "pan",
  };

  if (
    param.includes("Niederschlagswahrscheinlichkeit") ||
    param.includes("Bewölkung") ||
    param.includes("Nebelwahrscheinlichkeit") ||
    param.includes("Relative Luftfeuchtigkeit") ||
    param.includes("Gewitterwahrscheinlichkeit")
  ) {
    layout.yaxis.range = [-5, 105];
    layout.yaxis.minor = {
      dtick: 10,
      showgrid: true,
      gridwidth: 1,
      gridcolor: "rgba(200, 200, 200, 0.5)",
      griddash: "dash"           
    };
  } else if (param.includes("Sonnenstunden")) {
    layout.yaxis.range = [-2, 24];
  } else if (param.includes("UV-Index")) {
    layout.yaxis.range = [-1, 13];
  } else if (param.includes("Strahlungsintensität")) {
    layout.yaxis.range = [-100, 1400];
  } 
  return layout;
}

// --- Hilfsfunktionen für spezifische Plots ---

function renderUvIndexPlot(plotlyDiv, param, seriesMap, timeSteps, result_uv_and_pt, timeZoneId) {
  if (!result_uv_and_pt || !result_uv_and_pt["uvi_times"]) {
    plotlyDiv.innerHTML = "<em>Keine UV-Daten für diesen Standort verfügbar</em>";
    return;
  }

  const day_strings = result_uv_and_pt["uvi_times"];
  const hours = result_uv_and_pt["UVH"];
  const timeStep_uv = day_strings.map((date, i) => {
    const newDate = new Date(date);
    newDate.setUTCHours(hours[i], 0, 0, 0);
    return getStationTime(newDate, timeZoneId).plotlyString;
  });

  const yData = seriesMap[param].map((v) => (v == null ? null : v));
  const traces = [
    {
      x: timeStep_uv, y: yData,
      type: "scatter", mode: "lines",
      line: { width: 2, shape: "spline", color: "rgb(102, 102, 102)" },
      connectgaps: true, hoverinfo: "skip", showlegend: false,
    },
    {
      x: timeStep_uv, y: yData,
      type: "scatter", mode: "markers",
      marker: { size: 6, color: "rgb(68, 68, 68)" },
      name: param,
    }
  ];

  const layout = {
    ...getLayout(param, timeSteps, timeZoneId),
    shapes: [
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 0, y1: 3, fillcolor: "rgba(0, 255, 0, 0.2)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 3, y1: 6, fillcolor: "rgba(255, 255, 0, 0.2)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 6, y1: 8, fillcolor: "rgba(255, 165, 0, 0.2)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 8, y1: 11, fillcolor: "rgba(255, 0, 0, 0.2)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 11, y1: 13, fillcolor: "rgba(128, 0, 128, 0.2)", line: { width: 0 } },
    ],
  };

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}

function renderPrecipitationProbPlot(plotlyDiv, param, xData, yData, seriesMap, timeSteps, timeZoneId, shapes) {
  const traces = [{
    x: xData, y: yData,
    type: "scatter", mode: "lines+markers", connectgaps: true,
    line: { width: 3, shape: "spline", color: "rgba(17, 24, 39, 1)" },
    marker: { size: 6, color: "rgba(17, 24, 39, 1)" },
    name: "Gesamt",
  }];

  const extraProbs = [
    { key: elementNamesMap["wwZ"] || "wwZ", name: "Nieselregen", color: "rgb(156, 163, 175)" },
    { key: elementNamesMap["wwD"] || "wwD", name: "Frontregen", color: "rgb(37, 99, 235)" },
    { key: elementNamesMap["wwC"] || "wwC", name: "Konvektion", color: "rgb(147, 51, 234)" },
    { key: elementNamesMap["wwT"] || "wwT", name: "Gewitter", color: "rgb(234, 179, 8)" },
  ];

  extraProbs.forEach((ep) => {
    if (seriesMap[ep.key]) {
      traces.push({
        x: xData, y: seriesMap[ep.key].map((v) => (v == null ? null : v)),
        type: "scatter", mode: "lines", connectgaps: true,
        line: { width: 2, shape: "spline", color: ep.color, dash: "dot" }, 
        name: ep.name,
      });
    }
  });

  const baseLayout = getLayout(param, timeSteps, timeZoneId);
  const layout = {
    ...baseLayout,
    shapes: shapes,
    yaxis: { ...baseLayout.yaxis, title: "Wahrscheinlichkeit (%)" },
  };

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}

function renderThunderstormProbPlot(plotlyDiv, param, xData, yData, seriesMap, timeSteps, timeZoneId, shapes) {
  const traces = [{
    x: xData, y: yData,
    type: "scatter", mode: "lines+markers", connectgaps: true,
    line: { width: 3, shape: "spline", color: "rgb(234, 179, 8)" },
    marker: { size: 6, color: "rgb(234, 179, 8)" },
    name: "Gewitter",
  }];

  const extraProbs = [
    { key: elementNamesMap["W_GEWSK_01"] || "W_GEWSK_01", name: "Starkes Gewitter", color: "rgb(249, 115, 22)" },
    { key: elementNamesMap["U_GEWSW_01"] || "U_GEWSW_01", name: "Schweres Gewitter", color: "rgb(239, 68, 68)" }, 
  ];

  extraProbs.forEach((ep) => {
    if (seriesMap[ep.key]) {
      traces.push({
        x: xData, y: seriesMap[ep.key].map((v) => (v == null ? null : v)),
        type: "scatter", mode: "lines", connectgaps: true,
        line: { width: 2, shape: "spline", color: ep.color, dash: "dot" }, 
        name: ep.name,
      });
    }
  });

  const baseLayout = getLayout(param, timeSteps, timeZoneId);
  const layout = {
    ...baseLayout, shapes: shapes,
    yaxis: { ...baseLayout.yaxis, title: "Wahrscheinlichkeit (%)" },
  };

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}

function renderConvectivePotentialPlot(plotlyDiv, param, xData, seriesMap, timeSteps, timeZoneId, shapes) {
  const extraParams = [
    { key: "Modified Convective Potential", name: "MCP", color: "rgb(17, 24, 39)", yaxis: "y", mode: "lines+markers", dash: "solid" },
    { key: "Bulk Richardson Number", name: "BRN", color: "rgb(156, 107, 72)", yaxis: "y", mode: "lines", dash: "dash" },
    { key: "Convective Available Potential Energy", name: "CAPE", color: "rgb(248, 113, 113)", yaxis: "y2", mode: "lines", dash: "dash" },
    { key: "Convective Inhibition", name: "CIN", color: "rgb(147, 197, 253)", yaxis: "y2", mode: "lines", dash: "dash" }
  ];

  let y1Vals = [], y2Vals = [];
  let minDataIndex = xData.length - 1, maxDataIndex = 0;
  const traces = [];

  extraParams.forEach((ep) => {
    if (seriesMap[ep.key]) {
      const epData = seriesMap[ep.key].map((v) => (v == null ? null : v));
      
      epData.forEach((val, idx) => {
        if (val !== null) {
          if (ep.yaxis === "y") y1Vals.push(val);
          if (ep.yaxis === "y2") y2Vals.push(val);
          if (idx < minDataIndex) minDataIndex = idx;
          if (idx > maxDataIndex) maxDataIndex = idx;
        }
      });
      
      traces.push({
        x: xData, y: epData,
        type: "scatter", mode: ep.mode, connectgaps: true,
        line: { width: 2, shape: "spline", color: ep.color, dash: ep.dash }, 
        name: ep.name, yaxis: ep.yaxis
      });
    }
  });

  const minY1 = y1Vals.length ? Math.min(...y1Vals, 0) : 0;
  const maxY1 = y1Vals.length ? Math.max(...y1Vals, 0.001) : 1;
  const minY2 = y2Vals.length ? Math.min(...y2Vals, 0) : 0;
  const maxY2 = y2Vals.length ? Math.max(...y2Vals, 0.001) : 1;

  const maxRatio = Math.max(Math.abs(minY1) / maxY1, Math.abs(minY2) / maxY2);
  const tickPadding = 1.05; 
  
  const rangeY1 = [ -(maxY1 * maxRatio) * tickPadding, maxY1 * tickPadding ];
  const rangeY2 = [ -(maxY2 * maxRatio) * tickPadding, maxY2 * tickPadding ];

  let rangeX = null;
  
  if (minDataIndex <= maxDataIndex) {
    // 1. Die exakten Start- und Endzeitpunkte in Millisekunden holen
    // Wir nutzen timeSteps anstatt xData, da timeSteps ein standardisiertes Datumsformat hat, 
    // das von 'new Date()' auf jedem Browser (inkl. Safari) 100% fehlerfrei gelesen wird.
    const startMs = new Date(timeSteps[minDataIndex]).getTime();
    const endMs = new Date(timeSteps[maxDataIndex]).getTime();

    // 2. Zeitspanne und das 5% Padding berechnen (mindestens 2 Stunden als Fallback)
    const diffMs = endMs - startMs;
    const paddingMs = Math.max(diffMs * 0.05, 2 * 60 * 60 * 1000);

    // 3. Das errechnete Padding vorne abziehen und hinten aufaddieren
    const paddedStart = new Date(startMs - paddingMs);
    const paddedEnd = new Date(endMs + paddingMs);

    // 4. Die neuen Zeiten wieder in das richtige Plotly-Format der lokalen Zeitzone formatieren
    rangeX = [
      getStationTime(paddedStart, timeZoneId).plotlyString,
      getStationTime(paddedEnd, timeZoneId).plotlyString
    ];
  }

  const baseLayout = getLayout(param, timeSteps, timeZoneId);
  const layout = {
    ...baseLayout, shapes: shapes, showlegend: false,
    margin: { ...baseLayout.margin, r: 60 }, 
    xaxis: { ...baseLayout.xaxis, autorange: false, range: rangeX },
    yaxis: {
      ...baseLayout.yaxis, title: "MCP / BRN", autorange: false, range: rangeY1,   
      zeroline: true, zerolinecolor: "rgba(17, 24, 39, 0.3)", zerolinewidth: 1
    },
    yaxis2: {
      title: "CAPE / CIN", overlaying: "y", side: "right", fixedrange: true, 
      autorange: false, range: rangeY2, showgrid: false, zeroline: true,
      zerolinecolor: "rgba(17, 24, 39, 0.3)", zerolinewidth: 1
    }
  };

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}

function renderSunHoursPlot(plotlyDiv, param, seriesMap, timeSteps, timeZoneId, shapes) {
  const xDataSun = timeSteps.map((ts) => {
    const date = new Date(ts);
    date.setDate(date.getDate() - 1); 
    const prevDay = getStationTime(date, timeZoneId);
    return `${prevDay.dayIso} 12:00:00`;
  });
  const yDataSun = seriesMap[param].map((v) => (v == null ? null : v / 60));

  const traces = [
    {
      x: xDataSun, y: yDataSun,
      type: "scatter", mode: "lines",
      line: { width: 2, shape: "spline", color: "rgba(17, 24, 39, 1)" },
      connectgaps: true, name: param, hoverinfo: "skip", showlegend: false,
    },
    {
      x: xDataSun, y: yDataSun,
      type: "scatter", mode: "markers",
      marker: { size: 6, color: "rgba(17, 24, 39, 1)" },
      name: param,
    }
  ];

  const layout = { ...getLayout(param, timeSteps, timeZoneId), shapes: shapes };
  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}

// HAUPTFUNKTION: Rendert den Plot
export function renderPlot(param, seriesMap, timeSteps, result_uv_and_pt, timeZoneId) {
  const plotlyDiv = document.getElementById("plotlyDiv");

  if (!seriesMap || !seriesMap[param]) {
    plotlyDiv.innerHTML = "<em>Keine Daten für diesen Parameter</em>";
    return;
  }

  if (param.includes("UV-Index")) {
    return renderUvIndexPlot(plotlyDiv, param, seriesMap, timeSteps, result_uv_and_pt, timeZoneId);
  }

  const traces = [];
  const xData = timeSteps.map((ts) => getStationTime(ts, timeZoneId).plotlyString);
  const yData = seriesMap[param].map((v) => (v == null ? null : v));
  const hasError = !!seriesMap[param + "_error"];
  let shapes = [];

  // Nachtbereiche 
  if (!param.includes("UV-Index")) {
    const nightColor = "rgba(241, 241, 241, 0.75)";
    const datesSet = new Set();
    timeSteps.forEach((ts) => {
      const bTime = getStationTime(ts, timeZoneId);
      if (datesSet.has(bTime.dayIso)) return;
      datesSet.add(bTime.dayIso);
      shapes.push({ type: "rect", xref: "x", yref: "paper", x0: `${bTime.dayIso} 00:00:00`, x1: `${bTime.dayIso} 08:00:00`, y0: 0, y1: 1, fillcolor: nightColor, line: { width: 0 }, layer: "below" });
      shapes.push({ type: "rect", xref: "x", yref: "paper", x0: `${bTime.dayIso} 20:00:00`, x1: `${bTime.dayIso} 23:59:59`, y0: 0, y1: 1, fillcolor: nightColor, line: { width: 0 }, layer: "below" });
    });
  }

  // Abzweigungen für spezielle Plots die Shapes nutzen
  if (param === (elementNamesMap["wwP"] || "Niederschlagswahrscheinlichkeit")) {
    return renderPrecipitationProbPlot(plotlyDiv, param, xData, yData, seriesMap, timeSteps, timeZoneId, shapes);
  }

  if (param === (elementNamesMap["W_GEW_01"] || "Gewitterwahrscheinlichkeit")) {
    return renderThunderstormProbPlot(plotlyDiv, param, xData, yData, seriesMap, timeSteps, timeZoneId, shapes);
  }

  if (param === "Konvektionspotential") {
    return renderConvectivePotentialPlot(plotlyDiv, param, xData, seriesMap, timeSteps, timeZoneId, shapes);
  }

  if (param.includes("Sonnenstunden")) {
    return renderSunHoursPlot(plotlyDiv, param, seriesMap, timeSteps, timeZoneId, shapes);
  }

  // --- Spezielle Add-on Traces (Felt Temp, Gusts, Errors) ---
  if (param.includes("Temperatur (°C)") && result_uv_and_pt && result_uv_and_pt["gft_times"] && seriesMap["Gefühlte Temperatur"]) {
    const gft_time_step = result_uv_and_pt["gft_times"].map((ts) => getStationTime(ts, timeZoneId).plotlyString);
    const gft_data = seriesMap["Gefühlte Temperatur"];
    traces.push({ x: gft_time_step, y: gft_data, type: "scatter", mode: "lines", line: { width: 2, shape: "spline", color: "rgb(200, 0, 0)" }, connectgaps: true, hoverinfo: "skip", showlegend: false });
    traces.push({ x: gft_time_step, y: gft_data, type: "scatter", mode: "markers", connectgaps: true, marker: { size: 6, color: "rgb(120, 0, 0)" }, name: "Gefühlte Temperatur (°C)" });
  }

  if (param.includes("Windgeschwindigkeit (km/h)") && seriesMap["Maximale Windböe"]) {
    const gust_data = seriesMap["Maximale Windböe"];
    const gust_time_step = timeSteps.map((ts) => getStationTime(ts, timeZoneId).plotlyString);
    traces.push({ x: gust_time_step, y: gust_data, type: "scatter", mode: "lines", line: { width: 2, shape: "spline", color: "rgb(0, 150, 200)" }, connectgaps: true, hoverinfo: "skip", showlegend: false });
    traces.push({ x: gust_time_step, y: gust_data, type: "scatter", mode: "markers", connectgaps: true, marker: { size: 6, color: "rgb(0, 100, 150)" }, name: "Maximale Windböe" });
  }

  if (hasError) {
    const errorData = seriesMap[param + "_error"];
    const yUpper = yData.map((v, i) => v != null && errorData[i] != null ? v + errorData[i] : null);
    const yLower = yData.map((v, i) => v != null && errorData[i] != null ? v - errorData[i] : null);
    traces.push({
      x: [...xData, ...xData.slice().reverse()], y: [...yUpper, ...yLower.slice().reverse()],
      type: "scatter", mode: "lines", fill: "toself", fillcolor: "rgba(79, 79, 79, 0.5)",
      line: { color: "transparent" }, hoverinfo: "skip", showlegend: false, connectgaps: true, name: `${param} Fehlerbereich`,
    });
  }

  if (param.includes("Totale Niederschlagsmenge (mm)")) {
    shapes.push(
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 0, y1: 0.5, fillcolor: "rgba(173, 216, 230, 0.25)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 0.5, y1: 1.5, fillcolor: "rgba(65, 105, 225, 0.2)", line: { width: 0 } },
      { type: "rect", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 1.5, y1: 5, fillcolor: "rgba(25, 25, 112, 0.3)", line: { width: 0 } },
    );
  }

  // --- Standard Linien-Plot ---
  traces.push({ x: xData, y: yData, type: "scatter", mode: "lines", line: { width: 2, shape: "spline", color: "rgba(17, 24, 39, 1)" }, connectgaps: true, name: param, hoverinfo: "skip", showlegend: false });
  traces.push({ x: xData, y: yData, type: "scatter", mode: "markers", marker: { size: 6, color: "rgba(17, 24, 39, 1)" }, name: param });

  const layout = { ...getLayout(param, timeSteps, timeZoneId), shapes: shapes };

  if (param.includes("Windrichtung")) {
    layout.yaxis = { title: "Windrichtung", tickmode: "array", gridcolor: "rgba(17, 24, 39, 0.2)", tickvals: [0, 90, 180, 270, 360], ticktext: ["N", "E", "S", "W", "N"], range: [0, 360] };
  }

  if (param.includes("Totale Niederschlagsmenge (mm)")) {
    const viewStart = new Date(timeSteps[0]).getTime();
    const viewEnd = viewStart + previewHours * 3600 * 1000;
    const dataVals = seriesMap[param].filter((v, index) => {
      const currentTime = new Date(timeSteps[index]).getTime();
      return v !== null && !isNaN(v) && currentTime >= viewStart && currentTime <= viewEnd;
    });

    if (dataVals.length > 0) {
      const minData = Math.min(...dataVals);
      const maxData = Math.max(...dataVals);
      const diff = maxData - minData;
      if (diff === 0) {
        layout.yaxis.range = [-0.1, 2.0];
      } else {
        const padding = diff * 0.1;
        layout.yaxis.range = [minData - padding, maxData + padding];
      }
    }
  }

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() => enforcePanAfterZoom(plotlyDiv));
}