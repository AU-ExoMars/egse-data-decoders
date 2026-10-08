"""Calibration values for OB and EB models.

This file contains the determined calibration values for
the various OB and EB instruments.

FIXME: All of these calibrations are approximate at the moment.
"""

from enfys_calibration import EbCalibration, ObCalibration
from models import (
    AdcNonlinearModel,
    LinearModel,
    Pt1000Model,
    TecThermistorModel,
    ThermistorBModel,
)

# BB2 OB calibration values.
# Is also DEM
ob_calibration_bb2 = ObCalibration(

    model_id = 2,
    model_name = "BB2",

    swir_chop_target = 5000,
    mwir_chop_target = 5000,

    swir_wavelength_model = LinearModel(0.1218, 607.8),
    mwir_wavelength_model = LinearModel(0.2165, 1096.1),

    heatsink_temperature_model = Pt1000Model(10000, 1021.31),
    swir_temperature_model = Pt1000Model(10000, 1013.02),
    eb_peltier_temperature_model = TecThermistorModel(4990, 1.364e-4, -3.758e-2, 8.153),
    digital_temperature_model = Pt1000Model(1000, 1060.74),
    detector_temperature_model = Pt1000Model(1000, 1079.80),
    mechanism_temperature_model = Pt1000Model(1000, 1042.92),
    motor_temperature_model = Pt1000Model(1000, 1017.55),

    voltage_3v3_model = LinearModel(1.0445e-4, 0),
    voltage_1v5_model = LinearModel(5.2413e-5, 0),
    mechanism_current_model = LinearModel(3.3897e-6, 0),

    swir_low_to_medium_model = AdcNonlinearModel(29.523, -715.3, 58),
    swir_medium_to_high_model = AdcNonlinearModel(29.398, -304.0, 50),

    mwir_low_to_medium_model = AdcNonlinearModel(29.591, -1137.5, 69),
    mwir_medium_to_high_model = AdcNonlinearModel(29.588, -357.1, 115),
)

# EM OB calibration values.
ob_calibration_em = ObCalibration(

    model_id = 4,
    model_name = "EM",

    swir_chop_target = 5000,
    mwir_chop_target = 15000,

    swir_wavelength_model = LinearModel(0.1218, 680.9),
    mwir_wavelength_model = LinearModel(0.2220, 1192.9),

    heatsink_temperature_model = Pt1000Model(10046, 1006),
    swir_temperature_model = Pt1000Model(9906, 988),
    eb_peltier_temperature_model = TecThermistorModel(4990, 1.364e-4, -3.758e-2, 8.153),
    digital_temperature_model = Pt1000Model(1000, 1060.74),
    detector_temperature_model = Pt1000Model(1000, 1079.80),
    mechanism_temperature_model = Pt1000Model(1000, 1042.92),
    motor_temperature_model = Pt1000Model(1000, 1017.55),

    voltage_3v3_model = LinearModel(1.0445e-4, 0),
    voltage_1v5_model = LinearModel(5.2413e-5, 0),
    mechanism_current_model = LinearModel(3.3897e-6, 0),

    swir_low_to_medium_model = AdcNonlinearModel(27.873, 7653.9, 145),
    swir_medium_to_high_model = AdcNonlinearModel(28.208, 8561.3, 208),

    mwir_low_to_medium_model = AdcNonlinearModel(27.718, 7218.6, 197),
    mwir_medium_to_high_model = AdcNonlinearModel(28.125, 7618.0, 148),
)

# EM EB calibration values.
eb_calibration_em = EbCalibration(

    model_name = "EM",

    plus_12v_model = LinearModel(0.000400543, 0),
    minus_12v_model = LinearModel(-0.00038147, 0),
    plus_5v_model = LinearModel(0.000152829, 0),
    plus_3v3_model = LinearModel(0.0000762939, 0),
    tec_rail_model = LinearModel(0.0000762939, 0),

    mcu_temperature_model = LinearModel(0.01637198, -273),
    internal_temperature_model = ThermistorBModel(1000, 5000, 25, 3891),
    psu_board_temperature_model = ThermistorBModel(1000, 5000, 25, 3891),

    tec_drive_current_model = LinearModel(0.000016164, 0),
)
