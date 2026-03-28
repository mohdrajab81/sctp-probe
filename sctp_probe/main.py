"""FastAPI application — wires all modules together."""
from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sctp_probe import decoder, encoder as enc_mod
from sctp_probe.export import export_json, export_pcap
from sctp_probe.rules import RuleEngine
from sctp_probe.sctp_client import SctpClient
from sctp_probe.sctp_server import SCTPUnavailableError, SctpServer
from sctp_probe.session import reset as session_reset
from sctp_probe.store import Store
from sctp_probe.ws import WsHub

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
DB_PATH = os.environ.get("DB_PATH", "sctp_probe.db")
AUTO_MODPROBE = os.environ.get("AUTO_MODPROBE", "false").lower() == "true"

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Singletons
# ------------------------------------------------------------------
_store = Store(DB_PATH)
_ws_hub = WsHub()
_sctp_server = SctpServer()
_sctp_client = SctpClient()
_rule_engine = RuleEngine(_store, enc_mod, _sctp_server, _sctp_client,
                          decoder=decoder, ws_hub=_ws_hub)


# ------------------------------------------------------------------
# Message pipeline callback
# ------------------------------------------------------------------
async def _on_message(raw_bytes: bytes, peer_addr: str, local_port: int) -> None:
    session_id = await _store.get_current_session_id()
    dm = decoder.decode(raw_bytes)
    msg_dict: dict[str, Any] = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": "inbound",
        "transport": "sctp",
        "local_port": local_port,
        "peer_addr": peer_addr,
        "protocol": dm.protocol,
        "pdu_type": dm.pdu_type,
        "message_identifier": dm.message_identifier,
        "serial_number": dm.serial_number,
        "decoded": dm.decoded,
        "raw_hex": dm.raw_hex,
        "raw_bytes_b64": dm.raw_bytes_b64,
    }
    saved = await _store.save_message(msg_dict)
    await _ws_hub.broadcast({"type": "message", "data": saved})
    await _rule_engine.evaluate(saved, None)


async def _on_event(event_type: str, peer_addr: str, port: int) -> None:
    await _ws_hub.broadcast({
        "type": "connection",
        "data": {"event": event_type, "peer": peer_addr, "port": port},
    })


_sctp_server.on_message = _on_message
_sctp_server.on_event = _on_event
_sctp_client.on_message = _on_message


# ------------------------------------------------------------------
# App lifecycle
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if AUTO_MODPROBE:
        import subprocess
        try:
            subprocess.run(["sudo", "modprobe", "sctp"], check=True, timeout=5)
        except Exception as e:
            log.warning("AUTO_MODPROBE failed: %s", e)
    await _store.init_db()
    log.info("sctp-probe started. DB=%s", DB_PATH)
    yield
    await _sctp_server.stop_all()
    await _sctp_client.disconnect_all()
    log.info("sctp-probe shutdown complete")


app = FastAPI(title="sctp-probe", lifespan=lifespan)

# Serve static files
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ------------------------------------------------------------------
# Pydantic models
# ------------------------------------------------------------------
class ServerStartBody(BaseModel):
    port: int
    ppid: int = 24
    bind_host: str = Field(default="127.0.0.1", alias="host")

    model_config = {
        "populate_by_name": True,
    }


class ServerStopBody(BaseModel):
    port: int | None = None


class ClientConnectBody(BaseModel):
    host: str
    port: int
    ppid: int = 24


class ClientDisconnectBody(BaseModel):
    id: str | None = None


class RuleBody(BaseModel):
    match_pdu_type: str = "*"
    match_message_identifier: str | None = None
    match_serial_number: str | None = None
    match_peer_addr: str | None = None
    action: str = "auto_reply"
    reply_template: str | None = None
    delay_ms: int = 0
    count: int = 0


class SendBody(BaseModel):
    hex: str | None = None
    connection_id: str | None = None
    template: str | None = None
    message_identifier: str | None = None
    serial_number: str | None = None


# ------------------------------------------------------------------
# Server endpoints
# ------------------------------------------------------------------
@app.post("/api/server/start")
async def server_start(body: ServerStartBody):
    try:
        await _sctp_server.start(body.port, body.ppid, bind_host=body.bind_host)
    except ValueError as e:
        raise HTTPException(409, detail=str(e))
    except SCTPUnavailableError as e:
        raise HTTPException(503, detail=str(e))
    return {"port": body.port, "bind_host": body.bind_host, "status": "listening"}


@app.post("/api/server/stop")
async def server_stop(body: ServerStopBody):
    if body.port is not None:
        await _sctp_server.stop(body.port)
        stopped = [body.port]
    else:
        ports = list(_sctp_server._listeners.keys())
        await _sctp_server.stop_all()
        stopped = ports
    return {"stopped": stopped}


@app.get("/api/server/status")
async def server_status():
    return {"listeners": _sctp_server.status()}


# ------------------------------------------------------------------
# Client endpoints
# ------------------------------------------------------------------
@app.post("/api/client/connect")
async def client_connect(body: ClientConnectBody):
    try:
        conn_id = await _sctp_client.connect(body.host, body.port, body.ppid)
    except SCTPUnavailableError as e:
        raise HTTPException(503, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=str(e))
    return {"id": conn_id, "status": "connected"}


@app.post("/api/client/disconnect")
async def client_disconnect(body: ClientDisconnectBody):
    if body.id:
        await _sctp_client.disconnect(body.id)
        disconnected = [body.id]
    else:
        ids = list(_sctp_client._conns.keys())
        await _sctp_client.disconnect_all()
        disconnected = ids
    return {"disconnected": disconnected}


@app.get("/api/client/status")
async def client_status():
    return {"connections": _sctp_client.status()}


# ------------------------------------------------------------------
# Rules endpoints
# ------------------------------------------------------------------
@app.post("/api/rules", status_code=201)
async def create_rule(body: RuleBody):
    rule = await _store.save_rule(body.model_dump())
    return rule


@app.get("/api/rules")
async def list_rules():
    return {"rules": await _store.get_rules()}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int):
    deleted = await _store.delete_rule(rule_id)
    return {"deleted": deleted}


@app.delete("/api/rules")
async def delete_all_rules():
    deleted = await _store.delete_all_rules()
    return {"deleted": deleted}


# ------------------------------------------------------------------
# Messages endpoints
# ------------------------------------------------------------------
@app.get("/api/messages")
async def get_messages(
    since_id: int = Query(0),
    direction: str | None = Query(None),
    pdu_type: str | None = Query(None),
    limit: int = Query(100),
):
    msgs = await _store.get_messages(since_id=since_id, direction=direction, pdu_type=pdu_type, limit=limit)
    return {"messages": msgs, "total": len(msgs)}


@app.delete("/api/messages")
async def delete_messages():
    deleted = await _store.delete_all_messages()
    return {"deleted": deleted}


# ------------------------------------------------------------------
# Send endpoint
# ------------------------------------------------------------------
@app.post("/api/send")
async def send_bytes(body: SendBody):
    raw: bytes | None = None

    if body.template:
        dm = decoder.DecodedMessage(
            message_identifier=body.message_identifier,
            serial_number=body.serial_number,
        )
        raw = enc_mod.encode(body.template, dm)
        if raw is None:
            raise HTTPException(400, detail=f"Template '{body.template}' produced no bytes")
    elif body.hex:
        hex_str = body.hex.replace(" ", "")
        try:
            raw = bytes.fromhex(hex_str)
        except ValueError:
            raise HTTPException(400, detail="Invalid hex string")
    else:
        raise HTTPException(400, detail="Provide either 'hex' or 'template'")

    if body.connection_id:
        try:
            await _sctp_client.send(body.connection_id, raw)
        except KeyError:
            raise HTTPException(409, detail=f"Connection '{body.connection_id}' not found")
        except RuntimeError as e:
            raise HTTPException(409, detail=str(e))
    else:
        # Broadcast to all server peers
        for entry in _sctp_server._listeners.values():
            for peer_addr in list(entry["peers"].keys()):
                await _sctp_server.send_to_peer(peer_addr, raw)

    # Log outbound message
    session_id = await _store.get_current_session_id()
    dm = decoder.decode(raw)
    await _store.save_message({
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": "outbound",
        "transport": "sctp",
        "protocol": dm.protocol,
        "pdu_type": dm.pdu_type,
        "message_identifier": dm.message_identifier,
        "serial_number": dm.serial_number,
        "decoded": dm.decoded,
        "raw_hex": dm.raw_hex,
        "raw_bytes_b64": dm.raw_bytes_b64,
    })

    return {"sent_bytes": len(raw)}


# ------------------------------------------------------------------
# Session endpoint
# ------------------------------------------------------------------
@app.post("/api/session/reset")
async def reset_session():
    return await session_reset(_store)


# ------------------------------------------------------------------
# Export endpoints
# ------------------------------------------------------------------
@app.get("/api/export/json")
async def export_json_ep(session_id: str | None = Query(None)):
    data = await export_json(_store, session_id)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=sctp_probe_export.json"},
    )


@app.get("/api/export/pcap")
async def export_pcap_ep(session_id: str | None = Query(None)):
    data = await export_pcap(_store, session_id)
    return Response(
        content=data,
        media_type="application/vnd.tcpdump.pcap",
        headers={"Content-Disposition": "attachment; filename=sctp_probe_export.pcap"},
    )


# ------------------------------------------------------------------
# WebSocket
# ------------------------------------------------------------------
@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await _ws_hub.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        pass
    finally:
        _ws_hub.disconnect(ws)


# ------------------------------------------------------------------
# Root — serve index.html
# ------------------------------------------------------------------
@app.get("/")
async def root():
    import pathlib
    idx = pathlib.Path(_STATIC_DIR) / "index.html"
    if idx.exists():
        return Response(content=idx.read_text(), media_type="text/html")
    return Response(content="<h1>sctp-probe</h1><p>static/index.html not found</p>", media_type="text/html")
