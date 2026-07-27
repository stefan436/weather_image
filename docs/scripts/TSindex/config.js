// config.js

// export const meta_path =
//   "https://users.ph.nat.tum.de/ge47fab/weather_data/pySTEPS_data/Forecast/meta.json";
export const meta_path =
  "/backend/TSindex/data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity

export const indexLevels = [
  { min: 5.0, color: "#7A007A", label: "> 5.0" },
  { min: 4.5, color: "#A00040", label: "4.5 - 5.0" },
  { min: 4.0, color: "#E60000", label: "4.0 - 4.5" },
  { min: 3.0, color: "#FF5000", label: "3.0 - 4.0" },
  { min: 2.0, color: "#FF8C00", label: "2.0 - 3.0" },
  { min: 1.0, color: "#FFC800", label: "1.0 - 2.0" },
  { min: 0.8, color: "#FFFF00", label: "0.8 - 1.0" },
  { min: 0.65, color: "#80FF00", label: "0.65 - 0.8" },
  { min: 0.5, color: "#00D000", label: "0.5 - 0.65" },
  { min: 0.35, color: "#00A0A0", label: "0.35 - 0.5" },
  { min: 0.2, color: "#105CFF", label: "0.2 - 0.35" },
  { min: 0.1, color: "#4E8CFF", label: "0.1 - 0.2" },
  { min: 0.05, color: "#8CBDFF", label: "0.05 - 0.1" },
];