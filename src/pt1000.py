"""Encapsulate a PT1000 temperature sensor connected to an ADC."""

# We're going to use Numpy's sqrt function, since this will allow
# the class to work on numpy arrays of TRP values, rather than
# just scalars.
import numpy as np

# The "refine_calibration" method uses scipy.optimize.
import scipy


class PT1000:
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

        self.adc_maxval = (1 << adc_bits)-1

        self.r_0 = r_0
        self.r_upper = r_upper

    def dn_to_r(self, dn: int) -> float:
        """Convert from DN to PT1000 resistance.

        Given an ADC DN value, calculate the resistance of the PT1000.
        """
        return self.r_upper*dn/(self.adc_maxval-dn)

    def r_to_dn(self, r: float) -> int:
        """Convert from PT1000 resistance to DN.

        Given a PT1000 resistance, calculate the DN value that the ADC
        should output.
        """
        return round(self.adc_maxval*r/(r+self.r_upper))

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

    def refine_calibration(self,
        dn_values: list[int],
        temperature_values: list[float],
        r_upper_tolerance_percent: float = 1,
        r_0_tolerance_percent: float = 5,
        r_upper_search_steps: int = 100,
        r_0_search_steps: int = 100,
    ) -> tuple[float, float, float]:
        """Refine the calibration values for r_upper and r_0.

        Neither resistor is likely to be perfectly on spec and,
        even with a 1% upper and 5% PT1000 tolerance, this can
        translate to errors in excess of 10 degrees. This method
        takes arrays of DN and temperature values and attempts to
        refine the values of r_upper and r_0 to improve the model's
        fit to the data.

        Once calibrated, the values of the r_upper and r_0 attributes
        will be those found to give the optimum fit. The method also
        returns these values.

        It's not expected that you'd run this function very often -
        typically you'd use it to characterise a sensor, and then
        retain the generated values for future use.

        :param dn_values: List (or numpy vector) of ADC DN values.
        :param temperature_values: Corresponding temperatures.
        :param r_upper_tolerance_percent: Percentage range to search.
        :param r_0_tolerance_percent: Percentage range to search.
        :param r_upper_search_steps: Steps across range.
        :param r_0_search_steps: Steps across range.
        """
        self._calibration_dn_values = np.array(dn_values)
        self._calibration_temperature_values = np.array(temperature_values)

        r_upper_range = (
            self.r_upper*(1-r_upper_tolerance_percent/100),
            self.r_upper*(1+r_upper_tolerance_percent/100),
        )
        r_upper_slice = slice(
            r_upper_range[0], r_upper_range[1],
            (r_upper_range[1]-r_upper_range[0])/r_upper_search_steps,
        )

        r_0_range = (
            self.r_0*(1-r_0_tolerance_percent/100),
            self.r_0*(1+r_0_tolerance_percent/100),
        )
        r_0_slice = slice(
            r_0_range[0], r_0_range[1],
            (r_0_range[1]-r_0_range[0])/r_0_search_steps,
        )

        model = scipy.optimize.brute(self._calibration_estimator,
            ranges = (r_upper_slice, r_0_slice),
            workers = -1,
            finish = None,
        )

        self.r_upper, self.r_0 = model
        error = self._calibration_estimator(model)

        del self._calibration_dn_values
        del self._calibration_temperature_values

        return self.r_upper, self.r_0, error

    def _calibration_estimator(self, x: tuple[float,float]) -> float:
        self.r_upper, self.r_0 = x

        estimated_temperatures = self.dn_to_t(self._calibration_dn_values)

        errors = estimated_temperatures - self._calibration_temperature_values

        ret = np.sqrt(sum(errors**2)/errors.shape[0])

        return ret

