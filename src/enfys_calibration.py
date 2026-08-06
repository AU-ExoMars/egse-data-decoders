import dataclasses

from typing import Callable

@dataclasses.dataclass
class RawScienceRow:
    """A data class to hold a row within the science data."""

    ABS_STEPS: int
    SWIR_LOW: int
    SWIR_MED: int
    SWIR_HIGH: int
    MWIR_LOW: int
    MWIR_MED: int
    MWIR_HIGH: int
    
class EnfysScienceRow:
    """Base class"""

    # The model ID, as recorded in science and HK data.
    model_id: int

    # A brief text name for this model.
    name: str

    # The ADC isn't linear at the top end of the scale, so
    # we need to have a threshold beyond which we'll switch to
    # a lower gain amplifier.
    max_usable_adc_value: int

    # Lambdas which model the relationship between low and medium
    # gain DNs.
    swir_low_to_medium_model: Callable[[int], float]
    mwir_low_to_medium_model: Callable[[int], float]

    # Lambdas which model the relationship between medium and high
    # gain DNs.
    swir_medium_to_high_model: Callable[[int|float], float]
    mwir_medium_to_high_model: Callable[[int|float], float]

    # Lambdas which normalise high gain DN values by removing the
    # effect of the DAC offset.
    swir_dac_offset_correction: Callable[[int|float, int], float]
    mwir_dac_offset_correction: Callable[[int|float, int], float]

    # From the constructor.
    swir_offset: int
    mwir_offset: int
    raw: RawScienceRow

    def __init__(self, science_row: RawScienceRow, swir_offset: int, mwir_offset: int):
        self.raw = science_row
        self.swir_offset = swir_offset
        self.mwir_offset = mwir_offset

    @property
    def swir_wavelength(self):
        return self.__class__.swir_wavelength_model(self.raw.ABS_STEPS)
        
    @property
    def mwir_wavelength(self):
        return self.__class__.mwir_wavelength_model(self.raw.ABS_STEPS)

    @property
    def swir_dn(self):
        if self.raw.SWIR_HIGH < self.max_usable_adc_value:
            return self.raw.SWIR_HIGH

        if self.raw.SWIR_MED < self.max_usable_adc_value:
            return
            round(self.__class__.swir_medium_to_high_model(self.raw.SWIR_MED))

        return round(self.__class__.swir_medium_to_high_model(
                    self.__class__.swir_low_to_medium_model(self.raw.SWIR_LOW)
        ))

    @property
    def mwir_dn(self):
        if self.raw.MWIR_HIGH < self.max_usable_adc_value:
            return self.raw.MWIR_HIGH

        if self.raw.MWIR_MED < self.max_usable_adc_value:
            return round(self.__class__.mwir_medium_to_high_model(self.raw.MWIR_MED))

        return round(self.__class__.mwir_medium_to_high_model(
                    self.__class__.mwir_low_to_medium_model(self.raw.MWIR_LOW)
        ))
