import sys
"""Attempt to emulate the behaviour of the ADCs at low DN values."""
import numpy as np

from .fittable import FittableModel


class AdcNonlinearModel(FittableModel):
    """Attempt to emulate the behaviour of the ADCs at low DN values."""

    def __init__(self,
        slope: float|tuple[float,float]|None = None,
        intercept: float|tuple[float,float]|None = None,
        cutover: int|tuple[int, int]|None = (50, 300),
        saturation: int|tuple[int, int]|None = (58000, 62000)
    ) -> None:
        """Class constructor.

        Just pass everything up to FittableModel.
        """
        super().__init__(slope=slope, intercept=intercept, cutover=cutover, saturation=saturation)

    def __call__(self, value: float|np.ndarray) -> float|np.ndarray:
        """Return real world value from DN.

        This function is linear for values above self.cutover and is a power
        curve for below self.cutover, where the power curve is chosen to meet the
        linear portion and to have the same slope as it (i.e. self.slope) at that point.

        It's a very simple model of the ADC, capturing its nonlinearity close to zero.

        Uses np.piecewise, since this allows matrix operations and hence
        scipy.optimize.curve_fit can use it.
        """

        if value is None:
            return None

        meetpoint = self.slope*self.cutover + self.intercept
        exponent = self.slope*self.cutover/meetpoint
        xsat = (self.saturation - self.intercept)/self.slope

        if isinstance(value, np.ndarray):
            # N.B. No attempt made to handle None here.
            value = np.array(value, dtype=float)
            return np.piecewise(value,
                [
                    value < self.cutover,
                    (value >= self.cutover) & (value < xsat),
                    value >= xsat
                ],
                [
                    meetpoint * (value[value < self.cutover]/self.cutover) ** exponent,
                    self.slope*value[(value >= self.cutover) & (value < xsat)] + self.intercept,
                    0*value[value >= xsat] + self.saturation
                ],
            )

        # The scalar case.
        return (
            self.saturation if value >= xsat else
            self.slope*value+self.intercept if value >= self.cutover else
            meetpoint * (value/self.cutover) ** exponent
        )
