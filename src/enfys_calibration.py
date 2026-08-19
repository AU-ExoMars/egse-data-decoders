import dataclasses
import numpy as np
import scipy

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
    SWIR_OFFSET: int
    MWIR_OFFSET: int
    HT_SINK_TEMP: int = dataclasses.field(default=None, kw_only=True)
    SWIR_TEMP: int = dataclasses.field(default=None, kw_only=True)
    timestamp: float = dataclasses.field(default=None, kw_only=True)

@dataclasses.dataclass
class ProcessedScienceRow(RawScienceRow):
    swir_wavelength: float
    swir_dn: float
    mwir_wavelength: float
    mwir_dn: float
    
class EnfysScienceRow:
    """Base class"""

    # The model ID, as recorded in science and HK data.
    model_id: int = 0

    # The name for this model ID.
    model_name: str = "UNKNOWN"

    # A brief text name for this data set.
    name: str

    # The ADC isn't linear at the top end of the scale, so
    # we need to have a threshold beyond which we'll switch to
    # a lower gain amplifier.
    max_usable_adc_value: int

    # Parameters which model the relationship between motor steps
    # and wavelength.
    swir_wavelength_model: tuple[float, float]
    mwir_wavelength_model: tuple[float, float]

    # Parameters which model the relationship between low and medium
    # gain DNs.
    swir_low_to_medium_model: tuple[float, float]
    mwir_low_to_medium_model: tuple[float, float]

    # Parameters which model the relationship between medium and high
    # gain DNs.
    swir_medium_to_high_model: tuple[float, float]
    mwir_medium_to_high_model: tuple[float, float]

    # Parameters which, given a DAC offset value, gives the correction
    # that should be applied to the high DN scale.
    swir_dac_offset_model: tuple[float, float]
    mwir_dac_offset_model: tuple[float, float]

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
        return self.raw.ABS_STEPS*self.swir_wavelength_model[0] + self.swir_wavelength_model[1]
        
    @property
    def mwir_wavelength(self):
        return self.raw.ABS_STEPS*self.mwir_wavelength_model[0] + self.mwir_wavelength_model[1]

    @property
    def swir_dn(self):
        raise Exception("ARGH swir_dn is obsolete")
        if self.raw.SWIR_HIGH < self.max_usable_adc_value:
            dn = self.raw.SWIR_HIGH
        elif self.raw.SWIR_MED < self.max_usable_adc_value:
            dn = gain_function(self.raw.SWIR_MED, *self.swir_medium_to_high_model)
        else:
            dn = gain_function(
                gain_function(self.raw.SWIR_LOW, *self.swir_low_to_medium_model),
                *self.swir_medium_to_high_model
            )

        return round(dn[0] + 
            self.swir_dac_offset_model[0]*self.swir_offset + self.swir_dac_offset_model[1]
        )

    @property
    def mwir_dn(self):
        raise Exception("ARGH mwir_dn is obsolete")
        if self.raw.MWIR_HIGH < self.max_usable_adc_value:
            dn = [self.raw.MWIR_HIGH]
        elif self.raw.MWIR_MED < self.max_usable_adc_value:
            dn = gain_function(self.raw.MWIR_MED, *self.mwir_medium_to_high_model)
        else:
            dn = gain_function(
                gain_function(self.raw.MWIR_LOW, *self.mwir_low_to_medium_model),
                *self.mwir_medium_to_high_model
            )

        return round(dn[0] + 
            self.mwir_dac_offset_model[0]*self.mwir_offset + self.mwir_dac_offset_model[1]
        )

class EnfysScienceDataSet:
    """Base class"""

    # The model ID, as recorded in science and HK data.
    model_id: int = 0

    # The name for this model ID.
    model_name: str = "UNKNOWN"

    # A brief text name for this data set.
    name: str

    # The ADC isn't linear at the top end of the scale, so
    # we need to have a threshold beyond which we'll switch to
    # a lower gain amplifier.
    max_usable_adc_value: int

    # Parameters which model the relationship between motor steps
    # and wavelength.
    swir_wavelength_model: tuple[float, float]
    mwir_wavelength_model: tuple[float, float]

    # Parameters which model the relationship between low and medium
    # gain DNs.
    swir_low_to_medium_model: tuple[float, float]
    mwir_low_to_medium_model: tuple[float, float]

    # Parameters which model the relationship between medium and high
    # gain DNs.
    swir_medium_to_high_model: tuple[float, float]
    mwir_medium_to_high_model: tuple[float, float]

    # Parameters which, given a DAC offset value, gives the correction
    # that should be applied to the high DN scale.
    swir_dac_offset_model: tuple[float, float]
    mwir_dac_offset_model: tuple[float, float]

    # Reflectivity of the "flat" (gold) data.
    flat_reflectivity = 0.95

    # Used in modelling.
    adc_cutover_bounds = [50, 300]

    def __init__(self, raw_rows=[], dark=None, flat=None, name=None):
        if name is not None:
            self.name = name
        self.raw_rows = raw_rows.copy()

        # If these are specified, then the *_dn properties will
        # take them into account (i.e. subtract dark, scale by flat).
        if flat is not None and dark is None:
            raise ValueError("If flat are specified then dark are needed too")
        self.dark = dark
        self.flat = flat

        # Sometimes, it's useful to be able to get an approximation
        # of the value at an arbitrary motor position. So we'll provide
        # swir_ and mwir_ interpolator properties, which get filled out
        # on demand.
        self._swir_interpolator = None
        self._mwir_interpolator = None

        # If actual data has been supplied, we may as well scan
        # now, as that's what would be needed later. We *don't*
        # scan after every .append(), for example, as the implication
        # there is that the data is being built incrementally.
        if hasattr(self, "scan"):
            self.scan()

    def steps_to_swir_wavelength(self, steps):
        return steps*self.swir_wavelength_model[0] + self.swir_wavelength_model[1]

    def steps_to_mwir_wavelength(self, steps):
        return steps*self.mwir_wavelength_model[0] + self.mwir_wavelength_model[1]

    def generate_gain_models(self, model_name=None):
        if model_name in ("swir_medium_to_high_model", None):
            self.swir_medium_to_high_model = self._generate_gain_model(
                "SWIR_MED", "SWIR_HIGH"
            )
        if model_name in ("swir_low_to_medium_model", None):
            self.swir_low_to_medium_model = self._generate_gain_model(
                "SWIR_LOW", "SWIR_MED"
            )
        if model_name in ("mwir_medium_to_high_model", None):
            self.mwir_medium_to_high_model = self._generate_gain_model(
                "MWIR_MED", "MWIR_HIGH"
            )
        if model_name in ("mwir_low_to_medium_model", None):
            self.mwir_low_to_medium_model = self._generate_gain_model(
                "MWIR_LOW", "MWIR_MED"
            )

    @property
    def swir_interpolator(self):
        if self._swir_interpolator is None:
            self._swir_interpolator = self._make_interpolator(
                [ [row.ABS_STEPS, row.swir_dn] for row in self ]
            )
        return self._swir_interpolator

    @property
    def mwir_interpolator(self):
        if self._mwir_interpolator is None:
            self._mwir_interpolator = self._make_interpolator(
                [ [row.ABS_STEPS, row.mwir_dn] for row in self ]
            )
        return self._mwir_interpolator

    def _make_interpolator(self, xy):
        # scipy requires strictly increasing x values, so 
        # we need to do some preprocessing.

        # Rather than throwing stuff away, we'll take averages for
        # duplicate values.
        data = {}
        for x, y in xy:
            if x not in data:
                data[x] = [ y, 1 ]
            else:
                data[x] = [ data[x][0] + y, data[x][1] + 1]
        data = np.array([ [k, data[k][0]/data[k][1]] for k in sorted(data.keys()) ])
        return scipy.interpolate.CubicSpline(data[:,0], data[:,1], extrapolate=False)

    def _generate_gain_model(self, lower_attr, upper_attr):
        cal = np.array([ 
            [ getattr(row, lower_attr), getattr(row, upper_attr) ]
            for row in self.raw_rows 
        ])
        model = scipy.optimize.curve_fit(
            gain_function, 
            cal[cal[:,1] < self.max_usable_adc_value, 0], 
            cal[cal[:,1] < self.max_usable_adc_value, 1], 
            bounds=(
                (-np.inf, -np.inf, self.adc_cutover_bounds[0]),
                (np.inf, np.inf, self.adc_cutover_bounds[1]),
            )
        )
        return model[0]

    def _swir_dn(self, row):
        if row.SWIR_HIGH < self.max_usable_adc_value:
            dn = row.SWIR_HIGH
        elif row.SWIR_MED < self.max_usable_adc_value:
            dn = gain_function(row.SWIR_MED, *self.swir_medium_to_high_model)
        else:
            dn = gain_function(
                gain_function(row.SWIR_LOW, *self.swir_low_to_medium_model),
                *self.swir_medium_to_high_model
            )

        combined = dn + self.swir_dac_offset_model[0]*row.SWIR_OFFSET + self.swir_dac_offset_model[1]
        if self.dark is not None:
            combined -= self.dark.swir_interpolator(row.ABS_STEPS)
        if self.flat is not None:
            divisor = self.flat.swir_interpolator(row.ABS_STEPS)-self.dark.swir_interpolator(row.ABS_STEPS)
            if divisor == 0:
                combined = None
            else:
                combined = combined*self.flat_reflectivity/divisor
        return combined

    def _mwir_dn(self, row):
        if row.MWIR_HIGH < self.max_usable_adc_value:
            dn = row.MWIR_HIGH
        elif row.MWIR_MED < self.max_usable_adc_value:
            dn = gain_function(row.MWIR_MED, *self.mwir_medium_to_high_model)
        else:
            dn = gain_function(
                gain_function(row.MWIR_LOW, *self.mwir_low_to_medium_model),
                *self.mwir_medium_to_high_model
            )

        combined = dn + self.mwir_dac_offset_model[0]*row.MWIR_OFFSET + self.mwir_dac_offset_model[1]
        if self.dark is not None:
            combined -= self.dark.mwir_interpolator(row.ABS_STEPS)
        if self.flat is not None:
            divisor = self.flat.mwir_interpolator(row.ABS_STEPS)-self.dark.mwir_interpolator(row.ABS_STEPS)
            if divisor == 0:
                combined = None
            else:
                combined = combined*self.flat_reflectivity/divisor
        return combined


    # We'll treat it as somewhat list-like so that, having stored a bunch
    # of raw rows, you can then iterate/access the processed versions
    # via familiar construct.
    # e.g.:
    # 
    # for processed_row in EnfysScienceDataSet(raw_rows):
    #     print(processed_row.swir_wavelength, processed_row.swir_dn)

    def append(self, rows):
        """This isn't quite the same as a normal list append
        because it handles appending another list. Implementing
        the __add__ method would be rather more difficult than
        just cheating here because __add__ creates a whole new
        instance.
        """
        if isinstance(rows, list):
            self.raw_rows += rows
        else:
            self.raw_rows.append(rows)

    def __len__(self):
        return len(self.raw_rows)

    def __iter__(self):
        for i in range(len(self.raw_rows)):
            yield self[i]

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            ret = []
            for row in self.raw_rows[idx]:
                ret.append(ProcessedScienceRow(**dataclasses.asdict(row),
                    swir_wavelength=self.steps_to_swir_wavelength(row.ABS_STEPS), 
                    swir_dn=self._swir_dn(row),
                    mwir_wavelength=self.steps_to_mwir_wavelength(row.ABS_STEPS), 
                    mwir_dn=self._mwir_dn(row),
                ))
            return ret

        row = self.raw_rows[idx]
        return ProcessedScienceRow(**dataclasses.asdict(row),
            swir_wavelength=self.steps_to_swir_wavelength(row.ABS_STEPS), 
            swir_dn=self._swir_dn(row),
            mwir_wavelength=self.steps_to_mwir_wavelength(row.ABS_STEPS), 
            mwir_dn=self._mwir_dn(row),
        )

def gain_function(x, a, b, cutover):
    """Attempt to emulate the behaviour of the ADCs at low values.

    This function is linear for values above cutover and is a power curve for below cutover,
    where the power curve is chosen to meet the linear portion and to have
    the same slope as it (i.e. a) at that point.
    
    It's a very simple model of the ADC, capturing its nonlinearity close to zero.

    Uses np.piecewise, since this allows matrix operations and hence 
    scipy.optimize.curve_fit can use it.
    """
    if isinstance(x, np.ndarray) or isinstance(x, list):
        return np.piecewise(np.array(x),
            [ 
                x < cutover, 
                x >= cutover 
            ],
            [
                ((x[x < cutover]/cutover)**(a*cutover/(a*cutover + b)))*(a*cutover+b),
                a*x[x >= cutover] + b
            ]
        )

    # The scalar case.
    return a*x+b if x >= cutover else ((x/cutover)**(a*cutover/(a*cutover + b)))*(a*cutover+b)
