"""Attempt to emulate the behaviour of the ADCs at low DN values."""
import numbers
import numpy as np

from .fittable import FittableModel


class AdcNonlinearModel(FittableModel):
    """Attempt to emulate the behaviour of the ADCs at low DN values."""

    def __init__(self,
        slope: numbers.Real|tuple[numbers.Real,numbers.Real]|None = None,
        intercept: numbers.Real|tuple[numbers.Real,numbers.Real]|None = None,
        cutover: numbers.Real|tuple[numbers.Real,numbers.Real]|None = None,
        saturation: int|tuple[int, int]|None = None
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

        # When modelling, we may want to force saturation, but when applying
        # we want to exclude it. e.g. when used to extrapolate from medium
        # to high gain. Therefore, we allow saturation to be None and, in
        # that case, set xsat to be an unattainable value so that we don't
        # output a saturated value.
        xsat = (self.saturation - self.intercept)/self.slope if self.saturation is not None else 65536

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
