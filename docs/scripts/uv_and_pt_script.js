const LAT_COUNT = 425;
const LON_COUNT = 700;
const TIME_STEPS = 72;


async function loadLatLonUvAndPt() {
    const [latRes, lonRes] = await Promise.all([
    fetch("data/latitudes_uv_and_pt.json").then(r => r.json()),
    fetch("data/longitudes_uv_and_pt.json").then(r => r.json())
    ]);
    return { latitudes: latRes, longitudes: lonRes };
}

function findNearestIndexUvAndPt(array, value) {
    let minDiff = Infinity;
    let idx = -1;
    for (let i = 0; i < array.length; i++) {
    const diff = Math.abs(array[i] - value);
    if (diff < minDiff) {
        minDiff = diff;
        idx = i;
    }
    }
    return idx;
}

async function loadTimeSeriesUvAndPt(latIdx, lonIdx) {
    const valuesPerStep = LAT_COUNT * LON_COUNT;

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
    for (let t = 0; t < TIME_STEPS; t++) {
    const index = t * valuesPerStep + latIdx * LON_COUNT + lonIdx;
    result_gft.push(allDatagft[index]);
    }

    const result_uvi = [];
    for (let t = 0; t < TIME_STEPS; t++) {
    const index = t * valuesPerStep + latIdx * LON_COUNT + lonIdx;
    result_uvi.push(allDataUvi[index]);
    }

    const result_uvh = [];
    for (let t = 0; t < TIME_STEPS; t++) {
    const index = t * valuesPerStep + latIdx * LON_COUNT + lonIdx;
    result_uvh.push(allDataUvh[index]);
    }


    return { GFT: result_gft, UVI: result_uvi, UVH:result_uvh };
}




async function loadTimeStamps() {
    const response_gft = await fetch("data/gft_forecast_times.json");
    const gft_times = await response_gft.json();

    const gft_times_formatted = gft_times.map(iso => {
        // Trim auf Millisekunden (max. 3 Stellen)
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1'); 
        return new Date(trimmed);
    });

    const response_uvi = await fetch("data/uvi_forecast_times.json");
    const uvi_times = await response_uvi.json();

    const uvi_times_formatted = uvi_times.map(iso => {
        // Trim auf Millisekunden (max. 3 Stellen)
        const trimmed = iso.replace(/(\.\d{3})\d*/, '$1'); 
        return new Date(trimmed);
    });


    return { gft_times: gft_times_formatted, uvi_times: uvi_times_formatted };
}

async function runForecastUvAndPt(userLat, userLon) {
    try {
    const { latitudes, longitudes } = await loadLatLonUvAndPt();
        const latIdx = findNearestIndexUvAndPt(latitudes, userLat);
        const lonIdx = findNearestIndexUvAndPt(longitudes, userLon);

        const results = await loadTimeSeriesUvAndPt(latIdx, lonIdx);
        const { gft_times, uvi_times } = await loadTimeStamps();
        
        // Kombiniere alles in einem Ergebnisobjekt
        return { ...results, gft_times, uvi_times };

    } catch (err) {
        console.error(err);
    };
}
