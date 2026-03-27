"""Tests for encoder.py — requires pycrate ASN.1 runtime (Linux/WSL2 with pycrate installed)."""
import pytest
from sctp_probe.decoder import DecodedMessage, decode
from sctp_probe import encoder as enc

pytestmark = pytest.mark.skipif(
    enc._PDU is None,
    reason="pycrate SBc-AP module unavailable — encoder tests require pycrate_asn1rt",
)

_INBOUND = DecodedMessage(
    protocol="SBc-AP",
    pdu_type="WRR_REQ",
    message_identifier="0x1144",
    serial_number="0x0001",
)

_RESPONSE_TEMPLATES = [
    "WRR_SUCCESS",
    "WRR_PARTIAL",
    "WRR_PERMANENT_FAILURE",
    "WRR_TRANSIENT_FAILURE",
    "SWR_SUCCESS",
    "SWR_NOT_FOUND",
]

_INDICATION_TEMPLATES = [
    "ERR_IND_SEMANTIC",
    "ERR_IND_TRANSFER_SYNTAX",
    "WRWI_SCHEDULED",
    "WRWI_CANCELLED",
    "SWI_CANCELLED",
]


@pytest.mark.parametrize("template", _RESPONSE_TEMPLATES)
def test_response_templates_return_bytes(template):
    result = enc.encode(template, _INBOUND)
    assert isinstance(result, bytes), f"{template} returned {result!r}"
    assert len(result) > 0


@pytest.mark.parametrize("template", _INDICATION_TEMPLATES)
def test_indication_templates_return_bytes(template):
    result = enc.encode(template, message_identifier="0x1144", serial_number="0x0001")
    assert isinstance(result, bytes), f"{template} returned {result!r}"
    assert len(result) > 0


def test_wrr_timeout_returns_none():
    result = enc.encode("WRR_TIMEOUT", _INBOUND)
    assert result is None


def test_unknown_template_returns_none():
    result = enc.encode("DOES_NOT_EXIST", _INBOUND)
    assert result is None


def test_unknown_template_does_not_raise():
    try:
        enc.encode("TOTALLY_MADE_UP", _INBOUND)
    except Exception as e:
        pytest.fail(f"encode raised: {e}")


def test_round_trip_wrr_success():
    raw = enc.encode("WRR_SUCCESS", _INBOUND)
    assert raw is not None
    dm = decode(raw)
    assert dm.pdu_type == "WRR_RESP"
    assert dm.message_identifier == "0x1144"
    assert dm.serial_number == "0x0001"


def test_round_trip_swr_success():
    inbound = DecodedMessage(
        protocol="SBc-AP",
        pdu_type="SWR_REQ",
        message_identifier="0x1234",
        serial_number="0x0002",
    )
    raw = enc.encode("SWR_SUCCESS", inbound)
    assert raw is not None
    dm = decode(raw)
    assert dm.pdu_type == "SWR_RESP"
    assert dm.message_identifier == "0x1234"
    assert dm.serial_number == "0x0002"


def test_encode_none_inbound_does_not_raise():
    result = enc.encode("WRR_SUCCESS", None)
    # MI/SN will be 0x0000 — that's fine, just must not raise
    assert result is None or isinstance(result, bytes)
