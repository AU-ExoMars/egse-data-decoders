import dataclasses
import numpy as np
import scipy
import warnings
import pt1000
import pathlib
import obtmpacket

class TimestampedScienceRow(obtmpacket.ScienceDataPacket):
    timestamp:            float|None

class ProcessedScienceRow(TimestampedScienceRow):
    swir_wavelength:      float|None
    swir_dn:              float|None
    mwir_wavelength:      float|None
    mwir_dn:              float|None
    swir_dark_subtracted: float|None
    mwir_dark_subtracted: float|None
    swir_relative:        float|None
    mwir_relative:        float|None
    heatsink_temperature: float|None
    swir_temperature:     float|None

class EnfysScienceDataSet:
    """Base class"""

    # The model ID, as recorded in science and HK data.
    model_id: int = 0

    # The name for this model ID.
    model_name: str = "UNKNOWN"

    # Where the data came from - optional.
    origin_file: pathlib.Path = None

    # A brief text name for this data set.
    name: str

    # The ADC isn't linear at the top end of the scale, so
    # we need to have a threshold beyond which we'll switch to
    # a lower gain amplifier.
    max_usable_adc_value: int

    # Temperature sensors.
    heatsink_pt1000: pt1000.PT1000
    swir_pt1000: pt1000.PT1000

    # Chop targets. These are used to offset the combined
    # DN value so it's nominally zero at the chop points.
    swir_chop_target: int
    mwir_chop_target: int

    # Parameters which model the relationship between motor steps
    # and wavelength.
    swir_wavelength_model: tuple[float, float]
    mwir_wavelength_model: tuple[float, float]

    # Parameters which model the relationship between low and medium
    # gain DNs.
    swir_low_to_medium_model: tuple[float, float, int]
    mwir_low_to_medium_model: tuple[float, float, int]

    # Parameters which model the relationship between medium and high
    # gain DNs.
    swir_medium_to_high_model: tuple[float, float, int]
    mwir_medium_to_high_model: tuple[float, float, int]

    # Reflectivity of the "flat" (gold) data.
    flat_reflectivity = 0.95

    # Used in modelling.
    adc_cutover_bounds = [50, 300]

    def __init__(self, raw_rows=[], dark=None, flat=None, name=None, origin_file=None):
        if origin_file is not None:
            self.origin_file = pathlib.Path(origin_file)

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
            try:
                self.swir_medium_to_high_model = self._generate_gain_model(
                    "SWIR_MED", "SWIR_HIGH"
                )
            except (ValueError, TypeError) as e:
                warnings.warn(f"{self.name} swir_medium_to_high_model: {str(e)}")
                pass

        if model_name in ("swir_low_to_medium_model", None):
            try:
                self.swir_low_to_medium_model = self._generate_gain_model(
                    "SWIR_LOW", "SWIR_MED"
                )
            except (ValueError, TypeError) as e:
                warnings.warn(f"{self.name} swir_low_to_medium_model: {str(e)}")
                pass

        if model_name in ("mwir_medium_to_high_model", None):
            try:
                self.mwir_medium_to_high_model = self._generate_gain_model(
                    "MWIR_MED", "MWIR_HIGH"
                )
            except (ValueError, TypeError) as e:
                warnings.warn(f"{self.name} mwir_medium_to_high_model: {str(e)}")
                pass

        if model_name in ("mwir_low_to_medium_model", None):
            try:
                self.mwir_low_to_medium_model = self._generate_gain_model(
                    "MWIR_LOW", "MWIR_MED"
                )
            except (ValueError, TypeError) as e:
                warnings.warn(f"{self.name} mwir_low_to_medium_model: {str(e)}")
                pass

        # In the case where interpolators have already been created, they're
        # now likely invalid. So wipe them out to force re-creation if
        # needed.
        self._mwir_interpolator = None
        self._swir_interpolator = None


    def tune_models(self):
        """Update models for this data set.

        Some models benefit from a bit of tuning on the current data set.
        For example, the relationship between amplifier outputs has a nice
        slope, but an intercept that differs from experiment to experiment.
        Rather than trying to model this from TRPs, DAC offsets, etc, we
        can just look at the data and find the optimal intercept.
        """

        try:
            # Copy the model before we adjust it, since it's initially a class
            # variable.
            self.swir_medium_to_high_model = self.swir_medium_to_high_model.copy()

            # Redo the fit, using the data we have. This fit constrains the
            # slope and cutover terms and only adjusts the intercept.
            self.swir_medium_to_high_model[1] = self._generate_gain_model(
                "SWIR_MED", "SWIR_HIGH", tune_intercept=self.swir_medium_to_high_model
            )[0]
        except (ValueError, TypeError) as e:
            warnings.warn(f"{self.name} swir_medium_to_high_model: {str(e)}")
            pass

        try:
            self.swir_low_to_medium_model = self.swir_low_to_medium_model.copy()
            self.swir_low_to_medium_model[1] = self._generate_gain_model(
                "SWIR_LOW", "SWIR_MED", tune_intercept=self.swir_low_to_medium_model
            )[0]
        except (ValueError, TypeError) as e:
            warnings.warn(f"{self.name} swir_low_to_medium_model: {str(e)}")
            pass

        try:
            self.mwir_medium_to_high_model = self.mwir_medium_to_high_model.copy()
            self.mwir_medium_to_high_model[1] = self._generate_gain_model(
                "MWIR_MED", "MWIR_HIGH", tune_intercept=self.mwir_medium_to_high_model
            )[0]
        except (ValueError, TypeError) as e:
            warnings.warn(f"{self.name} mwir_medium_to_high_model: {str(e)}")
            pass

        try:
            self.mwir_low_to_medium_model = self.mwir_low_to_medium_model.copy()
            self.mwir_low_to_medium_model[1] = self._generate_gain_model(
                "MWIR_LOW", "MWIR_MED", tune_intercept=self.mwir_low_to_medium_model
            )[0]
        except (ValueError, TypeError) as e:
            warnings.warn(f"{self.name} mwir_low_to_medium_model: {str(e)}")
            pass

        # Invalidate interpolators.
        self._mwir_interpolator = None
        self._swir_interpolator = None

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

    def _generate_gain_model(self, lower_attr, upper_attr, tune_intercept=None):
        cal = np.array([
            [ getattr(row, lower_attr), getattr(row, upper_attr) ]
            for row in self.raw_rows
        ])
        cal = cal[(cal[:,1] < self.max_usable_adc_value) & (cal[:,0] > 0)]

        if tune_intercept is None:
            model, covar = scipy.optimize.curve_fit(
                gain_function, cal[:,0], cal[:,1],
                bounds=(
                    (-np.inf, -np.inf, self.adc_cutover_bounds[0]),
                    (np.inf, np.inf, self.adc_cutover_bounds[1]),
                )
            )
            # Trim precision down a bit - we don't need full float
            # accuracy.

            # Slope can be to 3 dp.
            model[0] = np.round(model[0], 3)
            # Intercept can be to 1 dp.
            model[1] = np.round(model[1], 1)
            # Cutover is an integer.
            model[2] = np.ceil(model[2])
        else:
            a, b, cutover = tune_intercept
            model, covar = scipy.optimize.curve_fit(
                lambda x, b: gain_function(x, a, b, cutover),
                cal[:,0], cal[:,1],
            )
            model[0] = np.round(model[0], 1)

        cond = np.linalg.cond(covar)
        if cond > 1e8:
            raise ValueError(f"Model is ill-conditioned (condition number={cond:.3g})")

        return [ float(x) for x in model ]

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

        dn -= self.swir_chop_target

        return dn

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

        dn -= self.mwir_chop_target

        return dn

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
            # When we've got a slice, use it to build a comprehension
            # recursively.
            return [self[i] for i in range(idx.start, idx.stop, 1 if idx.step is None else idx.step)]

        row = self.raw_rows[idx]

        swir_dn = self._swir_dn(row)
        mwir_dn = self._mwir_dn(row)

        swir_dark_subtracted = None
        mwir_dark_subtracted = None
        swir_relative = None
        mwir_relative = None

        if self.dark is not None:
            swir_dark_subtracted = swir_dn - self.dark.swir_interpolator(row.ABS_STEPS)
            mwir_dark_subtracted = mwir_dn - self.dark.mwir_interpolator(row.ABS_STEPS)

            if self.flat is not None:
                flatval = self.flat.swir_interpolator(row.ABS_STEPS)-self.dark.swir_interpolator(row.ABS_STEPS)

                # Take some care here.
                if swir_dark_subtracted <= 0:
                    # If the dark-adjusted value is darker than dark, then
                    # the relative value should be zero.
                    swir_relative = 0
                elif swir_dark_subtracted > flatval/self.flat_reflectivity:
                    # If the dark-adjusted value is brighter than the flat
                    # value when adjusted for the flat's reflectivity, the
                    # relative value should be unity.
                    swir_relative = 1
                else:
                    swir_relative = swir_dark_subtracted*self.flat_reflectivity/flatval


                flatval = self.flat.mwir_interpolator(row.ABS_STEPS)-self.dark.mwir_interpolator(row.ABS_STEPS)
                if mwir_dark_subtracted <= 0:
                    mwir_relative = 0
                elif mwir_dark_subtracted > flatval/self.flat_reflectivity:
                    mwir_relative = 1
                else:
                    mwir_relative = mwir_dark_subtracted*self.flat_reflectivity/flatval

        heatsink_temperature = None
        if row.HT_SINK_TEMP is not None:
            heatsink_temperature = self.heatsink_pt1000(row.HT_SINK_TEMP)

        swir_temperature = None
        if row.SWIR_TEMP is not None:
            swir_temperature = self.swir_pt1000(row.SWIR_TEMP)

        return ProcessedScienceRow(**dataclasses.asdict(row),
            swir_wavelength=self.steps_to_swir_wavelength(row.ABS_STEPS),
            mwir_wavelength=self.steps_to_mwir_wavelength(row.ABS_STEPS),

            swir_dn=swir_dn,
            mwir_dn=mwir_dn,

            swir_dark_subtracted = swir_dark_subtracted,
            mwir_dark_subtracted = mwir_dark_subtracted,

            swir_relative = swir_relative,
            mwir_relative = mwir_relative,

            heatsink_temperature = heatsink_temperature,
            swir_temperature = swir_temperature,
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
