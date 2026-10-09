"""Classes for decoding Telemetry packets.

The base class, ObTmPacket, does most of the work. Subclasses are defined for
the various packet types, and ObTmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
a template which defines how to decode the packet data into class attributes
and, optionally, a decode() method, which is called after the template
decoding, to perform any further decoding that the subclass might wish to do.
"""

from typing import ClassVar

import tmstruct as tm
from bitstruct_template_class import BitstructTemplateClass


class ObTmPacket(BitstructTemplateClass):
    """Base class for TM packets from the OB.

    This class doesn't do anything except give us somewhere that we can
    hang common functions and start the recursive search when using
    frombinary/fromhex. If we started the search from BitstructTemplateClass,
    it could go through classes that clearly weren't appropriate and
    potentially return the wrong decode.
    """

class ObTmPacketWithCrc(ObTmPacket):
    """Most of our OB TM packets come with a CRC.

    This class adds the capability to check the supplied CRC
    while decoding.
    """

    crc_field_name: ClassVar[str|None] = None

    crc_valid: bool|None = None
    calculated_crc: int|None = None

    def _decode(self, data: bytes) -> bytes:
        data = super()._decode(data)

        # Validate CRC.
        crc_offset = self.byte_offset_of(self.crc_field_name)

        self.calculated_crc = self.crc8(data[:crc_offset])
        self.crc_valid = getattr(self, self.crc_field_name) == self.calculated_crc

        return data

    def crc8(self, data: bytes) -> int:
        """Calculate the 8 bit CRC over a chunk of data.

        N.B. The SWIS used an initialiser of 0xFF and a polynomial
        of 0x31. This doesn't match what the OB EB ICD says (initialiser
        of 0 and polynomial of 0x07. The OB EB ICD looks to be correct.
        """
        crc = 0
        for b in data:
            crc ^= b
            for _ in range(8):
                crc <<= 1
                if crc & 0x100:
                    crc ^= 0x107
        return crc

class ObHkPacket(ObTmPacketWithCrc):
    """An OB HK packet."""

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tm.hk
    crc_field_name: ClassVar[str|None] = "CRC8"

class ObScienceDataPacket(ObTmPacketWithCrc):
    """An OB science packet."""

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tm.sci
    crc_field_name: ClassVar[str|None] = "CRC"

class ObAckPacket(ObTmPacketWithCrc):
    """An OB ACK packet."""

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tm.ack_struct
    crc_field_name: ClassVar[str|None] = "CRC8"

class ObNackPacket(ObTmPacket):
    """An OB NACK packet."""

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tm.nack

if __name__ == "__main__":
    hk = ObTmPacket.fromhex("""
        4061 0000 0000 0000 0012 25f5 ff0d 40c8 0f09 0000 0000 0000 0000
        0000 0003 0000 0000 0000 0000 0007 1300 0a7b 306f 9084 6085 4083
        5082 5087 2000 0000 0000 0000 0065
    """)
    assert(isinstance(hk, ObHkPacket))

    sci = ObTmPacket.fromhex("""
        4f af00 1f40 0007 1303 e004 6413 8d00 bd00 1f17 d500 d600 3018 2017 e2b6
    """)
    assert(isinstance(sci, ObScienceDataPacket))

    ack = ObTmPacket.fromhex("""
        49 0007 a800 0000 0062
    """)
    assert(isinstance(ack, ObAckPacket))

    nack = ObTmPacket.fromhex("""
        49 2A
    """)
    assert(isinstance(nack, ObNackPacket))

    print("All tests passed")
