// config.js

export const meta_path =
  "https://users.ph.nat.tum.de/ge47fab/weather_data/pySTEPS_data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity

export const radarLevels = [
  { min: 100.0, color: "#7A007A", label: "> 100 mm/h" },
  { min: 60.0, color: "#A00040", label: "60 - 100 mm/h" },
  { min: 40.0, color: "#E60000", label: "40 - 60 mm/h" },
  { min: 25.0, color: "#FF5000", label: "25 - 40 mm/h" },
  { min: 20.0, color: "#FF8C00", label: "20 - 25 mm/h" },
  { min: 15.0, color: "#FFC800", label: "15 - 20 mm/h" },
  { min: 10.0, color: "#FFFF00", label: "10 - 15 mm/h" },
  { min: 7.5, color: "#80FF00", label: "7.5 - 10 mm/h" },
  { min: 5.0, color: "#00D000", label: "5 - 7.5 mm/h" },
  { min: 2.5, color: "#00A0A0", label: "2.5 - 5 mm/h" },
  { min: 1.0, color: "#105CFF", label: "1 - 2.5 mm/h" },
  { min: 0.5, color: "#4E8CFF", label: "0.5 - 1 mm/h" },
  { min: 0.25, color: "#8CBDFF", label: "0.25 - 0.5 mm/h" },
];
