#!/usr/bin/env python3

import sys
import re
import argparse
import csv
from pathlib import Path

from obtmpacket import TmPacket

class ObEgseDumpDecoder:
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

           log_reader = ObEgseDumpDecoder("20251001T150731_SCI.LOG")
           for timestamp, packet in log_reader:
               # Do something with timestamp and packet

        """

        line_number = 0
        for line in self.in_file:
            line_number += 1
            if m := re.match(r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+) - (?P<hex>[0-9a-f ]*)\s*$", line):
                try:
                    matched = m.groupdict()

                    # Extract and return the data.
                    packet = TmPacket.frombinary(bytes.fromhex(matched["hex"]))
                    yield matched["time"], packet

                except Exception as e:
                    raise ValueError(f"Error at line {line_number}: {e}")

        # Seek back to the start of the file so the iterator can be re-run if needed.
        self.in_file.seek(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode data from OB egse log")
    parser.add_argument("logfile", type=str, metavar="something.LOG", help="Data log from egse")
    parser.add_argument("-outfile", type=str, nargs="?", metavar="output.csv", help="Output CSV filename")
    args = parser.parse_args()

    try:
        log_file = ObEgseDumpDecoder(args.logfile)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        exit(1)

    if args.outfile is None:
        output = sys.stdout
    else:
        output = Path(args.outfile).open("w")
    writer = csv.writer(output)

    data_type = None
    try:
        for timestamp, packet in log_file:
            if data_type is None:
                data_type = packet.typeName
                print(f"Data type detected as {data_type}", file=sys.stderr)
                writer.writerow(["Date", "Time"] + list(packet.keys()))
            elif data_type != packet.typeName:
                print(
                    f"Error: Multiple data types ({data_type} and "
                    f"{packet.typeName}) were detected in the file!", 
                    file=sys.stderr
                )
                exit(1)
            writer.writerow(timestamp.split(" ") + list(packet.values()))
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        exit(1)
