import os
import sys

retina_solver_path = os.environ.get("RETINA_SOLVER_PATH", "/app/RETINAsolver")
if retina_solver_path not in sys.path:
    sys.path.append(retina_solver_path)

from detection_triple import Detection, DetectionTriple  # noqa: E402
from initial_guess_3det import get_initial_guess  # noqa: E402
from lm_solver_3det import solve_position_velocity_3d  # noqa: E402


class RETINASolverLocalisation:
    """RETINASolver integration into 3lips localization pipeline."""

    def __init__(self):
        self.max_iterations = int(os.environ.get("RETINA_SOLVER_MAX_ITERATIONS", "100"))
        self.convergence_threshold = float(
            os.environ.get("RETINA_SOLVER_CONVERGENCE_THRESHOLD", "1e-6")
        )

    def process(self, assoc_detections, radar_data):
        """Process detections using RETINASolver.

        Args:
            assoc_detections (dict): Associated detections by target ID
            radar_data (dict): Radar configuration data

        Returns:
            dict: Localized positions in 3lips format
        """
        print("🔥 RETINASOLVER PROCESS FUNCTION CALLED")
        print(f"🔥 TARGETS: {len(assoc_detections)}")
        print(f"🔥 KEYS: {list(assoc_detections.keys())}")
        output = {}

        for target in assoc_detections:
            if len(assoc_detections[target]) >= 3:
                print(f"🚀 RETINASolver processing target {target} with {len(assoc_detections[target])} detections")
                try:
                    detections = []
                    for radar in assoc_detections[target][:3]:
                        detections.append(self._create_detection(radar, radar_data))
                        print(f"📡 Detection: radar={radar['radar']}, delay={radar['delay']:.3f}, doppler={radar['doppler']:.3f}")

                    triple = DetectionTriple(
                        detections[0], detections[1], detections[2]
                    )
                    print("🎯 Getting initial guess...")
                    initial_guess = get_initial_guess(triple)
                    print(f"💡 Initial guess: {initial_guess}")
                    print("⚙️ Starting LM solver...")
                    result = solve_position_velocity_3d(
                        triple,
                        initial_guess,
                    )
                    print(f"✅ RETINASolver result: {result}")

                    if result and "error" not in result:
                        velocity_enu = [
                            result.get("velocity_east", 0.0),
                            result.get("velocity_north", 0.0),
                            result.get("velocity_up", 0.0)
                        ]
                        print(f"🎯 RETINASolver SUCCESS: pos=({result['lat']:.6f}, {result['lon']:.6f}, {result['alt']:.1f}), vel_enu={velocity_enu}")
                        output[target] = {
                            "points": [[result["lat"], result["lon"], result["alt"]]],
                            "velocity_enu": velocity_enu
                        }
                    else:
                        print(f"❌ RETINASolver failed for target {target}: {result}")
                except Exception as e:  # nosec B110
                    print(f"💥 RETINASolver exception for target {target}: {e}")
                    pass
            else:
                print(f"⚠️ Target {target} has only {len(assoc_detections[target])} detections (need 3)");

        return output

    def _create_detection(self, radar, radar_data):
        config = radar_data[radar["radar"]]["config"]
        return Detection(
            sensor_lat=config["location"]["rx"]["latitude"],
            sensor_lon=config["location"]["rx"]["longitude"],
            ioo_lat=config["location"]["tx"]["latitude"],
            ioo_lon=config["location"]["tx"]["longitude"],
            freq_mhz=config["capture"]["fc"] / 1e6,
            timestamp=radar["timestamp"],
            bistatic_range_km=radar["delay"],
            doppler_hz=radar["doppler"],
        )
