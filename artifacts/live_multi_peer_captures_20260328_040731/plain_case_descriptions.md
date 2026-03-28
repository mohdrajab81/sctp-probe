# Plain Multi-Peer Case Descriptions

34. `34_multi_peer_wrr_both_success`  
SentinelCBC sends one write-replace warning to two configured peers at the same time. Both simulator peers accept it and reply with successful `WRR_RESP` messages. Expected effect: both peer dispatch rows finish successfully.

35. `35_multi_peer_wrr_mixed_outcomes`  
SentinelCBC sends one write-replace warning to two configured peers. Probe A replies with a successful `WRR_RESP`, while probe B replies with a permanent-failure `WRR_RESP`. Expected effect: peer A ends in success, peer B ends in failure, and the system records the split outcome correctly per peer.

36. `36_multi_peer_whole_network_enabled_peers`  
SentinelCBC creates a whole-network warning without explicitly naming target peers. The service resolves that warning to all enabled peers, which in this run are the two simulator peers. Both peers receive a `WRR_REQ` and both reply successfully. Expected effect: whole-network peer resolution fans out to both enabled peers and both dispatches complete successfully.
