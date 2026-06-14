//ui.js

export function renderWeather(fields) {
  const container = document.getElementById("weather_data");
  document.querySelector('.weather-card').style.height = ''; // Reset falls nötig
  container.innerHTML = "";
  
  for (const [label, value] of Object.entries(fields)) {
    const row = document.createElement("div");
    row.innerHTML = `<span class="label">${label}:</span><span class="value">${value}</span>`;
    container.appendChild(row);
  }
}

export function setStatusMessage(msg) {
  document.getElementById("location_output").innerText = msg;
}

export function showError(error) {
  const messages = {
    1: "Zugriff auf Standort verweigert.",
    2: "Standortinformationen nicht verfügbar.",
    3: "Anfrage dauerte zu lange.",
    default: "Unbekannter Fehler."
  };
  setStatusMessage(messages[error.code] || messages.default);
}