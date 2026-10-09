"""Classes for decoding Telemetry packets.

The base class, EbTmPacket, does most of the work. Subclasses are defined for
the various packet types, and EbTmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
the packet typeId they inhabit, a template which defines how to decode the
packet data into class attributes and, optionally, a decode() method, which
is called after the template decoding, to perform any further decoding that
the subclass might wish to do.
"""

import binascii
from typing import ClassVar

import tmstruct as tm
from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateError

# EB HKs embed an OB HK. If we decode that here, we
# get CRC checking of the OB data for free.
from ob_tm_packet import ObHkPacket


class EbTmPacketError(BitstructTemplateError):
    pass

class EbTmHeader(BitstructTemplateClass):
    decoder: ClassVar[bool] = True

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

    def _decode(self, data: bytes) -> bytes:
        data = super()._decode(data)

        self.lobt = self.lobtInt + self.lobtFrac/65536.0

        return data

class EbTmPacket(BitstructTemplateClass):
    """The base class for TMs.

    This provides the generic primitives for decoding TM packets. Subclasses
    should be pretty minimal, in general, just defining a typeId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C

    # It's sometimes useful to look at the packet that resulted
    # in the data held by the class, for debugging.
    raw: bytes|None = None

    header: EbTmHeader|None = None

    lobt: float|None

    def _decode(self, data: bytes) -> bytes:
        header = EbTmHeader.frombinary(data[:EbTmHeader.min_length_bytes])
        if header.magic != self.MAGIC:
            raise EbTmPacketError("Incorrect packet magic number")

        if header.tmTypeId != self.typeId:
            raise EbTmPacketError("Incorrect type ID")

        data = super()._decode(data[:EbTmHeader.min_length_bytes + header.blockLen])

        # If no exception has been raised, store the raw packet
        # data and return the object.
        self.raw = data

        self.header = header
        self.lobt = self.header.lobt

        return data

    @classmethod
    def strip_padding(cls, template: list[tuple[str, str]], name="PADDING"):
        if template[-1][0] == name:
            template.pop()
        return template

class EbHkPacket(EbTmPacket):
    """Base class for HK packets.

    There are two typeIds which contain HK packets, so we'll have a base
    class, should we need anything extra, but use the derived classes
    for decoding.
    """

    # Even though we don't actually do a decode at this level,
    # we'll put the template here, since it's common across regular and
    # response HK's
    template: ClassVar[list[tuple[str, str]]] = EbTmPacket.strip_padding(tm.eb_hk)

    # FIXME - this shouldn't be needed, but there's a bug in both
    # BSW and ASW which reports packet sizes incorrectly.
    # Confirmed in 2026-09-17 mail from Ben.
    strict_length_checking: ClassVar[bool] = False

    crc_valid: bool|None = None
    calculated_crc: int|None = None
    ob_hk: ObHkPacket|None = None

    def _decode(self, data) -> bytes:
        data = super()._decode(data)

        # Validate CRCs
        length = self.byte_offset_of("HK_PACKET_CRC")
        self.calculated_crc = self.crc16(data[:length])
        self.crc_valid = self.calculated_crc == self.HK_PACKET_CRC

        # It's not absolutely obvious to me that the OB_* fields will
        # definitely be populated once we're running ASW. Rather than
        # using only CURRENT_OPERATING_STATE, let's also use the presence
        # of all zeros in the relevant area of the packet as a signal.
        if self.CURRENT_OPERATING_STATE in (4, 8):
            obpacket = data[self.byte_offset_of("OB_HK_ID"):self.byte_offset_of("OB_HK_CRC8")+1]
            if sum(obpacket) != 0:
                self.ob_hk = ObHkPacket.frombinary(obpacket)

        return data

    def crc16(self, data: bytes):
        return binascii.crc_hqx(data, 0xFFFF)

class EbRegularHkPacket(EbHkPacket):
    """Subclass for regular HKs."""
    decoder: ClassVar[bool] = True
    typeId: ClassVar[int] = 0b000001

class EbResponseHkPacket(EbHkPacket):
    """Subclass for response HKs."""
    decoder: ClassVar[bool] = True
    typeId: ClassVar[int] = 0b000010

class EbPostHkPacket(EbTmPacket):
    """Subclass for power on self test HK."""

    decoder: ClassVar[bool] = True
    typeId: ClassVar[int] = 0b000011
    template: ClassVar[list[tuple[str, str]]] = EbTmPacket.strip_padding(tm.post_hk)

class EbDumpDataPacket(EbTmPacket):
    """Subclass for dump data packets."""

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = EbTmPacket.strip_padding(tm.dump_data, "DUMP_DATA")
    typeId: ClassVar[int] = 0b000100

    # Dump data is variable-length, so we can't use strict checking.
    strict_length_checking: ClassVar[bool] = False

    DUMP_DATA: bytes|None

    def _decode(self, data: bytes) -> bytes:
        # EbTmPacket will have stripped padding off.
        data = super()._decode(data)

        if len(data) < self.header.min_length_bytes + self.header.blockLen:
            raise EbTmPacketError("Packet too short")

        if len(data) > self.header.min_length_bytes + self.header.blockLen:
            raise EbTmPacketError("Packet too long")

        # Copy it over.
        self.DUMP_DATA = data[self.min_length_bytes:]

        return data

class EbScienceRow(BitstructTemplateClass):
    """A single row of science data"""
    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tm.sci_data

    # We'll be handing this the full array of data, so
    # in most cases it's going to be too long.
    strict_length_checking: ClassVar[bool] = False

class EbScienceDataPacket(EbTmPacket):
    """Base class for science packets.

    There are two typeIds which contain science packets, so we'll have a base
    class which handles commonality.
    """

    # Science data is variable-length, so we can't use strict checking.
    strict_length_checking: ClassVar[bool] = False

    # Define the template at this level, but it's the subclasses
    # that declare themselves to be decoders.
    template: ClassVar[list[tuple[str, str]]] = EbTmPacket.strip_padding(tm.eb_sci, name="SCI_DATA")

    measurements: list[EbScienceRow] | None
    start_time: float | None
    end_time: float | None

    def _decode(self, data: bytes) -> bytes:
        data = super()._decode(data)

        # The science rows themselves need decoding. Run through the
        # data, creating new EbScienceRow objects.
        self.measurements = []

        # Extract the part of the packet that should contain science
        # rows. This should be a multiple of the row size. We get
        # that check for free in EbScienceRow.frombinary, which will
        # raise an exception if the last chunk of data is too short.
        science = data[self.min_length_bytes:self.header.blockLen]
        while len(science) > 0:
            # Extract the first row from the data, then strip it
            # off the front.
            self.measurements.append(EbScienceRow.frombinary(science))
            science = science[EbScienceRow.min_length_bytes:]

        # Decode start and end times to floating point seconds.
        self.start_time = self.START_TIME_S + self.START_TIME_MS / 1000
        self.end_time = self.END_TIME_S + self.END_TIME_MS / 1000

        return data

class EbScienceDataCPacket(EbScienceDataPacket):
    """Subclass for critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """
    decoder: ClassVar[bool] = True
    typeId: ClassVar[int] = 0b000101

class EbScienceDataNcPacket(EbScienceDataPacket):
    """Subclass for non-critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """
    decoder: ClassVar[bool] = True
    typeId: ClassVar[int] = 0b000110
