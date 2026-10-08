"""Encapsulate the MWIR TEC's temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt and exp functions, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

from .potential_divider import PotentialDividerModel


class TecThermistorModel(PotentialDividerModel):
    """Encapsulate the MWIR TEC's temperature sensor connected to an ADC.

    This class represents a the MWIR's temperature sensor connected as the
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
                  | | TEC thermistor
                  | |
                  -+-
                   |
                   +------------------ Gnd

    All temperatures are specified in degrees Celsius and all resistances
    are in Ohms.

    The calibration data I've seen looks to be best fitted by a formula
    of the form r = exp(a*t*t + b*t + c), so this is what we'll use and
    calibrate below.
    """

    def __init__(self,
            r_upper: float|tuple[float,float]|None = None,
            a: float|None = None,
            b: float|None = None,
            c: float|None = None,
            adc_bits: int = 16,
        ) -> None:
        """Class constructor.

        :param r_upper: The resistance of the top half of the potential divider.
        :param adc_bits: The resolution of the ADC, in bits.
        """
        # Pass calibration data up to FittableModel.
        super().__init__(r_upper = r_upper, a=a, b=b, c=c, adc_bits=adc_bits)

    def t_to_r(self, t: float|np.ndarray) -> float|np.ndarray:
        """Convert a temperature to a thermistor resistance value.

        After examining calibration data, it looks like a good fit
        can be found using an exponential of a quadratic function
        of temperature:

           resistance = exp(a*t**2 + b*t + c)

        A fit of the calibration data gave the class attributes
        a, b and c.
        """
        return np.exp(self.a*t*t + self.b*t + self.c)

    def r_to_t(self, r: float|np.ndarray) -> float|np.ndarray:
        """Convert a resistance to a temperature.

        Given a thermistor resistance, we can solve the quadratic
        to calculate the temperature. See t_to_r above.
        """
        with np.errstate(divide="ignore"):
            inner = self.b*self.b - 4*self.a*(self.c - np.log(r))

        if isinstance(inner, np.ndarray):
            inner[inner < 0] = 0
        elif inner < 0:
            inner = 0

        return (-self.b - np.sqrt(inner))/(2*self.a)

    def __str__(self):
        return f"{self.__class__.__name__}(r_upper={self.r_upper}, a={self.a}, b={self.b}, c={self.c}, adc_bits={self.adc_bits})"
