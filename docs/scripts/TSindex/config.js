// config.js

export const meta_path =
  "https://users.ph.nat.tum.de/ge47fab/weather_data/TSindex_data/Forecast/meta.json";
// export const meta_path =
//   "/backend/TSindex/data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity


export const indexLevels = [
  { min: 4.0, color: "#7A007A", label: ">= 4.0" },
  { min: 3.75, color: "#95005E", label: "3.75 - 4.0" },
  { min: 3.5, color: "#B00042", label: "3.5 - 3.75" },
  { min: 3.25, color: "#CB0026", label: "3.25 - 3.5" },
  { min: 3.0, color: "#E60000", label: "3.0 - 3.25" },
  { min: 2.75, color: "#EC1400", label: "2.75 - 3.0" },
  { min: 2.5, color: "#F32800", label: "2.5 - 2.75" },
  { min: 2.4, color: "#F53000", label: "2.4 - 2.5" },
  { min: 2.3, color: "#F83B00", label: "2.3 - 2.4" },
  { min: 2.2, color: "#FA4300", label: "2.2 - 2.3" },
  { min: 2.1, color: "#FD4C00", label: "2.1 - 2.2" },
  { min: 2.0, color: "#FF5000", label: "2.0 - 2.1" },
  { min: 1.9, color: "#FF5600", label: "1.9 - 2.0" },
  { min: 1.8, color: "#FF5C00", label: "1.8 - 1.9" },
  { min: 1.7, color: "#FF6200", label: "1.7 - 1.8" },
  { min: 1.6, color: "#FF6800", label: "1.6 - 1.7" },
  { min: 1.5, color: "#FF6E00", label: "1.5 - 1.6" },
  { min: 1.4, color: "#FF7400", label: "1.4 - 1.5" },
  { min: 1.3, color: "#FF7A00", label: "1.3 - 1.4" },
  { min: 1.2, color: "#FF8000", label: "1.2 - 1.3" },
  { min: 1.1, color: "#FF8600", label: "1.1 - 1.2" },
  { min: 1.0, color: "#FF8C00", label: "1.0 - 1.1" },
  { min: 0.9, color: "#FFAA00", label: "0.9 - 1.0" },
  { min: 0.8, color: "#FFC800", label: "0.8 - 0.9" },
  { min: 0.7, color: "#E3E300", label: "0.7 - 0.8" },
  { min: 0.6, color: "#80FF00", label: "0.6 - 0.7" },
  { min: 0.5, color: "#00D000", label: "0.5 - 0.6" },
  { min: 0.4, color: "#00B06A", label: "0.4 - 0.5" },
  { min: 0.3, color: "#0090C0", label: "0.3 - 0.4" },
  { min: 0.2, color: "#105CFF", label: "0.2 - 0.3" },
  { min: 0.1, color: "#8CBDFF", label: "0.1 - 0.2" },
];