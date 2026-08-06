from enfys_calibration import EnfysScienceRow

class BB2ScienceRow(EnfysScienceRow):
    model_id = 2
    max_usable_adc_value = 60000

    swir_wavelength_model = lambda abs_steps: abs_steps*0.1211 + 614.2
    mwir_wavelength_model = lambda abs_steps: abs_steps*0.2224 + 1084.1
    swir_low_to_medium_model = lambda dn: 29.4968*dn
    mwir_low_to_medium_model = lambda dn: 29.4590*dn
    swir_medium_to_high_model = lambda dn: 29.3227*dn
    mwir_medium_to_high_model = lambda dn: 29.5825*dn
    swir_dac_offset_correction = lambda dn, offset: dn - 48.771*offset
    mwir_dac_offset_correction = lambda dn, offset: dn - 419.277*offset

class EMScienceRow(EnfysScienceRow):
    model_id = 4
    max_usable_adc_value = 60000

    swir_wavelength_model = lambda abs_steps: abs_steps*0.1225 + 675.5
    mwir_wavelength_model = lambda abs_steps: abs_steps*0.2228 + 1193.0
    swir_low_to_medium_model = lambda dn: 32.1265*dn
    mwir_low_to_medium_model = lambda dn: 29.1412*dn
    swir_medium_to_high_model = lambda dn: 28.5025*dn
    mwir_medium_to_high_model = lambda dn: 28.6571*dn
    swir_dac_offset_correction = lambda dn, offset: dn - 48.8356*offset
    mwir_dac_offset_correction = lambda dn, offset: dn - 420.2187*offset

