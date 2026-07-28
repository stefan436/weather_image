// config.js

export const meta_path =
  "https://users.ph.nat.tum.de/ge47fab/weather_data/index/Forecast/meta.json";
// export const meta_path =
//   "/backend/index-MCP/data/Forecast/meta.json";
export const time_per_frame = 500; // in ms; dauer bis nächster frame beginnt eingeblendet zu werden (und gleichzeitig der alte ausgeblendet wird)
export const cross_fade_time = 0; // in s; time needed for the frame to get to set opacity


export const indexLevels = [
  { min: 400.0, color: "#7A007A", label: ">= 400.0" },
  { min: 375.0, color: "#95005E", label: "375.0 - 400.0" },
  { min: 350.0, color: "#B00042", label: "350.0 - 375.0" },
  { min: 325.0, color: "#CB0026", label: "325.0 - 350.0" },
  { min: 300.0, color: "#E60000", label: "300.0 - 325.0" },
  { min: 275.0, color: "#EC1400", label: "275.0 - 300.0" },
  { min: 250.0, color: "#F32800", label: "250.0 - 275.0" },
  { min: 240.0, color: "#F53000", label: "240.0 - 250.0" },
  { min: 230.0, color: "#F83B00", label: "230.0 - 240.0" },
  { min: 220.0, color: "#FA4300", label: "220.0 - 230.0" },
  { min: 210.0, color: "#FD4C00", label: "210.0 - 220.0" },
  { min: 200.0, color: "#FF5000", label: "200.0 - 210.0" },
  { min: 190.0, color: "#FF5600", label: "190.0 - 200.0" },
  { min: 180.0, color: "#FF5C00", label: "180.0 - 190.0" },
  { min: 170.0, color: "#FF6200", label: "170.0 - 180.0" },
  { min: 160.0, color: "#FF6800", label: "160.0 - 170.0" },
  { min: 150.0, color: "#FF6E00", label: "150.0 - 160.0" },
  { min: 140.0, color: "#FF7400", label: "140.0 - 150.0" },
  { min: 130.0, color: "#FF7A00", label: "130.0 - 140.0" },
  { min: 120.0, color: "#FF8000", label: "120.0 - 130.0" },
  { min: 110.0, color: "#FF8600", label: "110.0 - 120.0" },
  { min: 100.0, color: "#FF8C00", label: "100.0 - 110.0" },
  { min: 90.0,  color: "#FFAA00", label: "90.0 - 100.0" },
  { min: 80.0,  color: "#FFC800", label: "80.0 - 90.0" },
  { min: 70.0,  color: "#E3E300", label: "70.0 - 80.0" },
  { min: 60.0,  color: "#80FF00", label: "60.0 - 70.0" },
  { min: 50.0,  color: "#00D000", label: "50.0 - 60.0" },
  { min: 40.0,  color: "#00B06A", label: "40.0 - 50.0" },
  { min: 30.0,  color: "#0090C0", label: "30.0 - 40.0" },
  { min: 20.0,  color: "#105CFF", label: "20.0 - 30.0" },
  { min: 10.0,  color: "#8CBDFF", label: "10.0 - 20.0" },
];