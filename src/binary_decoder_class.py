"""A base class for decoding binary data."""

import typing


class BinaryDecoderError(Exception):
    """Used for signalling within the BinaryDecoderClass hierarchy."""

class BinaryDecoderClass:
    """A base class for decoding binary data.

    This provides a class method, frombinary(data: bytes) which will
    recurse through subclasses, looking for one which declares itself
    able to decode the data (by declaring a "decoder" class attribute
    that is True).

    When such a class is found, its constructor is called with no arguments,
    followed by a call to the resulting object's _decode(data: bytes) method.
    That method can populate fields or otherwise act on the object.

    If _decode raises a BinaryDecoderError then it is assumed
    to have declined the decode, and the search will continue.

    Recursion is pruned at any subclass which declares itself as a decoder;
    this allows decoder classes to be subclassed for other purposes without
    affecting the search.
    """

    @classmethod
    def __init_subclass__(
        cls: "type(BinaryDecoderClass)",
        **kwargs: typing.Any
    ) -> None:
        """Perform a basic check on the class hierarchy."""
        if "decoder" in cls.__dict__ and cls.decoder:
            for parent in cls.__bases__:
                if hasattr(parent, "decoder") and parent.decoder:
                    raise BinaryDecoderError(
                        cls.__name__
                         + " declares itself a decoder, but one of its parents also does"
                    )

    @classmethod
    def frombinary(
        cls: "type(BinaryDecoderClass)",
        data: bytes
    ) -> "BinaryDecoderClass|None":
        """Walk the hierarchy until we find a suitable subclass.

        A suitable subclass that has a "decoder" attribute that is True
        and which, when its _decode method is handed the data, doesn't
        raise BinaryDecoderError exception for the given data.

        This will either return a class instance or None.
        """
        def _find_handler(
            cls: "type(BinaryDecoderClass)",
            seen: set|None = None
        ) -> "type(BinaryDecoderClass)|None":
            """Recurse the class hierarchy, looking for a decoder."""
            # Avoid revisiting subclasses.
            if seen is None:
                seen = set()
            if cls in seen:
                return None
            seen.add(cls)

            # Does this class mark itself as a decoder?
            if hasattr(cls, "decoder") and cls.decoder:
                # Yep, so run its _decode method on the
                # data.
                try:
                    instance = cls()
                    instance._decode(data)
                    return instance
                except BinaryDecoderError:
                    # If decoding raises an exception,
                    # we return None to avoid recursing futher
                    # down (decoders are effectively leaf nodes
                    # in the class search, even if not in the
                    # hierarchy).
                    return None

            # Recurse through subclasses, looking for another
            # candidate. We'll do it in sort order just to give
            # some form of determinacy to it.
            for c in sorted(cls.__subclasses__(), key=lambda c: c.__name__):
                ret = _find_handler(c, seen)
                if ret is not None:
                    return ret

            return None
        ret = _find_handler(cls)
        if ret is None:
            raise BinaryDecoderError("No subclass accepted this data packet")
        return ret

