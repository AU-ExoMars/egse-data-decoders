"""Post-processing of OB HK data."""

from enfys_calibration import ObCalibration
from ob_tm_packet import ObHkPacket


class TimestampedObHk(ObHkPacket):
    """An OB HK packet with added timestamp.

    This timestamp can be any float that makes sense to the user
    and doesn't have to be derived from lobt, for example.
    """

    timestamp: float|None = None

class ProcessedObHk(TimestampedObHk):
    """An OB HK packet with post-processing of data.

    Given an instrument calibration object, this class will perform
    decoding of data to real-world units.
    """

    swir_wavelength: float|None = None
    mwir_wavelength: float|None = None

    voltage_3v3: float|None = None
    voltage_1v5: float|None = None

    digital_temperature: float|None = None
    detector_temperature: float|None = None
    mechanism_temperature: float|None = None
    motor_temperature: float|None = None

    mechanism_current: float|None = None

    def __init__(self, calibration: ObCalibration, **kwargs) -> None:
        """Class constructor.

        Pass most args up to the parent constructor, then use
        the supplied calibration to decode data.
        """
        super().__init__(**kwargs)

        self.swir_wavelength = calibration.swir_wavelength_model(
            self.MTR_ABS_STEPS
        )
        self.mwir_wavelength = calibration.mwir_wavelength_model(
            self.MTR_ABS_STEPS
        )
        self.voltage_3v3 = calibration.voltage_3v3_model(
            self.HK_V_3V3
        )
        self.voltage_1v5 = calibration.voltage_1v5_model(
            self.HK_V_1V5
        )
        self.digital_temperature = calibration.digital_temperature_model(
            self.DIGITAL_TRP
        )
        self.detector_temperature = calibration.detector_temperature_model(
            self.DETEC_TRP
        )
        self.mechanism_temperature = calibration.mechanism_temperature_model(
            self.MECH_TRP
        )
        self.motor_temperature = calibration.motor_temperature_model(
            self.MOTOR_TRP
        )

        self.mechanism_current = calibration.mechanism_current_model(
            self.HK_MECH_CUR
        )
