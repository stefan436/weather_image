// config.js

export const meta_path =
  "https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/meta.json";
// export const meta_path =
//   "/backend/index-MCP/data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity


export const indexLevels = [
  { min: 99.61, color: "#7A007A", label: ">= 99.61" },
  { min: 99.45, color: "#95005E", label: "99.45 - 99.61" },
  { min: 99.22, color: "#B00042", label: "99.22 - 99.45" },
  { min: 98.89, color: "#CB0026", label: "98.89 - 99.22" },
  { min: 98.44, color: "#E60000", label: "98.44 - 98.89" },
  { min: 97.80, color: "#EC1400", label: "97.80 - 98.44" },
  { min: 96.88, color: "#F32800", label: "96.88 - 97.80" },
  { min: 96.41, color: "#F53000", label: "96.41 - 96.88" },
  { min: 95.87, color: "#F83B00", label: "95.87 - 96.41" },
  { min: 95.26, color: "#FA4300", label: "95.26 - 95.87" },
  { min: 94.56, color: "#FD4C00", label: "94.56 - 95.26" },
  { min: 93.75, color: "#FF5000", label: "93.75 - 94.56" },
  { min: 92.84, color: "#FF5600", label: "92.84 - 93.75" },
  { min: 91.77, color: "#FF5C00", label: "91.77 - 92.84" },
  { min: 90.55, color: "#FF6200", label: "90.55 - 91.77" },
  { min: 89.14, color: "#FF6800", label: "89.14 - 90.55" },
  { min: 87.52, color: "#FF6E00", label: "87.52 - 89.14" },
  { min: 85.66, color: "#FF7400", label: "85.66 - 87.52" },
  { min: 83.52, color: "#FF7A00", label: "83.52 - 85.66" },
  { min: 81.06, color: "#FF8000", label: "81.06 - 83.52" },
  { min: 78.24, color: "#FF8600", label: "78.24 - 81.06" },
  { min: 75.00, color: "#FF8C00", label: "75.00 - 78.24" },
  { min: 71.27, color: "#FFAA00", label: "71.27 - 75.00" },
  { min: 67.00, color: "#FFC800", label: "67.00 - 71.27" },
  { min: 62.10, color: "#E3E300", label: "62.10 - 67.00" },
  { min: 56.47, color: "#80FF00", label: "56.47 - 62.10" },
  { min: 50.00, color: "#00D000", label: "50.00 - 56.47" },
  { min: 42.57, color: "#00B06A", label: "42.57 - 50.00" },
  { min: 34.03, color: "#0090C0", label: "34.03 - 42.57" },
  { min: 24.21, color: "#105CFF", label: "24.21 - 34.03" },
  { min: 12.94, color: "#8CBDFF", label: "12.94 - 24.21" },
];