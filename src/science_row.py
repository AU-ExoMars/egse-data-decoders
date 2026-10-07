"""Encapsulate EB and OB science data rows."""

import dataclasses

from eb_tm_packet import (
    EbScienceDataCPacket,
    EbScienceDataNcPacket,
    EbScienceDataPacket,
    EbScienceRow,
)
from enfys_calibration import ObCalibration
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
    start_time: float | None = None
    end_time: float | None = None

    def __init__(self,
        src_row: "ScienceRow|ObScienceDataPacket|EbScienceRow|None" = None,
        src_header: EbScienceDataPacket|None = None,
    ) -> None:
        """Populate fields from a row of either valid type.

        In the case of EB data, we require an EB science data packet too,
        so we can capture information from its header.
        """
        # Get the list of defined dataclass fields.
        fields = {x.name for x in dataclasses.fields(self.__class__)}

        if isinstance(src_row, ScienceRow):
            for name in fields:
                if hasattr(src_row, name):
                    setattr(self, name, getattr(src_row, name))
            return

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
            return

        if isinstance(src_row, EbScienceRow):
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

@dataclasses.dataclass(init=False)
class TimestampedScienceRow(ScienceRow):
    """A science row with a timestamp.

    This timestamp can be any float that makes sense to the user
    and doesn't have to be derived from lobt, for example.
    """

    timestamp: float|None = None

    def __init__(self,
        src_row: ScienceRow|ObScienceDataPacket|EbScienceRow|None = None,
        src_header: EbScienceDataPacket|None = None,
        timestamp: float|None = None,
    ) -> None:
        """Store timestamp and pass the rest up."""
        self.timestamp = timestamp
        super().__init__(src_row, src_header)

@dataclasses.dataclass(init=False)
class ProcessedScienceRow(TimestampedScienceRow):
    """A science row with post-processing of data.

    Given instrument calibration objects, this class will perform
    decoding of data to real-world units.
    """

    swir_wavelength: float|None = None
    mwir_wavelength: float|None = None

    swir_scaled_dn: float|None = None
    mwir_scaled_dn: float|None = None

    swir_start_temperature: float|None = None
    heatsink_start_temperature: float|None = None
    mwir_start_temperature: float|None = None

    swir_end_temperature: float|None = None
    heatsink_end_temperature: float|None = None
    mwir_end_temperature: float|None = None

    def __init__(self,
        src_row: ScienceRow|ObScienceDataPacket|EbScienceRow|None = None,
        src_header: EbScienceDataPacket|None = None,
        timestamp: float|None = None,
        ob_calibration: ObCalibration|None = None,
    ) -> None:
        """Post-process of data to real-world values.

        The incoming data is passed up to super(), and then the
        supplied calibration object is used to convert various DN
        values into more useful real-world(ish) values.
        """
        super().__init__(src_row, src_header, timestamp)

        if ob_calibration is not None:
            self.swir_wavelength = ob_calibration.swir_wavelength_model(
                self.MTR_ABS_STEPS
            )
            self.mwir_wavelength = ob_calibration.mwir_wavelength_model(
                self.MTR_ABS_STEPS
            )

            self.swir_start_temperature = ob_calibration.swir_temperature_model(
                self.SWIR_START_TEMP
            )
            self.heatsink_start_temperature = ob_calibration.heatsink_temperature_model(
                self.HEATSINK_START_TEMP
            )
            self.mwir_start_temperature = ob_calibration.eb_peltier_temperature_model(
                self.MWIR_START_TEMP
            )

            self.swir_end_temperature = ob_calibration.swir_temperature_model(
                self.SWIR_END_TEMP
            )
            self.heatsink_end_temperature = ob_calibration.heatsink_temperature_model(
                self.HEATSINK_END_TEMP
            )
            self.mwir_end_temperature = ob_calibration.eb_peltier_temperature_model(
                self.MWIR_END_TEMP
            )

            if self.SWIR_HIGH < ob_calibration.max_usable_adc_value:
                self.swir_scaled_dn = self.SWIR_HIGH
            elif self.SWIR_MED < ob_calibration.max_usable_adc_value:
                self.swir_scaled_dn = ob_calibration.swir_medium_to_high_model(
                    self.SWIR_MED
                )
            else:
                self.swir_scaled_dn = ob_calibration.swir_medium_to_high_model(
                    ob_calibration.swir_low_to_medium_model(self.SWIR_LOW)
                )

            if self.MWIR_HIGH < ob_calibration.max_usable_adc_value:
                self.mwir_scaled_dn = self.MWIR_HIGH
            elif self.MWIR_MED < ob_calibration.max_usable_adc_value:
                self.mwir_scaled_dn = ob_calibration.mwir_medium_to_high_model(
                    self.MWIR_MED
                )
            else:
                self.mwir_scaled_dn = ob_calibration.mwir_medium_to_high_model(
                    ob_calibration.mwir_low_to_medium_model(self.MWIR_LOW)
                )
