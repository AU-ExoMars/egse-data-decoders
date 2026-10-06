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

    While we have a calibration curve for the TEC thermistor, we've got
    another resistor and an ADC in the system.

    FittableModel's calibration will attempt to optimise the value for
    R_upper.
    """

    def __init__(self,
            r_upper: float|tuple[float,float]|None = (4990*0.99, 4990*1.01),
            adc_bits: int = 16,
        ) -> None:
        """Class constructor.

        :param r_upper: The resistance of the top half of the potential divider.
        :param adc_bits: The resolution of the ADC, in bits.
        """
        # Pass r_upper up to FittableModel.
        super().__init__(r_upper = r_upper)

        self.adc_bits = adc_bits
        self.adc_maxval = (1 << adc_bits)-1

        self.A = 1.364e-4
        self.B = -3.758e-02
        self.C = 8.153

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
        A, B and C.
        """
        return np.exp(self.A*t*t + self.B*t + self.C)

    def r_to_t(self, r: float|np.ndarray) -> float|np.ndarray:
        """Convert a resistance to a temperature.

        Given a thermistor resistance, we can solve the quadratic
        to calculate the temperature. See t_to_r above.
        """
        inner = self.B*self.B - 4*self.A*(self.C - np.log(r))
        if isinstance(inner, np.ndarray):
            inner[inner < 0] = 0
        elif inner < 0:
            inner = 0
        return (-self.B - np.sqrt(inner))/(2*self.A)

    def dn_to_t(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert a DN value to a temperature.

        Given a DN value, use dn_to_r, followed by r_to_t, to
        calculate the temperature.

        This is probably the main method from this class that you'll use.
        """
        return self.r_to_t(self.dn_to_r(dn))

    def __call__(self, dn: int|np.ndarray) -> float|np.ndarray:
        """Convert a DN value to a temperature.

        This is just a thin wrapper around dn_to_t, allowing the object
        to be callable, since this is the primary usage of the class.
        """
        return self.dn_to_t(dn)

    def t_to_dn(self, t: float|np.ndarray) -> int|np.ndarray:
        """Convert a temperature to an expected DN value.

        Given a temperature value, use t_to_r and r_to_dn to calculate
        the expected DN value.
        """
        return self.r_to_dn(self.t_to_r(t))

    def __str__(self):
        return f"{self.__class__.__name__}(r_upper={self.r_upper}, adc_bits={self.adc_bits})"
