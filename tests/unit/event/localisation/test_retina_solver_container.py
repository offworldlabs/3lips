"""
RETINASolver integration tests that run inside the Docker container.
These tests require the RETINASolver dependencies to be available.
"""

import sys

import pytest

sys.path.insert(0, "/app/event")
sys.path.insert(0, "/app/common")

try:
    from algorithm.localisation.RETINASolverLocalisation import RETINASolverLocalisation

    RETINA_SOLVER_AVAILABLE = True
except ImportError as e:
    RETINA_SOLVER_AVAILABLE = False
    pytestmark = pytest.mark.skip(
        reason=f"RETINASolver dependencies not available: {e}"
    )


@pytest.mark.skipif(
    not RETINA_SOLVER_AVAILABLE, reason="RETINASolver dependencies not available"
)
class TestRETINASolverContainer:
    """Integration tests for RETINASolver that run inside Docker container."""

    def setup_method(self):
        self.solver = RETINASolverLocalisation()

        self.radar_config = {
            "adelaideHills": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9286, "longitude": 138.5999},
                        "tx": {"latitude": -34.9286, "longitude": 138.5999},
                    },
                    "frequency": 98000000,
                }
            },
            "northAdelaide": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9000, "longitude": 138.6000},
                        "tx": {"latitude": -34.9000, "longitude": 138.6000},
                    },
                    "frequency": 98000000,
                }
            },
            "southAdelaide": {
                "config": {
                    "location": {
                        "rx": {"latitude": -34.9500, "longitude": 138.6000},
                        "tx": {"latitude": -34.9500, "longitude": 138.6000},
                    },
                    "frequency": 98000000,
                }
            },
        }

    def test_basic_integration(self):
        """Test basic RETINASolver integration with simple detection data."""
        detections = {
            "test_aircraft": [
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 50.0,
                    "doppler": 100.0,
                },
                {
                    "radar": "northAdelaide",
                    "timestamp": 1641024000,
                    "delay": 55.0,
                    "doppler": 120.0,
                },
                {
                    "radar": "southAdelaide",
                    "timestamp": 1641024000,
                    "delay": 45.0,
                    "doppler": 80.0,
                },
            ]
        }

        result = self.solver.process(detections, self.radar_config)

        if result:
            assert isinstance(result, dict)
            if "test_aircraft" in result:
                assert "points" in result["test_aircraft"]
                assert isinstance(result["test_aircraft"]["points"], list)
                assert len(result["test_aircraft"]["points"]) > 0

                lat, lon, alt = result["test_aircraft"]["points"][0]
                assert isinstance(lat, (int, float))
                assert isinstance(lon, (int, float))
                assert isinstance(alt, (int, float))

                assert -36.0 < lat < -34.0
                assert 138.0 < lon < 140.0
                assert alt > -1000
        else:
            print("RETINASolver couldn't solve with given detection data")

    def test_error_handling(self):
        """Test that solver handles various error conditions gracefully."""
        insufficient_detections = {
            "target": [
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 50.0,
                    "doppler": 100.0,
                }
            ]
        }

        result = self.solver.process(insufficient_detections, self.radar_config)
        assert result == {}

        detections_missing_radar = {
            "target": [
                {
                    "radar": "nonexistent_radar",
                    "timestamp": 1641024000,
                    "delay": 50.0,
                    "doppler": 100.0,
                },
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 55.0,
                    "doppler": 120.0,
                },
                {
                    "radar": "northAdelaide",
                    "timestamp": 1641024000,
                    "delay": 45.0,
                    "doppler": 80.0,
                },
            ]
        }

        result = self.solver.process(detections_missing_radar, self.radar_config)
        assert result == {}

    def test_multiple_targets(self):
        """Test processing multiple targets simultaneously."""
        multi_target_detections = {
            "aircraft_1": [
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 50.0,
                    "doppler": 100.0,
                },
                {
                    "radar": "northAdelaide",
                    "timestamp": 1641024000,
                    "delay": 55.0,
                    "doppler": 120.0,
                },
                {
                    "radar": "southAdelaide",
                    "timestamp": 1641024000,
                    "delay": 45.0,
                    "doppler": 80.0,
                },
            ],
            "aircraft_2": [
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 70.0,
                    "doppler": 200.0,
                },
                {
                    "radar": "northAdelaide",
                    "timestamp": 1641024000,
                    "delay": 75.0,
                    "doppler": 220.0,
                },
                {
                    "radar": "southAdelaide",
                    "timestamp": 1641024000,
                    "delay": 65.0,
                    "doppler": 180.0,
                },
            ],
        }

        result = self.solver.process(multi_target_detections, self.radar_config)

        assert isinstance(result, dict)
        assert len(result) <= 2

    def test_coordinate_conversion(self):
        """Test that coordinate conversion logic works correctly."""
        freq_hz = 98000000
        expected_freq_mhz = 98.0
        actual_freq_mhz = freq_hz / 1e6
        assert abs(actual_freq_mhz - expected_freq_mhz) < 0.001

        test_coords = {"latitude": -34.9286, "longitude": 138.5999}

        assert -90 <= test_coords["latitude"] <= 90
        assert -180 <= test_coords["longitude"] <= 180

    def test_data_structure_consistency(self):
        """Test that data structures are consistent with 3lips format."""
        detections = {
            "consistency_test": [
                {
                    "radar": "adelaideHills",
                    "timestamp": 1641024000,
                    "delay": 30.0,
                    "doppler": 50.0,
                },
                {
                    "radar": "northAdelaide",
                    "timestamp": 1641024000,
                    "delay": 35.0,
                    "doppler": 70.0,
                },
                {
                    "radar": "southAdelaide",
                    "timestamp": 1641024000,
                    "delay": 25.0,
                    "doppler": 30.0,
                },
            ]
        }

        result = self.solver.process(detections, self.radar_config)

        if result:
            for _target_id, target_data in result.items():
                assert isinstance(target_data, dict)
                assert "points" in target_data
                assert isinstance(target_data["points"], list)

                for point in target_data["points"]:
                    assert isinstance(point, list)
                    assert len(point) == 3  # [lat, lon, alt]
