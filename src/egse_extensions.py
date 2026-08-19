import ebtcpacket, ebtmpacket
from collections import deque
import dataclasses

@dataclasses.dataclass
class AcquisitionInfo:
    start_row: int
    end_row: int
    config: ebtcpacket.TcSetAcqConfigs
    packets: list[ebtmpacket.ScienceDataPacket]

@dataclasses.dataclass
class SciencePacketInfo:
    acquisition_number: int
    start_row: int
    end_row: int
    packet: ebtmpacket.ScienceDataPacket

class EbEgseExtensions:
    def __init__(self, *args, **kwargs):
        self.acquisitions = []
        self.science_packets = []
        self._acq_config = None
        super().__init__(*args, **kwargs)

    def store_acq_config(self, acq_config):
        self._acq_config = acq_config

    def add_science_packet(self, packet):
        self.science_packets.append(SciencePacketInfo(len(self.acquisitions)-1, len(self.raw_rows), len(self.raw_rows), packet))
        if len(self.acquisitions) > 0:
            self.acquisitions[-1].packets.append(self.science_packets[-1])

    def start_acquisition(self):
        self.acquisitions.append(AcquisitionInfo(len(self.raw_rows), len(self.raw_rows), self._acq_config, []))

    def scan(self):
        for i, sp in enumerate(self.science_packets):
            if i == len(self.science_packets)-1:
                sp.end_row = len(self.raw_rows)-1
            else:
                sp.end_row = self.science_packets[i+1].start_row-1

        for i, acq in enumerate(self.acquisitions):
            if i == len(self.acquisitions)-1:
                acq.end_row = len(self.raw_rows)-1
            else:
                acq.end_row = self.acquisitions[i+1].start_row-1

        # For chaining when we're initing and scanning in one go.
        return self


@dataclasses.dataclass
class ChopInfo:
    """A data class for holding information about a binary chop."""
    start: int
    end: int
    sensor: str
    motor_position: int
    final_offset: int
    final_hi_dn: int

@dataclasses.dataclass
class SweepInfo:
    """A data class for holding information about a sweep."""
    start: int
    end: int
    direction: str
    swir_chop: ChopInfo
    mwir_chop: ChopInfo

class ObEgseExtensions:
    def scan(self):
        self._find_binary_chops()
        self._find_sweeps()

        # For chaining when we're initing and scanning in one go.
        return self

    def _find_binary_chops(self) -> None:
        """Find binary chops within the provided science data.

        Run through the provided data, looking for sequences of records
        which appear to be DAC binary chop procedures. A number of
        heuristics are used, primarily focusing around the way that
        bits flip during a binary chop. I believe this function should
        reliably spot "real" chops without false positives.

        It stores a list of (start, end, type) tuples into the "chops"
        class attribye. These identify positions within the supplied data
        where chops were spotted, along with their type ("SWIR" or "MWIR).

        This function is used internally by the constructor to provide
        information for the "processed" iterator.
        """
        # We'll store a list of record numbers where binary
        # chops were found in the science data.
        self.chops = []

        # A queue for holding enough entries to detect a binary chop.
        checkqueue = deque(maxlen=12)

        for i, row in enumerate(self.raw_rows):
            checkqueue.append(row)
            if len(checkqueue) == checkqueue.maxlen:
                # Look at the queue and see whether it looks like a
                # binary chop. This look should break out as soon as
                # it determines a chop *isn't* taking place.
                found_chop = True

                # Keep track of which offsets are changing, so we can
                # tell whether it's an MWIR chop, a SWIR chop or something
                # else.
                maybe_mwir = False
                maybe_swir = False

                # We work along the queue, checking bit pairs to see
                # whether they're feasibly part of a chop. These masks
                # make the process a bit less painful (they get shifted
                # right inside the loop).
                mask1 = 0b11 << (checkqueue.maxlen - 1)
                mask2 = 0b01 << (checkqueue.maxlen - 1)
                mask3 = 0b10 << (checkqueue.maxlen - 1)

                # OK, work through the queue.
                for j in range(checkqueue.maxlen):

                    if checkqueue[j].ABS_STEPS != row.ABS_STEPS:
                        # The motor has moved, so we're definitely not seeing a chop.
                        found_chop = False
                        break

                    # From the second entry in the queue, check each aganist the
                    # preceding one.
                    if j > 0:
                        if checkqueue[j-1].SWIR_OFFSET != checkqueue[j].SWIR_OFFSET:
                            # SWIR offset is changing, so maybe it's a SWIR binary chop.
                            maybe_swir = True

                            # The only bits that can be changing at this point
                            # are the two adjacent bits at the mask position.
                            # Anything else indicates something that's not a binary
                            # chop.
                            if ((checkqueue[j-1].SWIR_OFFSET & ~mask1) !=
                                    (checkqueue[j].SWIR_OFFSET & ~mask1)):
                                found_chop = False
                                break

                            # During the chop, if a change has happened within the
                            # mask then it must involve the lower bit going from low
                            # to high.
                            if ((checkqueue[j-1].SWIR_OFFSET & mask2 != 0) or
                                    (checkqueue[j].SWIR_OFFSET & mask2 == 0)):
                                found_chop = False
                                break

                            # During the chop, if a change has happened within the
                            # mask upper bit then it must be going from high to low.
                            if ((checkqueue[j-1].SWIR_OFFSET & mask3 !=
                                        checkqueue[j].SWIR_OFFSET & mask3) and
                                    (checkqueue[j].SWIR_OFFSET & mask3 != 0)):
                                found_chop = False
                                break

                        # Now do exactly the same checks for the MWIR offset.

                        if checkqueue[j-1].MWIR_OFFSET != checkqueue[j].MWIR_OFFSET:
                            maybe_mwir = True

                            if ((checkqueue[j-1].MWIR_OFFSET & ~mask1) !=
                                    (checkqueue[j].MWIR_OFFSET & ~mask1)):
                                found_chop = False
                                break

                            if ((checkqueue[j-1].MWIR_OFFSET & mask2 != 0) or
                                    (checkqueue[j].MWIR_OFFSET & mask2 == 0)):
                                found_chop = False
                                break

                            if ((checkqueue[j-1].MWIR_OFFSET & mask3 !=
                                        checkqueue[j].MWIR_OFFSET & mask3) and
                                    (checkqueue[j].MWIR_OFFSET & mask3 != 0)):
                                found_chop = False
                                break


                        # Check we've not seen changes of *both* offsets. If we
                        # have then it's not a chop as we expect to see it.
                        if maybe_mwir and maybe_swir:
                            found_chop = False
                            break

                    # Move the masks, ready for the next time around the loop.
                    mask1 = mask1 >> 1
                    mask2 = mask2 >> 1
                    mask3 = mask3 >> 1

                if not maybe_mwir and not maybe_swir:
                    # Neither offset changed during the window, so it's not
                    # a chop.
                    found_chop = False

                if found_chop:
                    # Store the start and end point, along with the type.
                    if maybe_mwir:
                        self.chops.append(ChopInfo(
                            start = i-checkqueue.maxlen+1,
                            end = i,
                            sensor = "MWIR",
                            motor_position = row.ABS_STEPS,
                            final_offset = row.MWIR_OFFSET,
                            final_hi_dn = row.MWIR_HIGH,
                        ))
                    else:
                        self.chops.append(ChopInfo(
                            start = i-checkqueue.maxlen+1,
                            end = i,
                            sensor = "SWIR",
                            motor_position = row.ABS_STEPS,
                            final_offset = row.SWIR_OFFSET,
                            final_hi_dn = row.SWIR_HIGH,
                        ))

    def _find_sweeps(self) -> None:
        """Find monotonic sweeps.

        This function does a similar job to _find_binary_chops, but looks
        for "sweeps". A sweep is a collection of readings that, after binary
        chop removal, consists of monotonically increasing, monotonically
        decreasing or stationary ABS_STEPS values.

        As with _find_binary_chops, a list is created, "sweeps", which
        holds the start, stop and direction ("UP", "DOWN" or "STATIONARY")
        values for each detected sweep.
        """

        self.sweeps = []
        direction = None
        start = None
        steps = None
        runlength = 0
        pos_queue = deque(maxlen=2)

        def add_sweep(start, end, direction):
            swir_chop = None
            mwir_chop = None
            for chop in self.chops:
                if chop.sensor == "MWIR":
                    if mwir_chop is None or chop.end < start:
                        mwir_chop = chop
                elif chop.sensor == "SWIR":
                    if swir_chop is None or chop.end < start:
                        swir_chop = chop
            self.sweeps.append(SweepInfo(start=start, end=end, direction=direction, swir_chop=swir_chop, mwir_chop=mwir_chop))

        for i, row in enumerate(self.raw_rows):
            skip = False

            # This is pretty inefficient - should track position and
            # chop number better.
            for chop in self.chops:
                if chop.start <= i <= chop.end:
                    skip = True
                    break
            if skip:
                if start is not None:
                    # If we have an ongoing sweep, we need to terminate it.
                    add_sweep(start, pos_queue[1], direction)
                    start = None
                    steps = None
                    direction = None
                    runlength = 0
                continue

            if start is None:
                start = i
                steps = row.ABS_STEPS
                runlength = 1

            elif direction is None:
                if row.ABS_STEPS > steps:
                    direction = "UP"
                elif row.ABS_STEPS < steps:
                    direction = "DOWN"
                else:
                    direction = "STATIONARY"
                runlength += 1
                steps = row.ABS_STEPS

            elif ((direction == "UP" and row.ABS_STEPS <= steps) or
                (direction == "DOWN" and row.ABS_STEPS >= steps) or
                (direction == "STATIONARY" and row.ABS_STEPS != steps)):

                # Direction has changed. We need to be a bit careful here
                # because there might have been a binary chop between the
                # last point of the previous direction and the first of the
                # current one.
                if pos_queue[1]-pos_queue[0] == 1:
                    add_sweep(start, pos_queue[1], direction)
                else:
                    add_sweep(start, pos_queue[0], direction)
                start = pos_queue[1]
                direction = None
                steps = row.ABS_STEPS
                runlength = 1
            else:
                steps = row.ABS_STEPS
                runlength += 1
            pos_queue.append(i)

        if runlength > 1:
            add_sweep(start, i, direction)

