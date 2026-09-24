import numpy as np
import scipy
import warnings
import pt1000
import pathlib
import obtmpacket

class TimestampedObHkRow(obtmpacket.HkPacket):
    timestamp:  float | None

class ProcessedObHkRow(TimestampedObHkRow):
    """HK row with added data decode"""

    voltage_3v3: float|None = None
    voltage_1v5: float|None = None
    digital_temperature: float|None = None
    detector_temperature: float|None = None
    mechanism_temperature: float|None = None
    motor_temperature: float|None = None
    mechanism_current: float|None = None

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

        return ProcessedObHkRow(src=row,
            voltage_3v3 = row.HK_V_3V3 * self.voltage_3v3_slope,
            voltage_1v5 = row.HK_V_1V5 * self.voltage_1v5_slope,
            digital_temperature = self.digital_pt1000(row.DIGITAL_TRP),
            detector_temperature = self.digital_pt1000(row.DETEC_TRP),
            mechanism_temperature = self.digital_pt1000(row.MECH_TRP),
            motor_temperature = self.digital_pt1000(row.MOTOR_TRP),
            mechanism_current = row.HK_MECH_CUR * self.mech_current_slope
        )

