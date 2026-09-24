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

from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateException

class TmPacketException(BitstructTemplateException):
    pass

class TmPacket(BitstructTemplateClass):
    """Base class for TM packets from the OB.

    This class doesn't do anything except give us somewhere that we can
    hang common functions and start the recursive search when using
    frombinary/fromhex. If we started the search from BitstructTemplateClass,
    it could go through classes that clearly weren't appropriate and
    potentially return the wrong decode.
    """

    crc_field_name: ClassVar[str|None] = None

    crc_valid: bool|None = None
    calculated_crc: int|None = None

    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
        except Exception as e:
            raise

        if kwargs.get("packet", None) is not None and self.crc_field_name is not None:
            # Validate CRC.
            crc_offset = self.byte_offset_of(self.crc_field_name)

            self.calculated_crc = self.crc8(kwargs["packet"][:crc_offset])
            self.crc_valid = getattr(self, self.crc_field_name) == self.calculated_crc

    def crc8(self, data: bytes):
        """Calculate the 8 bit CRC over a chunk of data.

        N.B. The SWIS used an initialiser of 0xFF and a polynomial
        of 0x31. This doesn't match what the OB EB ICD says (initialiser
        of 0 and polynomial of 0x07. The OB EB ICD looks to be correct.
        """
        crc = 0
        for b in data:
            crc ^= b
            for i in range(8):
                crc <<= 1
                if crc & 0x100:
                    crc ^= 0x107
        return crc

class HkPacket(TmPacket):
    """An OB HK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.hk
    crc_field_name: ClassVar[str|None] = "CRC8"

class ScienceDataPacket(TmPacket):
    """An OB science packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.sci
    crc_field_name: ClassVar[str|None] = "CRC"

    @property
    def ABS_STEPS(self):
        return self.MTR_ABS_STEPS

class AckPacket(TmPacket):
    """An OB ACK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.ack_struct
    crc_field_name: ClassVar[str|None] = "CRC8"

class NackPacket(TmPacket):
    """An OB NACK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.nack
