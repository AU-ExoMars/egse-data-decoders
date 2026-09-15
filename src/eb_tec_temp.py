"""Encapsulate the MWIR TEC's temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt and exp functions, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

class EbTecTemp:
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

    """

    def __init__(self,
            r_upper: float = 4990,
            adc_bits: int = 16,
        ) -> None:
        """Class constructor.

        :param r_upper: The resistance of the top half of the potential divider.
        :param adc_bits: The resolution of the ADC, in bits.
        """
        self.adc_maxval = (1 << adc_bits)-0.5

        self.A = 1.364e-4
        self.B = -3.758e-02
        self.C = 8.153

        self.r_upper = r_upper

    def dn_to_r(self, dn: int) -> float:
        """Convert from DN to thermistor resistance.

        Given an ADC DN value, calculate the resistance of the thermistor.
        """
        if dn == 0 or dn == 65535:
            raise ValueError(f"DN of 0 or 65535 implies zero resistance")

        return self.r_upper*dn/(self.adc_maxval-dn)

    def r_to_dn(self, r: float) -> int:
        """Convert from thermistor resistance to DN.

        Given a thermistor resistance, calculate the DN value that the ADC
        should output.
        """
        return round(self.adc_maxval*r/(r+self.r_upper))

    def t_to_r(self, t: float) -> float:
        """Convert a temperature to a thermistor resistance value.

        After examining calibration data, it looks like a good fit
        can be found using an exponential of a quadratic function
        of temperature:

           resistance = exp(a*t**2 + b*t + c)

        A fit of the calibration data gave the class attributes
        A, B and C.
        """
        return np.exp(self.A*t*t + self.B*t + self.C)

    def r_to_t(self, r: float) -> float:
        """Convert a resistance to a temperature.

        Given a thermistor resistance, we can solve the quadratic
        to calculate the temperature. See t_to_r above.
        """
        inner = self.B*self.B - 4*self.A*(self.C - np.log(r))
        if inner < 0:
            inner = 0
        return (-self.B - np.sqrt(inner))/(2*self.A)

    def dn_to_t(self, dn: int) -> float:
        """Convert a DN value to a temperature.

        Given a DN value, use dn_to_r, followed by r_to_t, to
        calculate the temperature.

        This is probably the main method from this class that you'll use.
        """
        return self.r_to_t(self.dn_to_r(dn))

    def __call__(self, dn: int) -> float:
        """Convert a DN value to a temperature.

        This is just a thin wrapper around dn_to_t, allowing the object
        to be callable, since this is the primary usage of the class.
        """
        return self.dn_to_t(dn)

    def t_to_dn(self, t: float) -> int:
        """Convert a temperature to an expected DN value.

        Given a temperature value, use t_to_r and r_to_dn to calculate
        the expected DN value.
        """
        return self.r_to_dn(self.t_to_r(t))

