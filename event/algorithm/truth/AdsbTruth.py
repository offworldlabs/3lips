"""@file AdsbTruth.py
@author 30hours
"""

import ipaddress

import requests


def is_localhost(server):
    try:
        # Remove port if present
        host = server.split(":")[0]
        # Try to parse as IP address
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        # Not an IP, check for 'localhost' or container names that should use localhost
        return host.startswith("localhost") or host.startswith("synthetic-adsb")


def translate_localhost_to_container(server):
    """Translate localhost URLs to container names for inter-container communication."""
    # Disabled translation for host networking mode
    # Also handle synthetic-adsb as localhost since we're using host networking
    if server.startswith("synthetic-adsb"):
        return server.replace("synthetic-adsb", "localhost")
    return server


class AdsbTruth:
    """@class AdsbTruth
    @brief A class for storing ADS-B truth in the API response.
    @details Uses truth data in delay-Doppler space from an tar1090 server.
    """

    def __init__(self, seen_pos_limit):
        """@brief Constructor for the AdsbTruth class."""
        self.seen_pos_limit = seen_pos_limit

    def process(self, server):
        """@brief Store ADS-B truth for each target in LLA.
        @param server (str): The tar1090 server to get truth from.
        @return dict: Associated detections by [hex].
        """
        output = {}

        # Translate localhost to container name for inter-container communication
        translated_server = translate_localhost_to_container(server)

        # Check if server is on local network
        if is_localhost(server):
            url = "http://" + translated_server + "/data/aircraft.json"
        else:
            url = "https://" + translated_server + "/data/aircraft.json"

        print(f"Getting truth from {url}")

        # get ADSB detections
        try:
            response = requests.get(url, timeout=1)
            response.raise_for_status()
            data = response.json()
            adsb = data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            adsb = None

        # store relevant data
        if adsb:
            print(f"DEBUG: Processing {len(adsb['aircraft'])} aircraft from ADS-B data")
            # loop over aircraft
            for aircraft in adsb["aircraft"]:
                print(
                    f"DEBUG: Aircraft hex={aircraft.get('hex')}, seen_pos={aircraft.get('seen_pos')}, alt_geom={aircraft.get('alt_geom')}, flight={aircraft.get('flight')}, limit={self.seen_pos_limit}",
                )

                if (
                    aircraft.get("seen_pos") is not None
                    and aircraft.get("alt_geom")
                    and aircraft.get("flight")
                    and aircraft.get("seen_pos") < self.seen_pos_limit
                ):
                    print(f"DEBUG: Adding aircraft {aircraft['hex']} to output")
                    output[aircraft["hex"]] = {}
                    output[aircraft["hex"]]["lat"] = aircraft["lat"]
                    output[aircraft["hex"]]["lon"] = aircraft["lon"]
                    output[aircraft["hex"]]["alt"] = aircraft["alt_geom"]
                    output[aircraft["hex"]]["flight"] = aircraft["flight"]
                    output[aircraft["hex"]]["timestamp"] = (
                        adsb["now"] - aircraft["seen_pos"]
                    )
                else:
                    print(
                        f"DEBUG: Rejecting aircraft {aircraft.get('hex')} - conditions not met",
                    )
            print(f"DEBUG: Final output contains {len(output)} aircraft")
        return output
