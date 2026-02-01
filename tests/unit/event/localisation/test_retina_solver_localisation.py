import os
import sys
from unittest.mock import Mock, patch

# Mock all RETINASolver dependencies before importing
sys.modules["detection_triple"] = Mock()
sys.modules["initial_guess_3det"] = Mock()
sys.modules["lm_solver_3det"] = Mock()
sys.modules["geometry"] = Mock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../event"))

from algorithm.localisation.RETINASolverLocalisation import (
    RETINASolverLocalisation,
)


class TestRETINASolverLocalisation:
    def setup_method(self):
        self.solver = RETINASolverLocalisation()
        self.sample_radar_data = {
            "radar1": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9286, "longitude": 138.5999},
                        "tx": {"latitude": -34.9286, "longitude": 138.5999},
                    },
                    "capture": {
                        "fc": 98000000,
                    },
                }
            },
            "radar2": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9300, "longitude": 138.6000},
                        "tx": {"latitude": -34.9300, "longitude": 138.6000},
                    },
                    "capture": {
                        "fc": 98000000,
                    },
                }
            },
            "radar3": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9310, "longitude": 138.6010},
                        "tx": {"latitude": -34.9310, "longitude": 138.6010},
                    },
                    "capture": {
                        "fc": 98000000,
                    },
                }
            },
        }

        self.sample_detections = {
            "target1": [
                {"radar": "radar1", "timestamp": 1000, "delay": 15.5, "doppler": 100.0},
                {"radar": "radar2", "timestamp": 1000, "delay": 16.2, "doppler": 110.0},
                {"radar": "radar3", "timestamp": 1000, "delay": 17.1, "doppler": 120.0},
            ]
        }

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_successful_localization(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
            "velocity": [10, 20, 5],
        }

        result = self.solver.process(self.sample_detections, self.sample_radar_data)

        assert "target1" in result
        assert "points" in result["target1"]
        assert len(result["target1"]["points"]) == 1
        assert result["target1"]["points"][0] == [-34.9295, 138.6005, 1000]

        mock_detection.assert_called()
        mock_triple.assert_called_once()
        mock_initial_guess.assert_called_once()
        mock_solver.assert_called_once()

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_solver_failure_handling(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = {"error": "Solver failed to converge"}

        result = self.solver.process(self.sample_detections, self.sample_radar_data)

        assert result == {}
        mock_solver.assert_called_once()

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_solver_none_result(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = None

        result = self.solver.process(self.sample_detections, self.sample_radar_data)

        assert result == {}
        mock_solver.assert_called_once()

    def test_insufficient_detections(self):
        insufficient_detections = {
            "target1": [
                {"radar": "radar1", "timestamp": 1000, "delay": 15.5, "doppler": 100.0},
                {"radar": "radar2", "timestamp": 1000, "delay": 16.2, "doppler": 110.0},
            ]
        }

        result = self.solver.process(insufficient_detections, self.sample_radar_data)

        assert result == {}

    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_exception_handling(self, mock_detection):
        mock_detection.side_effect = Exception("Test exception")

        result = self.solver.process(self.sample_detections, self.sample_radar_data)

        assert result == {}

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_detection_data_conversion(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = {"lat": -34.9295, "lon": 138.6005, "alt": 1000}

        self.solver.process(self.sample_detections, self.sample_radar_data)

        expected_detection_data = {
            "sensor_lat": -34.9286,
            "sensor_lon": 138.5999,
            "ioo_lat": -34.9286,
            "ioo_lon": 138.5999,
            "freq_mhz": 98.0,
            "timestamp": 1000,
            "bistatic_range_km": 15.5,
            "doppler_hz": 100.0,
        }

        mock_detection.assert_called()
        call_args = mock_detection.call_args_list[0][1]
        assert call_args == expected_detection_data

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_multiple_targets(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = {"lat": -34.9295, "lon": 138.6005, "alt": 1000}

        multi_target_detections = {
            "target1": self.sample_detections["target1"],
            "target2": [
                {"radar": "radar1", "timestamp": 1000, "delay": 20.5, "doppler": 200.0},
                {"radar": "radar2", "timestamp": 1000, "delay": 21.2, "doppler": 210.0},
                {"radar": "radar3", "timestamp": 1000, "delay": 22.1, "doppler": 220.0},
            ],
        }

        result = self.solver.process(multi_target_detections, self.sample_radar_data)

        assert len(result) == 2
        assert "target1" in result
        assert "target2" in result
        assert mock_solver.call_count == 2

    @patch("algorithm.localisation.RETINASolverLocalisation.solve_position_velocity_3d")
    @patch("algorithm.localisation.RETINASolverLocalisation.get_initial_guess")
    @patch("algorithm.localisation.RETINASolverLocalisation.DetectionTriple")
    @patch("algorithm.localisation.RETINASolverLocalisation.Detection")
    def test_uses_only_first_three_detections(
        self, mock_detection, mock_triple, mock_initial_guess, mock_solver
    ):
        mock_detection.return_value = Mock()
        mock_triple.return_value = Mock()
        mock_initial_guess.return_value = {
            "lat": -34.9295,
            "lon": 138.6005,
            "alt": 1000,
        }
        mock_solver.return_value = {"lat": -34.9295, "lon": 138.6005, "alt": 1000}

        extended_detections = {
            "target1": self.sample_detections["target1"]
            + [
                {"radar": "radar4", "timestamp": 1000, "delay": 18.0, "doppler": 130.0},
                {"radar": "radar5", "timestamp": 1000, "delay": 19.0, "doppler": 140.0},
            ]
        }

        result = self.solver.process(extended_detections, self.sample_radar_data)

        assert mock_detection.call_count == 3
        assert "target1" in result

    def test_empty_input(self):
        result = self.solver.process({}, self.sample_radar_data)
        assert result == {}

        result = self.solver.process(self.sample_detections, {})
        assert result == {}

    def test_missing_radar_config(self):
        detections_with_missing_radar = {
            "target1": [
                {
                    "radar": "nonexistent_radar",
                    "timestamp": 1000,
                    "delay": 15.5,
                    "doppler": 100.0,
                },
                {"radar": "radar2", "timestamp": 1000, "delay": 16.2, "doppler": 110.0},
                {"radar": "radar3", "timestamp": 1000, "delay": 17.1, "doppler": 120.0},
            ]
        }

        result = self.solver.process(
            detections_with_missing_radar, self.sample_radar_data
        )

        assert result == {}
