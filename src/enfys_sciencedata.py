"""Convenience class for handling science data sets."""

import copy
import pathlib
import numpy as np
import scipy
from collections.abc import Iterator
from typing import ClassVar

from science_row import ScienceRow


class EnfysScienceDataSet:
    """Convenience class for handling science data sets.

    With an added mixin, this can make generating processed data,
    identifying sweeps, binary chops, etc, fairly simple.

    The class behaves in a somewhat list-like fashion so that, having
    stored a bunch of rows, you can then iterate/access them using familiar
    constructs.

    e.g.:

      for processed_row in EnfysScienceDataSet(raw_rows):
          print(processed_row.swir_wavelength, processed_row.swir_dn)
    """

    # Reflectivity of the "flat" (gold) data.
    flat_reflectivity: ClassVar[float] = 0.95

    # Where the data came from - optional.
    origin_file: pathlib.Path|None = None

    dark: "EnfysScienceDataSet|None" = None
    flat: "EnfysScienceDataSet|None" = None

    rows: list[ScienceRow]

    def __init__(self,
            rows: list[ScienceRow]|None = None,
            dark: "EnfysScienceDataSet|None" = None,
            flat: "EnfysScienceDataSet|None" = None,
            name: str|None = None,
            origin_file: str|None = None,
    ) -> None:
        """Class constructor.

        Save the various attributes and, if a mixin supplies a "scan"
        method, run it on the supplied rows.
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

        # Store the rows. We do it via .append, since that will handle
        # any processing needed and saves code duplication.
        self.rows = copy.copy(rows)

        # It's sometimes useful to be able to get an interpolated
        # spectrum for any motor step value.
        self._swir_interpolator: scipy.interpolate.CubicSpline|None = None
        self._mwir_interpolator: scipy.interpolate.CubicSpline|None = None

        if hasattr(self, "scan"):
            self.scan()

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

        if isinstance(rows, list):
            self.rows += copy.copy(rows)
            return

        self.rows.append(copy.copy(rows))

    @property
    def swir_interpolator(self):
        if self._swir_interpolator is None:
            self._swir_interpolator = self._make_interpolator(
                [ [row.MTR_ABS_STEPS, row.swir_scaled_dn] for row in self ]
            )
        return self._swir_interpolator

    @property
    def mwir_interpolator(self):
        if self._mwir_interpolator is None:
            self._mwir_interpolator = self._make_interpolator(
                [ [row.MTR_ABS_STEPS, row.mwir_scaled_dn] for row in self ]
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


    def __len__(self) -> int:
        """Return the length of the data set."""
        return len(self.rows)

    def __iter__(self) -> Iterator[ScienceRow]:
        """Iterate over the row list."""
        for i in range(len(self.rows)):
            yield self[i]

    def __getitem__(self, idx: int|slice) -> ScienceRow|list[ScienceRow]:
        """Return the requested item from the list."""
        if isinstance(idx, slice):
            # When we've got a slice, use it to build a comprehension
            # recursively.
            return [
                self[i]
                    for i in range(idx.start, idx.stop,
                        1 if idx.step is None else idx.step)
            ]

        return self.rows[idx]
