"""Classes for decoding Telemetry packets.

The base class, TmPacket, does most of the work. Subclasses are defined for
the various packet types, and TmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
the packet typeId they inhabit, a template which defines how to decode the
packet data into class attributes and, optionally, a decode() method, which
is called after the template decoding, to perform any further decoding that
the subclass might wish to do.
"""

import tmstruct as tm
from typing import ClassVar

from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateException

class TmPacketException(BitstructTemplateException):
    pass

class TmHeader(BitstructTemplateClass):
    # Oddly, tmstruct doesn't have a broken out TM header described. I'll
    # break my self-imposed rule and put it here.
    template: ClassVar[list[tuple[str, str]]] = [
        ( "magic",         ">u32" ),
        ( "blockType",     ">u1" ),
        ( "tmCriticality", ">u2" ),
        ( "mmsDest",       ">u1" ),
        ( "instrId",       ">u4" ),
        ( "tmTypeId",      ">u6" ),
        ( "seqFlag",       ">u2" ),
        ( "lobtInt",       ">u32" ),
        ( "lobtFrac",      ">u16" ),
        ( "blockLen",      ">u16" ),
    ]

    lobt: float

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.lobtInt is not None and self.lobtFrac is not None:
            self.lobt = self.lobtInt + self.lobtFrac/65536.0

class TmPacket(BitstructTemplateClass):
    """The base class for TMs.

    This provides the generic primitives for decoding TM packets. Subclasses
    should be pretty minimal, in general, just defining a typeId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C

    header: TmHeader

    @classmethod
    def frombinary(cls, data):
        header = TmHeader(packet=data[:TmHeader.min_length_bytes])
        if header.magic != cls.MAGIC:
            raise TmPacketException("Incorrect packet magic number")
        try:
            return super().frombinary(data[:TmHeader.min_length_bytes + header.blockLen])
        except BitstructTemplateException as e:
            raise TmPacketException(f"No subclass accepted this packet (type ID={header.tmTypeId}, data length={header.blockLen})") from e

    @classmethod
    def strip_padding(cls, template: list[tuple[str, str]], name="PADDING"):
        if template[-1][0] == name:
            template.pop()
        return template

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "packet" in kwargs:
            self.header = TmHeader(packet=kwargs["packet"][:TmHeader.min_length_bytes])

        if self.header is not None and self.header.tmTypeId != self.typeId:
            raise TmPacketException("Type ID does not match")

class HkPacket(TmPacket):
    """Base class for HK packets.

    There are two typeIds which contain HK packets, so we'll have a base
    class, should we need anything extra, but use the derived classes
    for decoding.
    """

    # FIXME - this shouldn't be needed 2026-09-16
    strict_length_checking: ClassVar[bool] = False


class RegularHkPacket(HkPacket):
    """Subclass for regular HKs."""
    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.eb_hk)
    typeId: ClassVar[int] = 0b000001

class ResponseHkPacket(HkPacket):
    """Subclass for response HKs."""
    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.eb_hk)
    typeId: ClassVar[int] = 0b000010

class PostHkPacket(TmPacket):
    """Subclass for power on self test HK."""

    typeId: ClassVar[int] = 0b000011
    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.post_hk)

    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
        except Exception as e:
            raise

class DumpDataPacket(TmPacket):
    """Subclass for dump data packets."""

    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.dump_data)
    typeId: ClassVar[int] = 0b000100

class EbScienceRow(BitstructTemplateClass):
    """A single row of science data"""
    template: ClassVar[list[tuple[str, str]]] = tm.sci_data

    # We'll be handing this the full array of data, so
    # in most cases it's going to be too long.
    strict_length_checking: ClassVar[bool] = False

class ScienceDataPacket(TmPacket):
    """Base class for science packets.

    There are two typeIds which contain science packets, so we'll have a base
    class which handles commonality.
    """

    # Science data is variable-length, so we can't use strict checking.
    strict_length_checking: ClassVar[bool] = False

    measurements: list[EbScienceRow]
    startTime: float
    endTime: float

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if "packet" in kwargs:
            # The science rows themselves need decoding. Run through the
            # data, creating new EbScienceRow objects.
            self.measurements = []

            # Extract the part of the packet that should contain science
            # rows. This should be a multiple of the row size. We get
            # that check for free in EbScienceRow.frombinary, which will
            # raise an exception if the last chunk of data is too short.
            science = kwargs["packet"][self.min_length_bytes:self.header.blockLen]
            while len(science) > 0:
                # Extract the first row from the data, then strip it
                # off the front.
                self.measurements.append(EbScienceRow.frombinary(science))
                science = science[EbScienceRow.min_length_bytes:]

            # Decode start and end times to floating point seconds.
            self.startTime = self.START_TIME_S + self.START_TIME_MS / 1000
            self.endTime = self.END_TIME_S + self.END_TIME_MS / 1000

class ScienceDataCPacket(ScienceDataPacket):
    """Subclass for critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """
    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.eb_sci, name="SCI_DATA")
    typeId: ClassVar[int] = 0b000101

class ScienceDataNcPacket(ScienceDataPacket):
    """Subclass for non-critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """
    template: ClassVar[list[tuple[str, str]]] = TmPacket.strip_padding(tm.eb_sci, name="SCI_DATA")
    typeId: ClassVar[int] = 0b000110

import sys
for line in sys.stdin:
    line = line.strip()
    try:
        pkt = TmPacket.fromhex(line)

        if isinstance(pkt, ScienceDataPacket):
            m = pkt.measurements
            pkt.measurements = len(m)
            print(pkt)
            print("Rows:")
            for row in m:
                print(row)
    except TmPacketException as e:
        print(f"Failed decode: {e}")
        print(f"Hex was: {line}")
        raise

