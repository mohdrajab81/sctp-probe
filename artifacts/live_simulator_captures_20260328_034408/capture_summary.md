# Live Simulator Capture Summary

Folder: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408

## 01_write_replace_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\01_write_replace_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\01_write_replace_happy_path.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS

## 02_stop_warning_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\02_stop_warning_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\02_stop_warning_happy_path.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch DONE/SUCCESS; warning stoppedAt set

## 03_write_replace_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\03_write_replace_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\03_write_replace_indication_happy_path.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRWI ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: WRITE_REPLACE_WARNING_INDICATION stored and correlated

## 04_stop_warning_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\04_stop_warning_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\04_stop_warning_indication_happy_path.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->, UNKNOWN ->
Observed counts: inbound=2, outbound=3, total=5
Expected effect: STOP_WARNING_INDICATION stored and correlated

## 05_error_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\05_error_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\05_error_indication_happy_path.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, ERR_IND ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: ERROR_INDICATION stored, correlated, cause persisted

## 06_dispatch_wrr_success
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\06_dispatch_wrr_success.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\06_dispatch_wrr_success.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS

## 07_dispatch_wrr_partial
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\07_dispatch_wrr_partial.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\07_dispatch_wrr_partial.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/PARTIAL

## 08_dispatch_wrr_permanent_failure
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\08_dispatch_wrr_permanent_failure.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\08_dispatch_wrr_permanent_failure.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/FAILED

## 09_dispatch_wrr_transient_failure
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\09_dispatch_wrr_transient_failure.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\09_dispatch_wrr_transient_failure.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/FAILED under current worker semantics

## 10_dispatch_swr_success
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\10_dispatch_swr_success.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\10_dispatch_swr_success.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch DONE/SUCCESS

## 11_dispatch_swr_not_found
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\11_dispatch_swr_not_found.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\11_dispatch_swr_not_found.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch treated as DONE/SUCCESS

## 12_family_cmas_presidential
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\12_family_cmas_presidential.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\12_family_cmas_presidential.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: CMAS Presidential dispatch succeeds

## 13_family_cmas_public_safety
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\13_family_cmas_public_safety.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\13_family_cmas_public_safety.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: Whole-network CMAS Public Safety dispatch succeeds

## 14_family_etws_primary_only
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\14_family_etws_primary_only.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\14_family_etws_primary_only.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: ETWS PRIMARY_ONLY dispatch succeeds

## 15_family_etws_with_message_body
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\15_family_etws_with_message_body.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\15_family_etws_with_message_body.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: ETWS WITH_MESSAGE_BODY dispatch succeeds

## 16_family_eu_alert
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\16_family_eu_alert.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\16_family_eu_alert.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: EU-Alert dispatch succeeds

## 17_family_operator_defined
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\17_family_operator_defined.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\17_family_operator_defined.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: Operator-defined dispatch succeeds

## 18_delivery_area_tai_list_multiple
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\18_delivery_area_tai_list_multiple.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\18_delivery_area_tai_list_multiple.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRR request carries a TAI_LIST with three TAC entries and dispatch succeeds

## 19_delivery_area_cell_list_single
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\19_delivery_area_cell_list_single.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\19_delivery_area_cell_list_single.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRR request carries a CELL_ID_LIST with one cell and dispatch succeeds

## 20_delivery_area_cell_list_multiple
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\20_delivery_area_cell_list_multiple.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\20_delivery_area_cell_list_multiple.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRR request carries a CELL_ID_LIST with three cells and dispatch succeeds

## 21_multiple_warnings_sequential_same_peer
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\21_multiple_warnings_sequential_same_peer.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\21_multiple_warnings_sequential_same_peer.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: Two distinct warnings on the same peer produce two distinct successful WRR exchanges

## 22_create_validation_whole_network_with_delivery_area
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\22_create_validation_whole_network_with_delivery_area.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\22_create_validation_whole_network_with_delivery_area.json
Observed PDUs: 
Observed counts: inbound=0, outbound=0, total=0
Expected effect: Invalid create request rejected locally with no simulator traffic

## 23_create_validation_specific_area_without_delivery_area
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\23_create_validation_specific_area_without_delivery_area.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\23_create_validation_specific_area_without_delivery_area.json
Observed PDUs: 
Observed counts: inbound=0, outbound=0, total=0
Expected effect: Invalid create request rejected locally with no simulator traffic

## 24_create_validation_too_many_tais
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\24_create_validation_too_many_tais.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\24_create_validation_too_many_tais.json
Observed PDUs: 
Observed counts: inbound=0, outbound=0, total=0
Expected effect: Invalid create request rejected locally with no simulator traffic

## 25_stop_validation_invalid_delivery_area_type
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\25_stop_validation_invalid_delivery_area_type.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\25_stop_validation_invalid_delivery_area_type.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: Invalid stop request rejected locally with no new simulator traffic

## 26_stop_validation_already_stopped_conflict
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\26_stop_validation_already_stopped_conflict.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\26_stop_validation_already_stopped_conflict.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: Second stop rejected with conflict and no new simulator traffic

## 27_wrwi_after_stop_uncorrelated
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\27_wrwi_after_stop_uncorrelated.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\27_wrwi_after_stop_uncorrelated.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->, WRWI ->
Observed counts: inbound=2, outbound=3, total=5
Expected effect: WRWI after stop is logged but remains uncorrelated

## 28_error_indication_ambiguous_uncorrelated
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\28_error_indication_ambiguous_uncorrelated.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\28_error_indication_ambiguous_uncorrelated.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRR_REQ <-, WRR_RESP ->, ERR_IND ->
Observed counts: inbound=2, outbound=3, total=5
Expected effect: Ambiguous ERROR_INDICATION is logged but remains uncorrelated

## 29_duplicate_wrwi_logs_twice
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\29_duplicate_wrwi_logs_twice.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\29_duplicate_wrwi_logs_twice.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRWI ->, WRWI ->
Observed counts: inbound=1, outbound=3, total=4
Expected effect: Duplicate WRWI messages are both persisted

## 30_swi_before_stop_uncorrelated
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\30_swi_before_stop_uncorrelated.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\30_swi_before_stop_uncorrelated.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, UNKNOWN ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: SWI before stop is logged but remains uncorrelated

## 31_duplicate_swi_logs_twice
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\31_duplicate_swi_logs_twice.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\31_duplicate_swi_logs_twice.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->, UNKNOWN ->, UNKNOWN ->
Observed counts: inbound=2, outbound=4, total=6
Expected effect: Duplicate SWI messages are both persisted

## 32_malformed_inbound_pdu_discarded
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\32_malformed_inbound_pdu_discarded.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\32_malformed_inbound_pdu_discarded.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, UNKNOWN ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: Malformed inbound bytes are discarded without protocol_messages growth

## 33_unsupported_inbound_initiating_message_discarded
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\33_unsupported_inbound_initiating_message_discarded.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_034408\33_unsupported_inbound_initiating_message_discarded.json
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRR_REQ ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: Unsupported inbound initiating message is discarded without protocol_messages growth
