"""Post-processing of EB HK data"""

from eb_tm_packet import EbHkPacket, EbRegularHkPacket, EbResponseHkPacket
from enfys_calibration import EbCalibration, ObCalibration
from ob_hk import ProcessedObHk


class TimestampedEbHk(EbHkPacket):
    """An EB HK packet with added timestamp.

    This timestamp can be any float that makes sense to the user
    and doesn't have to be derived from lobt, for example.
    """

    timestamp: float|None = None

class ProcessedEbHk(TimestampedEbHk):

    processed_ob_hk: ProcessedObHk
    source_type: (type(EbRegularHkPacket)|type(EbResponseHkPacket)|None)

    tec_setpoint_temperature: float
    voltage_plus_12v: float
    voltage_minus_12v: float
    voltage_5v: float
    voltage_3v3: float
    voltage_tec_rail: float
    mcu_internal_temperature: float
    peltier_temperature: float
    internal_trp_temperature: float
    psu_board_temperature: float
    tec_drive_current: float

    def __init__(self, ob_calibration: ObCalibration, eb_calibration: EbCalibration, **kwargs):
        super().__init__(**kwargs)

        self.processed_ob_hk = ProcessedObHk(src=self.ob_hk, calibration=ob_calibration)

        # TEC is an odd case - the thermistor is in the OB, but it's the
        # EB that controls it. So calibration data lives in the OB
        # calibration.
        self.tec_setpoint_temperature = ob_calibration.eb_peltier_temperature_model(self.TEC_SETPOINT)

        self.voltage_plus_12v = eb_calibration.plus_12v_model(self.EB_MEAS_MAIN_12V)
        self.voltage_minus_12v = eb_calibration.plus_12v_model(self.EB_MEAS_MAIN_NEG12V)
        self.voltage_5v = eb_calibration.plus_5v_model(self.EB_MEAS_5V)
        self.voltage_3v3 = eb_calibration.plus_5v_model(self.EB_MEAS_3V3)
        self.voltage_tec_rail = eb_calibration.plus_5v_model(self.EB_MEAS_TEC_RAIL)
        self.mcu_internal_temperature = eb_calibration.mcu_temperature_model(self.EB_MCU_INTERNAL_TEMP)
        self.peltier_temperature = ob_calibration.eb_peltier_temperature_model(self.EB_PELTIER_TEMP)
        self.internal_trp_temperature = eb_calibration.internal_temperature_model(self.EB_INTERNAL_TRP_TEMP)
        self.psu_board_temperature = eb_calibration.psu_board_temperature_model(self.EB_PSU_BOARD_TEMP)
        self.tec_drive_current = eb_calibration.tec_drive_current_model(self.EB_TEC_DRIVE_CURRENT)
