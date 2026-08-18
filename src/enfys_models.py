from enfys_calibration import EnfysScienceRow, EnfysScienceDataSet
from egse_extensions import EbEgseExtensions, ObEgseExtensions

class BB2ScienceRow(EnfysScienceRow):
    model_id = 2
    model_name = "BB2"

    name = "BB2 science data"

    max_usable_adc_value = 60000

    swir_wavelength_model = [ 0.1211, 614.2 ]
    swir_low_to_medium_model = [ 29.5088, -662.9, 50 ]
    swir_medium_to_high_model = [ 29.3570, -212.3, 50 ]
    swir_dac_offset_model = [ -48.771, 0 ]

    mwir_wavelength_model = [ 0.2224, 1084.1 ]
    mwir_low_to_medium_model = [ 29.5080, -1073.4, 60 ]
    mwir_medium_to_high_model = [ 29.5566, -314.8, 110 ]
    mwir_dac_offset_model = [ -419.277, 0 ]
    
class EMScienceRow(EnfysScienceRow):
    model_id = 4
    model_name = "EM"

    name = "EM science data"

    max_usable_adc_value = 60000

    swir_wavelength_model = [ 0.1225, 675.5 ]
    swir_low_to_medium_model = [ 29.5546, -792.3, 100 ]
    swir_medium_to_high_model = [ 29.3347, -272.1, 150 ]
    swir_dac_offset_model = [ -48.8356, 0 ]

    mwir_wavelength_model = [ 0.2228, 1193.0 ]
    mwir_low_to_medium_model = [ 29.5842, -1265.2, 100 ]
    mwir_medium_to_high_model = [ 29.5825, -407.7, 100 ]
    mwir_dac_offset_model = [ -420.2187, 0 ]

class BB2ScienceDataSet(EnfysScienceDataSet):
    model_id = 2
    model_name = "BB2"

    name = "BB2 science data"

    max_usable_adc_value = 60000

    swir_wavelength_model = [ 0.1211, 614.2 ]
    swir_low_to_medium_model = [ 29.4968, 0, 0 ]
    swir_medium_to_high_model = [ 29.3227, 0, 0 ]
    swir_dac_offset_model = [ -48.771, 0 ]

    mwir_wavelength_model = [ 0.2224, 1084.1 ]
    mwir_low_to_medium_model = [ 29.4590, 0, 0 ]
    mwir_medium_to_high_model = [ 29.5825, 0, 0 ]
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

    swir_wavelength_model = [ 0.1225, 675.5 ]
    swir_low_to_medium_model = [ 29.5546, -792.3, 100 ]
    swir_medium_to_high_model = [ 29.3347, -272.1, 150 ]
    swir_dac_offset_model = [ -48.8356, 0 ]

    mwir_wavelength_model = [ 0.2228, 1193.0 ]
    mwir_low_to_medium_model = [ 29.5842, -1265.2, 100 ]
    mwir_medium_to_high_model = [ 29.5825, -407.7, 100 ]
    mwir_dac_offset_model = [ -420.2187, 0 ]

class EMEbScienceDataSet(EbEgseExtensions,EMScienceDataSet):
    pass

class EMObScienceDataSet(ObEgseExtensions,EMScienceDataSet):
    pass
    
