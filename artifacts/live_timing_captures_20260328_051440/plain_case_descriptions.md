# Phase 9C Plain Case Descriptions

1. `42_delayed_wrr_response_no_retry`
SentinelCBC sends a normal write-replace warning request. The simulator waits a few seconds before replying with success. Expected effect: SentinelCBC accepts the delayed response and completes the dispatch successfully without sending a retry.

2. `43_wrr_timeout_then_retry_success`
SentinelCBC sends a write-replace request and gets no response the first time. It retries the same warning, and the simulator replies successfully on the second attempt. Expected effect: the dispatch is retried once and then completes successfully.

3. `44_wrr_timeout_exhausted_terminal`
SentinelCBC sends a write-replace request and the simulator never replies. The warning is configured with only one allowed attempt. Expected effect: SentinelCBC stops retrying and marks the dispatch as a terminal timeout.

4. `45_wrr_disconnect_then_retry_success`
SentinelCBC starts sending a write-replace request, then the simulator side disconnects before the exchange completes. After the probe listener comes back and the SCTP association reconnects, SentinelCBC retries and eventually gets a successful response. Expected effect: the dispatch survives the transport break and ends successfully after recovery.

5. `46_wrr_transport_failure_exhausted_terminal`
SentinelCBC sends a write-replace request, the first attempt times out, and then the SCTP peer is no longer available when the retry is attempted. Expected effect: SentinelCBC exhausts the allowed attempts and finishes the dispatch as a terminal transport failure.
