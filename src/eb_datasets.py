"""Extend EnfysScienceDataSet with functions for handling EB data."""
import dataclasses
import typing

from eb_tc_packet import EbTcSetAcqConfigs
from eb_tm_packet import EbScienceDataPacket
from enfys_sciencedata import EnfysScienceDataSet
from enfys_hkdata import EnfysHkDataSet
from science_row import ProcessedScienceRow
from eb_hk import ProcessedEbHk
from enfys_models import ob_models


@dataclasses.dataclass
class AcquisitionInfo:
    """A data class for holding information about an acquisition."""

    start: int
    end: int|None
    config: EbTcSetAcqConfigs

class EbScienceDataSet(EnfysScienceDataSet):
    """A subclass that provides methods for handling EB science data."""

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Class constructor.

        Initialise _latest_acq_config and _acquisitions for use later.
        """
        super().__init__(*args, **kwargs)

        self._latest_acq_config = None
        self._acquisitions = []

    def scan(self) -> None:
        """Make sure the dataset is in a consistent state.

        i.e. patch up the "end" locations in the acquisition list.
        """
        for i, acq in enumerate(self._acquisitions[:-1]):
            if acq.end is None:
                acq.end = self._acquisitions[i+1].start-1
        self._acquisitions[-1].end = len(self.rows)-1

        self._scanned = True

    def append(self, rows: ProcessedScienceRow|list[ProcessedScienceRow]) -> None:
        """Check data type before calling parent method.

        To get a ProcessedScienceRow, we need info that's not in
        an EB science row (it's in the header). So we need processing
        to have happened before append is called.
        """
        if (
            (
                isinstance(rows, list) and
                    any(not isinstance(x, ProcessedScienceRow) for x in rows)
            ) or (
                not isinstance(rows, list) and
                    not isinstance(rows, ProcessedScienceRow)
            )
        ):
            raise ValueError("This class can only accept processed science rows")
        super().append(rows)

    @property
    def acquisitions(self) -> AcquisitionInfo:
        """Return a filtered list of acquisitions.

        Acquistions are akin to the OB data's "sweeps", but are easier
        to spot when you've got access to TC data.
        """
        if not self._scanned:
            self.scan()

        # This removes acquisitions that have no measurements.
        # It's safer to do this here than in scan(), because
        # the final acquisition may gain points later even if
        # it doesn't right now.
        return [
            acq for acq in self._acquisitions
                if acq.end >= acq.start
        ]


    def store_acq_config(self, config: EbTcSetAcqConfigs) -> None:
        """Store an acquisition config packet.

        When we start an acquisition later, we'll use this.
        """
        self._latest_acq_config = config

    def start_acquisition(self) -> None:
        """Add an acquisition to the list.

        When we see an ACQUISITION TC, we can call this to
        note down where the acquisition starts, and what the
        active acquisition config is at that point.
        """
        # For now, the acquisition value is a stub, since we
        # only know the start point. We'll fill in end points
        # on the next call to scan().
        self._acquisitions.append(AcquisitionInfo(
            start = len(self.rows),
            end = None,
            config = self._latest_acq_config,
        ))

    def add_science_packet(self, packet: EbScienceDataPacket, timestamp=None) -> None:
        """Add rows from a science packet to the data set.

        For this class, we actually do ProcessedScienceRow conversion
        here, since the packet header contains relevant info that's not
        available elsewhere.
        """
        for row in packet.measurements:
            self.append(ProcessedScienceRow(
                src_row=row,
                src_header=packet,
                timestamp=timestamp,
                ob_calibration=self.ob_calibration,
                swir_dark_interpolator=None
                    if self.dark is None else self.dark.swir_interpolator,
                mwir_dark_interpolator=None
                    if self.dark is None else self.dark.mwir_interpolator,
                swir_flat_interpolator=None
                    if self.flat is None else self.flat.swir_interpolator,
                mwir_flat_interpolator=None
                    if self.flat is None else self.flat.mwir_interpolator,
            ))

class EbHkDataSet(EnfysHkDataSet):
    """A subclass that provides a scan() method for EB HK data.

    This class needs to be handed an EB calibration object, since
    there's no info in EB telemetry which identifies the specific
    model that's in use.
    """

    eb_calibration: EbCalibration|None
    ob_calibration: ObCalibration|None

    def __init__(self,
        eb_calibration: EbCalibration,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        """Class constructor.

        eb_calibration is mandatory, since it can't be acquired from
        anywhere else. The ob_calibration attribute will be determined
        using the model ID that's embeded in OB HK data within the EB
        telemetry. This is, of course, not available until the OB has
        been powered up, but that doesn't matter since we won't have
        any OB data to work with before then.
        """
        super().__init__(*args, **kwargs)

        # Save the calibration.
        self.eb_calibration = eb_calibration
        self.ob_calibration = None

    def scan(self) -> None:
        """Convert any rows which aren't of type ProcessedEbHkRow"""

        for i, row in enumerate(self.rows):
            ob_model_id = (row.OB_HK_ID & 0b11100000) >> 5
            if ob_model_id != 0:
                if self.ob_calibration is None:
                    self.ob_calibration = ob_models[ob_model_id]
                elif ob_model_id != self.ob_calibration.model_id:
                    raise ValueError("Data set contains multiple OB model IDs")

            if not isinstance(row, ProcessedEbHk):
                self.rows[i] = ProcessedEbHk(
                    src = row,
                    ob_calibration = self.ob_calibration,
                    eb_calibration = self.eb_calibration,
                )
