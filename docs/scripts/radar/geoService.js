// geoService.js

export function getLocation(callback) {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => callback(pos.coords.latitude, pos.coords.longitude, true),
      (err) => {
        showError(err);

        if (err.code === err.PERMISSION_DENIED) {
          callback(48.1374, 11.5755, false);
        }
      },
    );
  } else {
    document.getElementById("location_output").innerText =
      "Geolocation wird nicht unterstützt.";
    callback(48.1374, 11.5755, false);
  }
}

function showError(error) {
  const messages = {
    1: "Zugriff auf Standort verweigert.",
    2: "Standortinformationen nicht verfügbar.",
    3: "Anfrage dauerte zu lange.",
    default: "Unbekannter Fehler.",
  };
  document.getElementById("location_output").innerText =
    messages[error.code] || messages.default;
}