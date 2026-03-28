## Phase 9E Capture Summary

Folder: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653`

### 37_multi_instance_single_peer_no_duplicate_send
PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\37_multi_instance_single_peer_no_duplicate_send.pcap`
JSON: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\37_multi_instance_single_peer_no_duplicate_send.json`
Observed messages: 2 total
Observed PDUs: `WRR_REQ` inbound, `WRR_RESP` outbound
Expected effect: with two SentinelCBC instances connected to one peer, only one write-replace request is sent and the dispatch completes successfully.

### 38_multi_instance_cross_instance_stop_no_duplicate_send
PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\38_multi_instance_cross_instance_stop_no_duplicate_send.pcap`
JSON: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\38_multi_instance_cross_instance_stop_no_duplicate_send.json`
Observed messages: 4 total
Observed PDUs: `WRR_REQ` inbound, `WRR_RESP` outbound, `SWR_REQ` inbound, `SWR_RESP` outbound
Expected effect: one instance creates the warning, the other instance stops it, and the simulator still sees exactly one stop request.

### 39_multi_instance_restart_no_duplicate_replay
PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\39_multi_instance_restart_no_duplicate_replay.pcap`
JSON: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\39_multi_instance_restart_no_duplicate_replay.json`
Observed messages: 4 total
Observed PDUs: `WRR_REQ` inbound, `WRR_RESP` outbound, `WRR_REQ` inbound, `WRR_RESP` outbound
Expected effect: restarting one SentinelCBC instance does not replay already-completed work, and a follow-up warning sent through the surviving cluster still succeeds once.

### 40_multi_instance_primary_dies_secondary_continues
PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\40_multi_instance_primary_dies_secondary_continues.pcap`
JSON: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\40_multi_instance_primary_dies_secondary_continues.json`
Observed messages: 4 total
Observed PDUs: `WRR_REQ` inbound, `WRR_RESP` outbound, `WRR_REQ` inbound, `WRR_RESP` outbound
Expected effect: after one SentinelCBC instance is terminated, the surviving instance can still submit a new warning and the simulator still sees only one request per warning.

### 41_multi_instance_stale_reserved_reclaimed_by_secondary
PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\41_multi_instance_stale_reserved_reclaimed_by_secondary.pcap`
JSON: `C:\Projects\sctp-probe\artifacts\live_multi_instance_captures_20260328_044653\41_multi_instance_stale_reserved_reclaimed_by_secondary.json`
Observed messages: 4 total
Observed PDUs: `WRR_REQ` inbound, `WRR_RESP` outbound, `WRR_REQ` inbound, `WRR_RESP` outbound
Expected effect: a stale `RESERVED` write-replace row left behind by a dead instance is reclaimed by the surviving instance and eventually completes successfully. In this capture, the reclaim path required one retry during association recovery.
