# Plain Case Descriptions

1. `01_write_replace_happy_path`  
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS.

2. `02_stop_warning_happy_path`  
Expected effect: STOP dispatch DONE/SUCCESS; warning stoppedAt set.

3. `03_write_replace_indication_happy_path`  
Expected effect: WRITE_REPLACE_WARNING_INDICATION stored and correlated.

4. `04_stop_warning_indication_happy_path`  
Expected effect: STOP_WARNING_INDICATION stored and correlated.

5. `05_error_indication_happy_path`  
Expected effect: ERROR_INDICATION stored, correlated, cause persisted.

6. `06_dispatch_wrr_success`  
Expected effect: WRITE_REPLACE dispatch DONE/SUCCESS.

7. `07_dispatch_wrr_partial`  
Expected effect: WRITE_REPLACE dispatch DONE/PARTIAL.

8. `08_dispatch_wrr_permanent_failure`  
Expected effect: WRITE_REPLACE dispatch DONE/FAILED.

9. `09_dispatch_wrr_transient_failure`  
Expected effect: WRITE_REPLACE dispatch DONE/FAILED under current worker semantics.

10. `10_dispatch_swr_success`  
Expected effect: STOP dispatch DONE/SUCCESS.

11. `11_dispatch_swr_not_found`  
Expected effect: STOP dispatch treated as DONE/SUCCESS.

12. `12_family_cmas_presidential`  
Expected effect: CMAS Presidential dispatch succeeds.

13. `13_family_cmas_public_safety`  
Expected effect: Whole-network CMAS Public Safety dispatch succeeds.

14. `14_family_etws_primary_only`  
Expected effect: ETWS PRIMARY_ONLY dispatch succeeds.

15. `15_family_etws_with_message_body`  
Expected effect: ETWS WITH_MESSAGE_BODY dispatch succeeds.

16. `16_family_eu_alert`  
Expected effect: EU-Alert dispatch succeeds.

17. `17_family_operator_defined`  
Expected effect: Operator-defined dispatch succeeds.

18. `18_delivery_area_tai_list_multiple`  
Expected effect: WRR request carries a TAI_LIST with three TAC entries and dispatch succeeds.

19. `19_delivery_area_cell_list_single`  
Expected effect: WRR request carries a CELL_ID_LIST with one cell and dispatch succeeds.

20. `20_delivery_area_cell_list_multiple`  
Expected effect: WRR request carries a CELL_ID_LIST with three cells and dispatch succeeds.

21. `21_multiple_warnings_sequential_same_peer`  
Expected effect: Two distinct warnings on the same peer produce two distinct successful WRR exchanges.

22. `22_create_validation_whole_network_with_delivery_area`  
SentinelCBC receives a create-warning request that incorrectly mixes WHOLE_NETWORK scope with a deliveryArea. Expected effect: the request is rejected locally with HTTP 400 and nothing is sent to the simulator.

23. `23_create_validation_specific_area_without_delivery_area`  
SentinelCBC receives a create-warning request for SPECIFIC_AREA without any deliveryArea. Expected effect: the request is rejected locally with HTTP 400 and nothing is sent to the simulator.

24. `24_create_validation_too_many_tais`  
SentinelCBC receives a create-warning request whose TAI list exceeds the supported maximum. Expected effect: the request is rejected locally with HTTP 400 and nothing is sent to the simulator.

25. `25_stop_validation_invalid_delivery_area_type`  
SentinelCBC receives a stop request with an invalid deliveryArea type. Expected effect: the stop request is rejected locally with HTTP 400 and no new stop message is sent to the simulator.

26. `26_stop_validation_already_stopped_conflict`  
SentinelCBC receives a second stop request for a warning that has already been stopped. Expected effect: the request is rejected with HTTP 409 and no second stop exchange is sent to the simulator.

27. `27_wrwi_after_stop_uncorrelated`  
After a warning is already stopped, the simulator sends a WRWI using the old message identifier and serial number. Expected effect: SentinelCBC logs the message but does not correlate it back to the stopped warning.

28. `28_error_indication_ambiguous_uncorrelated`  
With more than one active warning on the same peer, the simulator sends an ERROR_INDICATION. Expected effect: SentinelCBC logs it but keeps it uncorrelated because the target warning is ambiguous.

29. `29_duplicate_wrwi_logs_twice`  
The simulator sends the same WRWI twice for the same warning. Expected effect: SentinelCBC persists both protocol messages rather than silently dropping the duplicate.

30. `30_swi_before_stop_uncorrelated`  
The simulator sends an SWI before SentinelCBC has issued a stop request for that warning. Expected effect: SentinelCBC logs the indication but does not correlate it to the still-active warning.

31. `31_duplicate_swi_logs_twice`  
The simulator sends the same SWI twice for the same stopped warning. Expected effect: SentinelCBC persists both protocol messages rather than silently dropping the duplicate.

32. `32_malformed_inbound_pdu_discarded`  
The simulator sends raw malformed bytes that do not decode as SBc-AP. Expected effect: SentinelCBC discards the payload, stays healthy, and does not create any protocol_messages row.

33. `33_unsupported_inbound_initiating_message_discarded`  
The simulator sends a valid SBc-AP initiating message of an unsupported inbound type. Expected effect: SentinelCBC discards it, stays healthy, and does not create any protocol_messages row.
