"""Encapsulate a PT1000 temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt function, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

from .potential_divider import PotentialDividerModel


class Pt1000Model(PotentialDividerModel):
    """Encapsulate a PT1000 temperature sensor connected to an ADC.

    This class represents a PT1000 temperature sensor connected as the
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
                  | | R_0 (PT1000)
                  | |
                  -+-
                   |
                   +------------------ Gnd

    All temperatures are specified in degrees Celsius and all resistances
    are in Ohms.

    While the PT1000 has a nominal resistance of 1000 ohms at zero degrees,
    they are typically supplied with a resistance tolerance of +/-5%. When
    you run through the temperature calculation, it turns out that, over the
    range -50 to +20 degrees, the error due to this tolerance can be as much
    as 14 degrees. The class constructor therefore allows you to specify R0,
    the measured (or otherwise estimated) temperature at zero degrees.

    The upper resistor value defaults to 1000 Ohms, but can be specified as
    r_upper (or the first unnamed argument to the constructor). While
    nominally a constant, this resistance has a tolerance and you might wish
    to determine the true value of this resistor.

    The upper resistor will also have a temperature coefficient. In theory,
    this would need to be taken into account too. But the coefficient for a
    metal oxide SMD resistor is typically around 5ppm, which is low enough
    to be negligible.

    Neither resistor is likely to be perfectly on spec and, even with a 1%
    upper and 5% PT1000 tolerance, this can translate to errors in excess of
    10 degrees. The calibration process attempts to optimise the value of
    r_0 to improve the model's fit to the data.

    r_upper does *not* get modified by this process since, for each possible
    value for r_upper, there's a corresponding value for r_0 which gives the
    same overall error value. Allowing both to vary could allow arbitrarily
    unrealistic values for r_upper and r_0 to be selected.
    """

    def __init__(self,
            r_upper: float = 1000,
            r_0: float = 1000,
            adc_bits: int = 16,
        ) -> None:
        """Class constructor.

        :param r_upper: The resistance of the top half of the potential divider.
        :param r_0: The resistance of the PT1000 at zero degrees.
        :param adc_bits: The resolution of the ADC, in bits.
        """
        # The following are from the datasheet and I expect they are
        # constants.
        self.A = 3.90802e-3
        self.B = 5.802e-7

        # Fitting only tweaks r_0, so that's all we tell
        # FittableModel about.
        super().__init__(r_upper=r_upper, r_0 = r_0, adc_bits=adc_bits)

    # Go from PT1000 resistance to temperature.
    def r_to_t(self, r: float) -> float:
        """Convert a resistance to a temperature.

        Given a PT1000 resistance, solve the quadratic from the datasheet
        to calculate the temperature.
        """
        return (-self.A + np.sqrt(self.A*self.A - 4*self.B*(1-r/self.r_0)))/(2*self.B)

    def t_to_r(self, t: float) -> float:
        """Convert a temperature to a PT1000 resistance value.

        Given a temperature, use the information from the datasheet to
        calculate the expected resistance of the PT1000.
        """
        return self.r_0*(1+self.A*t+self.B*t*t)

    def __str__(self) -> str:
        """Return a representation of the object."""
        return f"{self.__class__.__name__}(r_0={self.r_0}, r_upper={self.r_upper}, adc_bits={self.adc_bits})"
