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
import bitstruct
import copy
import typing

class BitstructTemplateException(Exception):
    pass

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

    For convieninence, a "fields" attribute is provided. This is a dict
    whose keys are attribute names and values are (offset, size) tuples.
    The dict is populated using the template to identify the packet data
    offset and bit size of each template entry. It will also contain
    entries for any type-hinted class attributes that aren't ClassVar hints
    and are "simple" types (things you could reasonably expect to go
    into a CSV or JSON file without causing problems).

    This allows you to build augmented subclasses (e.g. adding a timestamp
    or further-decoded value) and have these further attributes identified
    for e.g. automatic generation of CSV files. These extra .fields entries
    take a value of (None, None) to indicate they're not present in packet
    data.

    Example usage:

        import tmstruct
        class HkPacket(BitstructTemplateClass):
            template = tmstruct.hk

        decoded = HkPacket(packet_data)
        print(decoded)

    """

    # Things we'll allow to go into .fields
    simple_types: typing.ClassVar[type] = (int, float, bool, str)

    start_byte: typing.ClassVar[int] = 0
    strict_length_checking: typing.ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: typing.Any) -> None:
        """Create subclass attributes and packet parsing info from template.

        This method is run when the base class is subclassed. It's assumed
        that the subclass will provide a "template" attribute, taking the
        form of a list of (NAME, bitstruct_format) tuples. This is the form
        that tmstruct uses. We iterate that list, creating class attributes,
        storing information about sizing and offsets (for possible use by
        class users) and building a bitstruct format string.
        """

        # If the subclass doesn't have a template then we can't do any of
        # the below. Not necessarily an error - the subclass could be an
        # intermediate class.
        if not hasattr(cls, "template"):
            return

        # I'm not convinced the offset and size info is actually
        # all that useful. But it's easy to generate it here, and
        # more difficult for a subclass to do it. So let's keep it
        # for now. The main point is to have a dict indicating which
        # fields are available.
        cls.fields = {}

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
            offset = bitstruct.calcsize(cls.bitstruct_fmt)

            # Now we add on the format string for this item.
            cls.bitstruct_fmt += fmt

            # The size of this item will therefore be the size of the new
            # format string minus that of the previous one. I suspect I
            # could just use calcsize(fmt), but there may be wrinkles
            # around e.g. endianness, so we'll do it this way. Again, maybe
            # nothing will use offset_of and size_of, and I can just remove
            # the whole thing!
            size = bitstruct.calcsize(cls.bitstruct_fmt) - offset

            # Record bit offset and size information for this field.
            cls.fields[name] = (offset, size)

        # For later checking, we want to know how long of a packet is
        # needed.
        cls.min_length_bits = bitstruct.calcsize(cls.bitstruct_fmt)
        cls.min_length_bytes = (
            cls.min_length_bits // 8
            + (1 if cls.min_length_bits & 7 else 0)
        )

        # We also run through the subclass's type annotations. Any annotated
        # fields that are present (but not ClassVar annotations) will also
        # be added to cls.fields, but with None as the offset and size. This
        # allows users to iterate over obj.fields.keys(). Useful if you're
        # doing automatic csv generation, for example.
        for name, value in typing.get_type_hints(cls).items():
            if not hasattr(cls, name):
                setattr(cls, name, None)
            if typing.get_origin(value) is not typing.ClassVar:
                # I am not absolutely sure this is the correct
                # way of doing things, but it matches everything
                # I've tried to do so far.

                simple = False
                try:
                    for t in cls.simple_types:
                        if issubclass(t, value):
                            simple = True
                            break
                except TypeError:
                    pass
                if simple:
                    cls.fields[name] = (None, None)

    def __init__(self, packet: bytes|None = None, src: "BitstructTemplateClass|None" = None, **kwargs: typing.Any) -> None:
        """Class constructor.

        If a packet is given, then the information derived from
        the class template string is used to decode it and populate
        attributes.

        Otherwise, if a src is given, copy its inheritable attributes
        over to self. This is used as a copy constructor for initialising
        subclasses.

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
        if packet is not None and src is not None:
            raise RuntimeError("Only one of 'packet' and 'src' may be provided")

        if packet is not None:
            # If a packet was supplied, check it's the right length before
            # attempting a decode.
            if len(packet) < self.start_byte + self.min_length_bytes:
                raise BitstructTemplateException("Packet too short")

            # By default, we check exact length, but if the class unsets
            # strict_length_checking, then we only check for minimum length.
            # Some packet types are variable length, so we have to relax the
            # check in those cases.
            if self.strict_length_checking and len(packet) > self.start_byte + self.min_length_bytes:
                raise BitstructTemplateException("Packet too long")

            # Decode according to the bitstruct format string.
            unpacked = bitstruct.unpack(self.bitstruct_fmt, packet[self.start_byte:])

            # Store the unpacked data into the class attributes.
            for i, value in enumerate(unpacked):
                setattr(self, self.template[i][0], value)

        elif src is not None:
            if not isinstance(self, src.__class__):
                raise BitstructTemplateException(f"src is not derived from {self.__class__.__name__}")
            for f in src.__dict__:
                if not f.startswith("__"):
                    setattr(self, f, copy.deepcopy(getattr(src, f)))

        # If any kwargs have been supplied, examine them.
        for attr, value in kwargs.items():
            # If the attribute name isn't actually present in the class
            # "fields" list, raise an exception, rather than allowing
            # arbitrary members to be set via this avenue.
            if attr not in self.fields:
                raise BitstructTemplateException(f"{attr} is not annotated or templated in this class")

            # Raise an exception if a packet was supplied and the
            # kwargs-supplied attribute would normally be derived from
            # the packet data.
            if (
                    packet is not None and
                    attr in self.fields and
                    self.fields[attr][0] is not None
            ):
                raise BitstructTemplateException(f"{attr} was specified both in packet and kwargs")

            # OK, everything looks OK, so set the class attribute.
            setattr(self, attr, value)

    @property
    def type_name(self) -> str:
        """Return the type name that this object ended up as."""
        return self.__class__.__name__

    @classmethod
    def fromhex(cls, hex_data: str) -> "BitstructTemplateClass":
        """Given some hex data, decode it and construct an object.

        Various logging formats exist, so we'll try to be lenient in what we
        accept.
        """
        hex_data = [ x.replace("0x", "") for x in hex_data.strip().split() ]
        hex_data = [ "0" * (len(x) % 2)+x for x in hex_data ]
        hex_data = "".join(hex_data)
        return cls.frombinary(bytes.fromhex(hex_data))

    @classmethod
    def frombinary(cls, data: bytes):
        def _recursive_subclasses(cls: "type[BitstructTemplateClass]") -> set:
            s = set()
            for c in cls.__subclasses__():
                s.add(c)
                s = s.union(_recursive_subclasses(c))
            return s
        for c in [cls] + list(_recursive_subclasses(cls)):
            if hasattr(c, "template"):
                # We'll offer the data to each subclass, in turn, and
                # the first one whose constructor accepts the data can
                # have it. This does imply that constructors should be
                # careful about what they accept. The base class
                # constructor does length checking, but subclasses will
                # likely need to do further checks.
                try:
                    return c(packet=data)
                except BitstructTemplateException as e:
                    pass
        raise BitstructTemplateException("No subclass accepted this packet")

    """
    We'll allow dict-like retrieval from the class.

    This vastly simplifies matters where you just want to dump all
    fields to a csv file, for example.
    """

    def __getitem__(self, key: str) -> typing.Any:
        """By-key retrieval."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Dict-style "keys()" method."""
        return list(self.fields.keys())

    def values(self) -> list[typing.Any]:
        """Dict-style "values()" method."""
        return [ getattr(self, key) for key in self.fields ]

    def items(self) -> typing.Iterator[tuple[str, typing.Any]]:
        """Dict-style "items()" method."""
        for k in self.fields:
            yield k, getattr(self, k)

    def __repr__(self) -> str:
        """Create a human/machine-readable representation of the object.

        N.B. This will not be properly quoted in the case where fields are
        not integers. If you create a subclass for which this matters, you
        should override __repr__.
        """
        ret = [
            f"{name}={getattr(self, name)}"
                for name in self.fields
        ]
        return f"{self.__class__.__name__}({', '.join(ret)})"

if __name__ == "__main__":
    class BtcTest(BitstructTemplateClass):
        """Example demonstrating usage of class."""

        template: typing.ClassVar[list[tuple[str,str]]] = [
            ("arg1", "u3"),
            ("arg2", "u1"),
            ("arg3", "u4"),
        ]
        start_byte: typing.ClassVar[int] = 1

    class SubBtcTest(BtcTest):
        """Example subclass."""
        extra: float|None = None

    # The "X" should be skipped because of start_byte.
    # "\x74" should decode to arg1=3, arg2=1, arg3=4
    t = BtcTest(b"X\x74")
    print(t)

    s = SubBtcTest(src=t, extra=1)
    print(s)
