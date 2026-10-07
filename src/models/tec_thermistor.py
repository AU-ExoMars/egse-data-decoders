"""Encapsulate the MWIR TEC's temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt and exp functions, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

from .fittable import FittableModel


class TecThermistorModel(FittableModel):
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
        super().__init__(r_upper = r_upper, a=a, b=b, c=c)

        self.adc_bits = adc_bits
        self.adc_maxval = (1 << adc_bits)-1

    def __call__(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert a DN value to a temperature.

        This is just a thin wrapper around dn_to_t, allowing the object
        to be callable, since this is the primary usage of the class.
        """
        return self.dn_to_t(dn)

    def dn_to_r(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert from DN to thermistor resistance.

        Given an ADC DN value, calculate the resistance of the thermistor.
        """
        if (
             (isinstance(dn, np.ndarray) and
                (np.any(dn < 1) or np.any(dn >= self.adc_maxval))) or
             (not isinstance(dn, np.ndarray)
                and (dn < 1 or dn >= self.adc_maxval))
        ):
            raise ValueError("DN of 0 or maxval implies zero resistance")

        return self.r_upper*dn/(self.adc_maxval-dn)

    def r_to_dn(self, r: float|np.ndarray) -> int|np.ndarray:
        """Convert from thermistor resistance to DN.

        Given a thermistor resistance, calculate the DN value that the ADC
        should output.
        """
        return np.round(self.adc_maxval*r/(r+self.r_upper))

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
        inner = self.b*self.b - 4*self.a*(self.c - np.log(r))
        if isinstance(inner, np.ndarray):
            inner[inner < 0] = 0
        elif inner < 0:
            inner = 0
        return (-self.b - np.sqrt(inner))/(2*self.a)

    def dn_to_t(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert a DN value to a temperature.

        Given a DN value, use dn_to_r, followed by r_to_t, to
        calculate the temperature.

        This is probably the main method from this class that you'll use.
        """
        return self.r_to_t(self.dn_to_r(dn))

    def t_to_dn(self, t: float|np.ndarray) -> int|np.ndarray:
        """Convert a temperature to an expected DN value.

        Given a temperature value, use t_to_r and r_to_dn to calculate
        the expected DN value.
        """
        return self.r_to_dn(self.t_to_r(t))

    def __str__(self):
        return f"{self.__class__.__name__}(r_upper={self.r_upper}, adc_bits={self.adc_bits})"
