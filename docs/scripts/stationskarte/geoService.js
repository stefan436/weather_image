// geoService.js

export function getLocation(callback) {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => callback(pos.coords.latitude, pos.coords.longitude, true),
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          callback(48.1374, 11.5755, false);
        }
      },
    );
  } else {
    callback(48.1374, 11.5755, false);
  }
}