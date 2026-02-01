import numpy as np
from stonesoup.models.measurement.linear import LinearGaussian


def create_enu_position_measurement_model(noise_covariance=None):
    """Factory function to create ENU position measurement model.

    Args:
        noise_covariance: 3x3 covariance matrix for measurement noise.
                        If None, uses default uncertainty values.

    Returns:
        LinearGaussian measurement model for ENU position.
    """
    if noise_covariance is None:
        # Default measurement noise (500m std dev in each ENU direction)
        noise_covariance = np.diag([500**2, 500**2, 500**2])

    return LinearGaussian(
        ndim_state=6,
        mapping=[0, 1, 2],  # Map to east, north, up positions
        noise_covar=noise_covariance,
    )
