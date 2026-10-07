"""Encapsulate a thermistor using the "B" equation, connected to an ADC."""

import numpy as np

from .fittable import FittableModel


class ThermistorBModel(FittableModel):
    """Encapsulate a thermistor using the "B" equation, connected to an ADC.

    This class represents a thermistor that uses the "B" equation, connected 
    as the lower half of a potential divider, with the top connected to Vref,
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
                  | | R_0 (Thermistor)
                  | |
                  -+-
                   |
                   +------------------ Gnd

    All temperatures are specified in degrees Celsius and all resistances
    are in Ohms.

    The thermistor is typically specified with values r_0, t_0 and b. r_0
    is its nominal resistance at t_0 celsius, and "b" is a 
    manufacturer-supplied "material" value.

    The upper resistor, is specified as r_upper. While nominally a constant, 
    this resistance has a tolerance and you might wish to determine its true 
    value.

    The calibration process attempts to optimise the value of
    r_upper to improve the model's fit to the data.
    """


    celsius_to_kelvin = 273.15

    def __init__(self,
        r_upper: float|None = None,
        r_0: float|None = None,
        t_0: float|None = None,
        b: float|None = None,
        adc_bits: int = 16,
    ):
        """Class constructor.
        Hard to be certain, but I think we're likely to want to calibrate
        just r_upper.
        """
        super().__init__(r_upper=r_upper)
        self.r_0 = r_0
        self.t_0 = t_0
        self.b = b
        self.adc_bits = adc_bits

        self.adc_maxval = (1 << adc_bits)-1

    def __call__(self, value: float|np.ndarray) -> float|np.ndarray:
        """Perform the model calculation."""
        if isinstance(value, np.ndarray):
            return self.dn_to_t(value)
        return float(self.dn_to_t(value))

    def dn_to_t(self, dn):
        return self.r_to_t(self.dn_to_r(dn))

    def t_to_r(self, t):
        return self._r_inf * np.exp(self.b / (t + self.celsius_to_kelvin))

    def r_to_t(self, r):
        return self.b / np.log(r / self._r_inf) - self.celsius_to_kelvin

    def dn_to_r(self, dn):
        return self.r_upper*dn/(self.adc_maxval - dn)

    def r_to_dn(self, r):
        return np.round(self.adc_maxval*r/(r+self.r_upper))

    def __str__(self):
        return f"{self.__class__.__name__}(r_upper={self.r_upper}, r_0={self.r_0}, t_0={self.t_0}, b={self.b}, adc_bits={self.adc_bits})"

    @property
    def _r_inf(self):
        return self.r_0 * np.exp(-self.b/(self.t_0 + self.celsius_to_kelvin))

