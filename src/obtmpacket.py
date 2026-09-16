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
    we can start the recursive search when using frombinary/fromhex. If
    we started the search from BitstructTemplateClass, it could go through
    classes that clearly weren't appropriate and potentially return the
    wrong decode.
    """

class HkPacket(TmPacket):
    """An OB HK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.hk

class ScienceDataPacket(TmPacket):
    """An OB science packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.sci

    def __init__(self, **kwargs):
        """Class constructor.

        This is only present for compatibility with EB science data.
        An EB science data packet can contain multiple rows of science 
        data, so we decode it into a "measurements" list. Having a dummy
        "measurements" list here gives us consistency between the two
        classes.
        """
        super().__init__(**kwargs)
        self.measurements = [ self ]

class AckPacket(TmPacket):
    """An OB ACK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.ack_struct

class NackPacket(TmPacket):
    """An OB NACK packet."""
    template: ClassVar[list[tuple[str, str]]] = tm.nack
