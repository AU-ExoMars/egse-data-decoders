"""Encapsulate EB and OB science data rows."""

import dataclasses

from eb_tm_packet import (
    EbScienceDataCPacket,
    EbScienceDataNcPacket,
    EbScienceDataPacket,
    EbScienceRow,
)
from ob_tm_packet import ObScienceDataPacket


@dataclasses.dataclass(init=False)
class ScienceRow:
    """A merger of what the OB and what the EB can provide.

    This class is intended to simplify handling data from either source, since
    much of what we usually want to look at is present in both (unsurprisingly)
    and it would be nice if some of the downstream processing could handle
    either data type.
    """

    # The class which originated this data. For OB rows, it's just the packet
    # type. For EN rows, it's the type of the originating science packet.
    source_type: (type(ObScienceDataPacket)|type(EbScienceDataCPacket)|
        type(EbScienceDataNcPacket)|None
    ) = None

    # From OB science data. We'll also populate
    # fields here from EB science rows.
    MOD_ID: int|None = None
    CMD_ID: int|None = None
    CMD_CNT: int|None = None
    ERROR_BYTE: int|None = None
    MTR_ABS_STEPS: int|None = None
    THRM_STATUS_BYTE: int|None = None
    SWIR_OFFSET: int|None = None
    MWIR_OFFSET: int|None = None
    SCI_ADC_SAMPLES: int|None = None
    SCI_ADC_SKIP: int|None = None
    SWIR_HIGH: int|None = None
    SWIR_MED: int|None = None
    SWIR_LOW: int|None = None
    MWIR_HIGH: int|None = None
    MWIR_MED: int|None = None
    MWIR_LOW: int|None = None
    HT_SINK_TEMP: int|None = None
    SWIR_TEMP: int|None = None
    CRC: int|None = None

    # From EB science header, but pruned for
    # things that are already present in OB rows.
    PACKET_NUMBER: int|None = None
    SOL_NO: int|None = None
    MEASUREMENT_TYPE_ID: int|None = None
    MEASUREMENT_RUN_NO: int|None = None
    START_TIME_S: int|None = None
    START_TIME_MS: int|None = None
    END_TIME_S: int|None = None
    END_TIME_MS: int|None = None
    HEATSINK_START_TEMP: int|None = None
    HEATSINK_END_TEMP: int|None = None
    SWIR_START_TEMP: int|None = None
    SWIR_END_TEMP: int|None = None
    MWIR_START_TEMP: int|None = None
    MWIR_END_TEMP: int|None = None
    START_MTR_ABS_STEPS: int|None = None
    SAMPLE_DELAY: int|None = None
    FPGA_SAMPLES: int|None = None
    ACQUISITION_MODE: int|None = None
    AVERAGING_NUMBER: int|None = None

    lobt: float|None = None
    startTime: float | None = None
    endTime: float | None = None

    def __init__(self,
        src_row: ObScienceDataPacket|EbScienceRow|None = None,
        src_header: EbScienceDataPacket|None = None,
    ) -> None:
        """Populate fields from a row of either valid type.

        In the case of EB data, we require an EB science data packet too,
        so we can capture information from its header.
        """
        # Get the list of fields defined above.
        fields = {x.name for x in dataclasses.fields(self.__class__)}

        seen = set()
        if isinstance(src_row, ObScienceDataPacket):
            if src_header is not None:
                raise TypeError("src_header is only valid for EB science rows")

            # Source type is the row type.
            self.source_type = type(src_row)

            # BitstructTemplateClass objects can behave like dicts.
            for name, value in src_row.items():
                if name in fields:
                    setattr(self, name, value)
                    seen.add(name)

            # We can fill out a few other fields from OB data, by
            # duplication.
            self.HEATSINK_START_TEMP = self.HT_SINK_TEMP
            self.HEATSINK_END_TEMP = self.HT_SINK_TEMP
            self.SWIR_START_TEMP = self.SWIR_TEMP
            self.SWIR_END_TEMP = self.SWIR_TEMP
            self.START_MTR_ABS_STEPS = self.MTR_ABS_STEPS
            # FPGA_SAMPLES perhaps?

        elif isinstance(src_row, EbScienceRow):
            if not isinstance(src_header, EbScienceDataPacket):
                raise TypeError("src_header must also be present for EB science rows")

            # Source type is the packet type.
            self.source_type = type(src_header)

            # BitstructTemplateClass objects can behave like dicts.
            for name, value in src_row.items():

                # Inconsistent naming in tmstruct.py
                if name == "ABS_STEPS":
                    name = "MTR_ABS_STEPS"

                if name in fields:
                    setattr(self, name, value)
                    seen.add(name)

                for name, value in src_header.items():
                    if name in fields and name not in seen:
                        setattr(self, name, value)
                        seen.add(name)

