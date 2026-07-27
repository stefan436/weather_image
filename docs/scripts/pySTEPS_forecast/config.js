// config.js

export const meta_path =
  "https://users.ph.nat.tum.de/ge47fab/weather_data/pySTEPS_data/Forecast/meta.json";
// export const meta_path =
//   "/backend/BlendingForecast/data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity

export const radarLevels = [
  { min: 140.0, color: "#7A007A", label: "> 140 mm/h" },
  { min: 130.0, color: "#95005E", label: "130 - 140 mm/h" },
  { min: 120.0, color: "#B00042", label: "120 - 130 mm/h" },
  { min: 115.0, color: "#CB0026", label: "115 - 120 mm/h" },
  { min: 110.0, color: "#E60000", label: "110 - 115 mm/h" },
  { min: 105.0, color: "#EC1400", label: "105 - 110 mm/h" },
  { min: 100.0, color: "#F32800", label: "100 - 105 mm/h" },
  { min: 95.0, color: "#F53000", label: "95 - 100 mm/h" },
  { min: 90.0, color: "#F83B00", label: "90 - 95 mm/h" },
  { min: 85.0, color: "#FA4300", label: "85 - 90 mm/h" },
  { min: 80.0, color: "#FD4C00", label: "80 - 85 mm/h" },
  { min: 75.0, color: "#FF5000", label: "75 - 80 mm/h" },
  { min: 70.0, color: "#FF5600", label: "70 - 75 mm/h" },
  { min: 65.0, color: "#FF5C00", label: "65 - 70 mm/h" },
  { min: 60.0, color: "#FF6200", label: "60 - 65 mm/h" },
  { min: 55.0, color: "#FF6800", label: "55 - 60 mm/h" },
  { min: 50.0, color: "#FF6E00", label: "50 - 55 mm/h" },
  { min: 45.0, color: "#FF7400", label: "45 - 50 mm/h" },
  { min: 40.0, color: "#FF7A00", label: "40 - 45 mm/h" },
  { min: 35.0, color: "#FF8000", label: "35 - 40 mm/h" },
  { min: 30.0, color: "#FF8600", label: "30 - 35 mm/h" },
  { min: 25.0, color: "#FF8C00", label: "25 - 30 mm/h" },
  { min: 20.0, color: "#FFAA00", label: "20 - 25 mm/h" },
  { min: 15.0, color: "#FFC800", label: "15 - 20 mm/h" },
  { min: 10.0, color: "#E3E300", label: "10 - 15 mm/h" },
  { min: 7.5,  color: "#80FF00", label: "7.5 - 10 mm/h" },
  { min: 5.0,  color: "#00D000", label: "5 - 7.5 mm/h" },
  { min: 2.5,  color: "#00B06A", label: "2.5 - 5 mm/h" },
  { min: 1.0,  color: "#0090C0", label: "1 - 2.5 mm/h" },
  { min: 0.5,  color: "#105CFF", label: "0.5 - 1 mm/h" },
  { min: 0.25, color: "#8CBDFF", label: "0.25 - 0.5 mm/h" },
];
