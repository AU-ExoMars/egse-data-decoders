#!/usr/bin/env python3

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
        the date (where known) and resulting object are yielded.

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
                timestamp = m.group(1)
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

    hk_csv = None
    sci_csv = None
    acq_number = 0
    try:
        for timestamp, packet in log_file:
            if isinstance(packet, TcPacket):
                print(f"TC: {packet}", file=sys.stderr)
                if isinstance(packet, TcAcquisition):
                    if args.outbase is None:
                        sci_csv = sys.stdout
                    else:
                        acq_number += 1
                        if sci_csv is not None:
                            sci_csv.close()
                        sci_csv = Path(f"{args.outbase}_SCI_{acq_number:02d}.csv").open("w")
                        sci_writer = csv.writer(sci_csv)
                        sci_writer.writerow([
                            "ABS_STEPS", 
                            "SWIR_LOW", "SWIR_MED", "SWIR_HIGH", 
                            "MWIR_LOW", "MWIR_MED", "MWIR_HIGH"
                        ])
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
                    for row in packet.measurements:
                        sci_writer.writerow([
                            row.ABS_STEPS, 
                            row.SWIR_LOW, row.SWIR_MED, row.SWIR_HIGH, 
                            row.MWIR_LOW, row.MWIR_MED, row.MWIR_HIGH
                        ])
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        exit(1)
