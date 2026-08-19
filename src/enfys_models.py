from enfys_calibration import EnfysScienceDataSet
from egse_extensions import EbEgseExtensions, ObEgseExtensions

class BB2ScienceDataSet(EnfysScienceDataSet):
    model_id = 2
    model_name = "BB2"

    name = "BB2 science data"

    max_usable_adc_value = 60000

    swir_wavelength_model = [ 0.1218, 607.8 ]
    swir_low_to_medium_model = [ 29.5138, -610.6, 50 ]
    swir_medium_to_high_model = [ 29.3979, -211.9, 50 ]
    swir_dac_offset_model = [ -48.771, 0 ]

    mwir_wavelength_model = [ 0.2165, 1096.1 ]
    mwir_low_to_medium_model = [ 29.5592, -1001.5, 61.4 ]
    mwir_medium_to_high_model = [ 29.5533, -244.1, 109 ]
    mwir_dac_offset_model = [ -419.277, 0 ]

class BB2EbScienceDataSet(BB2ScienceDataSet,EbEgseExtensions):
    pass

class BB2ObScienceDataSet(BB2ScienceDataSet,ObEgseExtensions):
    pass
    
class EMScienceDataSet(EnfysScienceDataSet):
    model_id = 4
    model_name = "EM"

    name = "EM science data"
    max_usable_adc_value = 60000

    swir_wavelength_model = [ 0.1218, 680.9 ]
    swir_low_to_medium_model = [ 29.5546, -792.3, 100 ]
    swir_medium_to_high_model = [ 29.3347, -272.1, 150 ]
    swir_dac_offset_model = [ -48.8356, 0 ]

    mwir_wavelength_model = [ 0.2220, 1192.9 ]
    mwir_low_to_medium_model = [ 29.5842, -1265.2, 100 ]
    mwir_medium_to_high_model = [ 29.5825, -407.7, 100 ]
    mwir_dac_offset_model = [ -420.2187, 0 ]

class EMEbScienceDataSet(EbEgseExtensions,EMScienceDataSet):
    pass

class EMObScienceDataSet(ObEgseExtensions,EMScienceDataSet):
    pass
    
