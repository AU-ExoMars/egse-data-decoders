"""Provide a base class for decoding TC/TM packets."""
import bitstruct
from collections.abc import Iterator
from typing import Any, ClassVar

class PacketTemplate:
    """A class to hold a template for parsing binary data.

    start_byte is the position within the bytes data where we'll start
        reading from. 
    structure is a list of (name, bitstruct_format) pairs which will be
        used to decode the data.
    """

    def __init__(self, structure: list[tuple[str, str]], start_byte: int = 0) -> None:
        """Class constructor."""

        # The main bulk of this could be a couple of list comprehensions.
        # But being able to check the offset and size of each item in the
        # struct is useful for e.g. calculating CRC's
        self.bit_offset_of = {}
        self.bit_size_of = {}
        self.fmt = ""
        for name, fmt in structure:
            self.bit_offset_of[name] = bitstruct.calcsize(self.fmt)
            self.fmt += fmt
            self.bit_size_of[name] = bitstruct.calcsize(self.fmt) - self.bit_offset_of[name]

        self.start_byte = start_byte
        self.min_length_bits = bitstruct.calcsize(self.fmt)
        self.min_length_bytes = self.min_length_bits // 8 + (1 if self.min_length_bits & 7 else 0)

    def min_length(self):
        """Return the minimum length, in bits, needed to satisfy the format"""

    def decode(self, packet: bytes) -> dict[str, Any]:
        """Decode the supplied packets using the information in the class."""
        return bitstruct.unpack_dict(self.fmt, list(self.bit_offset_of.keys()), packet[self.start_byte:])
        
class PacketDecoder:
    """A base class providing functionality for decoding TC and TM packets.

    The idea is that subclasses will provide a template for decoding
    packets and the base class will be able to determine which subclass
    it should become on decoding. If that makes sense!
    """

    # Create an empty template for the cases where subclasses
    # don't need to specify one.
    template: ClassVar[dict[str, tuple[int, str]]] = {}

    def __init__(self):
        """Class constructor."""
        self.fields = {}

    @property
    def typeName(self) -> str:
        """Return the type name that this object ended up as."""
        return self.__class__.__name__

    @classmethod
    def _select_appropriate_subclass(
            cls: "type[PacketDecoder]",
            td: "PacketDecoder",
            payload: bytes
        ) -> None:
        """Find a subclass which can handle this packet.

        This function recursively iterates through subclasses of cls,
        looking for one which implements a subclass_matcher method
        which returns True when passed the packet. The type of td is
        then set to that subclass, the subclass's "template" items
        are handled, and its _decode method is called, if present.

        If no subclass handles this packet, a ValueError exception
        is raised.
        """

        # Save the payload into the class. We do it here, since it
        # gives the caller an opportunity to select what exactly
        # it thinks the payload is (e.g. it can strip off a packet
        # header if appropriate).
        td.payload = payload

        def _recursive_subclasses(cls: "type[PacketDecoder]") -> set:
            """Recursively find all subclasses of a class."""
            s = set()
            for c in cls.__subclasses__():
                s.add(c)
                s = s.union(_recursive_subclasses(c))
            return s

        # For each subclass...
        for c in _recursive_subclasses(cls):
            # If that class declares a blockId, check whether it
            # equals the blockId in the packet.
            if hasattr(c, "subclass_matcher") and c.subclass_matcher(td):

                # This is a bit nasty, but apparently legitimate - set
                # td's __class__ attribute to the class we're currently
                # looking at - basically we're casting the base class
                # instance to the subclass we've found.
                td.__class__ = c

                # Run through the template, using its entries to
                # decode the packet into class attributes.
                for name, value in c.template.decode(payload).items():
                    setattr(td, name, value)
                    td.fields[name] = 1

                # Some packet types may need further decoding, beyond
                # what the template provides.
                if hasattr(td, "decode"):
                    td.decode()

                 # And return, breaking out of the loop.
                return

        # We went through all subclasses, and none claimed this type Id.
        raise ValueError("No subclass claimed this packet")

    @classmethod
    def fromhex(cls, hexdata: str) -> "PacketDecoder":
        """Given some hex data, decode it and call the frombinary() method.

        Various logging formats exist, so we'll try to be lenient in what we
        accept.
        """
        return cls.frombinary(bytes([ int(x, 16) for x in hexdata.strip().split() ]))
    """
    We'll allow dict-like retrieval from the class.

    This vastly simplifies matters where you just want to dump all
    fields to a csv file, for example.
    """

    def __getitem__(self, key: str) -> Any:
        """By-key retrieval."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Dict-style "keys()" method."""
        return list(self.fields.keys())

    def values(self) -> list[Any]:
        """Dict-style "values()" method."""
        return [ getattr(self, key) for key in self.fields ]

    def items(self) -> Iterator[tuple[str, Any]]:
        """Dict-style "items()" method."""
        for k in self.fields:
            yield k, getattr(self, k)

