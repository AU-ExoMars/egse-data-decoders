"""Classes for decoding OB Telecommand packets.

The base class, ObTmPacket, does most of the work. Subclasses are defined for
the various packet types, and ObTmPacket.frombinary() will return an object of
the appropriate class for the decoded packet. The subclasses each define
a template which defines how to decode the packet data into class attributes
and, optionally, a decode() method, which is called after the template
decoding, to perform any further decoding that the subclass might wish to do.
"""

from typing import ClassVar

import tcstruct as tc
from bitstruct_template_class import BitstructTemplateClass, BitstructTemplateError


class ObTcPacketError(BitstructTemplateError):
    """Error signalling within TC handling."""

class ObTcHeader(BitstructTemplateClass):
    """A generic decode to get header and CRC info.

    We'll call it "Header", but it's actually got to examine the
    whole packet to get the CRC fields. And since we're doing that,
    we may as well check the CRC here.
    """

    decoder: ClassVar[bool] = True
    template: ClassVar[list[tuple[str, str]]] = tc.ob_generic

    crc_valid: bool|None = None
    calculated_crc: int|None = None

    def _decode(self, data: bytes) -> bytes:
        data = super()._decode(data)

        crc_offset = self.byte_offset_of("CRC")

        self.calculated_crc = self.crc8(data[:crc_offset])
        self.crc_valid = (self.calculated_crc == self.CRC)

        return data

    def crc8(self, data: bytes) -> int:
        """Calculate the 8 bit CRC over a chunk of data."""
        crc = 0
        for b in data:
            crc ^= b
            for _ in range(8):
                crc <<= 1
                if crc & 0x100:
                    crc ^= 0x107
        return crc

class ObTcPacket(BitstructTemplateClass):
    """Base class for TC packets from the OB.

    All TC packets take the same format: 8 bytes long with an 8 bit CRC at
    the end.
    """

    crc_valid: bool|None = None
    calculated_crc: int|None = None

    def _decode(self, data: bytes) -> bytes:
        header = ObTcHeader.frombinary(data)

        self.crc_valid = header.crc_valid
        self.calculated_crc = header.calculated_crc

        if header.CMD_ID != self.match_cmd_id:
            raise ObTcPacketError("Command ID does not match")

        return super()._decode(data)

    def tobinary(self) -> bytes:
        """Example convenience helper for BitstructClass.tobinary().

        * Store self.match_cmd_id into self.CMD_ID.
        * Get an initial encode using super().tobinary()
        * Use ObTcHeader to get a CRC from that
        * Call super().tobinary() again to get a correctly checksummed result.
        """

        self.CMD_ID = self.match_cmd_id

        header = ObTcHeader.frombinary(super().tobinary())

        self.CRC = header.calculated_crc

        return super().tobinary()


class ObTcHkRequest(ObTcPacket):
    """An OB HK_REQUEST TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0000
    template: ClassVar[list[tuple[str, str]]] = tc.ob_hk_request

class ObTcClearErrors(ObTcPacket):
    """An OB CLEAR_ERRORS TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0010
    template: ClassVar[list[tuple[str, str]]] = tc.ob_clear_errors

class ObTcSetErrors(ObTcPacket):
    """An OB SET_ERRORS TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0011
    template: ClassVar[list[tuple[str, str]]] = tc.ob_set_errors

class ObTcPowerControl(ObTcPacket):
    """An OB POWER_CONTROL TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0100
    template: ClassVar[list[tuple[str, str]]] = tc.ob_power_control

class ObTcHeaterControl(ObTcPacket):
    """An OB HEATER_CONTROL TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0101
    template: ClassVar[list[tuple[str, str]]] = tc.ob_heater_control

class ObTcSetMechSp(ObTcPacket):
    """An OB SET_MECH_SP TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0110
    template: ClassVar[list[tuple[str, str]]] = tc.ob_set_mech_sp

class ObTcSetDetecSp(ObTcPacket):
    """An OB SET_DETEC_SP TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b0111
    template: ClassVar[list[tuple[str, str]]] = tc.ob_set_detec_sp

class ObTcSetMtrParam(ObTcPacket):
    """An OB SET_MTR_PARAM TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1000
    template: ClassVar[list[tuple[str, str]]] = tc.ob_set_mtr_param

class ObTcMtrMovPos(ObTcPacket):
    """An OB MTR_MOV_POS TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1001
    template: ClassVar[list[tuple[str, str]]] = tc.ob_mtr_mov_pos

class ObTcMtrMovNeg(ObTcPacket):
    """An OB MTR_MOVE_NEG TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1010
    template: ClassVar[list[tuple[str, str]]] = tc.ob_mtr_move_neg

class ObTcMtrHalt(ObTcPacket):
    """An OB MTR_HALT TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1011
    template: ClassVar[list[tuple[str, str]]] = tc.ob_mtr_halt

class ObTcMtrHoming(ObTcPacket):
    """An OB MTR_HOMING TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1100
    template: ClassVar[list[tuple[str, str]]] = tc.ob_mtr_homing

class ObTcSetHkSamples(ObTcPacket):
    """An OB SET_HK_SAMPLES TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1101
    template: ClassVar[list[tuple[str, str]]] = tc.ob_set_hk_samples

class ObTcSciOffset(ObTcPacket):
    """An OB SCI_OFFSET TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1110
    template: ClassVar[list[tuple[str, str]]] = tc.ob_sci_offset

class ObTcSciRequest(ObTcPacket):
    """An OB SCI_REQUEST TC."""

    decoder: ClassVar[bool] = True
    match_cmd_id: ClassVar[int] = 0b1111
    template: ClassVar[list[tuple[str, str]]] = tc.ob_sci_request

if __name__ == "__main__":
    import sys

    print()
    print("Test harness - running all examples from the OB-EB ICD")
    print()

    for packet, expected_decode in (
        ( "0000 0000 0000 0000",
            ObTcHkRequest(
                UNUSED=0, CMD_ID=0, DONTC=0,
                CRC=0, crc_valid=True, calculated_crc=0x00
            )
        ),
        ( "0200 0000 0000 00B9", ObTcClearErrors(
                UNUSED=0, CMD_ID=2, DONTC=0,
                CRC=0xB9, crc_valid=True, calculated_crc=0xB9
            )
        ),
        ( "0302 0000 0000 0034", ObTcSetErrors(
                UNUSED=0, CMD_ID=3, DONTC1=0,
                TMO=1, IPA=0, DONTC2=0, CD=0, AB=0, ABS=0,
                DSE=0, IG_B=0, IG_O=0, DONTC3=0, M_CD=0,
                M_AB=0, M_ABS=0, M_DSE=0, DONTC4=0,
                CRC=0x34, crc_valid=True, calculated_crc=0x34
            )
        ),
        ( "0300 0200 0000 00A2", ObTcSetErrors(
                UNUSED=0, CMD_ID=3, DONTC1=0,
                TMO=0, IPA=0, DONTC2=0, CD=0, AB=0, ABS=1,
                DSE=0, IG_B=0, IG_O=0, DONTC3=0, M_CD=0,
                M_AB=0, M_ABS=0, M_DSE=0, DONTC4=0,
                CRC=0xA2, crc_valid=True, calculated_crc=0xA2
            )
        ),
        ( "0300 0001 0000 0070", ObTcSetErrors(
                UNUSED=0, CMD_ID=3, DONTC1=0,
                TMO=0, IPA=0, DONTC2=0, CD=0, AB=0, ABS=0,
                DSE=0, IG_B=0, IG_O=0, DONTC3=0, M_CD=0,
                M_AB=0, M_ABS=0, M_DSE=1, DONTC4=0,
                CRC=0x70, crc_valid=True, calculated_crc=0x70
            )
        ),
        ( "0401 0000 0000 005C", ObTcPowerControl(
                UNUSED=0, CMD_ID=4, DONTC1=0,
                PD=0, PM=1, DONTC2=0,
                CRC=0x5C, crc_valid=True, calculated_crc=0x5C
            )
        ),
        ( "0403 0000 0000 000E", ObTcPowerControl(
                UNUSED=0, CMD_ID=4, DONTC1=0,
                PD=1, PM=1, DONTC2=0,
                CRC=0x0E, crc_valid=True, calculated_crc=0x0E
            )
        ),
        ( "0509 0000 0000 00CC", ObTcHeaterControl(
                UNUSED=0, CMD_ID=5, DONTC1=0,
                S=0, DM=1, DA=0, MM=0, MA=1, DONTC2=0,
                CRC=0xCC, crc_valid=True, calculated_crc=0xCC
            )
        ),
        ( "0515 0000 0000 00B9", ObTcHeaterControl(
                UNUSED=0, CMD_ID=5, DONTC1=0,
                S=1, DM=0, DA=1, MM=0, MA=1, DONTC2=0,
                CRC=0xB9, crc_valid=True, calculated_crc=0xB9
            )
        ),
        ( "0607 9A07 3800 00B9", ObTcSetMechSp(
                UNUSED=0, CMD_ID=6, DONTC1=0,
                THRM_MECH_OFF_SP=0x79A, DONTC2=0, THRM_MECH_ON_SP=0x738, DONTC3=0,
                CRC=0xB9, crc_valid=True, calculated_crc=0xB9
            )
        ),
        ( "0707 9A07 3800 0066", ObTcSetDetecSp(
                UNUSED=0, CMD_ID=7, DONTC1=0,
                THRM_DET_OFF_SP=0x79A, DONTC2=0, THRM_DET_ON_SP=0x738, DONTC3=0,
                CRC=0x66, crc_valid=True, calculated_crc=0x66
            )
        ),
        ( "0840 003C 0400 0076", ObTcSetMtrParam(
                UNUSED=0, CMD_ID=8, DONTC1=0,
                MTR_CURRENT=0x40, DONTC2=0, MGS=0, MTR_CHOP=0x3C, DONTC3=0,
                MTR_SPEED=0x04, DONTC4=0,
                CRC=0x76, crc_valid=True, calculated_crc=0x76
            )
        ),
        ( "0900 3200 0000 00A7", ObTcMtrMovPos(
                UNUSED=0, CMD_ID=9, DONTC1=0,
                MTR_POS=50, DONTC2=0,
                CRC=0xA7, crc_valid=True, calculated_crc=0xA7
            )
        ),
        ( "0A01 5400 0000 000F", ObTcMtrMovNeg(
                UNUSED=0, CMD_ID=10, DONTC1=0,
                MTR_NEG=340, DONTC2=0,
                CRC=0x0F, crc_valid=True, calculated_crc=0x0F
            )
        ),
        ( "0B00 0000 0000 008C", ObTcMtrHalt(
                UNUSED=0, CMD_ID=11, DONTC=0,
                CRC=0x8C, crc_valid=True, calculated_crc=0x8C
            )
        ),
        ( "0C02 0000 0000 00CD", ObTcMtrHoming(
                UNUSED=0, CMD_ID=12, DONTC1=0,
                CAL=1, DIR=0, DONTC2=0,
                CRC=0xCD, crc_valid=True, calculated_crc=0xCD
            )
        ),
        ( "0D04 0000 0000 00E4", ObTcSetHkSamples(
                UNUSED=0, CMD_ID=13,
                HK_ADC_SAMP=4, DONTC2=0,
                CRC=0xE4, crc_valid=True, calculated_crc=0xE4
            )
        ),
        ( "0D00 0000 0000 0040", ObTcSetHkSamples(
                UNUSED=0, CMD_ID=13,
                HK_ADC_SAMP=0, DONTC2=0,
                CRC=0x40, crc_valid=True, calculated_crc=0x40
            )
        ),
        ( "0E02 AB08 4800 005F", ObTcSciOffset(
                UNUSED=0, CMD_ID=14, DONTC1=0,
                SWIR_OFFSET=0x2AB, DONTC2=0, MWIR_OFFSET=0x848, DONTC3=0,
                CRC=0x5F, crc_valid=True, calculated_crc=0x5F
            )
        ),
        ( "0F08 6400 0000 0095", ObTcSciRequest(
                UNUSED=0, CMD_ID=15, DONTC1=0,
                SCI_ADC_SAMP=8, SCI_ADC_SKIP=100, DONTC2=0,
                CRC=0x95, crc_valid=True, calculated_crc=0x95
            )
        ),
        ( "0F00 2C00 0000 000B", ObTcSciRequest(
                UNUSED=0, CMD_ID=15, DONTC1=0,
                SCI_ADC_SAMP=0, SCI_ADC_SKIP=44, DONTC2=0,
                CRC=0x0B, crc_valid=True, calculated_crc=0x0B
            )
        ),
    ):
        decoded = ObTcPacket.fromhex(packet)

        if not isinstance(decoded, type(expected_decode)):
            print(f"{packet} decoded to a {type(decoded)}, should have been a {type(expected_decode)}")
            sys.exit(1)
        if dict(decoded) != dict(expected_decode):
            print(f"{packet} did not decode to expected value of {type(expected_decode)}:")
            for k, v in expected_decode.items():
                if decoded[k] != v:
                    print(f"   {k}: Expected {v} but got {decoded[k]}")
            sys.exit(1)
        print(packet, f"Decode success as {decoded.__class__.__name__}")

