"""Encapsulate a resistive temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt function, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

from .fittable import FittableModel


class PotentialDividerModel(FittableModel):
    """Encapsulate a resistive temperature sensor connected to an ADC.

    This is the base class for other models. Subclasses should provide
    t_to_r and r_to_t methods that convert between resistance and
    temperature.

    This class represents a resistive temperature sensor connected as the
    lower half of a potential divider, with the top connected to Vref,
    the bottom connected to ground and the midpoint connected to an ADC:

                   +------------------ Vref
                   |
                  -+-
                  | | R_upper
                  | |
                  -+-
                   |
                   +------------------ ADC
                   |
                  -+-
                  | | R_sensor
                  | |
                  -+-
                   |
                   +------------------ Gnd

    All temperatures are specified in degrees Celsius and all resistances
    are in Ohms.
    """

    def __init__(self,
            r_upper: float,
            adc_bits: int = 16,
            **kwargs
        ) -> None:
        """Class constructor.

        :param r_upper: The resistance of the top half of the potential divider.
        :param adc_bits: The resolution of the ADC, in bits.
        """

        self.adc_maxval = (1 << adc_bits)-1
        self.r_upper = r_upper

        # Pass anything else up to the base class.
        super().__init__(**kwargs)

    def dn_to_r(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert from DN to R_sensor resistance.

        Given an ADC DN value, calculate the R_sensor
        """
        if isinstance(dn, np.ndarray):
            # Dividing by zero will give np.inf, which is
            # kind of what we want. So let's suppress the
            # warning when it does it.
            with np.errstate(divide="ignore"):
                return self.r_upper*dn/(self.adc_maxval-dn)

        # For integers, we'll need to catch the exception
        # and return infinity manually.
        try:
            return self.r_upper*dn/(self.adc_maxval-dn)
        except ZeroDivisionError:
            return float(np.inf)

    def r_to_dn(self, r: float) -> int:
        """Convert from R_sensor resistance to DN.

        Given a resistance, calculate the DN value that the ADC
        should output.
        """
        return round(self.adc_maxval*r/(r+self.r_upper))

    def __call__(self, dn: int|np.ndarray) -> float:
        """Convert a DN value to a temperature.

        This is just a thin wrapper around dn_to_r and the 
        subclass-provided r_to_t.
        """
        if isinstance(dn, np.ndarray):
            return self.r_to_t(self.dn_to_r(dn))

        # I wish numpy would convert scalars to floats automatically.
        return float(self.r_to_t(self.dn_to_r(dn)))

