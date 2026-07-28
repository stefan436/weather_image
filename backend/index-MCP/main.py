import numpy as np
from datetime import datetime, timezone
import config
from mosmix import build_unified_api
from read_current_ICON_RUC import download_ruc, get_ruc_urls, create_prediction
from convert_to_mobile_format import generate_time_arrays_ruc, prepare_data_icon, export_data
from calculation import calculate_TSindex, calculate_BRN


if __name__ == "__main__":
    TARGET_DATE = datetime.utcnow()
    today = datetime.now(timezone.utc)
    time_now = today.replace(minute=0, second=0, microsecond=0)

    # ==========================================
    # 1. ICON RUC Daten laden & Indizes berechnen
    # ==========================================
    predictions = {}
    for product_name, params in config.PRODUCTS.items():
        urls = get_ruc_urls(set_past_date=config.set_past_date, steps_into_future=config.steps_into_future, base_url_ruc=params["base_url"])
        download_dir = download_ruc(urls, params["download_dir"])
        pred_raw, projection_ruc = create_prediction(download_dir, config.steps_into_future)

        nodata_vals = params["nodata"] if isinstance(params["nodata"], (list, tuple)) else [params["nodata"]]
        mask = np.logical_or.reduce([np.isclose(pred_raw, nd, atol=1e-3) for nd in nodata_vals])
        pred_masked = np.where(mask, np.nan, pred_raw)
        
        predictions[product_name] = pred_masked

    final_pred = calculate_TSindex(
        cape=predictions["CAPE_MU"], 
        cin=predictions["CIN_MU"], 
        cape_ref=config.CAPE_MU_ref, 
        cin_ref=config.CIN_MU_ref
    )

    brn_pred = calculate_BRN(
        cape=predictions["CAPE_MU"],
        wshear_u=predictions["WSHEAR_U"],
        wshear_v=predictions["WSHEAR_V"]
    )

    total_frames = final_pred.shape[0]
    absolute_time_array, relative_time_array = generate_time_arrays_ruc(total_frames, time_now)

    # 4326-Arrays abgreifen, um die reinen Geodaten für die Stationsextraktion zu bekommen
    da_web_ts, leaflet_bounds, da_mask_web, da_ts_4326 = prepare_data_icon(
        final_pred=final_pred, projection_ruc=projection_ruc, time_array=absolute_time_array
    )
    _, _, _, da_brn_4326 = prepare_data_icon(
        final_pred=brn_pred, projection_ruc=projection_ruc, time_array=absolute_time_array
    )
    _, _, _, da_cape_4326 = prepare_data_icon(
        final_pred=predictions["CAPE_MU"], projection_ruc=projection_ruc, time_array=absolute_time_array
    )
    _, _, _, da_cin_4326 = prepare_data_icon(
        final_pred=predictions["CIN_MU"], projection_ruc=projection_ruc, time_array=absolute_time_array
    )

    x_coords = da_ts_4326.x.values
    y_coords = da_ts_4326.y.values

    # Dictionary für die `build_unified_api` zusammenbauen
    icon_data_dict = {
        "CAPE": da_cape_4326.values,
        "CIN": da_cin_4326.values,
        "MCP": da_ts_4326.values,
        "BRN": da_brn_4326.values
    }

    # ==========================================
    # 2. Unified API aufbauen (schreibt die JSONs)
    # ==========================================
    warnmos_arguments = (
        config.WARNMOS_BASE_URL, 
        TARGET_DATE, 
        config.WARNMOS_TARGETS, 
        config.WARNMOS_DOWNLOAD_PATH
    )

    build_unified_api(
        mosmix_url=config.MOSMIX_URL, 
        out_dir=config.OUT_DIR, 
        coords_json=config.COORDS_JSON, 
        warnmos_args=warnmos_arguments, 
        target_params=config.MOSMIX_TARGETS,
        icon_data_dict=icon_data_dict,
        icon_times=absolute_time_array,
        x_coords=x_coords,
        y_coords=y_coords
    )

    # ==========================================
    # 3. Export der Raster/Vektor-Frames (.webp & .geojson)
    # ==========================================
    export_data(
        da_web=da_web_ts, 
        da_brn_4326=da_brn_4326, 
        leaflet_bounds=leaflet_bounds, 
        da_mask_web=da_mask_web, 
        relative_time_array=relative_time_array
    )


