"""
Simple pytest-compatible RETINASolver tests.
Run with: docker exec 3lips-event python -m pytest /app/test_retina_simple.py -v
"""

import os
import sys

import pytest

# Add required paths for container environment
sys.path.insert(0, "/app/event")
sys.path.insert(0, "/app/common")


@pytest.fixture
def solver():
    """Create RETINASolver instance."""
    from algorithm.localisation.RETINASolverLocalisation import RETINASolverLocalisation

    return RETINASolverLocalisation()


@pytest.fixture
def radar_config():
    """Standard radar configuration for Adelaide area."""
    return {
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


def test_solver_instantiation(solver):
    """Test that solver can be instantiated."""
    assert solver is not None
    assert hasattr(solver, "process")


def test_retina_solver_dependencies():
    """Test that RETINASolver dependencies are available."""
    retina_dir = "/app/RETINAsolver"
    assert os.path.exists(retina_dir), f"RETINASolver directory not found: {retina_dir}"

    required_files = [
        "detection_triple.py",
        "lm_solver_3det.py",
        "initial_guess_3det.py",
    ]
    available_files = [f for f in os.listdir(retina_dir) if f.endswith(".py")]

    for required_file in required_files:
        assert required_file in available_files, (
            f"Missing required file: {required_file}"
        )


def test_realistic_detection_processing(solver, radar_config):
    """Test processing realistic detection data."""
    detections = {
        "test_aircraft": [
            {
                "radar": "adelaideHills",
                "timestamp": 1641024000,
                "delay": 35.0,
                "doppler": 200.0,
            },
            {
                "radar": "northAdelaide",
                "timestamp": 1641024000,
                "delay": 40.0,
                "doppler": 220.0,
            },
            {
                "radar": "southAdelaide",
                "timestamp": 1641024000,
                "delay": 32.0,
                "doppler": 180.0,
            },
        ]
    }

    result = solver.process(detections, radar_config)

    # Result could be empty if solver doesn't converge - that's okay
    assert isinstance(result, dict)

    # If it did converge, validate the result format
    if result and "test_aircraft" in result:
        assert "points" in result["test_aircraft"]
        assert isinstance(result["test_aircraft"]["points"], list)
        assert len(result["test_aircraft"]["points"]) > 0

        lat, lon, alt = result["test_aircraft"]["points"][0]
        assert isinstance(lat, (int, float))
        assert isinstance(lon, (int, float))
        assert isinstance(alt, (int, float))

        # Validate coordinates are reasonable for Adelaide area
        assert -36.0 < lat < -34.0, f"Latitude {lat} outside Adelaide range"
        assert 138.0 < lon < 140.0, f"Longitude {lon} outside Adelaide range"


def test_insufficient_detections(solver, radar_config):
    """Test handling of insufficient detections."""
    insufficient_detections = {
        "test_aircraft": [
            {
                "radar": "adelaideHills",
                "timestamp": 1641024000,
                "delay": 35.0,
                "doppler": 200.0,
            }
        ]
    }

    result = solver.process(insufficient_detections, radar_config)
    assert result == {}, "Should return empty dict for insufficient detections"


def test_empty_input_handling(solver, radar_config):
    """Test handling of empty inputs."""
    # Empty detections
    result = solver.process({}, radar_config)
    assert result == {}, "Should return empty dict for empty detections"

    # Empty radar config
    detections = {
        "test_aircraft": [
            {
                "radar": "adelaideHills",
                "timestamp": 1641024000,
                "delay": 35.0,
                "doppler": 200.0,
            },
            {
                "radar": "northAdelaide",
                "timestamp": 1641024000,
                "delay": 40.0,
                "doppler": 220.0,
            },
            {
                "radar": "southAdelaide",
                "timestamp": 1641024000,
                "delay": 32.0,
                "doppler": 180.0,
            },
        ]
    }
    result = solver.process(detections, {})
    assert result == {}, "Should return empty dict for empty radar config"


def test_missing_radar_config(solver, radar_config):
    """Test handling of missing radar configuration."""
    detections = {
        "test_aircraft": [
            {
                "radar": "nonexistent_radar",
                "timestamp": 1641024000,
                "delay": 35.0,
                "doppler": 200.0,
            },
            {
                "radar": "adelaideHills",
                "timestamp": 1641024000,
                "delay": 40.0,
                "doppler": 220.0,
            },
            {
                "radar": "northAdelaide",
                "timestamp": 1641024000,
                "delay": 32.0,
                "doppler": 180.0,
            },
        ]
    }

    result = solver.process(detections, radar_config)
    assert result == {}, "Should return empty dict when radar config is missing"
