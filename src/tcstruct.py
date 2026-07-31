# Definitions, in the same format as used by tmstruct, used by the
# various EB telecommands.
#
# This needs improving, since it is incomplete for some of the more 
# esoteric ones (SET_FDIR_FLAGS and PATCH). I'll get back to these 
# once the pressure is off.

# Header of all TC's
eb_header = [
    ( "magic",        ">u32" ),
    ( "blockType",    ">u1"  ),
    ( "instrumentId", ">u4"  ),
    ( "blockId",      ">u8"  ),
    ( "counter",      ">u11" ),
    ( "dataLen",      ">u16" ),
]

# TC-specific structures after the header has been stripped off.

eb_ret = [
    ( "retSeconds",    ">u32" ),
    ( "retFractional", ">u16" ),
]
    
eb_request_hk = [
    ( "qualifier", ">u8" ),
]

eb_patch = [
    ( "variant", ">u8" ),
]

eb_patch_single = [
    ( "variant",     ">u8"  ),
    ( "targetAddr",  ">u32" ),
    ( "patchLength", ">u16" ),
    ( "crc",         ">u16" ),
    # Data follows here.
]

eb_patch_initialise = [
    ( "variant",          ">u8"  ),
    ( "targetAddr",       ">u32" ),
    ( "actuaPatchLength", ">u16" ),
    ( "crc",              ">u16" ),
]

eb_patch_continuation = [
    ( "variant",          ">u8"  ),
    ( "sequenceCount",    ">u16" ),
    # Data follows here
]

eb_patch_finalise = [
    ( "variant",          ">u8"  ),
    ( "sequenceCount",    ">u16" ),
    # Data follows here
]

eb_dump = [
    ( "qualifier",   ">u8"  ),
    ( "dumpAddress", ">u32" ),
    ( "dumpLength",  ">u16" ),
]

eb_set_hk_rate = [
    ( "qualifier", ">u8"  ),
    ( "interval",  ">u16" ),
]

eb_monitor_addr = [
    ( "qualifier",      ">u8"  ),
    ( "monitorAddress", ">u32" ),
]

eb_abort = [
    ( "qualifier", ">u8" ),
]

eb_generic_tc = [
    ( "qualifier",    ">u8"   ),
    ( "binaryString", ">u128" ),
]

eb_safe = [
    ( "qualifier", ">u8" ),
]

eb_standby = [
    ( "aswImage",    ">u8" ),
    ( "forceLaunch", ">u8" ),
]

eb_acquisition = [
    ( "qualifier", ">u8" ),
]

eb_set_motor_configs = [
    ( "qualifier",        ">u8"  ),
    ( "motorPeakCurrent", ">u16" ),
    ( "reserved1",        ">u16" ),
    ( "motorSpeed",       ">u8"  ),
    ( "reserved2",        ">u16" ),
    ( "motorGuardTime",   ">u16" ),
    ( "motorRecVal",      ">u8"  ),
    ( "reserved3",        ">u32" ),
    ( "motorRelativeMax", ">u16" ),
    ( "reserved4",        ">u16" ),
]

eb_set_heater_configs = [
    ( "qualifier",      ">u8"  ),
    ( "mechUpperLimit", ">u16" ),
    ( "mechLowerLimit", ">u16" ),
    ( "detUpperLimit",  ">u16" ),
    ( "detLowerLimit",  ">u16" ),
]

eb_set_acq_configs = [
    ( "measurementMode",       ">u8"  ),
    ( "signalAveragingNumber", ">u8"  ),
    ( "reserved1",             ">u16" ),
    ( "sampleTimeSpacing",     ">u16" ),
    ( "measurementDuration",   ">u16" ),
    ( "startPosition",         ">u16" ),
    ( "endPosition",           ">u16" ),
    ( "detectorSelect",        ">u8"  ),
    ( "parkAtEnd",             ">u8"  ),
    ( "currentSol",            ">u16" ),
    ( "measurementTypeId",     ">u16" ),
    ( "measurementRunNo",      ">u16" ),
    ( "criticality",           ">u8"  ),
    ( "measurementTable",      ">u8"  ),
]

eb_set_tec_setpoint = [
    ( "qualifier", ">u8"  ),
    ( "setpoint",  ">u16" ),
]

eb_set_fdir_limits = [
    ( "qualifier",                                   ">u8"  ),
    ( "ebAnalogPlus12vWarnLow",                      ">u16" ),
    ( "ebAnalogMinus12vWarnLow",                     ">u16" ),
    ( "ebAnalogPlus5vWarnLow",                       ">u16" ),
    ( "ebAnalogPlus3v3WarnLow",                      ">u16" ),
    ( "ebAnalogTecRailWarnLow",                      ">u16" ),
    ( "ebAdc0vWarnLow",                              ">u16" ),
    ( "ebMicroProcessorInternalTemperatureWarnLow",  ">u16" ),
    ( "ebPeltierTemperatureWarnLow",                 ">u16" ),
    ( "ebInternalTrpThermistorTemperatureWarnLow",   ">u16" ),
    ( "ebPsuBoardThermistorTemperatureWarnLow",      ">u16" ),
    ( "ebInAsDetectorTecDriveCurrentSenseWarnLow",   ">u16" ),
    ( "obPlus3v3WarnLow",                            ">u16" ),
    ( "obPlus1v5WarnLow",                            ">u16" ),
    ( "obDigitalTrpWarnLow",                         ">u16" ),
    ( "obDetTemperatureWarnLow",                     ">u16" ),
    ( "obMechTemperatureWarnLow",                    ">u16" ),
    ( "obMotorTrpWarnLow",                           ">u16" ),
    ( "ebAnalogPlus12vWarnHigh",                     ">u16" ),
    ( "ebAnalogMinus12vWarnHigh",                    ">u16" ),
    ( "ebAnalogPlus5vWarnHigh",                      ">u16" ),
    ( "ebAnalogPlus3v3WarnHigh",                     ">u16" ),
    ( "ebAnalogTecRailWarnHigh",                     ">u16" ),
    ( "ebAdc0vWarnHigh",                             ">u16" ),
    ( "ebMicroProcessorInternalTemperatureWarnHigh", ">u16" ),
    ( "ebPeltierTemperatureWarnHigh",                ">u16" ),
    ( "ebInternalTrpThermistorTemperatureWarnHigh",  ">u16" ),
    ( "ebPsuBoardThermistorTemperatureWarnHigh",     ">u16" ),
    ( "ebInAsDetectorTecDriveCurrentSenseWarnHigh",  ">u16" ),
    ( "obPlus3v3WarnHigh",                           ">u16" ),
    ( "obPlus1v5WarnHigh",                           ">u16" ),
    ( "obDigitalTrpWarnHigh",                        ">u16" ),
    ( "obDetTemperatureWarnHigh",                    ">u16" ),
    ( "obMechTemperatureWarnHigh",                   ">u16" ),
    ( "obMotorTrpWarnHigh",                          ">u16" ),
    ( "ebAnalogPlus12vAlarmLow",                     ">u16" ),
    ( "ebAnalogMinus12vAlarmLow",                    ">u16" ),
    ( "ebAnalogPlus5vAlarmLow",                      ">u16" ),
    ( "ebAnalogPlus3v3AlarmLow",                     ">u16" ),
    ( "ebAnalogTecRailAlarmLow",                     ">u16" ),
    ( "ebAdc0vAlarmLow",                             ">u16" ),
    ( "ebMicroProcessorInternalTemperatureAlarmLow", ">u16" ),
    ( "ebPeltierTemperatureAlarmLow",                ">u16" ),
    ( "ebInternalTrpThermistorTemperatureAlarmLow",  ">u16" ),
    ( "ebPsuBoardThermistorTemperatureAlarmLow",     ">u16" ),
    ( "ebInAsDetectorTecDriveCurrentSenseAlarmLow",  ">u16" ),
    ( "obPlus3v3AlarmLow",                           ">u16" ),
    ( "obPlus1v5AlarmLow",                           ">u16" ),
    ( "obDigitalTrpAlarmLow",                        ">u16" ),
    ( "obDetTemperatureAlarmLow",                    ">u16" ),
    ( "obMechTemperatureAlarmLow",                   ">u16" ),
    ( "obMotorTrpAlarmLow",                          ">u16" ),
    ( "ebAnalogPlus12vAlarmHigh",                    ">u16" ),
    ( "ebAnalogMinus12vAlarmHigh",                   ">u16" ),
    ( "ebAnalogPlus5vAlarmHigh",                     ">u16" ),
    ( "ebAnalogPlus3v3AlarmHigh",                    ">u16" ),
    ( "ebAnalogTecRailAlarmHigh",                    ">u16" ),
    ( "ebAdc0vAlarmHigh",                            ">u16" ),
    ( "ebMicroProcessorInternalTemperatureAlarmHigh",">u16" ),
    ( "ebPeltierTemperatureAlarmHigh",               ">u16" ),
    ( "ebInternalTrpThermistorTemperatureAlarmHigh", ">u16" ),
    ( "ebPsuBoardThermistorTemperatureAlarmHigh",    ">u16" ),
    ( "ebInAsDetectorTecDriveCurrentSenseAlarmHigh", ">u16" ),
    ( "obPlus3v3AlarmHigh",                          ">u16" ),
    ( "obPlus1v5AlarmHigh",                          ">u16" ),
    ( "obDigitalTrpAlarmHigh",                       ">u16" ),
    ( "obDetTemperatureAlarmHigh",                   ">u16" ),
    ( "obMechTemperatureAlarmHigh",                  ">u16" ),
    ( "obMotorTrpAlarmHigh",                         ">u16" ),
]

eb_en_mech_board = [
    ( "enable", ">u8" ),
]

eb_en_det_board = [
    ( "enable", ">u8" ),
]

eb_en_mech_heater = [
    ( "enable", ">u8" ),
]

eb_en_det_heater = [
    ( "enable", ">u8" ),
]

eb_en_ob5v = [
    ( "enable", ">u8" ),
]

eb_ob_park = [
    ( "qualifier", ">u8" ),
]

eb_ob_homing = [
    ( "destination", ">u8" ),
]

eb_ob_hk = [
    ( "qualifier", ">u8" ),
]

eb_check_memory = [
    ( "qualifier",    ">u8"  ),
    ( "startAddress", ">u32" ),
    ( "length",       ">u16" ),
]

eb_goto = [
    ( "qualifier",   ">u8"  ),
    ( "gotoAddress", ">u32" ),
]

eb_copy_memory = [
    ( "qualifier",   ">u8"  ),
    ( "fromAddress", ">u32" ),
    ( "toAddress",   ">u32" ),
    ( "length",      ">u16" ),
]

eb_switch_rs422 = [
    ( "port", ">u8" ),
]

eb_set_tec_current = [
    ( "qualifier", ">u8"  ),
    ( "peltierDv", ">u16" ),
]
