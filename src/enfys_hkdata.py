"""Convenience class for handling housekeeping data sets."""

import copy
import pathlib
from collections.abc import Iterator

import numpy as np
import scipy

from enfys_calibration import ObCalibration, EbCalibration

from eb_tm_packet import EbHkPacket
from eb_hk import ProcessedEbHk
from ob_tm_packet import ObHkPacket
from ob_hk import ProcessedObHk


class EnfysHkDataSet:
    """Convenience class for handling science data sets.

    With subclasses for Ob and Eb, this can make generating processed data,
    identifying sweeps, binary chops, etc, fairly simple.

    The class behaves in a somewhat list-like fashion so that, having
    stored a bunch of rows, you can then iterate/access them using familiar
    constructs.

    e.g.:

      for processed_row in EnfysHkDataSet(raw_rows):
          print(processed_row.swir_wavelength, processed_row.swir_relative_dn)
    """

    # Where the data came from - optional.
    origin_file: pathlib.Path|None = None

    # Store the calibration data that's appropriate to this set.
    # The relevant subclass is responsible for getting hold of the
    # correct calibration object.
    ob_calibration: ObCalibration|None = None
    eb_calibration: EbCalibration|None = None

    # The actual meat of the data set.
    rows: list[ProcessedObHk|ProcessedEbHk]

    def __init__(self,
            rows: list[EbHkPacket|ObHkPacket]|None = None,
            name: str|None = None,
            origin_file: str|None = None,
    ) -> None:
        """Class constructor.

        Save the various attributes.
        """
        # Save args.
        self.name = name
        if origin_file is not None:
            self.origin_file = pathlib.Path(origin_file)

        # Store the rows. We'll do this via .append, since
        # it guarantees the dependent invalidation of information
        # also happens.
        self.rows = []
        self.append([] if rows is None else rows)

    def append(self,
        rows: EbHkPacket|ObHkPacket|list[EbHkPacket|ObHkPacket],
    ) -> None:
        """Append one or more rows to the dataset.

        This isn't quite the same as a normal list append
        because it handles appending another list. Implementing
        the __add__ method would be rather more difficult than
        just cheating here because __add__ creates a whole new
        instance.
        """
        # Invalidate the interpolators since we've
        # just changed what data is present.
        self._swir_interpolator = None
        self._mwir_interpolator = None
        self._scanned = False

        if isinstance(rows, list):
            self.rows += copy.copy(rows)
            return

        self.rows.append(copy.copy(rows))

    def __len__(self) -> int:
        """Return the length of the data set."""
        return len(self.rows)

    def __iter__(self) -> Iterator[ProcessedEbHk|ProcessedObHk]:
        """Iterate over the row list."""
        for i in range(len(self.rows)):
            yield self[i]

    def __getitem__(self,
        idx: int|slice
    ) -> ProcessedEbHk|ProcessedObHk|list[ProcessedEbHk|ProcessedObHk]:
        """Return the requested item from the list."""
        # Call the subclass-provided "scan" method, on demand.
        # This should ensure that all rows are converted from
        # *HkRow to Processed*HkRow.
        if not self._scanned:
            # We defer running the subclass "scan" method until
            # we're asked for some data. This allows .append() to
            # run efficiently in the case where the data set is
            # being built row by row.
            self.scan()
            self._scanned = True

        if isinstance(idx, slice):
            # When we've got a slice, use it to build a comprehension
            # recursively.
            return [
                self[i]
                    for i in range(
                        idx.start, idx.stop,
                        1 if idx.step is None else idx.step
                    )
            ]

        return self.rows[idx]

