set -euo pipefail
cd /mnt/c/Projects/sentinel-cbc
GO=/usr/local/go/bin/go
BIN=/tmp/sentinel-cbc-peer-drill
LOG=/tmp/sentinel-cbc-peer-drill.log
PROBE_DB=/tmp/sctp-probe-peer-drill.db
OUT=/tmp/peer-drill
SCTP_PORT=29170
HTTP_PORT=18081
BASE_URL=http://127.0.0.1:$HTTP_PORT
export BASE_URL
cleanup() {
  if [ -n "${APP_PID:-}" ]; then kill "$APP_PID" >/dev/null 2>&1 || true; fi
  if [ -n "${PROBE_API_PID:-}" ]; then kill "$PROBE_API_PID" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
mkdir -p "$OUT"
pkill -f 'sctp-probe-peer-drill-api.log' >/dev/null 2>&1 || true
pkill -f 'sentinel-cbc-peer-drill.log' >/dev/null 2>&1 || true

$GO build -o "$BIN" ./cmd/sentinel-cbc
psql 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' <<'SQL'
TRUNCATE protocol_messages, warning_peer_dispatches, warnings, warning_idempotency_keys RESTART IDENTITY CASCADE;
TRUNCATE peers CASCADE;
INSERT INTO peers (
  id, name, primary_address, secondary_address, enabled,
  connection_state, association_id, inbound_streams, outbound_streams,
  last_connected_at, last_disconnected_at, updated_at, transport_kind
) VALUES (
  'peer-drill-mme', 'peer disconnect drill peer', '127.0.0.1', '', true,
  'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now(), 'SBCAP_SCTP'
);
SQL
rm -f "$PROBE_DB"

nohup bash -lc "cd /mnt/c/Projects/sctp-probe && source .venv-wsl/bin/activate && DB_PATH='$PROBE_DB' uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8890" >/tmp/sctp-probe-peer-drill-api.log 2>&1 &
PROBE_API_PID=$!
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:8890/api/messages >/dev/null 2>&1 && break; sleep 1; done
curl -fsS -X DELETE http://127.0.0.1:8890/api/messages >/dev/null
curl -fsS -X DELETE http://127.0.0.1:8890/api/rules >/dev/null
curl -fsS -X POST http://127.0.0.1:8890/api/session/reset >/dev/null
curl -fsS -H 'Content-Type: application/json' -d '{"match_pdu_type":"WRR_REQ","action":"auto_reply","reply_template":"WRR_SUCCESS","count":0}' http://127.0.0.1:8890/api/rules >/dev/null
curl -fsS -H 'Content-Type: application/json' -d '{"match_pdu_type":"SWR_REQ","action":"auto_reply","reply_template":"SWR_SUCCESS","count":0}' http://127.0.0.1:8890/api/rules >/dev/null
curl -fsS -H 'Content-Type: application/json' -d "{\"host\":\"127.0.0.1\",\"port\":$SCTP_PORT,\"ppid\":24}" http://127.0.0.1:8890/api/server/start >/dev/null
sleep 2

nohup env \
  SENTINELCBC_DATABASE_DSN='postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' \
  SENTINELCBC_AUTH_ENABLED=false \
  SENTINELCBC_SCTP_ENABLED=true \
  SENTINELCBC_SCTP_PORT=$SCTP_PORT \
  SENTINELCBC_HTTP_ADDR=:$HTTP_PORT \
  "$BIN" >"$LOG" 2>&1 &
APP_PID=$!
for _ in $(seq 1 30); do curl -fsS $BASE_URL/health >/dev/null 2>&1 && break; sleep 1; done
sleep 3

curl -fsS $BASE_URL/health > "$OUT/01_health.json"
curl -fsS $BASE_URL/ready > "$OUT/02_ready_baseline.json"
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT id || '|' || connection_state FROM peers WHERE id='peer-drill-mme';" > "$OUT/02b_peer_state_baseline.txt"

cat > "$OUT/create.json" <<'JSON'
{
  "family": "CMAS",
  "cmasCategory": "PRESIDENTIAL",
  "language": "en",
  "messageText": "Peer disconnect drill baseline",
  "targetScope": "SPECIFIC_AREA",
  "deliveryArea": {
    "type": "EUTRAN_TAI_LIST",
    "taiList": [{"plmn": "41601", "tacHex": "0001"}]
  },
  "broadcastBehavior": "REPEAT_FIXED_COUNT",
  "repetitionPeriodSeconds": 30,
  "numberOfBroadcasts": 3,
  "maxAttempts": 3,
  "retryIntervalSeconds": 5,
  "targetPeerIds": ["peer-drill-mme"]
}
JSON
curl -fsS -H 'Content-Type: application/json' --data @"$OUT/create.json" $BASE_URL/api/v1/warnings > "$OUT/03_create_connected.json"
sleep 5
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT state || '|' || operation_kind || '|' || COALESCE(last_attempt_status,'') || '|' || attempt_count FROM warning_peer_dispatches ORDER BY created_at;" > "$OUT/04_queue_connected.txt"

curl -fsS -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:8890/api/server/stop >/dev/null || true
sleep 6
curl -sS $BASE_URL/ready > "$OUT/05_ready_disconnected.json"
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT id || '|' || connection_state || '|' || COALESCE(to_char(last_connected_at, 'YYYY-MM-DD HH24:MI:SS'), '') || '|' || COALESCE(to_char(last_disconnected_at, 'YYYY-MM-DD HH24:MI:SS'), '') FROM peers WHERE id='peer-drill-mme';" > "$OUT/06_peer_state_disconnected.txt"

python3 - <<'PY' > "$OUT/07_create_disconnected.json"
import json, os, urllib.request
body = {
  "family": "CMAS",
  "cmasCategory": "PRESIDENTIAL",
  "language": "en",
  "messageText": "Peer disconnect drill while down",
  "targetScope": "SPECIFIC_AREA",
  "deliveryArea": {"type": "EUTRAN_TAI_LIST", "taiList": [{"plmn": "41601", "tacHex": "0001"}]},
  "broadcastBehavior": "REPEAT_FIXED_COUNT",
  "repetitionPeriodSeconds": 30,
  "numberOfBroadcasts": 3,
  "maxAttempts": 3,
  "retryIntervalSeconds": 5,
  "targetPeerIds": ["peer-drill-mme"]
}
base = os.environ['BASE_URL']
req = urllib.request.Request(base + '/api/v1/warnings', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(resp.read().decode())
PY
sleep 2
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT state || '|' || operation_kind || '|' || COALESCE(last_attempt_status,'') || '|' || attempt_count FROM warning_peer_dispatches ORDER BY created_at;" > "$OUT/08_queue_during_disconnect.txt"

curl -fsS -H 'Content-Type: application/json' -d "{\"host\":\"127.0.0.1\",\"port\":$SCTP_PORT,\"ppid\":24}" http://127.0.0.1:8890/api/server/start >/dev/null
sleep 10
curl -sS $BASE_URL/ready > "$OUT/09_ready_reconnected.json"
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT id || '|' || connection_state || '|' || COALESCE(to_char(last_connected_at, 'YYYY-MM-DD HH24:MI:SS'), '') || '|' || COALESCE(to_char(last_disconnected_at, 'YYYY-MM-DD HH24:MI:SS'), '') FROM peers WHERE id='peer-drill-mme';" > "$OUT/09b_peer_state_reconnected.txt"
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT state || '|' || operation_kind || '|' || COALESCE(last_attempt_status,'') || '|' || attempt_count FROM warning_peer_dispatches ORDER BY created_at;" > "$OUT/10_queue_after_reconnect.txt"
psql -At 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' -c "SELECT message_type || '|' || count(*) FROM protocol_messages GROUP BY message_type ORDER BY message_type;" > "$OUT/11_protocol_counts.txt"
python3 /mnt/c/Projects/sentinel-cbc/scripts/report_ambiguous_dispatches.py --dsn 'postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable' > "$OUT/12_ambiguous.txt"

echo OK:$OUT
