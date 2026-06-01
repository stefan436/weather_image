const LAT_COUNT_GFT = 225;
const LON_COUNT_GFT = 250;

const LAT_COUNT_UV = 657;
const LON_COUNT_UV = 1377;

const TIME_STEPS_GFT = 72;
const TIME_STEPS_UV = 3;


async function loadLatLonGft() {
    const [latRes, lonRes] = await Promise.all([
    fetch("data/latitudes_gft.json").then(r => r.json()),
    fetch("data/longitudes_gft.json").then(r => r.json())
    ]);
    return { latitudes_gft: latRes, longitudes_gft: lonRes };
}

async function loadLatLonUv() {
    const [latRes, lonRes] = await Promise.all([
    fetch("data/latitudes_uv.json").then(r => r.json()),
    fetch("data/longitudes_uv.json").then(r => r.json())
    ]);
    return { latitudes_uv: latRes, longitudes_uv: lonRes };
}

function findNearestIndices(latitudes, longitudes, userLat, userLon) {
    const toRad = x => x * Math.PI / 180;

    let bestLatIdx = -1;
    let bestLonIdx = -1;
    let minDist = Infinity;

    for (let i = 0; i < latitudes.length; i++) {
        for (let j = 0; j < longitudes.length; j++) {
            const lat = latitudes[i];
            const lon = longitudes[j];

            const dLat = toRad(lat - userLat);
            const dLon = toRad(lon - userLon);

            const a = Math.sin(dLat / 2) ** 2 +
                      Math.cos(toRad(userLat)) * Math.cos(toRad(lat)) *
                      Math.sin(dLon / 2) ** 2;

            const c = 2 * Math.asin(Math.sqrt(a));
            const dist = c; // Abstand auf Einheitskugel (in Radiant), multiplizierbar mit Erdradius

            if (dist < minDist) {
                minDist = dist;
                bestLatIdx = i;
                bestLonIdx = j;
            }
        }
    }

    return { latIdx: bestLatIdx, lonIdx: bestLonIdx, distanceRad: minDist };
}


async function loadTimeSeriesUvAndPt(latIdx_gft, lonIdx_gft, latIdx_uv, lonIdx_uv) {
    const valuesPerStep_GFT = LAT_COUNT_GFT * LON_COUNT_GFT;
    const valuesPerStep_UV = LAT_COUNT_UV * LON_COUNT_UV;

    const response_gft = await fetch("data/data_gft.bin");
    const buffer_gft = await response_gft.arrayBuffer();
    const allDatagft = new Float32Array(buffer_gft);

    const response_uvi = await fetch("data/data_uvi.bin");
    const buffer_uvi = await response_uvi.arrayBuffer();
    const allDataUvi = new Float32Array(buffer_uvi);

    const response_uvh = await fetch("data/data_uvh.bin");
    const buffer_uvh = await response_uvh.arrayBuffer();
    const allDataUvh = new Float32Array(buffer_uvh);

    const result_gft = [];
    for (let t = 0; t < TIME_STEPS_GFT; t++) {
    const index = t * valuesPerStep_GFT + latIdx_gft * LON_COUNT_GFT + lonIdx_gft;
    result_gft.push(allDatagft[index]);
    }

    const result_uvi = [];
    for (let t = 0; t < TIME_STEPS_UV; t++) {
    const index = t * valuesPerStep_UV + latIdx_uv * LON_COUNT_UV + lonIdx_uv;
    result_uvi.push(allDataUvi[index]);
    }

    const result_uvh = [];
    for (let t = 0; t < TIME_STEPS_UV; t++) {
    const index = t * valuesPerStep_UV + latIdx_uv * LON_COUNT_UV + lonIdx_uv;
    result_uvh.push(allDataUvh[index]);
    }


    return { GFT: result_gft, UVI: result_uvi, UVH:result_uvh };
}




async function loadTimeStamps() {
    const response_gft = await fetch("data/gft_forecast_times.json");
    const gft_times = await response_gft.json();

    const gft_times_formatted = gft_times.map(iso => {
        // Trim auf Millisekunden (max. 3 Stellen)
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1') + 'Z'; 
        return new Date(trimmed);
    });

    const response_uvi = await fetch("data/uvi_forecast_times.json");
    const uvi_times = await response_uvi.json();

    const uvi_times_formatted = uvi_times.map(iso => {
        // Trim auf Millisekunden (max. 3 Stellen)
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1') + 'Z'; 
        return new Date(trimmed);
    });


    return { gft_times: gft_times_formatted, uvi_times: uvi_times_formatted };
}

async function runForecastUvAndPt(userLat, userLon) {
    try {
    const { latitudes_gft, longitudes_gft } = await loadLatLonGft();
    const { latitudes_uv, longitudes_uv } = await loadLatLonUv();

        const { latIdx: latIdx_gft, lonIdx: lonIdx_gft, distanceRad: distanceRadGft } =
            findNearestIndices(latitudes_gft, longitudes_gft, userLat, userLon);

        const { latIdx: latIdx_uv, lonIdx: lonIdx_uv, distanceRad: distanceRadUv } =
            findNearestIndices(latitudes_uv, longitudes_uv, userLat, userLon);

        const results = await loadTimeSeriesUvAndPt(latIdx_gft, lonIdx_gft, latIdx_uv, lonIdx_uv);
        const { gft_times, uvi_times } = await loadTimeStamps();
        
        // Kombiniere alles in einem Ergebnisobjekt
        return { ...results, gft_times, uvi_times, distanceRadGft, distanceRadUv };

    } catch (err) {
        console.error(err);
    };
}
