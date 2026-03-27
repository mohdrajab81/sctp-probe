"""Export message log to JSON or PCAP.

PCAP format:
  Global header : magic=0xa1b2c3d4 LE, version 2.4, snaplen=65535,
                  network=1 (LINKTYPE_ETHERNET)
  Per record    : fake Ethernet + IPv4 + SCTP (DATA chunk) headers wrapping
                  the raw SBc-AP payload so Wireshark dissects the full stack.

Fake addresses used for all packets:
  Inbound  (peer → probe) : src=10.0.0.2:29168  dst=127.0.0.1:29168
  Outbound (probe → peer) : src=127.0.0.1:29168  dst=10.0.0.2:29168
"""
from __future__ import annotations

import base64
import json
import struct
from datetime import datetime, timezone

from sctp_probe.store import Store

# ---------------------------------------------------------------------------
# PCAP global header — LINKTYPE_ETHERNET (1)
# ---------------------------------------------------------------------------
_PCAP_GLOBAL_HEADER = struct.pack(
    "<IHHiIII",
    0xA1B2C3D4,  # magic (little-endian)
    2, 4,        # version 2.4
    0,           # thiszone
    0,           # sigfigs
    65535,       # snaplen
    1,           # network: LINKTYPE_ETHERNET
)

# Fake MAC addresses (locally-administered, no actual hardware)
_MAC_PROBE = b"\x02\x00\x00\x00\x00\x01"
_MAC_PEER  = b"\x02\x00\x00\x00\x00\x02"

# Fake IP addresses
_IP_PROBE  = b"\x7f\x00\x00\x01"   # 127.0.0.1
_IP_PEER   = b"\x0a\x00\x00\x02"   # 10.0.0.2

_SCTP_PORT = 29168
_PPID      = 24   # SBc-AP PPID


def _checksum(data: bytes) -> int:
    """Internet checksum (RFC 1071)."""
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f"!{len(data)//2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def _build_packet(payload: bytes, inbound: bool) -> bytes:
    """Wrap SBc-AP payload in Ethernet + IPv4 + SCTP DATA chunk."""
    src_mac = _MAC_PEER  if inbound else _MAC_PROBE
    dst_mac = _MAC_PROBE if inbound else _MAC_PEER
    src_ip  = _IP_PEER   if inbound else _IP_PROBE
    dst_ip  = _IP_PROBE  if inbound else _IP_PEER
    src_port = _SCTP_PORT
    dst_port = _SCTP_PORT

    # --- SCTP DATA chunk ---
    # Chunk type=0 (DATA), flags=0x03 (beginning+ending fragment), length=16+payload
    chunk_len = 16 + len(payload)
    padding = (4 - chunk_len % 4) % 4
    # SCTP DATA chunk wire layout (RFC 4960 §3.3.1):
    #   type(1B) flags(1B) length(2B) TSN(4B) stream_id(2B) stream_seq(2B) ppid(4B)
    #   = 16 bytes total header, format "!BBHIHHI" + 4B ppid manually appended
    # SCTP DATA chunk header (RFC 4960 §3.3.1) — exactly 16 bytes:
    #   type(1) flags(1) length(2) TSN(4) stream_id(2) stream_seq(2) ppid(4)
    sctp_data_chunk = struct.pack(
        "!BBHIHHI",
        0x00,          # chunk type: DATA
        0x03,          # flags: B+E (single-fragment message)
        chunk_len,     # chunk value length = 16 + len(payload)
        1,             # TSN
        0,             # stream identifier
        0,             # stream sequence number
        _PPID,         # payload protocol identifier (SBc-AP = 24)
    ) + payload + b"\x00" * padding

    # --- SCTP common header (12 bytes) + DATA chunk ---
    # Checksum is CRC-32c; we use 0 (Wireshark accepts it with checksum validation off)
    sctp_header = struct.pack(
        "!HHII",
        src_port,  # source port
        dst_port,  # destination port
        0,         # verification tag (0 for simplicity)
        0,         # checksum (placeholder — set to 0)
    )
    sctp_payload = sctp_header + sctp_data_chunk

    # --- IPv4 header (20 bytes, no options) ---
    ip_total_len = 20 + len(sctp_payload)
    ip_header_no_csum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,          # version=4, IHL=5
        0x00,          # DSCP/ECN
        ip_total_len,
        0,             # identification
        0x40 << 8,     # flags=DF, fragment offset=0
        64,            # TTL
        132,           # protocol: SCTP
        0,             # checksum placeholder
        src_ip,
        dst_ip,
    )
    ip_csum = _checksum(ip_header_no_csum)
    ip_header = ip_header_no_csum[:10] + struct.pack("!H", ip_csum) + ip_header_no_csum[12:]

    # --- Ethernet frame ---
    eth_header = dst_mac + src_mac + b"\x08\x00"  # EtherType IPv4

    return eth_header + ip_header + sctp_payload


async def export_json(store: Store, session_id: str | None = None) -> str:
    messages = await store.get_messages(limit=1000)
    if session_id:
        messages = [m for m in messages if m.get("session_id") == session_id]
    return json.dumps({"messages": messages}, indent=2, default=str)


async def export_pcap(store: Store, session_id: str | None = None) -> bytes:
    messages = await store.get_messages(limit=1000)
    if session_id:
        messages = [m for m in messages if m.get("session_id") == session_id]

    buf = bytearray(_PCAP_GLOBAL_HEADER)
    for msg in messages:
        raw_b64 = msg.get("raw_bytes_b64", "")
        if not raw_b64:
            continue
        try:
            raw = base64.b64decode(raw_b64)
        except Exception:
            continue

        try:
            ts = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
        except Exception:
            ts = datetime.now(timezone.utc)

        inbound = msg.get("direction") == "inbound"
        packet = _build_packet(raw, inbound)

        ts_sec = int(ts.timestamp())
        ts_usec = ts.microsecond
        buf += struct.pack("<IIII", ts_sec, ts_usec, len(packet), len(packet))
        buf += packet

    return bytes(buf)
