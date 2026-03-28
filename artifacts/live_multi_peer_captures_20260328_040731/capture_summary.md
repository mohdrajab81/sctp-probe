# Live Multi-Peer Capture Summary

Folder: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731`

## 34_multi_peer_wrr_both_success
Probe A PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\34_multi_peer_wrr_both_success_probe_a.pcap`
Probe A JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\34_multi_peer_wrr_both_success_probe_a.json`
Probe A observed PDUs: `WRR_REQ <-`, `WRR_RESP ->`
Probe A observed counts: `inbound=1`, `outbound=1`, `total=2`

Probe B PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\34_multi_peer_wrr_both_success_probe_b.pcap`
Probe B JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\34_multi_peer_wrr_both_success_probe_b.json`
Probe B observed PDUs: `WRR_REQ <-`, `WRR_RESP ->`
Probe B observed counts: `inbound=1`, `outbound=1`, `total=2`

Expected effect: one write-replace dispatch per peer, both ending `DONE/SUCCESS`.

## 35_multi_peer_wrr_mixed_outcomes
Probe A PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\35_multi_peer_wrr_mixed_outcomes_probe_a.pcap`
Probe A JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\35_multi_peer_wrr_mixed_outcomes_probe_a.json`
Probe A observed PDUs: `WRR_REQ <-`, `WRR_RESP(success) ->`
Probe A observed counts: `inbound=1`, `outbound=1`, `total=2`

Probe B PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\35_multi_peer_wrr_mixed_outcomes_probe_b.pcap`
Probe B JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\35_multi_peer_wrr_mixed_outcomes_probe_b.json`
Probe B observed PDUs: `WRR_REQ <-`, `WRR_RESP(permanent-failure) ->`
Probe B observed counts: `inbound=1`, `outbound=1`, `total=2`

Expected effect: peer A dispatch ends `DONE/SUCCESS`; peer B dispatch ends `DONE/FAILED`.

## 36_multi_peer_whole_network_enabled_peers
Probe A PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\36_multi_peer_whole_network_enabled_peers_probe_a.pcap`
Probe A JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\36_multi_peer_whole_network_enabled_peers_probe_a.json`
Probe A observed PDUs: `WRR_REQ <-`, `WRR_RESP ->`
Probe A observed counts: `inbound=1`, `outbound=1`, `total=2`

Probe B PCAP: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\36_multi_peer_whole_network_enabled_peers_probe_b.pcap`
Probe B JSON: `C:\Projects\sctp-probe\artifacts\live_multi_peer_captures_20260328_040731\36_multi_peer_whole_network_enabled_peers_probe_b.json`
Probe B observed PDUs: `WRR_REQ <-`, `WRR_RESP ->`
Probe B observed counts: `inbound=1`, `outbound=1`, `total=2`

Expected effect: a whole-network warning resolves to both enabled peers and both write-replace dispatches end `DONE/SUCCESS`.
