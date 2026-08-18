#!/usr/bin/env python3

import datetime
import sys
import re
import argparse
import csv
from pathlib import Path

from ebtcpacket import TcPacket, TcAcquisition
from ebtmpacket import TmPacket, HkPacket, ScienceDataPacket

class EbEgseDumpDecoder:
    """
    This class implements an iterator which can be used to decode an EB EGSE log
    containing packet dumps.
    """

    struct_pattern = None
    struct_names = None
    struct_expected_length = None

    def __init__(self, log_file_name: str):
        """Initialise the iterator.

        Arguments:
        log_file_name -- The name of the EGSE log file to read.
        """

        # Open the hex dump file.
        try:
            self.in_file = open(log_file_name, "r")
        except (FileNotFoundError, PermissionError) as e:
            raise Exception(f"Failed to open file: {e.strerror}")

    def __iter__(self):
        """The iterator.

        This function reads the file, a line at a time and validates the
        CRC. If this are OK, the hex data is decoded to a TC or TM packet
        the unix timestamp (where known) and resulting object are yielded.

        Usage would be something like:

           log_reader = EGSEDumpDecoder("RS422if_YYYY-MM-DD_HH-MM-SS.log")
           for timestamp, packet in log_reader:
               # Do something with timestamp and packet

        """

        line_number = 0
        timestamp = None
        for line in self.in_file:
            line_number += 1
            if m := re.match(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\s*$", line):
                timestamp = datetime.datetime.strptime(
                                m.group(1),
                                "%Y-%m-%d_%H-%M-%S"
                ).timestamp()
            elif re.match(r"^Telecommand:\s*$", line):
                try:
                    hexdata = next(self.in_file)
                    yield None, TcPacket.fromhex(hexdata)
                except Exception as e:
                    raise ValueError(f"Error at line {line_number}: {e}")
            elif re.match(r"^Telemetry Data:\s*$", line):
                try:
                    hexdata = next(self.in_file)
                    yield timestamp, TmPacket.fromhex(hexdata)
                except Exception as e:
                    raise ValueError(f"Error at line {line_number}: {e}")
            elif re.match(r"^Starting RS422if\s*$", line):
                pass
            else:
                raise ValueError(f"Unmatched at line {line_number}: {line.strip()}")

        # Seek back to the start of the file so the iterator can be re-run if needed.
        self.in_file.seek(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode data from EB egse log")
    parser.add_argument("logfile", type=str, metavar="something.LOG", help="Data log from egse")
    parser.add_argument("-outbase", type=str, nargs="?", metavar="outbase", help="Base name for constructing CSV files")
    args = parser.parse_args()

    try:
        log_file = EbEgseDumpDecoder(args.logfile)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        exit(1)

    sci_header_fields = [
        "ACQUISITION_MODE",
        "SOL_NO", "MEASUREMENT_TYPE_ID", "MEASUREMENT_RUN_NO",
        "startTime", "endTime",
        "SWIR_OFFSET", "MWIR_OFFSET",
        "HEATSINK_START_TEMP", "HEATSINK_END_TEMP",
        "SWIR_START_TEMP", "SWIR_END_TEMP",
        "MWIR_START_TEMP", "MWIR_END_TEMP",
        "SAMPLE_DELAY", "FPGA_SAMPLES",
        "AVERAGING_NUMBER"
    ]
    sci_row_fields = [
        "ABS_STEPS",
        "SWIR_LOW", "SWIR_MED", "SWIR_HIGH",
        "MWIR_LOW", "MWIR_MED", "MWIR_HIGH",
    ]

    hk_csv = None
    sci_csv = None
    acq_number = 0
    try:
        for timestamp, packet in log_file:
            if isinstance(packet, TcPacket):
                print(f"TC: {packet}", file=sys.stderr)
                if isinstance(packet, TcAcquisition):
                    if sci_csv is not None and args.outbase is not None:
                        sci_csv.close()
                        sci_csv = None
            else:
                print(f"TM: {packet}", file=sys.stderr)
                if isinstance(packet, HkPacket):
                    if hk_csv is None:
                        if args.outbase is None:
                            hk_csv = sys.stdout
                        else:
                            hk_csv = Path(f"{args.outbase}_HK.csv").open("w")
                        hk_writer = csv.writer(hk_csv)
                        hk_writer.writerow(packet.keys())
                    hk_writer.writerow(packet.values())
                elif isinstance(packet, ScienceDataPacket):
                    if sci_csv is None:
                        if args.outbase is None:
                            sci_csv = sys.stdout
                        else:
                            acq_number += 1
                            if sci_csv is not None:
                                sci_csv.close()
                            sci_csv = Path(f"{args.outbase}_SCI_{acq_number:02d}.csv").open("w")
                        sci_writer = csv.writer(sci_csv)

                        for field in sci_header_fields:
                            sci_writer.writerow([field, packet[field]])
                        sci_writer.writerow([])

                        sci_writer.writerow(sci_row_fields)
                    for row in packet.measurements:
                        sci_writer.writerow([getattr(row, field) for field in sci_row_fields])
    except Exception as e:
        raise
        print(f"Error: {str(e)}", file=sys.stderr)
        exit(1)
