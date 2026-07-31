"""Classes for decoding TC packets."""
from typing import ClassVar
import tcstruct as tc

from packet_decoder import PacketDecoder, PacketTemplate


class TcPacket(PacketDecoder):
    """The base class for TCs.

    This provides the generic primitives for decoding TC packets. Subclasses
    should be pretty minimal, in general, just defining a blockId to match,
    and an optional template and decode() method.
    """

    MAGIC: ClassVar[int] = 0x7C6EA12C
    header_template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_header)

    @classmethod
    def frombinary(cls: "type[TcPacket]", packet: bytes) -> "TcPacket":
        """Decode binary data and return an object of the appropriate subclass."""
        # Create an object of the base type.
        tc = TcPacket()

        if len(packet) < tc.header_template.min_length_bytes:
            raise ValueError("Packet is too short for a TC header")

        # Decode the TC header.
        header = tc.header_template.decode(packet)

        # Huh, it's not a TC header.
        if header["magic"] != tc.MAGIC:
            raise ValueError(f"Bad magic (0x{header['magic']:08x}), should be 0x{tc.MAGIC:08x}")

        tc.blockType = header["blockType"]
        tc.instrumentId = header["instrumentId"]
        tc.blockId = header["blockId"]
        tc.counter = header["counter"]
        tc.dataLen = header["dataLen"]

        tc.fields = {
            "blockType": 1, "instrumentId": 1, "blockId": 1,
            "counter": 1, "dataLen": 1,
        }

        if len(packet) != tc.dataLen + tc.header_template.min_length_bytes:
            raise ValueError("Packet data doesn't match specified length")

        # Call out to a super-class to find the right class for this packet.
        cls._select_appropriate_subclass(tc, packet[tc.header_template.min_length_bytes:])

        return tc

    @classmethod
    def subclass_matcher(cls: "type[TcPacket]", tc: "TcPacket") -> bool:
        """Given a subclass, indicate whether the subclass can handle the tc.

        For TC's, the determination is currently based on just the block Id.
        We could go deeper for some TC types (e.g. PATCH) where different
        variants do different things, based on the qualifier. But, at the
        top level, this is good enough.
        """
        return getattr(cls, "blockId", None) == tc.blockId

    def __str__(self) -> str:
        """By default, just return the packet type name."""
        return self.typeName

class TcRet(TcPacket):
    """The RET telecommand."""

    blockId: ClassVar[int] = 0x00
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_ret)

    def decode(self) -> None:
        """Decode the RET to fractional seconds."""
        self.fields["ret"] = 1
        self.ret = self.retSeconds + self.retFractional/65536.0

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Set RET to {self.ret:.5f}"

class TcRequestHk(TcPacket):
    """The REQUEST_HK telecommand."""

    blockId: ClassVar[int] = 0x01
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_request_hk)

class TcPatch(TcPacket):
    """The PATCH telecommand.

    This is a bit complicated, since the patch data structure is variable,
    based on the qualifier. So we declare the base template to just contain
    the qualifier, and have a decode() which then finishes the decoding.
    """

    blockId: ClassVar[int] = 0x02
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_patch)

    variant_templates: ClassVar[list[PacketTemplate]] = [
        PacketTemplate(tc.eb_patch_single),
        PacketTemplate(tc.eb_patch_initialise),
        PacketTemplate(tc.eb_patch_continuation),
        PacketTemplate(tc.eb_patch_finalise)
    ]

    def decode(self) -> None:
        """Decode the patch information.

        This uses the already-decoded variant to select one of the
        variant templates.
        """
        template = self.variant_templates[self.variant]
        for k, v in template.decode(self.payload).items():
            self.fields[k] = 1
            setattr(self, k, v)
        if self.variant != 1:
            self.patchData = self.payload[template.min_length_bytes:]

class TcDump(TcPacket):
    """The DUMP telecommand."""

    blockId: ClassVar[int] = 0x03
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_dump)

class TcSetHkRate(TcPacket):
    """The SET_HK_RATE telecommand."""

    blockId: ClassVar[int] = 0x04
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_hk_rate)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Set HK rate to {self.interval}s"

class TcMonitorAddr(TcPacket):
    """The MONITOR_ADDR telecommand."""

    blockId: ClassVar[int] = 0x05
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_monitor_addr)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Start monitoring memory address {self.monitorAddress:08x}"

class TcAbort(TcPacket):
    """The ABORT telecommand."""

    blockId: ClassVar[int] = 0x06
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_abort)

class TcGenericTc(TcPacket):
    """The GENERIC_TC telecommand."""

    blockId: ClassVar[int] = 0x07
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_generic_tc)

class TcSafe(TcPacket):
    """The SAFE telecommand."""

    blockId: ClassVar[int] = 0x08
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_safe)

class TcStandby(TcPacket):
    """The STANDBY telecommand."""

    blockId: ClassVar[int] = 0x09
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_standby)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Image {self.aswImage}, force = {self.forceLaunch}"

class TcAcquisition(TcPacket):
    """The ACQUISITION telecommand."""

    blockId: ClassVar[int] = 0x0A
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_acquisition)

class TcSetMotorConfigs(TcPacket):
    """The SET_MOTOR_CONFIGS telecommand."""

    blockId: ClassVar[int] = 0x0B
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_motor_configs)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return (
            f"{self.typeName}: PeakCurrent={self.motorPeakCurrent}, "
            f"Speed={self.motorSpeed}, GuardTime={self.motorGuardTime}, "
            f"RecVal={self.motorRecVal}, RelativeMax={self.motorRelativeMax}"
        )

class TcSetHeaterConfigs(TcPacket):
    """The SET_HEATER_CONFIGS telecommand."""

    blockId: ClassVar[int] = 0x0C
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_heater_configs)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return (
            f"{self.typeName}: Mech={self.mechLowerLimit}-{self.mechUpperLimit}, "
            f"Det={self.detLowerLimit}-{self.detUpperLimit}"
        )

class TcSetAcqConfigs(TcPacket):
    """The SET_ACQ_CONFIGS telecommand."""

    blockId: ClassVar[int] = 0x0D
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_acq_configs)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        if self.measurementMode == 0:
            return (
                f"{self.typeName}: Mode 1, Table={self.measurementTable}, "
                f"Start={self.startPosition}, End={self.endPosition}"
            )
        elif self.measurementMode == 1:
            return (
                f"{self.typeName}: Mode 2, Position={self.startPosition}, "
                f"Interval={self.sampleTimeSpacing}ms, "
                f"Duration={self.measurementDuration}s"
            )
        return f"{self.typeName}: UNKNOWN MODE {self.measurementMode}"

class TcSetTecSetpoint(TcPacket):
    """The SET_TEC_SETPOINT telecommand."""

    blockId: ClassVar[int] = 0x0E
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_tec_setpoint)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Setpoint={self.setpoint}"

class TcSetFdirLimits(TcPacket):
    """The SET_FDIR_LIMITS telecommand.

    This one's not yet fully decoded either.
    """

    blockId: ClassVar[int] = 0x0F
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_fdir_limits)

class TcEnMechBoard(TcPacket):
    """The EN_MECH_BOARD telecommand."""

    blockId: ClassVar[int] = 0x10
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_en_mech_board)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Enable={self.enable}"

class TcEnDetBoard(TcPacket):
    """The EN_DET_BOARD telecommand."""

    blockId: ClassVar[int] = 0x11
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_en_det_board)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Enable={self.enable}"

class TcEnMechHeater(TcPacket):
    """The EN_MECH_HEATER telecommand."""

    blockId: ClassVar[int] = 0x12
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_en_mech_heater)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Enable={self.enable}"

class TcEnDetHeater(TcPacket):
    """The EN_DET_HEATER telecommand."""

    blockId: ClassVar[int] = 0x13
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_en_det_heater)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Enable={self.enable}"

class TcEnOb5V(TcPacket):
    """The EN_OB5V telecommand."""

    blockId: ClassVar[int] = 0x14
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_en_ob5v)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Enable={self.enable}"

class TcObPark(TcPacket):
    """The OB_PARK telecommand."""

    blockId: ClassVar[int] = 0x14
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_ob_park)

class TcObHoming(TcPacket):
    """The OB_HOMING telecommand."""

    blockId: ClassVar[int] = 0x16
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_ob_homing)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Destination={self.destination}"

class TcObHk(TcPacket):
    """The OB_HK telecommand."""

    blockId: ClassVar[int] = 0x17
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_ob_hk)

class TcCheckMemory(TcPacket):
    """The CHECK_MEMORY telecommand."""

    blockId: ClassVar[int] = 0x64
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_check_memory)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Start={self.startAddress:08x}, Length={self.length}"

class TcGoTo(TcPacket):
    """The GOTO telecommand."""

    blockId: ClassVar[int] = 0x65
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_goto)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Address={self.gotoAddress:08x}"

class TcCopyMemory(TcPacket):
    """The COPY_MEMORY telecommand."""

    blockId: ClassVar[int] = 0x66
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_copy_memory)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return (f"{self.typeName}: From={self.fromAddress:08x}, "
               f"To={self.toAddress:08x}, Length={self.length}")

class TcSwitchRs422(TcPacket):
    """The SWITCH_RS422 telecommand."""

    blockId: ClassVar[int] = 0x67
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_switch_rs422)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Port={self.port}"

class TcSetTecCurrent(TcPacket):
    """The SET_TEC_CURRENT telecommand."""

    blockId: ClassVar[int] = 0x68
    template: ClassVar[PacketTemplate] = PacketTemplate(tc.eb_set_tec_current)

    def __str__(self) -> str:
        """Provide a more detailed summary."""
        return f"{self.typeName}: Peltier Digital Value={self.peltierDv}"

