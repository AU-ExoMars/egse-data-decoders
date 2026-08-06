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

from packet_decoder import PacketDecoder, PacketTemplate
from enfys_calibration import RawScienceRow


class TmPacket(PacketDecoder):
    """The base class for TMs.

    This provides the generic primitives for decoding TM packets. Subclasses
    should be pretty minimal, in general, just defining a typeId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C
    header_template: ClassVar[PacketTemplate] = PacketTemplate([
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
    ])

    @classmethod
    def frombinary(cls: "type[TmPacket]", packet: bytes) -> "TmPacket":
        """Decode packet and return an object of the appropriate subclass."""
        # Create an object of the base type.
        tm = TmPacket()

        # Too little data?
        if len(packet) < tm.header_template.min_length_bytes:
            raise ValueError("Packet is too short for TM header")

        # Decode the TM header.
        header = tm.header_template.decode(packet)

        # Huh, it's not a TM header.
        if header["magic"] != tm.MAGIC:
            raise ValueError(f"Bad magic (0x{header['magic']:08x}), should be 0x{tm.MAGIC:08x}")

        # Too little data?
        if len(packet) < header["blockLen"] + tm.header_template.min_length_bytes:
            raise ValueError("Packet data is too short for TM packet")

        # Enough data, but is any excess purely made of padding bytes?
        if not all(ent == 0xAA for ent in packet[header["blockLen"]+tm.header_template.min_length_bytes:]):
            raise ValueError("Packet padding was not exclusively 0xAA")

        tm.tmTypeId = header["tmTypeId"]
        tm.seqFlag = header["seqFlag"]
        tm.blockType = header["blockType"]
        tm.tmCriticality = header["tmCriticality"]
        tm.mmsDest = header["mmsDest"]
        tm.instrId = header["instrId"]

        # Decode the local onboard time.
        tm.lobtInt = header["lobtInt"]
        tm.lobtFrac = header["lobtFrac"]
        tm.lobt = tm.lobtInt + tm.lobtFrac/65536.0

        # Store the block length.
        tm.blockLen = header["blockLen"]

        # The "fields" attribute will contain the names of all
        # fields derived from the decoded packet. I'm doing this
        # as a dict because sets don't preserve key order.
        tm.fields = {
            "blockType": 1, "tmCriticality": 1, "mmsDest": 1,
            "instrId": 1, "seqFlag": 1, "lobtInt": 1,
            "lobtFrac": 1, "lobt": 1, "blockLen": 1,
        }

        cls._select_appropriate_subclass(tm, packet)

        return tm

    @classmethod
    def subclass_matcher(cls: "type[TmPacket]", tm: "TmPacket") -> bool:
        """Given a subclass, indicate whether the subclass can handle the tm.

        For TM's, the determination is currently based on just the typeId.
        """
        return getattr(cls, "typeId", None) == tm.tmTypeId

    def __str__(self) -> str:
        """Add the local onboard time to the basic string summary."""
        return f"{self.typeName}: Time={self.lobt:.05f}"

class HkPacket(TmPacket):
    """Base class for HK packets.

    There are two typeIds which contain HK packets, so we define the
    template and decode method here, but *don't* specify a typeId. We'll
    subclass below for the specific type Ids.
    """

    template: ClassVar[PacketTemplate] = PacketTemplate(tm.eb_hk)

    def decode(self) -> None:
        """Trim out the less useful fields"""

        # The tmstruct definition duplicates header fields,
        # and contains unused blocks. Let's delete those here
        # so they don't turn up in automated exports. You can
        # still pick them up as class attributes, but they
        # won't turn up in the dict-style access.
        for field in (
            "PATTERN", "PACKET_ID", "LOBT_RET_TIME", "BLOCK_LENGTH",
            "SPARES_BLOCK_1", "SPARES_BLOCK_2", "SPARES_BLOCK_3",
            "SPARES_BLOCK_4", "SPARES_BLOCK_5", "SPARES_BLOCK_6",
            "SPARES_BLOCK_7", "PADDING"
        ):
            del self.fields[field]

class RegularHkPacket(HkPacket):
    """Subclass for regular HKs.

    This just inherits from HkPacket and specifies the relevant type Id.
    """

    typeId: ClassVar[int] = 0b000001

class ResponseHkPacket(HkPacket):
    """Subclass for response HKs.

    This just inherits from HkPacket and specifies the relevant type Id.
    """

    typeId: ClassVar[int] = 0b000010

    def __str__(self):
        return f"{self.typeName}: Time={self.lobt:.05f}, TCS_ACCEPTED={self.TCS_ACCEPTED}, TCS_REJECTED={self.TCS_REJECTED}"

class PostHkPacket(TmPacket):
    """Subclass for power on self test HK."""

    typeId: ClassVar[int] = 0b000011
    template: ClassVar[PacketTemplate] = PacketTemplate(tm.post_hk)

class DumpDataPacket(TmPacket):
    """Subclass for dump data packets."""

    typeId: ClassVar[int] = 0b000100

    template: ClassVar[PacketTemplate] = PacketTemplate(tm.dump_data)

class ScienceDataPacket(TmPacket):
    """Base class for science data packets.

    There are two typeIds which contain science packets, so we define the
    template and decode method here, but *don't* specify a typeId. We'll
    subclass below for the specific type Ids.
    """

    template: ClassVar[PacketTemplate] = PacketTemplate(tm.eb_sci_header)
    row_template: ClassVar[PacketTemplate] = PacketTemplate(tm.sci_data)

    def decode(self) -> None:
        """Decode the science rows."""

        science_data = self.payload[self.template.min_length_bytes:]
        self.fields["paddedMeasurementLength"] = 1
        self.paddedMeasurementLength = len(science_data)
        science_data = science_data.strip(b"\xAA")
        self.fields["unPaddedMeasurementLength"] = 1
        self.unPaddedMeasurementLength = len(science_data)

        self.fields["startTime"] = 1
        self.startTime = self.START_TIME_S + self.START_TIME_MS / 1000
        self.fields["endTime"] = 1
        self.endTime = self.END_TIME_S + self.END_TIME_MS / 1000

        row_length = self.row_template.min_length_bits // 8

        self.measurements = []
        self.fields["measurements"] = 1
        while len(science_data) > 0:
            self.measurements.append(RawScienceRow(*self.row_template.decode(science_data).values()))
            science_data = science_data[row_length:]

        # The tmstruct definition duplicates header fields,
        # and contains unused blocks. Let's delete those here
        # so they don't turn up in automated exports. You can
        # still pick them up as class attributes, but they
        # won't turn up in the dict-style access.
        for field in (
            "PATTERN", "PACKET_ID", "LOBT_RET_TIME", "BLOCK_LENGTH",
            "START_TIME_S", "START_TIME_MS",
            "END_TIME_S", "END_TIME_MS",
            "RESERVED_0", "RESERVED_1",
            "measurements"
        ):
            del self.fields[field]

    def __str__(self) -> str:
        """Add the local onboard time to the basic string summary."""
        return f"{self.typeName}: Time={self.lobt:.05f}, Rows={len(self.measurements)}"



class ScienceDataCPacket(ScienceDataPacket):
    """Subclass for critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """

    typeId: ClassVar[int] = 0b000101

class ScienceDataNcPacket(ScienceDataPacket):
    """Subclass for non-critical science packets.

    This just inherits from ScienceDataPacket and specifies the relevant type Id.
    """

    typeId: ClassVar[int] = 0b000110

