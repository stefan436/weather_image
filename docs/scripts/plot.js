// plot.js
// getLayout und getConfig werden NICHT exportiert, da sie nur intern in dieser Datei genutzt werden.

function getConfig() {
  return {
    responsive: true,
    displaylogo: false,
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

// getLayout braucht jetzt timeSteps als Parameter!
function getLayout(param, timeSteps) {
  const xData = timeSteps.map((ts) => new Date(ts));
  let xRange = null;
  if (xData.length > 0) {
    const start = xData[0];
    const end = new Date(start.getTime() + 60 * 3600 * 1000);
    xRange = [start, end];
  }
  return {
    margin: { l: 50, r: 20, t: 30, b: 70 },
    xaxis: { title: "Zeit", automargin: true, range: xRange },
    yaxis: { title: param, automargin: true },
    hovermode: "x",
    autosize: true,
    showlegend: false,
    dragmode: "pan",
  };
}

// HAUPTFUNKTION: Rendert den Plot (wird in main.js importiert)
export function renderPlot(param, seriesMap, timeSteps, result_uv_and_pt) {
  // Das Element lokal holen, statt global vorauszusetzen
  const plotlyDiv = document.getElementById("plotlyDiv");

  if (!seriesMap || !seriesMap[param]) {
    plotlyDiv.innerHTML = "<em>Keine Daten für diesen Parameter</em>";
    return;
  }

  // Fehlerbereich vorhanden?
  const hasError = !!seriesMap[param + "_error"];
  const traces = [];

  // UV-Index Plot
  if (param.includes("UV-Index")) {
    const day_strings = result_uv_and_pt["uvi_times"];
    const hours = result_uv_and_pt["UVH"]; // in 'hh' Format
    const timeStep_uv = day_strings.map((date, i) => {
      const newDate = new Date(date); // Kopie erstellen
      newDate.setUTCHours(hours[i], 0, 0, 0); // Nur UTC-Hours setzen
      return newDate;
    });

    const xData = timeStep_uv;
    const yData = seriesMap[param].map((v) => (v == null ? null : v));

    // Linie in grau
    traces.push({
      x: xData,
      y: yData,
      type: "scatter",
      mode: "lines",
      line: { width: 2, shape: "spline", color: "rgb(102, 102, 102)" },
      connectgaps: true,
      hoverinfo: "skip",
      showlegend: false,
    });

    // Marker anderem grau
    traces.push({
      x: xData,
      y: yData,
      type: "scatter",
      mode: "markers",
      marker: { size: 6, color: "rgb(68, 68, 68)" },
      name: param,
    });

    const layout = {
      ...getLayout(param, timeSteps),
      shapes: [
        {
          type: "rect",
          xref: "paper",
          yref: "y",
          x0: 0,
          x1: 1,
          y0: 0,
          y1: 3,
          fillcolor: "rgba(0, 255, 0, 0.2)",
          line: { width: 0 },
        },
        {
          type: "rect",
          xref: "paper",
          yref: "y",
          x0: 0,
          x1: 1,
          y0: 3,
          y1: 6,
          fillcolor: "rgba(255, 255, 0, 0.2)",
          line: { width: 0 },
        },
        {
          type: "rect",
          xref: "paper",
          yref: "y",
          x0: 0,
          x1: 1,
          y0: 6,
          y1: 8,
          fillcolor: "rgba(255, 165, 0, 0.2)",
          line: { width: 0 },
        },
        {
          type: "rect",
          xref: "paper",
          yref: "y",
          x0: 0,
          x1: 1,
          y0: 8,
          y1: 11,
          fillcolor: "rgba(255, 0, 0, 0.2)",
          line: { width: 0 },
        },
        {
          type: "rect",
          xref: "paper",
          yref: "y",
          x0: 0,
          x1: 1,
          y0: 11,
          y1: 13,
          fillcolor: "rgba(128, 0, 128, 0.2)",
          line: { width: 0 },
        },
      ],
    };

    Plotly.newPlot(plotlyDiv, traces, layout, getConfig());
    return;
  }

  // Gefühlte Temperatur Plot
  if (param.includes("Temperatur (°C)")) {
    const gft_time_step = result_uv_and_pt["gft_times"];
    const gft_data = seriesMap["Gefühlte Temperatur"];

    // Linie Gefühlte Temperatur in rot
    traces.push({
      x: gft_time_step,
      y: gft_data,
      type: "scatter",
      mode: "lines",
      line: { width: 2, shape: "spline", color: "rgb(200, 0, 0)" },
      connectgaps: true,
      hoverinfo: "skip",
      showlegend: false,
    });

    // Marker Gefühlte Temperatur in rot
    traces.push({
      x: gft_time_step,
      y: gft_data,
      type: "scatter",
      mode: "markers",
      marker: { size: 6, color: "rgb(120, 0, 0)" },
      name: "Gefühlte Temperatur (°C)",
    });
  }

  // Maximale Windböe Plot
  if (param.includes("Windgeschwindigkeit (km/h)")) {
    const gust_data = seriesMap["Maximale Windböe"];

    // Prüfen, ob Daten für Böen vorhanden sind
    if (gust_data) {
      const gust_time_step = timeSteps.map((ts) => new Date(ts));

      // Linie Maximale Windböe (hier in einem passenden Blauton)
      traces.push({
        x: gust_time_step,
        y: gust_data,
        type: "scatter",
        mode: "lines",
        line: { width: 2, shape: "spline", color: "rgb(0, 150, 200)" },
        connectgaps: true,
        hoverinfo: "skip",
        showlegend: false,
      });

      // Marker Maximale Windböe (etwas dunkleres Blau)
      traces.push({
        x: gust_time_step,
        y: gust_data,
        type: "scatter",
        mode: "markers",
        marker: { size: 6, color: "rgb(0, 100, 150)" },
        name: "Maximale Windböe",
      });
    }
  }

  const xData = timeSteps.map((ts) => new Date(ts));
  const yData = seriesMap[param].map((v) => (v == null ? null : v));

  // Fehlerbereich Plot
  if (hasError) {
    const errorData = seriesMap[param + "_error"];
    const yUpper = yData.map((v, i) =>
      v != null && errorData[i] != null ? v + errorData[i] : null,
    );
    const yLower = yData.map((v, i) =>
      v != null && errorData[i] != null ? v - errorData[i] : null,
    );

    // Fläche zwischen upper und lower in hellem Blau
    traces.push({
      x: [...xData, ...xData.slice().reverse()],
      y: [...yUpper, ...yLower.slice().reverse()],
      type: "scatter",
      mode: "lines",
      fill: "toself",
      fillcolor: "rgba(79, 79, 79, 0.5)",
      line: { color: "transparent" },
      hoverinfo: "skip",
      showlegend: false,
      connectgaps: true,
      name: `${param} Fehlerbereich`,
    });
  }

  // Nachtbereiche hinzufügen (20-8 Uhr) in hellgrau
  let shapes = [];

  if (!param.includes("UV-Index")) {
    const nightColor = "rgba(241, 241, 241, 0.75)"; // hellgrau
    const datesSet = new Set();

    xData.forEach((dt) => {
      const dateStr = dt.toISOString().split("T")[0]; // "YYYY-MM-DD"

      if (datesSet.has(dateStr)) return; // Nur ein Rechteck pro Datum
      datesSet.add(dateStr); // Rechteck von 00:00 bis 08:00

      shapes.push({
        type: "rect",
        xref: "x",
        yref: "paper",
        x0: new Date(dateStr + "T00:00:00Z"),
        x1: new Date(dateStr + "T06:00:00Z"),
        y0: 0,
        y1: 1,
        fillcolor: nightColor,
        line: { width: 0 },
        layer: "below",
      });

      // Rechteck von 20:00 bis 23:59
      shapes.push({
        type: "rect",
        xref: "x",
        yref: "paper",
        x0: new Date(dateStr + "T18:00:00Z"),
        x1: new Date(new Date(dateStr + "T23:59:59Z").getTime() + 1000), // leicht drüber hinaus
        y0: 0,
        y1: 1,
        fillcolor: nightColor,
        line: { width: 0 },
        layer: "below",
      });
    });
  }

  if (param.includes("Totale Niederschlagsmenge (mm)")) {
    shapes.push(
      {
        type: "rect",
        xref: "paper",
        yref: "y",
        x0: 0,
        x1: 1,
        y0: 0,
        y1: 0.5,
        fillcolor: "rgba(173, 216, 230, 0.25)",
        line: { width: 0 },
      },
      {
        type: "rect",
        xref: "paper",
        yref: "y",
        x0: 0,
        x1: 1,
        y0: 0.5,
        y1: 2.5,
        fillcolor: "rgba(65, 105, 225, 0.2)",
        line: { width: 0 },
      },
      {
        type: "rect",
        xref: "paper",
        yref: "y",
        x0: 0,
        x1: 1,
        y0: 2.5,
        y1: 5,
        fillcolor: "rgba(25, 25, 112, 0.3)",
        line: { width: 0 },
      },
    );
  }

  // Sonnenstunden Plot
  if (param.includes("Sonnenstunden")) {
    const xDataSun = timeSteps.map((ts) => {
      const date = new Date(ts);
      date.setDate(date.getDate() - 1); // Einen Tag abziehen
      date.setUTCHours(12, 0, 0, 0); // Uhrzeit auf 10:00:00.000 UTC setzen
      return date;
    });
    const yDataSun = seriesMap[param].map((v) => (v == null ? null : v / 60));

    // Linie in grau
    traces.push({
      x: xDataSun,
      y: yDataSun,
      type: "scatter",
      mode: "lines",
      line: { width: 2, shape: "spline", color: "rgba(17, 24, 39, 1)" },
      connectgaps: true,
      name: param,
      hoverinfo: "skip",
      showlegend: false,
    });

    // Marker anderem grau
    traces.push({
      x: xDataSun,
      y: yDataSun,
      type: "scatter",
      mode: "markers",
      marker: { size: 6, color: "rgba(17, 24, 39, 1)" },
      name: param,
    });

    const layout = {
      ...getLayout(param, timeSteps),
      shapes: shapes,
    };

    Plotly.newPlot(plotlyDiv, traces, layout, getConfig());
    return;
  }

  // Standard Plot für alles andere (Linie)
  traces.push({
    x: xData,
    y: yData,
    type: "scatter",
    mode: "lines",
    line: { width: 2, shape: "spline", color: "rgba(17, 24, 39, 1)" },
    connectgaps: true,
    name: param,
    hoverinfo: "skip",
    showlegend: false,
  });

  // Standard Plot für alles andere (Marker)
  traces.push({
    x: xData,
    y: yData,
    type: "scatter",
    mode: "markers",
    marker: { size: 6, color: "rgba(17, 24, 39, 1)" },
    name: param,
  });

  const layout = {
    ...getLayout(param, timeSteps),
    shapes: shapes,
  };

  // Wenn Windrichtung → Y-Achse in Richtungssymbolen anzeigen
  if (param.includes("Windrichtung")) {
    layout.yaxis = {
      title: "Windrichtung",
      tickmode: "array",
      tickvals: [0, 90, 180, 270, 360],
      ticktext: ["N", "E", "S", "W", "N"],
      range: [0, 360],
    };
  }

  // Niederschlag Auto-Zoom
  if (param.includes("Totale Niederschlagsmenge (mm)")) {
    // Hole den exakten Zeitraum des Startausschnitts aus deinem Layout
    const viewStart = layout.xaxis.range[0].getTime();
    const viewEnd = layout.xaxis.range[1].getTime();

    // Filtere nur die Datenpunkte, die in genau diesen Zeitraum fallen
    const dataVals = seriesMap[param].filter((v, index) => {
      const currentTime = new Date(timeSteps[index]).getTime();
      return (
        v !== null &&
        !isNaN(v) &&
        currentTime >= viewStart &&
        currentTime <= viewEnd
      );
    });

    if (dataVals.length > 0) {
      const minData = Math.min(...dataVals);
      const maxData = Math.max(...dataVals);
      const diff = maxData - minData;

      if (diff === 0) {
        // Wenn im Startzeitraum alles gleich ist (z.B. durchgehend 0 mm)
        layout.yaxis.range = [-0.1, 2.0];
      } else {
        // Exakt 5% der Differenz als Polster
        const padding = diff * 0.1;
        layout.yaxis.range = [minData - padding, maxData + padding];
      }
    }
  }

  Plotly.newPlot(plotlyDiv, traces, layout, getConfig());
}
