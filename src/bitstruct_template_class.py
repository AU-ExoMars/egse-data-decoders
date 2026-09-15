"""A class for handling packet data decodes.

I quite like the OB EGSE's way of describing packet data, and I
certainly don't want to start maintaining an independent set of
definitions that could get out of sync.

So, instead, the BitstructTemplateClass exists. It uses Python's
__init_subclass__ capability populate subclass attributes using
a tmstruct template. The idea is that you subclass
BitstructTemplateClass, supplying a tmstruct template, and the
resulting subclass gets a bunch of attributes whose names match
the tmstruct template names.

The base class also provides a constructor which can use a supplied
packet to initialise those attributes. This allows very simple
decode operations, such as:

  hk = HkPacket(packet)
  print(hk.SWIR_OFFSET)

"""
from typing import Any, ClassVar

import bitstruct


class BitstructTemplateClass:
    """A base class which can be subclassed using a "tmstruct" template.

    The OB EGSE has a nice set of definitions with its tmstruct.py, these
    describing how to decode various Enfys packet types. I'd very much like
    to avoid replicating that piece of work. So this base class has an
    __init_subclass__ method which will examine a tmstruct-style template
    (specified as a class variable) and generate class attributes to hold
    the values (setting them to None in the first instance).

    The class also provides a constructor which can decode packet data using
    the supplied template, populating the various attributes.

    Example usage:

        import tmstruct
        class HkPacket(BitstructTemplateClass):
            template = tmstruct.hk

        decoded = HkPacket(packet_data)
        print(decoded)

    """

    start_byte: int = 0

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Create subclass attributes and packet parsing info from template.

        This method is run when the base class is subclassed. It's assumed
        that the subclass will provide a "template" attribute, taking the
        form of a list of (NAME, bitstruct_format) tuples. This is the form
        that tmstruct uses. We iterate that list, creating class attributes,
        storing information about sizing and offsets (for possible use by
        class users) and building a bitstruct format string.
        """
        # I'm not convinced bit_offset_of and bit_size_of are actually
        # all that useful. But it's easy to generate them here, and
        # more difficult for a subclass to do it. So let's keep them for
        # now.
        cls.bit_offset_of = {}
        cls.bit_size_of = {}

        # We need to build the bitstruct format string from the template
        # definition.
        cls.bitstruct_fmt = ""
        for name, fmt in cls.template:
            # Add a class attribute, with the specified name and a default
            # value.
            setattr(cls, name, None)

            # The offset of this item is the length of the
            # data consumed by the partially constructed bitstruct
            # format.
            cls.bit_offset_of[name] = bitstruct.calcsize(cls.bitstruct_fmt)

            # Now we add on the format string for this item.
            cls.bitstruct_fmt += fmt

            # The size of this item will therefore be the size of the new
            # format string minus that of the previous one. I suspect I
            # could just use calcsize(fmt), but there may be wrinkles
            # around e.g. endianness, so we'll do it this way. Again, maybe
            # nothing will use offset_of and size_of, and I can just remove
            # the whole thing!
            cls.bit_size_of[name] = (
                bitstruct.calcsize(cls.bitstruct_fmt) - cls.bit_offset_of[name]
            )

        # For later checking, we want to know how long of a packet is
        # needed.
        cls.min_length_bits = bitstruct.calcsize(cls.bitstruct_fmt)
        cls.min_length_bytes = (
            cls.min_length_bits // 8
            + (1 if cls.min_length_bits & 7 else 0)
        )

    def __init__(self, packet: bytes|None = None, **kwargs: Any) -> None:
        """Class constructor.

        If a packet is given, then the information derived from
        the class template string is used to decode it and populate
        attributes.

        Entries in kwargs are examined and used to fill out class
        attributes, allowing initialisation of "augmented" sub-classes.
        While iterating kwargs, checks are performed to ensure that the
        specified attribute is both present and not decoded from any
        supplied packet.

        I think this covers all bases: you can create an un-initialised
        object, where all attributes are None; an object extracted from a
        received packet; an object from plain data (no supplied packet) and
        objects of e.g. further derived types.
        """
        if packet is not None:
            # If a packet was supplied, check it's long enough before
            # trying a decode.
            if len(packet) < self.start_byte + self.min_length_bytes:
                raise ValueError("Packet is too short to decode")

            # Decode according to the bitstruct format string.
            unpacked = bitstruct.unpack(self.bitstruct_fmt, packet[self.start_byte:])

            # Store the unpacket data into the class attributes.
            for i, value in enumerate(unpacked):
                setattr(self, self.template[i][0], value)

        # If any kwargs have been supplied, examine them.
        for attr, value in kwargs.items():
            # Raise an exception if a packet was supplied and the
            # attribute would normally be derived from the packet data.
            if attr in self.bit_offset_of and packet is not None:
                raise ValueError(f"{attr} was specified both in packet and kwargs")

            # If the attribute name isn't actually present in the class,
            # raise an exception, rather than allowing arbitrary members to
            # be set.
            if not hasattr(self, attr):
                raise ValueError(f"{attr} is not present in this class")

            # OK, let's do it!
            setattr(self, attr, value)

    def __repr__(self) -> str:
        """Create a human/machine-readable representation of the object."""
        ret = []
        for name, value in vars(self).items():
            ret.append(f"{name}={value}")
        return f"{self.__class__.__name__}({', '.join(ret)})"

if __name__ == "__main__":
    class BtcTest(BitstructTemplateClass):
        """Example demonstrating usage of class."""

        template: ClassVar[list[tuple[str,str]]] = [
            ("arg1", "u3"),
            ("arg2", "u1"),
            ("arg3", "u4"),
        ]
        start_byte = 1

    # The "X" should be skipped because of start_byte.
    # "\x74" should decode to arg1=3, arg2=1, arg3=4
    t = BtcTest(b"X\x74")
    print(t)
