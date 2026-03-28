# Phase 9C Timing Capture Summary

Capture folder: `C:\Projects\sctp-probe\artifacts\live_timing_captures_20260328_052457`

## 42_delayed_wrr_response_no_retry

- PCAP: [42_delayed_wrr_response_no_retry.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/42_delayed_wrr_response_no_retry.pcap)
- JSON: [42_delayed_wrr_response_no_retry.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/42_delayed_wrr_response_no_retry.json)
- Expected PDUs: `WRR_REQ`, delayed `WRR_RESP`
- Observed PDUs: `WRR_REQ`, `WRR_RESP`
- Observed counts: `1 inbound`, `1 outbound`, `2 total`
- Expected SentinelCBC effect: dispatch finishes `DONE/SUCCESS` without retry.

## 43_wrr_timeout_then_retry_success

- PCAP: [43_wrr_timeout_then_retry_success.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/43_wrr_timeout_then_retry_success.pcap)
- JSON: [43_wrr_timeout_then_retry_success.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/43_wrr_timeout_then_retry_success.json)
- Expected PDUs: first `WRR_REQ` times out, second `WRR_REQ` gets `WRR_RESP`
- Observed PDUs: `WRR_REQ`, `WRR_REQ`, `WRR_RESP`
- Observed counts: `2 inbound`, `1 outbound`, `3 total`
- Expected SentinelCBC effect: first attempt is retried, second attempt finishes `DONE/SUCCESS`.

## 44_wrr_timeout_exhausted_terminal

- PCAP: [44_wrr_timeout_exhausted_terminal.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/44_wrr_timeout_exhausted_terminal.pcap)
- JSON: [44_wrr_timeout_exhausted_terminal.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/44_wrr_timeout_exhausted_terminal.json)
- Expected PDUs: one `WRR_REQ` with no response
- Observed PDUs: `WRR_REQ`
- Observed counts: `1 inbound`, `0 outbound`, `1 total`
- Expected SentinelCBC effect: attempts are exhausted and the dispatch ends `DONE/TIMEOUT`.

## 45_wrr_disconnect_then_retry_success

- PCAP: [45_wrr_disconnect_then_retry_success.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/45_wrr_disconnect_then_retry_success.pcap)
- JSON: [45_wrr_disconnect_then_retry_success.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/45_wrr_disconnect_then_retry_success.json)
- Expected PDUs: initial `WRR_REQ`, disconnect, later retry succeeds after reconnect
- Observed PDUs: `WRR_REQ`, `WRR_REQ`, `WRR_RESP`, `WRR_REQ`, `WRR_RESP`
- Observed counts: `3 inbound`, `2 outbound`, `5 total`
- Expected SentinelCBC effect: transport disturbance is recovered and the dispatch finishes `DONE/SUCCESS`.
- Note: the exported wire trace shows multiple replayed `WRR_REQ` attempts for the same MI/SN during reconnect recovery, which is why this case has more traffic than the idealized two-attempt path.

## 46_wrr_transport_failure_exhausted_terminal

- PCAP: [46_wrr_transport_failure_exhausted_terminal.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/46_wrr_transport_failure_exhausted_terminal.pcap)
- JSON: [46_wrr_transport_failure_exhausted_terminal.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/46_wrr_transport_failure_exhausted_terminal.json)
- Expected PDUs: initial `WRR_REQ`, retry attempt while the SCTP peer is gone, no response
- Observed PDUs: `WRR_REQ`, `WRR_REQ`
- Observed counts: `2 inbound`, `0 outbound`, `2 total`
- Expected SentinelCBC effect: the retry path ends `DONE/TRANSPORT_FAILED` once attempts are exhausted.

## 47_swr_timeout_then_retry_success

- PCAP: [47_swr_timeout_then_retry_success.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/47_swr_timeout_then_retry_success.pcap)
- JSON: [47_swr_timeout_then_retry_success.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/47_swr_timeout_then_retry_success.json)
- Expected PDUs: successful `WRR_REQ/WRR_RESP`, then first `SWR_REQ` times out and second `SWR_REQ` gets `SWR_RESP`
- Observed PDUs: `WRR_REQ`, `WRR_RESP`, `SWR_REQ`, `SWR_REQ`, `SWR_RESP`
- Observed counts: `3 inbound`, `2 outbound`, `5 total`
- Expected SentinelCBC effect: the stop dispatch retries once and finishes `DONE/SUCCESS`.

## 48_swr_timeout_exhausted_terminal

- PCAP: [48_swr_timeout_exhausted_terminal.pcap](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/48_swr_timeout_exhausted_terminal.pcap)
- JSON: [48_swr_timeout_exhausted_terminal.json](C:/Projects/sctp-probe/artifacts/live_timing_captures_20260328_052457/48_swr_timeout_exhausted_terminal.json)
- Expected PDUs: successful `WRR_REQ/WRR_RESP`, then one `SWR_REQ` with no response
- Observed PDUs: `WRR_REQ`, `WRR_RESP`, `SWR_REQ`
- Observed counts: `2 inbound`, `1 outbound`, `3 total`
- Expected SentinelCBC effect: the stop dispatch exhausts its attempts and ends `DONE/TIMEOUT`.
