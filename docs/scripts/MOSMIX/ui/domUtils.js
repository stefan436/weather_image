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
      onStationSelect(st.station_id, st.distance);
    };
    container.appendChild(btn);
  });
}