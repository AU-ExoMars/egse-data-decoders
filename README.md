Much of this is based on the code I wrote while developing test validation
code for the Enfys SWIS. I needed to be able to read hex data from the
SWIS logfiles and decode it back to structures that corresponded to the
various telecommand and telemetry packets used by Enfys.

It's become obvious that we've an ongoing need for such decodes, so I've
broken them out tidied them up for more generic use.

The system makes heavy use of inheritance: a base "BitstructTemplateClass" class
is defined, providing a framework for decoding a packet and deciding which
of a set of its subclasses should be instantiated to hold a full decode of
the packet. It provides a "frombinary()" class method which, for each
candidate subclass, examines a template and attempts a data decode. If the
subclass defines a _decode(self, data) method, it will be given a chance to 
look at the raw data and, optionally, store extra attributes.

For example, the EB's TcPacket has a subclass, TcRet, which stores a decoded
RET TC request. Calling TcPacket.frombinary(packet_data) will cause a TcRet
object to be returned, with fields relevant to the RET request.

The focus is on making implementation of the subclasses as simple as
possible and to reuse already-existing information. I've copied the
"tmstruct.py" module from the OB EGSE - this module contains many of 
the packet definitions for both OB and EB. I've also added a "tcstruct.py",
which contains the EB TC data structures.

TODO: Add TC datastructures for the OB side of things.

In many cases, the subclass will only contain a couple of class
variables which will tell the parent how to select a subclass 
and how to decode the packet data.

An example:
```
    class TcSetHkRate(TcPacket):
        """The SET_HK_RATE telecommand."""

        decoder: ClasVar[bool] = True
        blockId: ClassVar[int] = 0x04
        template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_hk_rate
```

Calling TcPacket.frombinary(packet_data), where packet_data contains a
complete SET_HK_RATE telecommand will cause a TcSetHkRate object to be
returned, with an "interval" attribute containing the decoded HK interval.
The TcPacket base class will also add attributes decoded from the TC packet
header.

BitstructTemplateClass also provides a fromhex() method which does a fairly
flexible hexadecimal decode before passing the result on to frombinary().
This should make things quite convenient for deciphering EB and OB logs.
