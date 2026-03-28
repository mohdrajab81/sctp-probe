## Plain Case Descriptions

1. `37_multi_instance_single_peer_no_duplicate_send`
Two SentinelCBC instances are running at the same time against one simulator peer. A warning is created once. The expected result is that the simulator receives only one write-replace request and returns one successful response.

2. `38_multi_instance_cross_instance_stop_no_duplicate_send`
One SentinelCBC instance creates a warning, and the other instance sends the stop request for that same warning. The expected result is that the simulator receives one write request, one stop request, and no duplicate stop traffic.

3. `39_multi_instance_restart_no_duplicate_replay`
One SentinelCBC instance creates a warning successfully, then that instance is restarted while the second instance remains alive. The expected result is that the already-finished warning is not replayed after restart, and a new warning sent after the restart still succeeds exactly once.

4. `40_multi_instance_primary_dies_secondary_continues`
Two SentinelCBC instances start connected to one simulator peer. After one instance is terminated, the other instance submits a new warning. The expected result is that the surviving instance continues normally and the simulator still sees only one new write-replace request.

5. `41_multi_instance_stale_reserved_reclaimed_by_secondary`
A write-replace dispatch row is forced into a stale `RESERVED` state to simulate a dead worker leaving work behind. One SentinelCBC instance is then removed, the surviving instance reconnects to the simulator, and the expected result is that the stale row is reclaimed and finished successfully. In the recorded run, the reclaim path needed one retry while the SCTP association settled.
