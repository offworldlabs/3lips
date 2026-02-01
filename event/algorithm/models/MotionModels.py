from stonesoup.models.transition.linear import (
    CombinedLinearGaussianTransitionModel,
    ConstantAcceleration,
    ConstantVelocity,
)


def create_enu_constant_velocity_model(noise_diff_coeff=0.1):
    """Factory function to create ENU constant velocity motion model.

    Args:
        noise_diff_coeff: Noise diffusion coefficient (process noise intensity)

    Returns:
        CombinedLinearGaussianTransitionModel for 3D constant velocity motion.
    """
    return CombinedLinearGaussianTransitionModel(
        [
            ConstantVelocity(noise_diff_coeff),
            ConstantVelocity(noise_diff_coeff),
            ConstantVelocity(noise_diff_coeff),
        ]
    )


def create_enu_constant_acceleration_model(noise_diff_coeff=0.01):
    """Factory function to create ENU constant acceleration motion model.

    Args:
        noise_diff_coeff: Noise diffusion coefficient for acceleration

    Returns:
        CombinedLinearGaussianTransitionModel for 3D constant acceleration motion.
    """
    return CombinedLinearGaussianTransitionModel(
        [
            ConstantAcceleration(noise_diff_coeff),
            ConstantAcceleration(noise_diff_coeff),
            ConstantAcceleration(noise_diff_coeff),
        ]
    )
