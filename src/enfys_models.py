from enfys_sciencedata import EnfysScienceDataSet
from enfys_hkdata import EnfysObHkDataSet
from egse_extensions import EbEgseExtensions, ObEgseExtensions
from pt1000 import PT1000

class BB2ScienceDataSet(EnfysScienceDataSet):
    model_id = 2
    model_name = "BB2"

    name = "BB2 science data"

    max_usable_adc_value = 60000

    heatsink_pt1000 = PT1000(10000, 1021.31)
    swir_pt1000 = PT1000(10000, 1013.02)

    swir_chop_target = 5000
    mwir_chop_target = 5000

    swir_wavelength_model = [ 0.1218, 607.8 ]
    mwir_wavelength_model = [ 0.2165, 1096.1 ]

    swir_low_to_medium_model = [29.523, -715.3, 58]
    swir_medium_to_high_model = [29.398, -304.0, 50]

    mwir_low_to_medium_model = [29.591, -1137.5, 69]
    mwir_medium_to_high_model = [29.588, -357.1, 115]

class BB2EbScienceDataSet(BB2ScienceDataSet,EbEgseExtensions):
    pass

class BB2ObScienceDataSet(BB2ScienceDataSet,ObEgseExtensions):
    pass
    
class EMScienceDataSet(EnfysScienceDataSet):
    model_id = 4
    model_name = "EM"

    name = "EM science data"

    max_usable_adc_value = 60000

    # FIXME - these need calibrating.
    heatsink_pt1000 = PT1000(10046, 1006)
    swir_pt1000 = PT1000(9906, 988)

    swir_chop_target = 5000
    mwir_chop_target = 15000

    swir_wavelength_model = [ 0.1218, 680.9 ]
    mwir_wavelength_model = [ 0.2220, 1192.9 ]

    swir_low_to_medium_model = [27.873, 7653.9, 145]
    swir_medium_to_high_model = [28.208, 8561.3, 208]

    mwir_low_to_medium_model = [27.718, 7218.6, 197]
    mwir_medium_to_high_model = [28.125, 7618.0, 148]

class EMEbScienceDataSet(EbEgseExtensions,EMScienceDataSet):
    pass

class EMObScienceDataSet(ObEgseExtensions,EMScienceDataSet):
    pass
    
class BB2ObHkDataSet(EnfysObHkDataSet):
    model_id = 2
    model_name = "BB2"
    name = "BB2 OB HK data"

    # Nominal values, need calibration
    digital_pt1000 = PT1000(1000, 1060.74)
    detector_pt1000 = PT1000(1000, 1079.80)
    motor_pt1000 = PT1000(1000, 1017.55)
    mechanism_pt1000 = PT1000(1000, 1042.92)

    # Numbers from SWIS.
    voltage_3v3_slope = 1.0445e-4
    voltage_1v5_slope = 5.2413e-5
    mech_current_slope = 3.3897e-3

class EMObHkDataSet(EnfysObHkDataSet):
    model_id = 4
    model_name = "EM"
    name = "EM OB HK data"

    # Nominal values, need calibration
    digital_pt1000 = PT1000(1000, 1035.40)
    detector_pt1000 = PT1000(1000, 1033.15)
    motor_pt1000 = PT1000(1000, 1053.38)
    mechanism_pt1000 = PT1000(1000, 1028.94)

    # Numbers from SWIS.
    voltage_3v3_slope = 1.2231e-4
    voltage_1v5_slope = 6.1367e-5
    mech_current_slope = 3.7531e-3
