"""Base classes for enfys model calibrations."""

from dataclasses import dataclass

from models import AdcNonlinearModel, LinearModel, Pt1000Model, TecThermistorModel


@dataclass(frozen=True)
class ObCalibration:
    """Base class for Ob calibrations."""

    # OB models declare their identity via a field.
    model_id: int

    # The model name (EM, BB2, etc)
    model_name: str

    # Chop targets for the firmware on this model.
    swir_chop_target: int
    mwir_chop_target: int

    # Temperature models.
    heatsink_temperature_model: Pt1000Model
    swir_temperature_model: Pt1000Model

    # While the EB reads this, the thermistor itself is
    # in the OB and calibration needs to follow the board.
    eb_peltier_temperature_model: TecThermistorModel

    # Models for translating motor steps to wavelength.
    swir_wavelength_model: LinearModel
    mwir_wavelength_model: LinearModel

    # Models for the amplifier gains. The ADCs are nonlinear
    # at the low end. While we're not going to use the values
    # from the nonlinear area, making it part of the model helps
    # us to get a fit in calibration.
    swir_low_to_medium_model: AdcNonlinearModel
    swir_medium_to_high_model: AdcNonlinearModel

    mwir_low_to_medium_model: AdcNonlinearModel
    mwir_medium_to_high_model: AdcNonlinearModel

    # The ADCs are nonlinear at the high end, so we need
    # a threshold above which we'll move to a lower gain
    # stage.
    max_usable_adc_value: int = 60000

@dataclass(frozen=True)
class EbCalibration:
    """Base class for EB calibrations."""

    # The model name (EM, DEM, etc)
    model_name: str

    # Voltage models.
    plus_12v_model: LinearModel
    minus_12v_model: LinearModel
    plus_5v_model: LinearModel
    plus_3v3_model: LinearModel
    tec_rail_model: LinearModel

    # Temperature models.
    mcu_temperature_model: LinearModel
    internal_temperature_model: LinearModel
    psu_board_temperature_model: LinearModel
    tec_drive_current_model: LinearModel
