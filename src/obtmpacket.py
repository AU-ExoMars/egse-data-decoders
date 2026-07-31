"""Classes for decoding Telemetry packets.

The base class, TmPacket, does most of the work. Subclasses are defined for
the various packet types, and TmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
a template which defines how to decode the packet data into class attributes
and, optionally, a decode() method, which is called after the template
decoding, to perform any further decoding that the subclass might wish to do.
"""

import tmstruct as tm
from typing import ClassVar

from packet_decoder import PacketDecoder, PacketTemplate


class TmPacket(PacketDecoder):
    """Base class for TM packets from the OB.

    This is a bit naughty, really. There's no "magic" identifier in OB
    packets that clearly disambiguates them. The EGSE just dumps the data
    to separate files. Luckily, the various types have different-sized
    packets, so we can cheat and just compare each subclass's expected
    size with the packet size.
    """

    @classmethod
    def frombinary(cls: "type[TmPacket]", packet: bytes) -> "TmPacket":
        tm = TmPacket()

        cls._select_appropriate_subclass(tm, packet)

        return tm

    @classmethod
    def subclass_matcher(cls: "type[TmPacket]", tm: "TmPacket") -> bool:
        """Given a subclass, indicate whether the subclass can handle the tm."""
        return len(tm.payload) == cls.template.min_length_bytes


class HkPacket(TmPacket):
    template: ClassVar[PacketTemplate] = PacketTemplate(tm.hk)

class ScienceDataPacket(TmPacket):
    template: ClassVar[PacketTemplate] = PacketTemplate(tm.sci)

class AckPacket(TmPacket):
    template: ClassVar[PacketTemplate] = PacketTemplate(tm.ack_struct)

class NackPacket(TmPacket):
    template: ClassVar[PacketTemplate] = PacketTemplate(tm.nack)
