"""Classes for decoding Telemetry packets.

The base class, TmPacket, does most of the work. Subclasses are defined for
the various packet types, and TmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
the packet typeId they inhabit, a template which defines how to decode the
packet data into class attributes and, optionally, a decode() method, which
is called after the template decoding, to perform any further decoding that
the subclass might wish to do.
"""

import binascii
import tmstruct as tm
from typing import ClassVar

from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateException

# EB HKs embed an OB HK. If we decode that here, we
# get CRC checking of the OB data for free.
import obtmpacket

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

    lobt: float|None

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

    # It's sometimes useful to look at the packet that resulted
    # in the data held by the class, for debugging.
    raw: bytes|None = None
    header: TmHeader|None = None
    obHk: obtmpacket.HkPacket|None = None

    lobt: float|None

    @classmethod
    def frombinary(cls, data):
        header = TmHeader(packet=data[:TmHeader.min_length_bytes])
        if header.magic != cls.MAGIC:
            raise TmPacketException("Incorrect packet magic number")
        try:
            ret = super().frombinary(data[:TmHeader.min_length_bytes + header.blockLen])

            # If no exception has been raised, store the raw packet
            # data and return the object.
            ret.raw = data

            return ret
        except BitstructTemplateException as e:
            raise TmPacketException(f"No subclass accepted this packet (type ID={header.tmTypeId}, data length={header.blockLen})") from e

    @classmethod
    def strip_padding(cls, template: list[tuple[str, str]], name="PADDING"):
        if template[-1][0] == name:
            template.pop()
        return template

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get("packet", None) is not None:
            self.header = TmHeader(packet=kwargs["packet"][:TmHeader.min_length_bytes])
            self.lobt = self.header.lobt

        if self.header is not None and self.header.tmTypeId != self.typeId:
            raise TmPacketException("Type ID does not match")

class HkPacket(TmPacket):
    """Base class for HK packets.

    There are two typeIds which contain HK packets, so we'll have a base
    class, should we need anything extra, but use the derived classes
    for decoding.
    """

    # FIXME - this shouldn't be needed, but there's a bug in both
    # BSW and ASW which reports packet sizes incorrectly.
    # Confirmed in 2026-09-17 mail from Ben.
    strict_length_checking: ClassVar[bool] = False

    crc_valid: bool|None = None
    calculated_crc: int|None = None
    obHk: obtmpacket.HkPacket|None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if kwargs.get("packet", None) is not None:
            # Validate CRCs
            length = self.fields["HK_PACKET_CRC"][0] // 8
            self.calculated_crc = self.crc16(kwargs["packet"][:length])
            self.crc_valid = self.calculated_crc == self.HK_PACKET_CRC

            self.obHk = obtmpacket.HkPacket.frombinary(
                kwargs["packet"][self.fields["OB_HK_ID"][0]//8:1+self.fields["OB_HK_CRC8"][0]//8]
            )

    def crc16(self, data: bytes):
        return binascii.crc_hqx(data, 0xFFFF)

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

    measurements: list[EbScienceRow] | None
    startTime: float | None
    endTime: float | None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if kwargs.get("packet", None) is not None:
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

