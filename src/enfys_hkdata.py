import dataclasses
import numpy as np
import scipy
import warnings
import pt1000
import pathlib

@dataclasses.dataclass
class RawObHkRow:
    """A data class to hold a row within the OB HK data."""

    MOD_ID: int
    UNUSED1: int
    CMD_ID: int
    CMD_CNT: int
    ERROR_BYTE: int
    UNUSED2: int
    ERROR_MTR: int
    MTR_ERR_MSK_BYTE: int
    MTR_FLAGS_BYTE: int
    MTR_ABS_STEPS: int
    MTR_REL_STEPS: int
    UNUSED3: int
    MTR_CURRENT: int
    UNUSED4: int
    MTR_GUARD_SELECT: int
    MTR_CHOP: int
    UNUSED5: int
    MTR_SPEED: int
    UNUSED6: int
    PWR_STAT: int
    THRM_STATUS_BYTE: int
    THRM_MECH_OFF_SP: int
    THRM_MECH_ON_SP: int
    THRM_DET_OFF_SP: int
    THRM_DET_ON_SP: int
    SWIR_OFFSET: int
    MWIR_OFFSET: int
    HK_V_3V3: int
    HK_V_1V5: int
    DIGITAL_TRP: int
    DETEC_TRP: int
    MECH_TRP: int
    MOTOR_TRP: int
    HK_MECH_CUR: int
    UNUSED_ADC: int
    HK_SAMPLES: int
    UNUSED7: int
    CRC8: int
    timestamp: float = dataclasses.field(default=None, kw_only=True)

@dataclasses.dataclass
class ProcessedObHkRow(RawObHkRow):
    """HK row with added data decode"""

    voltage_3v3: float = dataclasses.field(default=None, kw_only=True)
    voltage_1v5: float = dataclasses.field(default=None, kw_only=True)
    digital_temperature: float = dataclasses.field(default=None, kw_only=True)
    detector_temperature: float = dataclasses.field(default=None, kw_only=True)
    mechanism_temperature: float = dataclasses.field(default=None, kw_only=True)
    motor_temperature: float = dataclasses.field(default=None, kw_only=True)
    mechanism_current: float = dataclasses.field(default=None, kw_only=True)

class EnfysObHkDataSet:
    """Base class"""

    # The model ID, as recorded in science and HK data.
    model_id: int = 0

    # The name for this model ID.
    model_name: str = "UNKNOWN"

    # Where the data came from - optional.
    origin_file: pathlib.Path = None

    # A brief text name for this data set.
    name: str

    # Temperature sensors.
    digital_pt1000: pt1000.PT1000
    detector_pt1000: pt1000.PT1000
    motor_pt1000: pt1000.PT1000
    mechanism_pt1000: pt1000.PT1000

    # Voltage and current sensors
    voltage_3v3_slope: float
    voltage_1v5_slope: float
    mech_current_slope: float

    def __init__(self, raw_rows=[], name=None, origin_file=None):
        if origin_file is not None:
            self.origin_file = pathlib.Path(origin_file)

        if name is not None:
            self.name = name
        self.raw_rows = raw_rows.copy()

        # If actual data has been supplied, we may as well scan
        # now, as that's what would be needed later. We *don't*
        # scan after every .append(), for example, as the implication
        # there is that the data is being built incrementally.
        if hasattr(self, "scan"):
            self.scan()

    # We'll treat it as somewhat list-like so that, having stored a bunch
    # of raw rows, you can then iterate/access the processed versions
    # via familiar construct.
    # e.g.:
    #
    # for processed_row in EnfysObHkDataSet(raw_rows):
    #     print(processed_row.motor_temperature)

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

        return ProcessedObHkRow(**dataclasses.asdict(row),
            voltage_3v3 = row.HK_V_3V3 * self.voltage_3v3_slope,
            voltage_1v5 = row.HK_V_1V5 * self.voltage_1v5_slope,
            digital_temperature = self.digital_pt1000(row.DIGITAL_TRP),
            detector_temperature = self.digital_pt1000(row.DETEC_TRP),
            mechanism_temperature = self.digital_pt1000(row.MECH_TRP),
            motor_temperature = self.digital_pt1000(row.MOTOR_TRP),
            mechanism_current = row.HK_MECH_CUR * self.mech_current_slope
        )

