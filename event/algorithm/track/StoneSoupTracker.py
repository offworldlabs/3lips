from datetime import datetime

import numpy as np
from stonesoup.dataassociator.neighbour import GNNWith2DAssignment
from stonesoup.gater.distance import DistanceGater
from stonesoup.hypothesiser.distance import DistanceHypothesiser
from stonesoup.predictor.kalman import KalmanPredictor
from stonesoup.tracker.simple import MultiTargetTracker
from stonesoup.types.detection import Detection
from stonesoup.types.state import GaussianState
from stonesoup.updater.kalman import KalmanUpdater

from ..geometry.Geometry import Geometry
from ..models.MeasurementModels import create_enu_position_measurement_model
from ..models.MotionModels import create_enu_constant_velocity_model
from .Track import Track, TrackStatus


class StoneSoupTracker:
    """Stone Soup MultiTargetTracker wrapper maintaining compatibility with existing Track interface."""

    def __init__(self, config=None):
        """Initialize Stone Soup tracker with 3lips-compatible configuration."""
        self.config = {
            "max_misses_to_delete": 5,
            "min_hits_to_confirm": 3,
            "gating_mahalanobis_threshold": 1000.0,  # Very permissive gating
            "initial_pos_uncertainty_enu_m": [
                1000.0,
                1000.0,
                1000.0,
            ],  # Higher uncertainty
            "initial_vel_uncertainty_enu_mps": [
                100.0,
                100.0,
                100.0,
            ],  # Moderate velocity uncertainty
            "dt_default_s": 1.0,
            "process_noise_coeff": 0.1,  # Lower process noise
            "measurement_noise_coeff": 1000.0,  # Higher measurement noise
            "verbose": False,  # Disable debugging for normal operation
            "ref_lat": -34.9286,  # Adelaide reference latitude
            "ref_lon": 138.5999,  # Adelaide reference longitude
            "ref_alt": 0.0,  # Reference altitude
        }
        if config:
            self.config.update(config)

        # Store reference point for ENU conversions
        self.ref_lat = self.config["ref_lat"]
        self.ref_lon = self.config["ref_lon"]
        self.ref_alt = self.config["ref_alt"]

        # Initialize Stone Soup components
        self.transition_model = create_enu_constant_velocity_model(
            noise_diff_coeff=self.config["process_noise_coeff"]
        )
        self.measurement_model = create_enu_position_measurement_model(
            noise_covariance=np.diag([self.config["measurement_noise_coeff"] ** 2] * 3)
        )

        self.predictor = KalmanPredictor(self.transition_model)
        self.updater = KalmanUpdater(self.measurement_model)

        # Use Euclidean distance for simpler, more reliable gating
        from stonesoup.measures import Euclidean

        self.hypothesiser = DistanceHypothesiser(
            predictor=self.predictor,
            updater=self.updater,
            measure=Euclidean(),
            missed_distance=self.config.get("gating_euclidean_threshold_m", 5000.0),
        )

        self.data_associator = GNNWith2DAssignment(self.hypothesiser)

        # Gater for initial filtering
        self.gater = DistanceGater(
            hypothesiser=self.hypothesiser,
            measure=Euclidean(),
            gate_threshold=self.config.get("gating_euclidean_threshold_m", 5000.0),
        )

        # Initialize multi-target tracker
        self.tracker = MultiTargetTracker(
            initiator=None,  # We'll handle initiation manually
            deleter=None,  # We'll handle deletion manually
            detector=None,  # We provide detections directly
            data_associator=self.data_associator,
            updater=self.updater,
        )

        # Track management
        self.active_tracks = {}
        self.last_timestamp_ms = None

        if self.config["verbose"]:
            print(f"StoneSoupTracker initialized with config: {self.config}")
            print(
                f"ENU reference point: lat={self.ref_lat}, lon={self.ref_lon}, alt={self.ref_alt}"
            )

    def _convert_localised_detections_to_stone_soup_detections(
        self, localised_detections_lla, timestamp_ms
    ):
        """Convert 3lips detections to Stone Soup Detection objects."""
        detections = []

        for det_data in localised_detections_lla:
            try:
                lat, lon, alt = det_data["lla_position"]
                east, north, up = Geometry.lla2enu(
                    lat, lon, alt, self.ref_lat, self.ref_lon, self.ref_alt
                )

                detection = Detection(
                    state_vector=np.array([east, north, up]),
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000.0),
                    metadata=det_data,
                )
                detections.append(detection)

            except Exception as e:
                if self.config["verbose"]:
                    print(
                        f"Error converting detection to Stone Soup format: {det_data}, Error: {e}"
                    )
                continue

        return detections

    def _initiate_new_track(self, detection, status=TrackStatus.TENTATIVE):
        """Create new track from unassociated detection."""
        measurement_pos_enu = detection.state_vector.flatten()

        initial_state_vector = np.concatenate([measurement_pos_enu, np.zeros(3)])

        pos_uncertainty = np.array(self.config["initial_pos_uncertainty_enu_m"])
        vel_uncertainty = np.array(self.config["initial_vel_uncertainty_enu_mps"])

        initial_covariance = np.block(
            [
                [np.diag(pos_uncertainty**2), np.zeros((3, 3))],
                [np.zeros((3, 3)), np.diag(vel_uncertainty**2)],
            ]
        )

        initial_state = GaussianState(
            state_vector=initial_state_vector,
            covar=initial_covariance,
            timestamp=detection.timestamp,
        )

        metadata = detection.metadata if hasattr(detection, "metadata") else {}
        adsb_info = metadata.get("adsb_info", None)

        new_track = Track(
            initial_detection=metadata,
            timestamp_ms=int(detection.timestamp.timestamp() * 1000),
            status=status,
            adsb_info=adsb_info,
        )

        # Store reference point in track for later conversion
        new_track.ref_lat = self.ref_lat
        new_track.ref_lon = self.ref_lon
        new_track.ref_alt = self.ref_alt

        new_track.append(initial_state)
        new_track.state_vector = initial_state_vector
        new_track.covariance_matrix = initial_covariance

        self.active_tracks[new_track.id] = new_track

        if self.config["verbose"]:
            track_type = (
                "ADS-B confirmed"
                if status == TrackStatus.CONFIRMED
                else "radar tentative"
            )
            print(
                f"Initiated new {track_type} track: {new_track.id} at ENU {measurement_pos_enu}"
            )

        return new_track

    def _manage_track_lifecycle(self):
        """Update track statuses and delete old tracks."""
        tracks_to_delete = []

        for track_id, track in self.active_tracks.items():
            # Promote tentative to confirmed
            if (
                track.status == TrackStatus.TENTATIVE
                and track.hits >= self.config["min_hits_to_confirm"]
            ):
                track.status = TrackStatus.CONFIRMED
                if self.config["verbose"]:
                    print(f"Track {track_id} confirmed.")

            # Delete tracks with too many misses
            if track.misses > self.config["max_misses_to_delete"]:
                tracks_to_delete.append(track_id)
                if self.config["verbose"]:
                    print(
                        f"Track {track_id} marked for deletion (misses: {track.misses})."
                    )

        for track_id in tracks_to_delete:
            if track_id in self.active_tracks:
                del self.active_tracks[track_id]
                if self.config["verbose"]:
                    print(f"Deleted Track {track_id}.")

    def update_all_tracks(
        self,
        all_localised_detections_lla,
        current_timestamp_ms,
        adsb_detections_lla=None,
    ):
        """Main entry point compatible with existing Tracker interface."""
        if self.config["verbose"]:
            print(
                f"[STONE_SOUP] update_all_tracks called with {len(all_localised_detections_lla)} detections, {len(self.active_tracks)} existing tracks"
            )

        if self.last_timestamp_ms is None:
            self.last_timestamp_ms = current_timestamp_ms - (
                self.config["dt_default_s"] * 1000
            )

        dt_seconds = (current_timestamp_ms - self.last_timestamp_ms) / 1000.0
        if dt_seconds <= 0:
            if self.config["verbose"]:
                print(
                    f"Warning: dt_seconds is not positive ({dt_seconds}). Using default: {self.config['dt_default_s']}s"
                )
            dt_seconds = self.config["dt_default_s"]

        self.last_timestamp_ms = current_timestamp_ms
        current_time = datetime.fromtimestamp(current_timestamp_ms / 1000.0)

        # Convert detections to Stone Soup format
        radar_detections = self._convert_localised_detections_to_stone_soup_detections(
            all_localised_detections_lla, current_timestamp_ms
        )

        adsb_detections = []
        if adsb_detections_lla:
            adsb_detections = (
                self._convert_localised_detections_to_stone_soup_detections(
                    adsb_detections_lla, current_timestamp_ms
                )
            )

        for detection in adsb_detections:
            associated = False

            for track_id, track in self.active_tracks.items():
                if track.states and len(track.states) > 0:
                    last_state = track.states[-1]

                    predicted_state = self.predictor.predict(
                        last_state, timestamp=current_time
                    )

                    try:
                        gated_detections = self.gater.gate_state(
                            [detection], predicted_state
                        )
                        if gated_detections:
                            updated_state = self.updater.update(
                                prediction=predicted_state, detection=detection
                            )

                            track.append(updated_state)
                            track.state_vector = updated_state.state_vector
                            track.covariance_matrix = updated_state.covar
                            track.update_custom(
                                detection.metadata
                                if hasattr(detection, "metadata")
                                else {}
                            )
                            track.increment_age()

                            associated = True
                            if self.config["verbose"]:
                                adsb_hex = (
                                    detection.metadata.get("adsb_info", {}).get(
                                        "hex", "unknown"
                                    )
                                    if hasattr(detection, "metadata")
                                    else "unknown"
                                )
                                print(
                                    f"Updated track {track_id} with ADS-B detection from aircraft {adsb_hex}"
                                )
                            break
                    except Exception as e:
                        if self.config["verbose"]:
                            print(
                                f"Error in ADS-B association for track {track_id}: {e}"
                            )
                        continue

            if not associated:
                self._initiate_new_track(detection, status=TrackStatus.CONFIRMED)

        if radar_detections:
            track_states = []
            track_ids = []

            for track_id, track in self.active_tracks.items():
                if hasattr(track, "states") and track.states and len(track.states) > 0:
                    last_state = track.states[-1]
                    try:
                        from stonesoup.types.state import GaussianState

                        dt = (current_time - last_state.timestamp).total_seconds()

                        state_vec = last_state.state_vector.copy()
                        state_vec[0] += state_vec[3] * dt
                        state_vec[1] += state_vec[4] * dt
                        state_vec[2] += state_vec[5] * dt

                        covar = last_state.covar.copy()
                        process_noise = self.config["process_noise_coeff"] * dt
                        covar[0, 0] += process_noise**2
                        covar[1, 1] += process_noise**2
                        covar[2, 2] += process_noise**2

                        predicted_state = GaussianState(
                            state_vector=state_vec, covar=covar, timestamp=current_time
                        )

                        track_states.append(predicted_state)
                        track_ids.append(track_id)
                    except Exception as e:
                        if self.config["verbose"]:
                            print(f"Error predicting track {track_id}: {e}")
                        continue

            if track_states:
                if self.config["verbose"]:
                    print(
                        f"[STONE_SOUP] Starting data association with {len(track_states)} tracks and {len(radar_detections)} detections"
                    )

                associated_pairs = []
                unassociated_tracks = list(track_states)
                unassociated_detections = list(radar_detections)

                gating_threshold = self.config.get(
                    "gating_euclidean_threshold_m", 5000.0
                )

                for i, track_state in enumerate(track_states):
                    track_id = track_ids[i]
                    track_pos = track_state.state_vector[:3].flatten()

                    best_detection = None
                    best_distance = float("inf")

                    for detection in radar_detections:
                        detection_pos = detection.state_vector.flatten()
                        distance = np.linalg.norm(track_pos - detection_pos)

                        if distance < gating_threshold and distance < best_distance:
                            best_detection = detection
                            best_distance = distance

                    if best_detection is not None:
                        associated_pairs.append((track_state, best_detection))
                        if track_state in unassociated_tracks:
                            unassociated_tracks.remove(track_state)
                        if best_detection in unassociated_detections:
                            unassociated_detections.remove(best_detection)

                        if self.config["verbose"]:
                            print(
                                f"Associated track {track_id} with detection at distance {best_distance:.2f}m"
                            )

                for track_state, detection in associated_pairs:
                    track_idx = track_states.index(track_state)
                    track_id = track_ids[track_idx]
                    track = self.active_tracks[track_id]

                    if self.config["verbose"]:
                        print(f"Associating detection to track {track_id}")

                    try:
                        updated_state = self.updater.update(track_state, detection)
                    except TypeError:
                        from stonesoup.types.state import GaussianState

                        detection_pos = detection.state_vector.flatten()
                        current_vel = track_state.state_vector[3:6].flatten()

                        updated_state_vector = np.concatenate(
                            [detection_pos, current_vel]
                        )

                        updated_state = GaussianState(
                            state_vector=updated_state_vector.reshape(-1, 1),
                            covar=track_state.covar.copy(),
                            timestamp=current_time,
                        )

                    track.append(updated_state)
                    track.state_vector = updated_state.state_vector
                    track.covariance_matrix = updated_state.covar
                    track.update_custom(
                        detection.metadata if hasattr(detection, "metadata") else {}
                    )
                    track.increment_age()

                for track_state in unassociated_tracks:
                    if track_state in track_states:
                        track_idx = track_states.index(track_state)
                        track_id = track_ids[track_idx]
                        track = self.active_tracks[track_id]

                        if self.config["verbose"]:
                            print(f"Track {track_id} unassociated, predicting...")

                        predicted_state = self.predictor.predict(
                            track.states[-1], timestamp=current_time
                        )
                        track.append(predicted_state)
                        track.state_vector = predicted_state.state_vector
                        track.covariance_matrix = predicted_state.covar
                        track.increment_misses()
                        track.increment_age()

                for detection in unassociated_detections:
                    if self.config["verbose"]:
                        print("Creating new track for unassociated detection")
                    self._initiate_new_track(detection, status=TrackStatus.TENTATIVE)
            else:
                for detection in radar_detections:
                    self._initiate_new_track(detection, status=TrackStatus.TENTATIVE)
        else:
            for track_id, track in self.active_tracks.items():
                if track.states and len(track.states) > 0:
                    try:
                        predicted_state = self.predictor.predict(
                            track.states[-1], timestamp=current_time
                        )
                        track.append(predicted_state)
                        track.state_vector = predicted_state.state_vector
                        track.covariance_matrix = predicted_state.covar
                        track.increment_misses()
                        track.increment_age()
                    except Exception as e:
                        if self.config["verbose"]:
                            print(f"Error predicting track {track_id}: {e}")

        self._manage_track_lifecycle()

        if self.config["verbose"]:
            self._log_all_track_states(current_timestamp_ms)

        return self.active_tracks.copy()

    def _log_all_track_states(self, timestamp_ms):
        """Log detailed state information for all active tracks."""
        if not self.active_tracks:
            print(f"[STONE_SOUP_TRACKER {timestamp_ms}] No active tracks")
            return

        print(
            f"[STONE_SOUP_TRACKER {timestamp_ms}] === TRACK SUMMARY ({len(self.active_tracks)} active) ==="
        )

        for track_id, track in self.active_tracks.items():
            pos_str = "N/A"
            vel_str = "N/A"

            if track.state_vector is not None and len(track.state_vector) >= 6:
                pos_str = f"[{track.state_vector[0]:.1f}, {track.state_vector[1]:.1f}, {track.state_vector[2]:.1f}]"
                vel_str = f"[{track.state_vector[3]:.1f}, {track.state_vector[4]:.1f}, {track.state_vector[5]:.1f}]"

            status_icon = "🎯" if track.status == TrackStatus.CONFIRMED else "❓"
            flight_info = "radar"

            if track.adsb_info:
                flight_info = track.adsb_info.get(
                    "flight", track.adsb_info.get("hex", "adsb")
                )
                status_icon = "✈️"

            print(
                f"  {status_icon}  {track_id} ({flight_info}) - {track.status.name} - Pos: {pos_str} - Vel: {vel_str} - H:{track.hits} M:{track.misses} A:{track.age_scans}"
            )

        print(f"[STONE_SOUP_TRACKER {timestamp_ms}] === END TRACK SUMMARY ===")
