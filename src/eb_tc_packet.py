"""Classes for decoding TC packets."""
from typing import ClassVar
import tcstruct as tc

from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateException

class EbTcPacketException(BitstructTemplateException):
    pass

class EbTcHeader(BitstructTemplateClass):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header

class EbTcPacket(BitstructTemplateClass):
    """The base class for TCs.

    This provides the generic primitives for decoding TC packets. Subclasses
    should be pretty minimal, in general, just defining a blockId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C

    @classmethod
    def frombinary(cls, data):
        header = EbTcHeader(data[:EbTcHeader.min_length_bytes])
        if header.magic != cls.MAGIC:
            raise EbTcPacketException("Incorrect packet magic number")
        try:
            return super().frombinary(data[:EbTcHeader.min_length_bytes+header.dataLen])
        except BitstructTemplateException as e:
            raise EbTcPacketException(f"No subclass accepted this packet (block ID={header.blockId}, data length={header.dataLen})") from e

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.blockId is not None and self.blockId != self.matchBlockId:
            raise EbTcPacketException("Block ID does not match")

class EbTcRet(EbTcPacket):
    """The RET telecommand."""

    matchBlockId: ClassVar[int] = 0x00
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ret

    ret: float = None

    def __init__(self, **kwargs):
        """Class constructor.

        If a packet was passed in, decode the RET to fractional seconds.
        """
        super().__init__(**kwargs)

        if kwargs.get("packet", None) is not None:
            self.ret = self.retSeconds + self.retFractional/65536.0

class EbTcRequestHk(EbTcPacket):
    """The REQUEST_HK telecommand."""

    matchBlockId: ClassVar[int] = 0x01
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_request_hk

class EbTcPatch(EbTcPacket):
    """The PATCH telecommand has several variants, we need a cleverer __init__.

    We'll use EbTcPatch as a base class, with the various variants subclassing
    it and declaring their variant ID's. The base class provides a
    constructor which checks the ID, and that should allow frombinary to
    find the right one.

    Patching is stateful, and the content of a TC isn't necessarily enough
    to tell what the packet contains. In particular, pulling the patch data
    out of the "Finalise" variant potentially requires knowledge of the patch 
    length from a prior "Initialise" variant. I don't want to build this 
    intelligence into a low level packet decoder, so we'll just store the
    remainder of the packet into patchPayload, and higher level code can 
    post-process if needed.
    """

    matchBlockId: ClassVar[int] = 0x02
    strict_length_checking: ClassVar[bool] = False

    patchPayload: bytes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.variant is not None and self.variant != self.matchVariant:
            raise EbTcPacketException("Wrong patch variant")

        if kwargs.get("packet", None) is not None:
            # Single variant has the data length specified in the header.
            self.patchPayload = kwargs["packet"][self.min_length_bytes:]

class EbTcPatchSingle(EbTcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_single
    matchVariant: ClassVar[int] = 0

class EbTcPatchInitialise(EbTcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_initialise
    matchVariant: ClassVar[int] = 1

class EbTcPatchContinuation(EbTcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_continuation
    matchVariant: ClassVar[int] = 2

class EbTcPatchFinalise(EbTcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_finalise
    matchVariant: ClassVar[int] = 3

class EbTcDump(EbTcPacket):
    """The DUMP telecommand."""

    matchBlockId: ClassVar[int] = 0x03
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_dump

class EbTcSetHkRate(EbTcPacket):
    """The SET_HK_RATE telecommand."""

    matchBlockId: ClassVar[int] = 0x04
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_hk_rate

class EbTcMonitorAddr(EbTcPacket):
    """The MONITOR_ADDR telecommand."""

    matchBlockId: ClassVar[int] = 0x05
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_monitor_addr

class EbTcAbort(EbTcPacket):
    """The ABORT telecommand."""

    matchBlockId: ClassVar[int] = 0x06
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_abort

class EbTcGenericTc(EbTcPacket):
    """The GENERIC_TC telecommand."""

    matchBlockId: ClassVar[int] = 0x07
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_generic_tc

class EbTcSafe(EbTcPacket):
    """The SAFE telecommand."""

    matchBlockId: ClassVar[int] = 0x08
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_safe

class EbTcStandby(EbTcPacket):
    """The STANDBY telecommand."""

    matchBlockId: ClassVar[int] = 0x09
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_standby

class EbTcAcquisition(EbTcPacket):
    """The ACQUISITION telecommand."""

    matchBlockId: ClassVar[int] = 0x0A
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_acquisition

class EbTcSetMotorConfigs(EbTcPacket):
    """The SET_MOTOR_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0B
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_motor_configs

class EbTcSetHeaterConfigs(EbTcPacket):
    """The SET_HEATER_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0C
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_heater_configs

class EbTcSetAcqConfigs(EbTcPacket):
    """The SET_ACQ_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0D
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_acq_configs

class EbTcSetTecSetpoint(EbTcPacket):
    """The SET_TEC_SETPOINT telecommand."""

    matchBlockId: ClassVar[int] = 0x0E
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_tec_setpoint

class EbTcSetFdirLimits(EbTcPacket):
    """The SET_FDIR_LIMITS telecommand.

    This one's not yet fully decoded.
    """

    matchBlockId: ClassVar[int] = 0x0F
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_fdir_limits

class EbTcEnMechBoard(EbTcPacket):
    """The EN_MECH_BOARD telecommand."""

    matchBlockId: ClassVar[int] = 0x10
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_mech_board

class EbTcEnDetBoard(EbTcPacket):
    """The EN_DET_BOARD telecommand."""

    matchBlockId: ClassVar[int] = 0x11
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_det_board

class EbTcEnMechHeater(EbTcPacket):
    """The EN_MECH_HEATER telecommand."""

    matchBlockId: ClassVar[int] = 0x12
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_mech_heater

class EbTcEnDetHeater(EbTcPacket):
    """The EN_DET_HEATER telecommand."""

    matchBlockId: ClassVar[int] = 0x13
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_det_heater

class EbTcEnOb5V(EbTcPacket):
    """The EN_OB5V telecommand."""

    matchBlockId: ClassVar[int] = 0x14
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_ob5v

class EbTcObPark(EbTcPacket):
    """The OB_PARK telecommand."""

    matchBlockId: ClassVar[int] = 0x14
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_park

class EbTcObHoming(EbTcPacket):
    """The OB_HOMING telecommand."""

    matchBlockId: ClassVar[int] = 0x16
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_homing

class EbTcObHk(EbTcPacket):
    """The OB_HK telecommand."""

    matchBlockId: ClassVar[int] = 0x17
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_hk

class EbTcCheckMemory(EbTcPacket):
    """The CHECK_MEMORY telecommand."""

    matchBlockId: ClassVar[int] = 0x64
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_check_memory

class EbTcGoTo(EbTcPacket):
    """The GOTO telecommand."""

    matchBlockId: ClassVar[int] = 0x65
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_goto

class EbTcCopyMemory(EbTcPacket):
    """The COPY_MEMORY telecommand."""

    matchBlockId: ClassVar[int] = 0x66
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_copy_memory

class EbTcSwitchRs422(EbTcPacket):
    """The SWITCH_RS422 telecommand."""

    matchBlockId: ClassVar[int] = 0x67
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_switch_rs422

class EbTcSetTecCurrent(EbTcPacket):
    """The SET_TEC_CURRENT telecommand."""

    matchBlockId: ClassVar[int] = 0x68
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_tec_current


if __name__ == "__main__":
    test = EbTcRet(packet=None)
    print(test)
