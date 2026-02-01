from enum import Enum, auto

import numpy as np
from stonesoup.types.track import Track as StoneSoupTrack

from ..geometry.Geometry import Geometry


# Define track status as an Enum
class TrackStatus(Enum):
    TENTATIVE = auto()
    CONFIRMED = auto()
    COASTING = auto()
    DELETED = auto()


class Track(StoneSoupTrack):
    """Extension of Stone-Soup's Track to add custom fields and logic for 3lips."""

    def __init__(
        self,
        *args,
        status=TrackStatus.TENTATIVE,
        filter_obj=None,
        adsb_info=None,
        last_chi_squared=None,
        **kwargs,
    ):
        print(
            f"[TRACK] __init__ called with status: {status}, adsb_info: {adsb_info is not None}",
        )
        # Remove custom fields before calling super().__init__
        custom_fields = [
            "initial_detection",
            "status",
            "filter_obj",
            "adsb_info",
            "last_chi_squared",
            "timestamp_ms",
            "initial_state",
            "initial_covariance",
        ]
        for field in custom_fields:
            kwargs.pop(field, None)
        super().__init__(*args, **kwargs)
        # Custom fields
        self.status = status
        self.filter = (
            filter_obj  # Placeholder for a filter object (e.g., KalmanFilter instance)
        )
        self.adsb_info = adsb_info  # To store associated ADS-B data if available
        self.last_chi_squared = (
            last_chi_squared  # Store chi-squared from last update for gating/quality
        )
        self.hits = 1  # Number of detections successfully associated with this track
        self.misses = (
            0  # Number of consecutive times this track was not updated with a detection
        )
        self.age_scans = 1  # Number of scans this track has existed for
        self.associated_detections_history = []  # Detections that formed/updated this track

        # Initialize state tracking properties
        self.state_vector = None
        self.covariance_matrix = None
        self.timestamp_update_ms = None

        # Initialize ENU reference point (will be set by tracker)
        self.ref_lat = None
        self.ref_lon = None
        self.ref_alt = None

        if adsb_info:
            print(
                f"[TRACK] Created {status.name} track {self.id} for ADS-B aircraft {adsb_info.get('hex', 'unknown')}",
            )
        else:
            print(f"[TRACK] Created {status.name} track {self.id} for radar detection")

    def update(self, detection, timestamp_ms, new_state, new_covariance):
        """Update the track's state, covariance, and history. Compatible with Tracker's update call."""
        from datetime import datetime

        from stonesoup.types.state import State

        old_pos = self.state_vector[:3] if self.state_vector is not None else None
        new_pos = new_state[:3] if new_state is not None else None

        print(
            f"[TRACK] Track {self.id} updated: Old pos: {old_pos}, New pos: {new_pos}, Status: {self.status.name}",
        )

        # Update state vector and covariance
        self.state_vector = new_state
        self.covariance_matrix = new_covariance
        self.timestamp_update_ms = timestamp_ms

        # Create a new State object and append to states list for to_dict() compatibility
        new_state_obj = State(
            state_vector=new_state,
            timestamp=datetime.fromtimestamp(timestamp_ms / 1000.0),
        )
        if hasattr(new_state_obj, "covar"):
            new_state_obj.covar = new_covariance
        self.append(new_state_obj)

        # Update custom fields/history
        self.update_custom(detection)

    def update_custom(
        self,
        detection,
        status=None,
        adsb_info=None,
        last_chi_squared=None,
    ):
        """Update custom fields after a new detection is associated."""
        self.associated_detections_history.append(detection)
        self.hits += 1
        self.misses = 0

        if status is not None:
            old_status = self.status
            self.status = status
            if old_status != status:
                print(
                    f"[TRACK] Track {self.id} status changed: {old_status.name} -> {status.name}",
                )

        if adsb_info is not None:
            self.adsb_info = adsb_info
        if last_chi_squared is not None:
            self.last_chi_squared = last_chi_squared

        # Check for status promotion
        if self.status == TrackStatus.TENTATIVE and self.hits > 3:
            old_status = self.status
            self.status = TrackStatus.CONFIRMED
            print(
                f"[TRACK] Track {self.id} promoted: {old_status.name} -> {self.status.name} (hits: {self.hits})",
            )

    def increment_misses(self):
        """Increments the miss counter and updates status if needed."""
        self.misses += 1
        print(
            f"[TRACK] Track {self.id} missed detection (misses: {self.misses}, status: {self.status.name})",
        )

        if self.status == TrackStatus.CONFIRMED and self.misses > 3:
            old_status = self.status
            self.status = TrackStatus.COASTING
            print(
                f"[TRACK] Track {self.id} status changed: {old_status.name} -> {self.status.name} (misses: {self.misses})",
            )

    def increment_age(self):
        """Increments the age of the track (in terms of scans/updates)."""
        self.age_scans += 1

    def get_position_lla(self):
        """Returns the track's current position in LLA (Latitude, Longitude, Altitude).
        Converts from internal ENU state to LLA using reference point.
        """
        if self.states and len(self.states[-1].state_vector) >= 3:
            sv = self.states[-1].state_vector
            # Convert from ENU to LLA if reference point is available
            if self.ref_lat is not None:
                east, north, up = sv[0], sv[1], sv[2]
                lat, lon, alt = Geometry.enu2lla(
                    east, north, up, self.ref_lat, self.ref_lon, self.ref_alt
                )
                return (lat, lon, alt)
            else:
                # Fallback if no reference point (shouldn't happen)
                return (sv[0], sv[1], sv[2])
        return None

    def to_dict(self):
        """Returns a dictionary representation of the track, suitable for JSON serialization."""
        # Get the most recent state vector and convert ENU to LLA for frontend
        current_state_lla = None
        if self.states:
            state_vector = self.states[-1].state_vector
            # Flatten nested arrays to a simple list
            if hasattr(state_vector, "flatten"):
                state_enu = state_vector.flatten()
            else:
                state_enu = np.array(state_vector)

            if len(state_enu) >= 3 and self.ref_lat is not None:
                # Convert ENU position to LLA for frontend
                east, north, up = state_enu[0], state_enu[1], state_enu[2]
                lat, lon, alt = Geometry.enu2lla(
                    east, north, up, self.ref_lat, self.ref_lon, self.ref_alt
                )

                # Create LLA state vector (position + velocity in ENU frame)
                if len(state_enu) >= 6:
                    # For velocity, we keep ENU values as they represent rates in local frame
                    current_state_lla = [
                        lat,
                        lon,
                        alt,
                        state_enu[3],  # velocity east
                        state_enu[4],  # velocity north
                        state_enu[5],  # velocity up
                    ]
                else:
                    current_state_lla = [lat, lon, alt]
            else:
                # Fallback if no reference point (shouldn't happen)
                current_state_lla = state_enu.tolist()

        return {
            "track_id": self.id,
            "status": self.status.name
            if hasattr(self.status, "name")
            else str(self.status),
            "current_state_vector": current_state_lla,
            "hits": self.hits,
            "misses": self.misses,
            "age_scans": self.age_scans,
            "adsb_info": self.adsb_info,
            "history_len": len(self.states),
        }

    def __repr__(self):
        pos = self.states[-1].state_vector[:3] if self.states else None
        return f"Track(ID: {self.id}, Status: {self.status}, Pos: {pos}, Hits: {self.hits}, Misses: {self.misses})"

    def predict(self, dt_seconds):
        """Predict the track's state forward in time using a simple constant velocity model."""
        # Get current state from either states list or direct state_vector
        if self.states and len(self.states) > 0:
            current_state = self.states[-1].state_vector
            current_cov = getattr(self.states[-1], "covar", np.eye(6) * 100)
        elif self.state_vector is not None:
            current_state = self.state_vector
            current_cov = (
                self.covariance_matrix
                if self.covariance_matrix is not None
                else np.eye(6) * 100
            )
        else:
            # No state to predict from
            return

        if len(current_state) >= 6:  # Position and velocity
            # Simple constant velocity prediction
            F = np.array(
                [
                    [1, 0, 0, dt_seconds, 0, 0],
                    [0, 1, 0, 0, dt_seconds, 0],
                    [0, 0, 1, 0, 0, dt_seconds],
                    [0, 0, 0, 1, 0, 0],
                    [0, 0, 0, 0, 1, 0],
                    [0, 0, 0, 0, 0, 1],
                ],
            )

            # Predict state
            predicted_state = F @ current_state

            # Simple process noise (Q matrix)
            q = 0.1  # Process noise variance
            Q = (
                np.array(
                    [
                        [dt_seconds**4 / 4, 0, 0, dt_seconds**3 / 2, 0, 0],
                        [0, dt_seconds**4 / 4, 0, 0, dt_seconds**3 / 2, 0],
                        [0, 0, dt_seconds**4 / 4, 0, 0, dt_seconds**3 / 2],
                        [dt_seconds**3 / 2, 0, 0, dt_seconds**2, 0, 0],
                        [0, dt_seconds**3 / 2, 0, 0, dt_seconds**2, 0],
                        [0, 0, dt_seconds**3 / 2, 0, 0, dt_seconds**2],
                    ],
                )
                * q
            )

            # Predict covariance
            predicted_cov = F @ current_cov @ F.T + Q

        elif len(current_state) == 3:
            predicted_state = np.concatenate([current_state, np.zeros(3)])
            predicted_cov = np.eye(6) * 100  # Default uncertainty
        else:
            predicted_state = current_state.copy()
            predicted_cov = current_cov * 1.1  # Increase uncertainty slightly

        # Update internal state
        self.state_vector = predicted_state
        self.covariance_matrix = predicted_cov
