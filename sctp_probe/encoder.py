"""SBc-AP encoder. Returns None on failure — never raises.

Uses the same SbcAP_gen pycrate module as decoder.py.

Template registry — all templates from DESIGN.md section 6.
Adding a new template: add an entry to _BUILDERS dict only.
"""
import logging
import os
import sys
from typing import Any

from sctp_probe.decoder import DecodedMessage

log = logging.getLogger(__name__)

_SPECS_DIR = os.path.join(os.path.dirname(__file__), "..", "specs")
if _SPECS_DIR not in sys.path:
    sys.path.insert(0, _SPECS_DIR)

_PDU = None
try:
    from SbcAP_gen import SBC_AP_PDU_Descriptions  # type: ignore
    _PDU = SBC_AP_PDU_Descriptions.SBC_AP_PDU
except Exception as _e:
    log.warning("SBc-AP pycrate module unavailable for encoder: %s", _e)


def _parse_hex(val: str | None, default: int = 0) -> int:
    """Parse '0x1234' or '1234' to int."""
    if val is None:
        return default
    try:
        return int(val, 16)
    except (ValueError, TypeError):
        return default


def _mi_sn(inbound: DecodedMessage | None, kwargs: dict[str, Any]) -> tuple[int, int]:
    mi = _parse_hex(kwargs.get("message_identifier") or (inbound.message_identifier if inbound else None))
    sn = _parse_hex(kwargs.get("serial_number") or (inbound.serial_number if inbound else None))
    return mi, sn


def _encode_pdu(val: Any) -> bytes | None:
    if _PDU is None:
        return None
    _PDU.set_val(val)
    return _PDU.to_aper()


# ------------------------------------------------------------------ builders

def _wrr_response(mi: int, sn: int, cause: int, unknown_tais: list | None = None) -> bytes | None:
    ies: list[dict] = [
        {"id": 5,  "criticality": "reject", "value": ("Message-Identifier", (mi, 16))},
        {"id": 11, "criticality": "reject", "value": ("Serial-Number",      (sn, 16))},
        {"id": 1,  "criticality": "ignore", "value": ("Cause", cause)},
    ]
    if unknown_tais:
        ies.append({"id": 22, "criticality": "ignore",
                    "value": ("List-of-TAIs", [{"tai": t} for t in unknown_tais])})
    return _encode_pdu((
        "successfulOutcome",
        {"procedureCode": 0, "criticality": "reject",
         "value": ("Write-Replace-Warning-Response", {"protocolIEs": ies})},
    ))


def _swr_response(mi: int, sn: int, cause: int) -> bytes | None:
    ies = [
        {"id": 5,  "criticality": "reject", "value": ("Message-Identifier", (mi, 16))},
        {"id": 11, "criticality": "reject", "value": ("Serial-Number",      (sn, 16))},
        {"id": 1,  "criticality": "ignore", "value": ("Cause", cause)},
    ]
    return _encode_pdu((
        "successfulOutcome",
        {"procedureCode": 1, "criticality": "reject",
         "value": ("Stop-Warning-Response", {"protocolIEs": ies})},
    ))


def _err_ind(mi: int, sn: int, cause: int) -> bytes | None:
    ies = [
        {"id": 1,  "criticality": "ignore", "value": ("Cause", cause)},
    ]
    return _encode_pdu((
        "initiatingMessage",
        {"procedureCode": 2, "criticality": "ignore",
         "value": ("Error-Indication", {"protocolIEs": ies})},
    ))


_SYNTHETIC_ECGI = {"eCGI": {"pLMNidentity": b"\x14\xf6\x10", "cell-ID": (0x0123456, 28)}}
_SYNTHETIC_ECGI_CANCELLED = {"eCGI": {"pLMNidentity": b"\x14\xf6\x10", "cell-ID": (0x0123456, 28)},
                              "numberOfBroadcasts": 1}


def _wrwi(mi: int, sn: int) -> bytes | None:
    # WRWI only carries Broadcast-Scheduled-Area-List (id 23).
    ies = [
        {"id": 5,  "criticality": "reject", "value": ("Message-Identifier", (mi, 16))},
        {"id": 11, "criticality": "reject", "value": ("Serial-Number",      (sn, 16))},
        {"id": 23, "criticality": "reject",
         "value": ("Broadcast-Scheduled-Area-List", {"cellId-Broadcast-List": [_SYNTHETIC_ECGI]})},
    ]
    return _encode_pdu((
        "initiatingMessage",
        {"procedureCode": 3, "criticality": "ignore",
         "value": ("Write-Replace-Warning-Indication", {"protocolIEs": ies})},
    ))


def _swi(mi: int, sn: int) -> bytes | None:
    ies = [
        {"id": 5,  "criticality": "reject", "value": ("Message-Identifier", (mi, 16))},
        {"id": 11, "criticality": "reject", "value": ("Serial-Number",      (sn, 16))},
        {"id": 25, "criticality": "reject", "value": ("Broadcast-Cancelled-Area-List",
                                                       {"cellID-Cancelled-List": [_SYNTHETIC_ECGI_CANCELLED]})},
    ]
    return _encode_pdu((
        "initiatingMessage",
        {"procedureCode": 4, "criticality": "ignore",
         "value": ("Stop-Warning-Indication", {"protocolIEs": ies})},
    ))


# ------------------------------------------------------------------ registry

def encode(
    template_name: str,
    inbound: DecodedMessage | None = None,
    **kwargs: Any,
) -> bytes | None:
    """Encode a reply PDU from a named template. Returns None on failure or for WRR_TIMEOUT."""
    try:
        mi, sn = _mi_sn(inbound, kwargs)

        if template_name == "WRR_TIMEOUT":
            return None
        if template_name == "WRR_SUCCESS":
            return _wrr_response(mi, sn, cause=0)
        if template_name == "WRR_PARTIAL":
            tai = {"pLMNidentity": b"\x14\xf6\x10", "tAC": b"\x00\x99"}
            return _wrr_response(mi, sn, cause=0, unknown_tais=[tai])
        if template_name == "WRR_PERMANENT_FAILURE":
            return _wrr_response(mi, sn, cause=1)
        if template_name == "WRR_TRANSIENT_FAILURE":
            return _wrr_response(mi, sn, cause=7)
        if template_name == "SWR_SUCCESS":
            return _swr_response(mi, sn, cause=0)
        if template_name == "SWR_NOT_FOUND":
            return _swr_response(mi, sn, cause=3)
        if template_name == "ERR_IND_SEMANTIC":
            return _err_ind(mi, sn, cause=14)
        if template_name == "ERR_IND_TRANSFER_SYNTAX":
            return _err_ind(mi, sn, cause=11)
        if template_name == "WRWI_SCHEDULED":
            return _wrwi(mi, sn)
        if template_name == "WRWI_CANCELLED":
            # WRWI only carries Broadcast-Scheduled-Area-List (id 23).
            # Cancelled-area reporting belongs to SWI (Stop-Warning-Indication).
            # Return a SWI PDU so the template produces valid bytes.
            return _swi(mi, sn)
        if template_name == "SWI_CANCELLED":
            return _swi(mi, sn)

        log.error("encode: unknown template '%s'", template_name)
        return None
    except Exception as exc:
        log.error("encode(%s) failed: %s", template_name, exc)
        return None
