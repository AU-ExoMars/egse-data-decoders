"""Convenience class for handling science data sets."""

import copy
import pathlib
from collections.abc import Iterator

import numpy as np
import scipy

from enfys_calibration import ObCalibration
from enfys_model_extensions import ObScienceExtension
from science_row import ProcessedScienceRow, ScienceRow


class EnfysScienceDataSet:
    """Convenience class for handling science data sets.

    With subclasses for Ob and Eb, this can make generating processed data,
    identifying sweeps, binary chops, etc, fairly simple.

    The class behaves in a somewhat list-like fashion so that, having
    stored a bunch of rows, you can then iterate/access them using familiar
    constructs.

    e.g.:

      for processed_row in EnfysScienceDataSet(raw_rows):
          print(processed_row.swir_wavelength, processed_row.swir_relative_dn)
    """

    # Where the data came from - optional.
    origin_file: pathlib.Path|None = None

    dark: "EnfysScienceDataSet|None" = None
    flat: "EnfysScienceDataSet|None" = None

    # Store the calibration data that's appropriate to this set.
    # The relevant subclass is responsible for getting hold of the
    # correct calibration object.
    ob_calibration: ObCalibration|None = None

    # The actual meat of the data set.
    rows: list[ProcessedScienceRow]

    def __init__(self,
            rows: list[ScienceRow]|None = None,
            dark: "EnfysScienceDataSet|None" = None,
            flat: "EnfysScienceDataSet|None" = None,
            name: str|None = None,
            origin_file: str|None = None,
    ) -> None:
        """Class constructor.

        Save the various attributes.
        """
        # Save args.
        self.dark = dark
        self.flat = flat
        self.name = name
        if origin_file is not None:
            self.origin_file = pathlib.Path(origin_file)

        # If these are specified, then we can generate relative spectra.
        if flat is not None and dark is None:
            raise ValueError("If flat are specified then dark are needed too")

        # Store the rows. We'll do this via .append, since
        # it guarantees the dependent invalidation of information
        # also happens.
        self.rows = []
        self.append([] if rows is None else rows)

    def append(self,
        rows: ScienceRow|list[ScienceRow],
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

    @property
    def swir_interpolator(self) -> scipy.interpolate.CubicSpline:
        """Return a cubic spline interpolator based on SWIR scaled DN data.

        In, for example, dark handling, we need to be able to get hold of a
        DN value for motor positions that are, potentially, not in the
        current data set. By using an interpolator, we can avoid worrying
        about that.
        """
        if self._swir_interpolator is None:
            self._swir_interpolator = self._make_interpolator(
                [ (row.MTR_ABS_STEPS, row.swir_scaled_dn) for row in self ]
            )
        return self._swir_interpolator

    @property
    def mwir_interpolator(self) -> scipy.interpolate.CubicSpline:
        """Return an interpolator for MWIR data."""
        if self._mwir_interpolator is None:
            self._mwir_interpolator = self._make_interpolator(
                [ (row.MTR_ABS_STEPS, row.mwir_scaled_dn) for row in self ]
            )
        return self._mwir_interpolator

    def _make_interpolator(self,
            xy: list[tuple[float, float]]
    ) -> scipy.interpolate.CubicSpline:
        """Given X/Y data, return a CubicSpline that fits it.

        scipy requires strictly increasing x values, so we need to do some
        preprocessing so we can give it what it wants.
        """
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


    def __len__(self) -> int:
        """Return the length of the data set."""
        return len(self.rows)

    def __iter__(self) -> Iterator[ProcessedScienceRow]:
        """Iterate over the row list."""
        for i in range(len(self.rows)):
            yield self[i]

    def __getitem__(self,
        idx: int|slice
    ) -> ProcessedScienceRow|list[ProcessedScienceRow]:
        """Return the requested item from the list."""
        # Call the subclass-provided "scan" method, on demand.
        # This should ensure that all rows are converted from
        # ScienceRow to ProcessedScienceRow. It might perform
        # other tasks, such as identifying acquisition sets.
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

