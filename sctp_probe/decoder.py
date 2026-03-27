"""SBc-AP decoder. Never raises — all exceptions caught, fallback to raw hex.

Confirmed pycrate SBc-AP import path (verified against installed pycrate 0.7.11):
  specs/SbcAP_gen.py compiled from 3GPP TS 29.168 V15.1.0 ASN.1 source.
  Top-level PDU: SBC_AP_PDU_Descriptions.SBC_AP_PDU (CHOICE type, singleton).

procedureCode mapping (TS 29.168 Table 9.1):
  0 = Write-Replace-Warning   (initiating=WRR_REQ, successful=WRR_RESP)
  1 = Stop-Warning            (initiating=SWR_REQ, successful=SWR_RESP)
  2 = Error-Indication        (initiating=ERR_IND)
  3 = Write-Replace-Warning-Indication  (initiating=WRWI)
  4 = Stop-Warning-Indication           (initiating=SWI)
  5 = PWS-Restart-Indication            (initiating=PWS_RESTART)
  6 = PWS-Failure-Indication            (initiating=PWS_FAILURE)
"""
import base64
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# Add specs/ directory to path so SbcAP_gen is importable
_SPECS_DIR = os.path.join(os.path.dirname(__file__), "..", "specs")
if _SPECS_DIR not in sys.path:
    sys.path.insert(0, _SPECS_DIR)

_PDU = None
try:
    from SbcAP_gen import SBC_AP_PDU_Descriptions  # type: ignore
    _PDU = SBC_AP_PDU_Descriptions.SBC_AP_PDU
except Exception as _e:
    log.warning("SBc-AP pycrate module unavailable: %s — decode will fall back to raw", _e)

# procedureCode → (initiating_key, successful_key)
_PROC_MAP: dict[int, tuple[str, str]] = {
    0: ("WRR_REQ", "WRR_RESP"),
    1: ("SWR_REQ", "SWR_RESP"),
    2: ("ERR_IND", "ERR_IND"),
    3: ("WRWI",    "WRWI"),
    4: ("SWI",     "SWI"),
    5: ("PWS_RESTART", "PWS_RESTART"),
    6: ("PWS_FAILURE",  "PWS_FAILURE"),
}

# protocolIE id constants
_IE_CAUSE        = 1
_IE_MSG_ID       = 5
_IE_SERIAL       = 11


@dataclass
class DecodedMessage:
    protocol: str = "raw"
    pdu_type: str | None = None
    message_identifier: str | None = None
    serial_number: str | None = None
    decoded: dict[str, Any] | None = None
    raw_hex: str = ""
    raw_bytes_b64: str = ""


def _hex(raw: bytes) -> str:
    return raw.hex(" ")


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _ie_val(ies: list, ie_id: int) -> Any:
    """Return the value of the first IE with the given id, or None."""
    for ie in ies:
        if ie.get("id") == ie_id:
            return ie.get("value")
    return None


def _hex_str(val: Any) -> str | None:
    """Convert pycrate BIT_STR tuple (int_val, bit_len) or raw int to '0xNNNN'."""
    if val is None:
        return None
    if isinstance(val, tuple):
        int_val = val[0]
    elif isinstance(val, int):
        int_val = val
    else:
        return None
    return f"0x{int_val:04x}"


def _ies_to_dict(ies: list) -> dict[str, Any]:
    """Flatten protocolIEs list into a readable dict."""
    result: dict[str, Any] = {}
    for ie in ies:
        ie_id = ie.get("id")
        ie_val = ie.get("value")
        if isinstance(ie_val, tuple) and len(ie_val) == 2:
            name, val = ie_val
            result[name] = val
        else:
            result[str(ie_id)] = ie_val
    return result


def decode(raw_bytes: bytes) -> DecodedMessage:
    """Decode raw SCTP bytes into a DecodedMessage. Never raises."""
    raw_h = _hex(raw_bytes)
    raw_b = _b64(raw_bytes)

    if _PDU is None or not raw_bytes:
        return DecodedMessage(raw_hex=raw_h, raw_bytes_b64=raw_b)

    try:
        _PDU.from_aper(raw_bytes)
        val = _PDU.get_val()
        # val = (direction_str, {procedureCode, criticality, value: (msg_name, {protocolIEs: [...]})})
        direction_str, body = val
        proc_code: int = body.get("procedureCode", -1)
        msg_val = body.get("value", ("", {}))
        msg_name: str = msg_val[0] if isinstance(msg_val, tuple) else ""
        msg_body: dict = msg_val[1] if isinstance(msg_val, tuple) and len(msg_val) > 1 else {}

        ies: list = msg_body.get("protocolIEs", [])

        # Determine pdu_type key
        keys = _PROC_MAP.get(proc_code)
        if keys is None:
            pdu_type = None
        elif direction_str == "initiatingMessage":
            pdu_type = keys[0]
        else:
            pdu_type = keys[1]

        # Extract MI and SN
        mi_raw = _ie_val(ies, _IE_MSG_ID)
        sn_raw = _ie_val(ies, _IE_SERIAL)
        # Each is (ie_name, actual_value) tuple from pycrate
        if isinstance(mi_raw, tuple):
            mi_raw = mi_raw[1]
        if isinstance(sn_raw, tuple):
            sn_raw = sn_raw[1]

        mi = _hex_str(mi_raw)
        sn = _hex_str(sn_raw)

        decoded_dict = _ies_to_dict(ies)

        return DecodedMessage(
            protocol="SBc-AP",
            pdu_type=pdu_type,
            message_identifier=mi,
            serial_number=sn,
            decoded=decoded_dict,
            raw_hex=raw_h,
            raw_bytes_b64=raw_b,
        )
    except Exception as exc:
        log.debug("SBc-AP decode failed (%s), falling back to raw. hex=%s", exc, raw_h[:60])
        return DecodedMessage(raw_hex=raw_h, raw_bytes_b64=raw_b)


def peek_pdu_type(raw_bytes: bytes) -> str | None:
    """Return just the pdu_type string without constructing a full DecodedMessage."""
    try:
        return decode(raw_bytes).pdu_type
    except Exception:
        return None
