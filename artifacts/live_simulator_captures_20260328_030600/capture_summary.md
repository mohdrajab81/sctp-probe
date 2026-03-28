# Live Simulator Capture Summary

Folder: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600

## 01_write_replace_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\01_write_replace_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\01_write_replace_happy_path.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS

## 02_stop_warning_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\02_stop_warning_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\02_stop_warning_happy_path.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch DONE/SUCCESS; warning stoppedAt set

## 03_write_replace_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\03_write_replace_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\03_write_replace_indication_happy_path.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, WRWI ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, WRWI ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: WRITE_REPLACE_WARNING_INDICATION stored and correlated

## 04_stop_warning_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\04_stop_warning_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\04_stop_warning_indication_happy_path.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->, SWI ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->,  ->
Observed counts: inbound=2, outbound=3, total=5
Expected effect: STOP_WARNING_INDICATION stored and correlated

## 05_error_indication_happy_path
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\05_error_indication_happy_path.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\05_error_indication_happy_path.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, ERR_IND ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, ERR_IND ->
Observed counts: inbound=1, outbound=2, total=3
Expected effect: ERROR_INDICATION stored, correlated, cause persisted

## 06_dispatch_wrr_success
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\06_dispatch_wrr_success.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\06_dispatch_wrr_success.json
Expected PDUs: WRR_REQ <-, WRR_RESP(success) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS

## 07_dispatch_wrr_partial
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\07_dispatch_wrr_partial.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\07_dispatch_wrr_partial.json
Expected PDUs: WRR_REQ <-, WRR_RESP(partial) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/PARTIAL

## 08_dispatch_wrr_permanent_failure
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\08_dispatch_wrr_permanent_failure.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\08_dispatch_wrr_permanent_failure.json
Expected PDUs: WRR_REQ <-, WRR_RESP(permanent-failure) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/FAILED

## 09_dispatch_wrr_transient_failure
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\09_dispatch_wrr_transient_failure.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\09_dispatch_wrr_transient_failure.json
Expected PDUs: WRR_REQ <-, WRR_RESP(transient-failure) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: WRITE_REPLACE dispatch DONE/FAILED under current worker semantics

## 10_dispatch_swr_success
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\10_dispatch_swr_success.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\10_dispatch_swr_success.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP(success) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch DONE/SUCCESS

## 11_dispatch_swr_not_found
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\11_dispatch_swr_not_found.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\11_dispatch_swr_not_found.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP(not-found) ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->, SWR_REQ <-, SWR_RESP ->
Observed counts: inbound=2, outbound=2, total=4
Expected effect: STOP dispatch treated as DONE/SUCCESS

## 12_family_cmas_presidential
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\12_family_cmas_presidential.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\12_family_cmas_presidential.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: CMAS Presidential dispatch succeeds

## 13_family_cmas_public_safety
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\13_family_cmas_public_safety.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\13_family_cmas_public_safety.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: Whole-network CMAS Public Safety dispatch succeeds

## 14_family_etws_primary_only
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\14_family_etws_primary_only.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\14_family_etws_primary_only.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: ETWS PRIMARY_ONLY dispatch succeeds

## 15_family_etws_with_message_body
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\15_family_etws_with_message_body.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\15_family_etws_with_message_body.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: ETWS WITH_MESSAGE_BODY dispatch succeeds

## 16_family_eu_alert
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\16_family_eu_alert.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\16_family_eu_alert.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: EU-Alert dispatch succeeds

## 17_family_operator_defined
PCAP: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\17_family_operator_defined.pcap
JSON: C:\Projects\sctp-probe\artifacts\live_simulator_captures_20260328_030600\17_family_operator_defined.json
Expected PDUs: WRR_REQ <-, WRR_RESP ->
Observed PDUs: WRR_REQ <-, WRR_RESP ->
Observed counts: inbound=1, outbound=1, total=2
Expected effect: Operator-defined dispatch succeeds

