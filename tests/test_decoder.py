"""Tests for decoder.py — run on any OS."""
import os
import pytest
from sctp_probe.decoder import decode, peek_pdu_type, DecodedMessage

FIXTURES_DIR = "/mnt/c/Projects/sentinel-cbc/schemas/protocol/fixtures"

# Collect all .bin fixture files
_bin_files = []
if os.path.isdir(FIXTURES_DIR):
    _bin_files = [
        os.path.join(FIXTURES_DIR, f)
        for f in os.listdir(FIXTURES_DIR)
        if f.endswith(".bin")
    ]


def test_decode_empty_bytes_never_raises():
    result = decode(b"")
    assert isinstance(result, DecodedMessage)
    assert result.protocol == "raw"
    assert result.pdu_type is None


def test_decode_garbage_never_raises():
    result = decode(b"\xff\xfe\x00\x01\x02\x03garbage")
    assert isinstance(result, DecodedMessage)
    # May decode or fall back — must not raise


def test_decode_returns_decoded_message():
    result = decode(b"\x00\x01\x00\x0f\x00\x00\x02")
    assert isinstance(result, DecodedMessage)
    assert isinstance(result.raw_hex, str)
    assert isinstance(result.raw_bytes_b64, str)


def test_peek_pdu_type_garbage():
    result = peek_pdu_type(b"\xff\xfe\xfd")
    # Must not raise; returns None or a string
    assert result is None or isinstance(result, str)


@pytest.mark.parametrize("bin_path", _bin_files, ids=[os.path.basename(p) for p in _bin_files])
def test_decode_fixture_never_raises(bin_path):
    with open(bin_path, "rb") as f:
        raw = f.read()
    result = decode(raw)
    assert isinstance(result, DecodedMessage)
    assert isinstance(result.raw_hex, str)
    assert len(result.raw_hex) > 0


@pytest.mark.parametrize("bin_path", _bin_files, ids=[os.path.basename(p) for p in _bin_files])
def test_decode_fixture_pdu_type(bin_path):
    """PDU type should be a known SBc-AP type or None — never crash."""
    known_types = {
        "WRR_REQ", "WRR_RESP", "SWR_REQ", "SWR_RESP",
        "ERR_IND", "WRWI", "SWI", "PWS_RESTART", "PWS_FAILURE",
        None,
    }
    with open(bin_path, "rb") as f:
        raw = f.read()
    result = decode(raw)
    assert result.pdu_type in known_types, f"Unexpected pdu_type: {result.pdu_type}"


def test_wrr_req_fixture_fields():
    """Decode a WRR_REQ fixture and check MI/SN are present."""
    wrr_path = os.path.join(FIXTURES_DIR, "wrr_req_tai_list_minimal.bin")
    if not os.path.exists(wrr_path):
        pytest.skip("WRR fixture not found")
    with open(wrr_path, "rb") as f:
        raw = f.read()
    result = decode(raw)
    assert result.pdu_type == "WRR_REQ"
    assert result.message_identifier is not None
    assert result.serial_number is not None
    assert result.protocol == "SBc-AP"
