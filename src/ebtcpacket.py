"""Classes for decoding TC packets."""
from typing import ClassVar
import tcstruct as tc

from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateException

class TcPacketException(BitstructTemplateException):
    pass

class TcHeader(BitstructTemplateClass):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header

class TcPacket(BitstructTemplateClass):
    """The base class for TCs.

    This provides the generic primitives for decoding TC packets. Subclasses
    should be pretty minimal, in general, just defining a blockId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C

    @classmethod
    def frombinary(cls, data):
        header = TcHeader(data[:TcHeader.min_length_bytes])
        if header.magic != cls.MAGIC:
            raise TcPacketException("Incorrect packet magic number")
        try:
            return super().frombinary(data[:TcHeader.min_length_bytes+header.dataLen])
        except BitstructTemplateException as e:
            raise TcPacketException(f"No subclass accepted this packet (block ID={header.blockId}, data length={header.dataLen})") from e

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.blockId is not None and self.blockId != self.matchBlockId:
            raise TcPacketException("Block ID does not match")

class TcRet(TcPacket):
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

class TcRequestHk(TcPacket):
    """The REQUEST_HK telecommand."""

    matchBlockId: ClassVar[int] = 0x01
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_request_hk

class TcPatch(TcPacket):
    """The PATCH telecommand has several variants, we need a cleverer __init__.

    We'll use TcPatch as a base class, with the various variants subclassing
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
            raise TcPacketException("Wrong patch variant")

        if kwargs.get("packet", None) is not None:
            # Single variant has the data length specified in the header.
            self.patchPayload = kwargs["packet"][self.min_length_bytes:]

class TcPatchSingle(TcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_single
    matchVariant: ClassVar[int] = 0

class TcPatchInitialise(TcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_initialise
    matchVariant: ClassVar[int] = 1

class TcPatchContinuation(TcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_continuation
    matchVariant: ClassVar[int] = 2

class TcPatchFinalise(TcPatch):
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_patch_finalise
    matchVariant: ClassVar[int] = 3

class TcDump(TcPacket):
    """The DUMP telecommand."""

    matchBlockId: ClassVar[int] = 0x03
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_dump

class TcSetHkRate(TcPacket):
    """The SET_HK_RATE telecommand."""

    matchBlockId: ClassVar[int] = 0x04
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_hk_rate

class TcMonitorAddr(TcPacket):
    """The MONITOR_ADDR telecommand."""

    matchBlockId: ClassVar[int] = 0x05
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_monitor_addr

class TcAbort(TcPacket):
    """The ABORT telecommand."""

    matchBlockId: ClassVar[int] = 0x06
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_abort

class TcGenericTc(TcPacket):
    """The GENERIC_TC telecommand."""

    matchBlockId: ClassVar[int] = 0x07
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_generic_tc

class TcSafe(TcPacket):
    """The SAFE telecommand."""

    matchBlockId: ClassVar[int] = 0x08
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_safe

class TcStandby(TcPacket):
    """The STANDBY telecommand."""

    matchBlockId: ClassVar[int] = 0x09
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_standby

class TcAcquisition(TcPacket):
    """The ACQUISITION telecommand."""

    matchBlockId: ClassVar[int] = 0x0A
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_acquisition

class TcSetMotorConfigs(TcPacket):
    """The SET_MOTOR_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0B
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_motor_configs

class TcSetHeaterConfigs(TcPacket):
    """The SET_HEATER_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0C
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_heater_configs

class TcSetAcqConfigs(TcPacket):
    """The SET_ACQ_CONFIGS telecommand."""

    matchBlockId: ClassVar[int] = 0x0D
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_acq_configs

class TcSetTecSetpoint(TcPacket):
    """The SET_TEC_SETPOINT telecommand."""

    matchBlockId: ClassVar[int] = 0x0E
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_tec_setpoint

class TcSetFdirLimits(TcPacket):
    """The SET_FDIR_LIMITS telecommand.

    This one's not yet fully decoded.
    """

    matchBlockId: ClassVar[int] = 0x0F
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_fdir_limits

class TcEnMechBoard(TcPacket):
    """The EN_MECH_BOARD telecommand."""

    matchBlockId: ClassVar[int] = 0x10
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_mech_board

class TcEnDetBoard(TcPacket):
    """The EN_DET_BOARD telecommand."""

    matchBlockId: ClassVar[int] = 0x11
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_det_board

class TcEnMechHeater(TcPacket):
    """The EN_MECH_HEATER telecommand."""

    matchBlockId: ClassVar[int] = 0x12
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_mech_heater

class TcEnDetHeater(TcPacket):
    """The EN_DET_HEATER telecommand."""

    matchBlockId: ClassVar[int] = 0x13
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_det_heater

class TcEnOb5V(TcPacket):
    """The EN_OB5V telecommand."""

    matchBlockId: ClassVar[int] = 0x14
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_en_ob5v

class TcObPark(TcPacket):
    """The OB_PARK telecommand."""

    matchBlockId: ClassVar[int] = 0x14
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_park

class TcObHoming(TcPacket):
    """The OB_HOMING telecommand."""

    matchBlockId: ClassVar[int] = 0x16
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_homing

class TcObHk(TcPacket):
    """The OB_HK telecommand."""

    matchBlockId: ClassVar[int] = 0x17
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_ob_hk

class TcCheckMemory(TcPacket):
    """The CHECK_MEMORY telecommand."""

    matchBlockId: ClassVar[int] = 0x64
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_check_memory

class TcGoTo(TcPacket):
    """The GOTO telecommand."""

    matchBlockId: ClassVar[int] = 0x65
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_goto

class TcCopyMemory(TcPacket):
    """The COPY_MEMORY telecommand."""

    matchBlockId: ClassVar[int] = 0x66
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_copy_memory

class TcSwitchRs422(TcPacket):
    """The SWITCH_RS422 telecommand."""

    matchBlockId: ClassVar[int] = 0x67
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_switch_rs422

class TcSetTecCurrent(TcPacket):
    """The SET_TEC_CURRENT telecommand."""

    matchBlockId: ClassVar[int] = 0x68
    template: ClassVar[list[tuple[str, str]]] = tc.eb_header + tc.eb_set_tec_current


if __name__ == "__main__":
    test = TcRet(packet=None)
    print(test)
