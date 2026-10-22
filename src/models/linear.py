"""A simple linear model."""

import numpy as np

from .fittable import FittableModel


class LinearModel(FittableModel):
    """A simple linear model."""

    def __init__(self,
        slope: float|None=None,
        intercept: float|None=None,
        zero_is_invalid: bool=True
    ) -> None:
        """Class constructor.

        Just passes named parameters up to FittableModel so it can
        create the calibration function.
        """
        super().__init__(slope=slope, intercept=intercept)

        self.zero_is_invalid = zero_is_invalid

    def __call__(self, value: float|np.ndarray) -> float|np.ndarray:
        """Perform the model calculation."""

        if value is None:
            return None

        if self.zero_is_invalid:
            if isinstance(value, np.ndarray):
                value[value == 0] = np.nan
            elif value == 0:
                value = np.nan

        if isinstance(value, np.ndarray):
            return self.slope*value + self.intercept

        return float(self.slope*value + self.intercept)
