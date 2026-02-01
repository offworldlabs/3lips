"""@file AdsbAssociator.py
@author 30hours
"""

import math
import os

import requests

from .Associator import Associator


class AdsbAssociator(Associator):
    """@class AdsbAssociator
    @brief A class for associating detections of the same target.
    @details First associate ADS-B truth with each radar detection.
    Then associate over multiple radars.
    @see blah2 at https://github.com/30hours/blah2.
    Uses truth data in delay-Doppler space from an adsb2dd server.
    @see adsb2dd at https://github.com/30hours/adsb2dd.
    @todo Add adjustable window for associating truth/detections.
    """

    def __init__(self):
        """@brief Constructor for the AdsbAssociator class."""

    def process(self, radar_list, radar_data, timestamp):
        """@brief Associate detections from 2+ radars.
        @param radar_list (list): List of radars to associate.
        @param radar_data (dict): Radar data for list of radars.
        @param timestamp (int): Timestamp to compute delays at (ms).
        @return dict: Associated detections by [hex][radar].
        """
        assoc_detections_radar = []

        for radar in radar_list:
            valid_config = radar_data[radar]["config"] is not None
            valid_detection = radar_data[radar]["detection"] is not None
            if valid_config and valid_detection:
                # get URL for adsb2truth
                url = self.generate_api_url(radar, radar_data[radar])
                print(f"🔗 Generated URL: {url}")

                # get ADSB detections
                try:
                    response = requests.get(url, timeout=1)
                    response.raise_for_status()
                    data = response.json()
                    adsb_detections = data
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching data from {url}: {e}")
                    adsb_detections = None
                    continue

                # associate radar and truth
                result = self.process_1_radar(
                    radar,
                    radar_data[radar]["detection"],
                    adsb_detections,
                    timestamp,
                    radar_data[radar]["config"]["capture"]["fc"],
                )
                assoc_detections_radar.append(result)

        # associate detections between radars
        output = {}
        for entry in assoc_detections_radar:
            for key, value in entry.items():
                if key not in output:
                    output[key] = [value]
                else:
                    output[key].append(value)
        # output = {key: values for key, values in output.items() if len(values) > 1}

        return output

    def process_1_radar(self, radar, radar_detections, adsb_detections, timestamp, fc):
        """@brief Associate detections between 1 radar/truth pair.
        @details Output 1 detection per truth point.
        @param radar (str): Name of radar to process.
        @param radar_detections (dict): blah2 radar detections.
        @param adsb_detections (dict): adsb2dd truth detections.
        @return dict: Associated detections.
        """
        assoc_detections = {}
        distance_window = 100

        for aircraft in adsb_detections:
            if "delay" in radar_detections:
                if (
                    "delay" in adsb_detections[aircraft]
                    and len(radar_detections["delay"]) >= 1
                ):
                    # Convert all delays/dopplers to float for closest_point
                    radar_delays = [float(x) for x in radar_detections["delay"]]
                    radar_dopplers = [float(x) for x in radar_detections["doppler"]]
                    adsb_delay = float(adsb_detections[aircraft]["delay"])
                    adsb_doppler = float(adsb_detections[aircraft]["doppler"])
                    # extrapolate delay to current time
                    # TODO extrapolate Doppler too
                    for i in range(len(radar_detections["delay"])):
                        delta_t = (timestamp - radar_detections["timestamp"]) / 1000
                        delay = (
                            1000 * float(radar_detections["delay"][i])
                            + (
                                -float(radar_detections["doppler"][i])
                                * (299792458 / fc)
                            )
                            * delta_t
                        ) / 1000
                        radar_detections["delay"][i] = delay
                    # distance from aircraft to all detections
                    closest_point, distance = self.closest_point(
                        adsb_delay,
                        adsb_doppler,
                        radar_delays,
                        radar_dopplers,
                    )
                    if distance < distance_window:
                        print(f"✅ ASSOCIATION SUCCESS: {aircraft} on {radar}, distance={distance:.3f}")
                        assoc_detections[aircraft] = {
                            "radar": radar,
                            "delay": closest_point[0],
                            "doppler": closest_point[1],
                            "timestamp": adsb_detections[aircraft]["timestamp"],
                        }
                    else:
                        print(f"❌ ASSOCIATION FAIL: {aircraft} on {radar}, distance={distance:.3f} > {distance_window}")

        return assoc_detections

    def generate_api_url(self, radar, radar_data):
        """@brief Generate an adsb2dd API endpoint for each radar.
        @see adsb2dd at https://github.com/30hours/adsb2dd.
        @param radar (str): Radar to run adsb2dd.
        @param radar_data (dict): Radar data for this radar.
        @return str: adsb2dd API for radar.
        """
        rx_lat = radar_data["config"]["location"]["rx"]["latitude"]
        rx_lon = radar_data["config"]["location"]["rx"]["longitude"]
        rx_alt = radar_data["config"]["location"]["rx"]["altitude"]
        tx_lat = radar_data["config"]["location"]["tx"]["latitude"]
        tx_lon = radar_data["config"]["location"]["tx"]["longitude"]
        tx_alt = radar_data["config"]["location"]["tx"]["altitude"]
        fc = radar_data["config"]["capture"]["fc"]

        adsb = radar_data["config"]["truth"]["adsb"]["tar1090"]
        
        # Translate localhost URLs to container names for adsb2dd
        original_adsb = str(adsb)
        adsb = str(adsb).replace("localhost:5001", "synthetic-adsb-test:5001")
        adsb = str(adsb).replace("//localhost:5001", "//synthetic-adsb-test:5001")
        if original_adsb != adsb:
            print(f"📡 Translated ADS-B URL: {original_adsb} → {adsb}")

        api_url = os.environ.get("ADSB2DD_API_URL", "http://adsb2dd.30hours.dev/api/dd")
        if not api_url.startswith("http://") and not api_url.startswith("https://"):
            api_url = "http://" + api_url

        api_query = (
            api_url
            + "?rx="
            + str(rx_lat)
            + ","
            + str(rx_lon)
            + ","
            + str(rx_alt)
            + "&tx="
            + str(tx_lat)
            + ","
            + str(tx_lon)
            + ","
            + str(tx_alt)
            + "&fc="
            + str(fc / 1000000)
            + "&server="
            + (str(adsb) if str(adsb).startswith("http") else "http://" + str(adsb))
        )

        return api_query

    def closest_point(self, x1, y1, x_coords, y_coords):
        x1, y1 = float(x1), float(y1)
        x_coords = [float(x) for x in x_coords]
        y_coords = [float(y) for y in y_coords]

        distances = [
            math.sqrt((x - x1) ** 2 + (y - y1) ** 2) for x, y in zip(x_coords, y_coords)
        ]
        min_distance_index = distances.index(min(distances))

        closest_x = x_coords[min_distance_index]
        closest_y = y_coords[min_distance_index]
        distance = distances[min_distance_index]

        return [closest_x, closest_y], distance
