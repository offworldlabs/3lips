"""@file api.py
@brief API for 3lips.
@author 30hours
"""

import json
import os

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
)

from common.Message import Message

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize configuration from environment variables
radar_data = []
radar_names = os.getenv("RADAR_NAMES", "")
radar_urls = os.getenv("RADAR_URLS", "")

if radar_names and radar_urls:
    radar_names_list = [name.strip() for name in radar_names.split(",") if name.strip()]
    radar_urls_list = [url.strip() for url in radar_urls.split(",") if url.strip()]
    if len(radar_names_list) != len(radar_urls_list):
        print(
            f"[ERROR] Number of RADAR_NAMES ({len(radar_names_list)}) does not match RADAR_URLS ({len(radar_urls_list)})",
            flush=True,
        )
    else:
        for name, url in zip(radar_names_list, radar_urls_list):
            radar_data.append({"name": name, "url": url})
        radar_list_str = [f"{r['name']}@{r['url']}" for r in radar_data]
        print(f"[INFO] Loaded {len(radar_data)} radars: {radar_list_str}", flush=True)
else:
    print("[WARNING] RADAR_NAMES or RADAR_URLS not set or empty.", flush=True)

map_data = {
    "location": {
        "latitude": float(os.getenv("MAP_LATITUDE", -34.9286)),
        "longitude": float(os.getenv("MAP_LONGITUDE", 138.5999)),
    },
    "center_width": int(os.getenv("MAP_CENTER_WIDTH", 50000)),
    "center_height": int(os.getenv("MAP_CENTER_HEIGHT", 40000)),
    "tar1090": os.getenv("TAR1090_URL", "localhost:5001"),
}

# store state data
servers = []
for radar in radar_data:
    if radar["name"] and radar["url"]:
        servers.append({"name": radar["name"], "url": radar["url"]})

associators = [{"name": "ADSB Associator", "id": "adsb-associator"}]

localisations = [
    {"name": "Ellipse Parametric (Mean)", "id": "ellipse-parametric-mean"},
    {"name": "Ellipse Parametric (Min)", "id": "ellipse-parametric-min"},
    {"name": "Ellipsoid Parametric (Mean)", "id": "ellipsoid-parametric-mean"},
    {"name": "Ellipsoid Parametric (Min)", "id": "ellipsoid-parametric-min"},
    {"name": "Spherical Intersection", "id": "spherical-intersection"},
    {"name": "RETINA Solver", "id": "retina-solver"},
]

adsbs = [
    {"name": map_data["tar1090"], "url": map_data["tar1090"]},
    {"name": "synthetic-adsb:5001", "url": "synthetic-adsb:5001"},
    {"name": "None", "url": ""},
]

# store valid ids
valid = {}
valid["servers"] = [item["url"] for item in servers]
valid["associators"] = [item["id"] for item in associators]
valid["localisations"] = [item["id"] for item in localisations]
valid["adsbs"] = [item["url"] for item in adsbs]


# message received callback
async def callback_message_received(msg):
    print(f"Callback: Received message in main.py: {msg}", flush=True)


# init messaging
message_api_request = Message("127.0.0.1", 6969)


@app.route("/")
def index():
    app_config = {
        "map": {
            "location": {
                "latitude": float(os.getenv("MAP_LATITUDE", -34.9286)),
                "longitude": float(os.getenv("MAP_LONGITUDE", 138.5999)),
            },
            "center_width": int(os.getenv("MAP_CENTER_WIDTH", 50000)),
            "center_height": int(os.getenv("MAP_CENTER_HEIGHT", 40000)),
            "tile_server": {
                "esri": os.getenv(
                    "TILE_SERVER_ESRI",
                    "tile.datr.dev/data/esri-adelaide/",
                ),
                "mapbox_streets": os.getenv(
                    "TILE_SERVER_MAPBOX_STREETS",
                    "tile.datr.dev/data/mapbox-streets-v11/",
                ),
                "mapbox_dark": os.getenv(
                    "TILE_SERVER_MAPBOX_DARK",
                    "tile.datr.dev/data/mapbox-dark-v10/",
                ),
                "opentopomap": os.getenv(
                    "TILE_SERVER_OPENTOPOMAP",
                    "tile.datr.dev/data/opentopomap/",
                ),
            },
            "tar1090": os.getenv("TAR1090_URL", "localhost:5001"),
        },
    }
    return render_template(
        "index.html",
        servers=servers,
        associators=associators,
        localisations=localisations,
        adsbs=adsbs,
        app_config=app_config,
        config_json=json.dumps(app_config),
    )


# serve static files from the /app/public folder
@app.route("/public/<path:file>")
def serve_static(file):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    public_folder = os.path.join(base_dir, "public")
    return send_from_directory(public_folder, file)


@app.route("/api")
def api():
    api = request.query_string.decode("utf-8")
    # input protection
    servers_api = request.args.getlist("server")
    associators_api = request.args.getlist("associator")
    localisations_api = request.args.getlist("localisation")
    adsbs_api = request.args.getlist("adsb")
    if not all(item in valid["servers"] for item in servers_api):
        return "Invalid server"
    if not all(item in valid["associators"] for item in associators_api):
        return "Invalid associator"
    if not all(item in valid["localisations"] for item in localisations_api):
        return "Invalid localisation"
    if not all(item in valid["adsbs"] for item in adsbs_api):
        return "Invalid ADSB"
    # send to event handler
    try:
        print(f"Sending API request: {api}", flush=True)
        reply_chunks = message_api_request.send_message(api)
        print("Got reply_chunks generator", flush=True)
        reply = "".join(reply_chunks)
        print(f"Final reply: {reply}", flush=True)
        return reply
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(f"Exception occurred: {e}", flush=True)
        print(f"Traceback: {error_trace}", flush=True)
        reply = "Exception: " + str(e)
        return jsonify(error=reply), 500


@app.route("/map/<path:file>")
def serve_map(file):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    public_folder = os.path.join(base_dir, "map")
    return send_from_directory(public_folder, file)


# handle /cesium/ specifically
@app.route("/cesium/")
def serve_cesium_index():
    return redirect("/cesium/index.html")


@app.route("/cesium/<path:file>")
def serve_cesium_content(file):
    apache_url = "http://127.0.0.1:8080/" + file
    try:
        response = requests.get(apache_url, timeout=10)
        if response.status_code == 200:
            return Response(
                response.content,
                content_type=response.headers["content-type"],
            )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching content from Apache server: {e}")
    return Response(
        "Error fetching content from Apache server",
        status=500,
        content_type="text/plain",
    )


if __name__ == "__main__":
    app.run()
