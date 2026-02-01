"""Event loop for 3lips."""

import asyncio
import hashlib
import importlib
import json
import os
import threading
import time

import requests
from algorithm.associator.AdsbAssociator import AdsbAssociator
from algorithm.geometry.Geometry import Geometry
from algorithm.localisation.EllipseParametric import EllipseParametric
from algorithm.localisation.EllipsoidParametric import EllipsoidParametric
from algorithm.localisation.RETINASolverLocalisation import RETINASolverLocalisation
from algorithm.localisation.SphericalIntersection import SphericalIntersection
from algorithm.track.Tracker import Tracker
from algorithm.truth.AdsbTruth import AdsbTruth
from data.Ellipsoid import Ellipsoid
from dotenv import load_dotenv

from common.Message import Message

load_dotenv()
required_vars = {
    "ELLIPSE_N_SAMPLES": int,
    "ELLIPSE_THRESHOLD": int,
    "ELLIPSE_N_DISPLAY": int,
    "ELLIPSOID_N_SAMPLES": int,
    "ELLIPSOID_THRESHOLD": int,
    "ELLIPSOID_N_DISPLAY": int,
    "ADSB_T_DELETE": int,
    "THREE_LIPS_SAVE": str,
    "THREE_LIPS_T_DELETE": int,
}

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise OSError(f"Missing required environment variables: {', '.join(missing_vars)}")

nSamplesEllipse = int(os.getenv("ELLIPSE_N_SAMPLES"))
thresholdEllipse = int(os.getenv("ELLIPSE_THRESHOLD"))
nDisplayEllipse = int(os.getenv("ELLIPSE_N_DISPLAY"))
nSamplesEllipsoid = int(os.getenv("ELLIPSOID_N_SAMPLES"))
thresholdEllipsoid = int(os.getenv("ELLIPSOID_THRESHOLD"))
nDisplayEllipsoid = int(os.getenv("ELLIPSOID_N_DISPLAY"))
tDeleteAdsb = int(os.getenv("ADSB_T_DELETE"))
save = os.getenv("THREE_LIPS_SAVE").lower() == "true"
tDelete = int(os.getenv("THREE_LIPS_T_DELETE"))

tracker_config_params = {
    "verbose": os.environ.get("TRACKER_VERBOSE", "False").lower() == "true",
    "max_misses_to_delete": int(os.environ.get("TRACKER_MAX_MISSES_TO_DELETE", 5)),
    "min_hits_to_confirm": int(os.environ.get("TRACKER_MIN_HITS_TO_CONFIRM", 3)),
    "gating_euclidean_threshold_m": float(
        os.environ.get("TRACKER_GATING_EUCLIDEAN_THRESHOLD_M", 10000.0),
    ),
    "gating_mahalanobis_threshold": float(
        os.environ.get("TRACKER_GATING_MAHALANOBIS_THRESHOLD", 11.345),
    ),
    "initial_pos_uncertainty_enu_m": [
        float(x)
        for x in os.environ.get(
            "TRACKER_INITIAL_POS_UNCERTAINTY_ENU_M",
            "500.0,500.0,500.0",
        ).split(",")
    ],
    "initial_vel_uncertainty_enu_mps": [
        float(x)
        for x in os.environ.get(
            "TRACKER_INITIAL_VEL_UNCERTAINTY_ENU_MPS",
            "100.0,100.0,100.0",
        ).split(",")
    ],
    "dt_default_s": float(os.environ.get("TRACKER_DT_DEFAULT_S", 1.0)),
    "process_noise_coeff": float(os.environ.get("TRACKER_PROCESS_NOISE_COEFF", 0.1)),
    "measurement_noise_coeff": float(
        os.environ.get("TRACKER_MEASUREMENT_NOISE_COEFF", 500.0)
    ),
    "ref_lat": float(os.environ.get("MAP_LATITUDE", -34.9286)),
    "ref_lon": float(os.environ.get("MAP_LONGITUDE", 138.5999)),
    "ref_alt": float(os.environ.get("MAP_ALTITUDE", 0.0)),
}
verbose_tracker = tracker_config_params["verbose"]

api = []

associator_type = os.getenv("ASSOCIATOR_TYPE", "AdsbAssociator")
try:
    associator_module = importlib.import_module(
        f"algorithm.associator.{associator_type}",
    )
    associator_class = getattr(associator_module, associator_type)
    associator = associator_class()
except (ModuleNotFoundError, AttributeError) as e:
    print(
        f"Warning: Could not load associator '{associator_type}', defaulting to AdsbAssociator. Error: {e}"
    )
    from algorithm.associator.AdsbAssociator import AdsbAssociator

    associator = AdsbAssociator()

ellipseParametricMean = EllipseParametric("mean", nSamplesEllipse, thresholdEllipse)
ellipseParametricMin = EllipseParametric("min", nSamplesEllipse, thresholdEllipse)
ellipsoidParametricMean = EllipsoidParametric(
    "mean",
    nSamplesEllipsoid,
    thresholdEllipsoid,
)
ellipsoidParametricMin = EllipsoidParametric(
    "min",
    nSamplesEllipsoid,
    thresholdEllipsoid,
)
sphericalIntersection = SphericalIntersection()
retinaSolver = RETINASolverLocalisation()
adsbTruth = AdsbTruth(tDeleteAdsb)
saveFile = "/app/save/" + str(int(time.time())) + ".ndjson"

global_tracker = Tracker(config=tracker_config_params)

# ENU tracking system - uses MAP_LATITUDE/MAP_LONGITUDE as reference point


async def event():
    global api, save, global_tracker
    timestamp = int(time.time() * 1000)

    if not api:
        if verbose_tracker:
            print(f"{timestamp}: No active API requests. Tracker will predict only.")
        if global_tracker:
            _ = global_tracker.update_all_tracks([], timestamp)
        return

    # Collect all API request configurations for this cycle
    api_event_configs_this_cycle = [
        c for c in api if (timestamp - c.get("timestamp", 0) <= tDelete * 1000)
    ]
    print(
        f"DEBUG: Found {len(api_event_configs_this_cycle)} API configs for processing"
    )
    for i, config in enumerate(api_event_configs_this_cycle):
        print(
            f"DEBUG: Config {i}: hash={config.get('hash')}, adsb={config.get('adsb')}, timestamp={config.get('timestamp')}"
        )

    def translate_localhost_to_container(server):
        """Translate localhost URLs to container names for inter-container communication."""
        # Disabled translation for host networking mode
        return server

    radar_names = []
    for item_config in api_event_configs_this_cycle:
        if "server" in item_config and isinstance(item_config["server"], list):
            for radar_url_name in item_config["server"]:
                radar_names.append(radar_url_name)
    radar_names = list(set(radar_names))

    radar_names = [translate_localhost_to_container(name) for name in radar_names]

    radar_dict = {}
    radar_detections_url = [
        f"http://{radar_name}/api/detection" for radar_name in radar_names
    ]
    radar_detections = []
    for url in radar_detections_url:
        try:
            response = requests.get(url, timeout=1)
            response.raise_for_status()
            data = response.json()
            radar_detections.append(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            radar_detections.append(None)

    radar_config_url = [f"http://{radar_name}/api/config" for radar_name in radar_names]
    radar_config = []
    for url in radar_config_url:
        try:
            response = requests.get(url, timeout=1)
            response.raise_for_status()
            data = response.json()
            radar_config.append(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            radar_config.append(None)

    for i in range(len(radar_names)):
        radar_dict[radar_names[i]] = {
            "detection": radar_detections[i],
            "config": radar_config[i],
        }

    truth_adsb = {}
    adsb_urls = []
    for item in api_event_configs_this_cycle:
        adsb_urls.append(item["adsb"])
    adsb_urls = list(set(adsb_urls))
    print(f"DEBUG: Processing {len(adsb_urls)} unique ADS-B URLs: {adsb_urls}")
    for url in adsb_urls:
        print(f"DEBUG: Calling adsbTruth.process({url})")
        result = adsbTruth.process(url)
        print(f"DEBUG: adsbTruth.process returned: {type(result)}, content: {result}")
        truth_adsb[url] = result

    all_localised_points_for_tracker_input_this_scan = []
    processed_api_request_outputs = []
    unique_lla_points_for_tracker_keys = set()
    for item_config in api_event_configs_this_cycle:
        item_processing_start_time = time.time()
        item_radars = item_config.get("server", [])
        if not isinstance(item_radars, list):
            item_radars = [item_radars]

        # Translate localhost URLs to container names for this item too
        item_radars_translated = [
            translate_localhost_to_container(name) for name in item_radars
        ]

        radar_dict_item = {
            key: radar_dict.get(key)
            for key in item_radars_translated
            if key in radar_dict and radar_dict.get(key) is not None
        }
        if not radar_dict_item or not any(
            radar_dict_item.get(r) and radar_dict_item[r].get("config")
            for r in item_radars_translated
        ):
            print(
                f"Skipping item {item_config.get('hash')} due to missing radar data/config for its servers."
            )
            temp_output = item_config.copy()
            temp_output["timestamp_event"] = timestamp
            temp_output["error"] = "Missing radar data/config for configured servers."
            temp_output["detections_associated"] = {}
            temp_output["detections_localised"] = {}
            temp_output["ellipsoids"] = {}
            temp_output["truth"] = {}
            temp_output["time"] = 0
            processed_api_request_outputs.append(temp_output)
            continue
        # Select associator & localisation_algorithm
        localisation_id = item_config.get("localisation")
        localisation_algorithm = None
        if localisation_id == "ellipse-parametric-mean":
            localisation_algorithm = ellipseParametricMean
        elif localisation_id == "ellipse-parametric-min":
            localisation_algorithm = ellipseParametricMin
        elif localisation_id == "ellipsoid-parametric-mean":
            localisation_algorithm = ellipsoidParametricMean
        elif localisation_id == "ellipsoid-parametric-min":
            localisation_algorithm = ellipsoidParametricMin
        elif localisation_id == "spherical-intersection":
            localisation_algorithm = sphericalIntersection
        elif localisation_id == "retina-solver":
            localisation_algorithm = retinaSolver
        else:
            print(
                f"Error: Localisation algorithm '{localisation_id}' invalid for item {item_config.get('hash')}."
            )
            error_output = item_config.copy()
            error_output.update(
                {
                    "timestamp_event": timestamp,
                    "error": f"Invalid localisation: {localisation_id}",
                    "detections_associated": {},
                    "detections_localised": {},
                    "ellipsoids": {},
                    "truth": truth_adsb.get(item_config.get("adsb"), {}),
                    "time": 0,
                },
            )
            processed_api_request_outputs.append(error_output)
            continue
        # Perform item-specific association
        associated_dets = associator.process(
            item_radars_translated, radar_dict_item, timestamp
        )
        # Prepare for localisation
        associated_dets_3_radars = {
            key: value
            for key, value in associated_dets.items()
            if isinstance(value, list) and len(value) >= 3
        }
        associated_dets_2_radars = {
            key: value
            for key, value in associated_dets.items()
            if isinstance(value, list) and len(value) >= 2
        }
        input_for_localisation = (
            associated_dets_3_radars
            if localisation_id
            in [
                "ellipse-parametric-mean",
                "ellipse-parametric-min",
                "ellipsoid-parametric-mean",
                "ellipsoid-parametric-min",
                "spherical-intersection",
            ]
            else associated_dets
        )
        localised_dets_for_item = localisation_algorithm.process(
            input_for_localisation,
            radar_dict_item,
        )
        # --- Collect unique localised points for the global tracker ---
        for target_id, data_dict in localised_dets_for_item.items():
            if data_dict.get("points"):
                for point_lla in data_dict["points"]:
                    if isinstance(point_lla, list) and len(point_lla) == 3:
                        point_key_tuple = (
                            round(point_lla[0], 4),
                            round(point_lla[1], 4),
                            round(point_lla[2], 1),
                        )
                        if point_key_tuple not in unique_lla_points_for_tracker_keys:
                            unique_lla_points_for_tracker_keys.add(point_key_tuple)
                            all_localised_points_for_tracker_input_this_scan.append(
                                {
                                    "lla_position": point_lla,
                                    "timestamp_ms": timestamp,
                                    "source_api_hash": item_config.get(
                                        "hash",
                                        "unknown_item",
                                    ),
                                    "source_target_id": target_id,
                                },
                            )
                    elif verbose_tracker:
                        print(
                            f"Skipping malformed point for tracker input: {point_lla}"
                        )
        # Calculate ellipsoids for display
        ellipsoids_for_item = {}
        if localisation_id in [
            "ellipse-parametric-mean",
            "ellipse-parametric-min",
            "ellipsoid-parametric-mean",
            "ellipsoid-parametric-min",
        ]:
            if associated_dets_2_radars:
                key = next(iter(associated_dets_2_radars))
                ellipsoid_radars = []
                for radar in associated_dets_2_radars[key]:
                    ellipsoid_radars.append(radar["radar"])
                    tx_lla = [
                        radar_dict_item[radar["radar"]]["config"]["location"]["tx"][
                            "latitude"
                        ],
                        radar_dict_item[radar["radar"]]["config"]["location"]["tx"][
                            "longitude"
                        ],
                        radar_dict_item[radar["radar"]]["config"]["location"]["tx"][
                            "altitude"
                        ],
                    ]
                    rx_lla = [
                        radar_dict_item[radar["radar"]]["config"]["location"]["rx"][
                            "latitude"
                        ],
                        radar_dict_item[radar["radar"]]["config"]["location"]["rx"][
                            "longitude"
                        ],
                        radar_dict_item[radar["radar"]]["config"]["location"]["rx"][
                            "altitude"
                        ],
                    ]
                    ellipsoid = Ellipsoid(tx_lla, rx_lla, radar["radar"])
                    points = localisation_algorithm.sample(
                        ellipsoid,
                        radar["delay"] * 1000,
                        nDisplayEllipse,
                    )
                    # Convert ENU points to LLA using ellipsoid midpoint as reference
                    for i in range(len(points)):
                        lat, lon, alt = Geometry.enu2lla(
                            points[i][0],
                            points[i][1],
                            points[i][2],
                            ellipsoid.midpoint_lla[0],
                            ellipsoid.midpoint_lla[1],
                            ellipsoid.midpoint_lla[2],
                        )
                        if localisation_id in [
                            "ellipsoid-parametric-mean",
                            "ellipsoid-parametric-min",
                        ]:
                            alt = round(alt)
                        if localisation_id in [
                            "ellipse-parametric-mean",
                            "ellipse-parametric-min",
                        ]:
                            alt = 0
                        points[i] = [round(lat, 3), round(lon, 3), alt]
                    ellipsoids_for_item[radar["radar"]] = points
        item_processing_stop_time = time.time()
        output_for_this_item = item_config.copy()
        output_for_this_item["timestamp_event"] = timestamp
        output_for_this_item["truth"] = truth_adsb.get(item_config.get("adsb"), {})
        output_for_this_item["detections_associated"] = associated_dets
        output_for_this_item["detections_localised"] = localised_dets_for_item
        output_for_this_item["ellipsoids"] = ellipsoids_for_item
        output_for_this_item["time"] = (
            item_processing_stop_time - item_processing_start_time
        )
        if verbose_tracker:
            print(
                f"{timestamp}: Item {item_config.get('hash')} Method: {localisation_id}, Time: {output_for_this_item['time']:.4f}s",
                flush=True,
            )
        processed_api_request_outputs.append(output_for_this_item)

    # --- Pass 2: Update Global Tracker with all unique localised points from this scan ---
    current_system_tracks_map = {}
    if global_tracker:
        # Convert ADS-B truth data to tracker format
        all_adsb_detections_for_tracker = convert_adsb_truth_to_tracker_format(
            truth_adsb,
            timestamp,
        )

        if verbose_tracker:
            print(
                f"{timestamp}: Updating global_tracker with {len(all_localised_points_for_tracker_input_this_scan)} unique radar points and {len(all_adsb_detections_for_tracker)} ADS-B detections."
            )

        current_system_tracks_map = global_tracker.update_all_tracks(
            all_localised_points_for_tracker_input_this_scan,
            timestamp,
            adsb_detections_lla=all_adsb_detections_for_tracker,
        )
    serializable_system_tracks = [
        track.to_dict() for track in current_system_tracks_map.values()
    ]
    if verbose_tracker and serializable_system_tracks:
        print(
            f"{timestamp}: Global System Tracks ({len(serializable_system_tracks)} generated): {[t['track_id'] for t in serializable_system_tracks]}",
            flush=True,
        )

    # --- Pass 3: Augment each API request's output with the global system tracks & Manage API list ---
    final_api_list_for_this_cycle = []
    for processed_item_output in processed_api_request_outputs:
        item_hash = processed_item_output.get("hash")
        original_config = next(
            (
                item_cfg
                for item_cfg in api_event_configs_this_cycle
                if item_cfg.get("hash") == item_hash
            ),
            None,
        )
        if original_config and (
            timestamp - original_config.get("timestamp", 0) <= tDelete * 1000
        ):
            processed_item_output["system_tracks"] = serializable_system_tracks
            final_api_list_for_this_cycle.append(processed_item_output)
        elif verbose_tracker and original_config:
            print(
                f"{timestamp}: API Config {item_hash} (orig_ts: {original_config.get('timestamp', 'N/A')}) timed out. Not including in final output.",
            )
        elif verbose_tracker and not original_config:
            print(
                f"{timestamp}: Warning - Processed item {item_hash} not found in original configs for timeout check."
            )
    api = final_api_list_for_this_cycle
    if save and api:
        append_api_to_file(api)
    elif save and not api and verbose_tracker:
        print(f"{timestamp}: Save is true, but 'api' list is empty. Nothing to save.")


def convert_adsb_truth_to_tracker_format(truth_adsb, timestamp_ms):
    """Convert ADS-B truth data to tracker-compatible format.

    Args:
        truth_adsb: ADS-B truth data from adsbTruth.process()
        timestamp_ms: Current timestamp in milliseconds

    Returns:
        List of ADS-B detection dicts for tracker input
    """
    adsb_detections = []

    for url, aircraft_dict in truth_adsb.items():
        for hex_code, aircraft_data in aircraft_dict.items():
            try:
                lat = aircraft_data.get("lat")
                lon = aircraft_data.get("lon")
                alt = aircraft_data.get("alt")
                flight = aircraft_data.get("flight")
                adsb_timestamp = aircraft_data.get("timestamp", timestamp_ms / 1000)

                if lat is not None and lon is not None and alt is not None:
                    adsb_detection = {
                        "lla_position": [lat, lon, alt],
                        "timestamp_ms": int(adsb_timestamp * 1000),
                        "source_api_hash": f"adsb_{url}",
                        "source_target_id": hex_code,
                        "adsb_info": {
                            "hex": hex_code,
                            "flight": flight,
                            "url": url,
                            "original_timestamp": adsb_timestamp,
                        },
                    }
                    adsb_detections.append(adsb_detection)

            except Exception as e:
                if verbose_tracker:
                    print(
                        f"Error converting ADS-B aircraft {hex_code} to tracker format: {e}"
                    )
                continue

    if verbose_tracker and adsb_detections:
        print(
            f"{timestamp_ms}: Converted {len(adsb_detections)} ADS-B aircraft to tracker format"
        )

    return adsb_detections


async def main():
    while True:
        await event()
        await asyncio.sleep(1)


def append_api_to_file(api_object, filename=saveFile):
    if not os.path.exists(filename):
        with open(filename, "w"):
            pass

    with open(filename, "a") as json_file:
        json.dump(api_object, json_file)
        json_file.write("\n")


def short_hash(input_string, length=10):
    hash_object = hashlib.sha256(input_string.encode())
    short_hash = hash_object.hexdigest()[:length]
    return short_hash


async def callback_message_received(msg):
    global api, verbose_tracker
    timestamp_receipt = int(time.time() * 1000)
    msg_hash = short_hash(msg)
    output_for_client = {}

    existing_item = next((item for item in api if item.get("hash") == msg_hash), None)

    if existing_item:
        existing_item["timestamp"] = timestamp_receipt
        output_for_client = json.dumps(existing_item)
        if verbose_tracker:
            print(
                f"{timestamp_receipt}: Updated timestamp for existing API config: {msg_hash}"
            )
    else:
        new_api_item = {"hash": msg_hash, "timestamp": timestamp_receipt}
        try:
            url_parts = msg.split("&")
            for part in url_parts:
                key, value = part.split("=")
                if key in new_api_item:
                    if not isinstance(new_api_item[key], list):
                        new_api_item[key] = [new_api_item[key]]
                    new_api_item[key].append(value)
                else:
                    new_api_item[key] = value
            if "server" in new_api_item and not isinstance(
                new_api_item["server"], list
            ):
                new_api_item["server"] = [new_api_item["server"]]
            api.append(new_api_item)
            output_for_client = json.dumps(new_api_item)
            if verbose_tracker:
                print(
                    f"{timestamp_receipt}: Added new API config: {msg_hash} - {new_api_item}"
                )
        except ValueError as e:
            print(f"Error parsing API request message '{msg}': {e}")
            output_for_client = json.dumps(
                {"error": "Invalid API request format", "request": msg}
            )
    return output_for_client


message_api_request = Message("0.0.0.0", 6969)  # nosec B104 - intentional for Docker networking
message_api_request.set_callback_message_received(callback_message_received)

if __name__ == "__main__":
    threading.Thread(target=message_api_request.start_listener).start()
    asyncio.run(main())
