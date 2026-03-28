# Plain Case Descriptions

1. `01_write_replace_happy_path`  
SentinelCBC creates a normal warning. It sends WRR_REQ to the simulator, and the simulator replies with WRR_RESP success. Expected effect: the write-replace dispatch finishes successfully.

2. `02_stop_warning_happy_path`  
SentinelCBC first creates a warning successfully, then sends a stop request for it. The simulator receives SWR_REQ and replies with SWR_RESP success. Expected effect: the stop dispatch finishes successfully and the warning becomes stopped.

3. `03_write_replace_indication_happy_path`  
SentinelCBC creates a warning and gets a successful write-replace response. After that, the simulator sends a WRWI indication back. Expected effect: SentinelCBC stores and correlates the write-replace indication to the correct warning.

4. `04_stop_warning_indication_happy_path`  
SentinelCBC creates a warning, stops it successfully, and then the simulator sends an SWI indication. Expected effect: SentinelCBC stores and correlates the stop-warning indication to the stopped warning.

5. `05_error_indication_happy_path`  
SentinelCBC creates a warning successfully, and then the simulator sends an ERROR_INDICATION. Expected effect: SentinelCBC stores the error indication, correlates it to the correct warning, and records the cause code.

6. `06_dispatch_wrr_success`  
This is a focused write-replace response case. SentinelCBC sends WRR_REQ, and the simulator returns a success response. Expected effect: dispatch result is DONE/SUCCESS.

7. `07_dispatch_wrr_partial`  
SentinelCBC sends WRR_REQ, and the simulator returns a partial-success response. Expected effect: dispatch result is DONE/PARTIAL.

8. `08_dispatch_wrr_permanent_failure`  
SentinelCBC sends WRR_REQ, and the simulator returns a permanent failure response. Expected effect: dispatch result is DONE/FAILED.

9. `09_dispatch_wrr_transient_failure`  
SentinelCBC sends WRR_REQ, and the simulator returns a transient failure response. Expected effect: under current worker behavior, this still ends as DONE/FAILED.

10. `10_dispatch_swr_success`  
SentinelCBC creates a warning, then sends a stop request. The simulator replies to the stop with success. Expected effect: stop dispatch is DONE/SUCCESS.

11. `11_dispatch_swr_not_found`  
SentinelCBC creates a warning, then sends a stop request. The simulator replies with warning not found. Expected effect: SentinelCBC still treats the stop as operational success.

12. `12_family_cmas_presidential`  
SentinelCBC sends a CMAS Presidential warning through the simulator path. Expected effect: the dispatch succeeds normally.

13. `13_family_cmas_public_safety`  
SentinelCBC sends a whole-network CMAS Public Safety warning through the simulator path. Expected effect: the dispatch succeeds normally.

14. `14_family_etws_primary_only`  
SentinelCBC sends an ETWS Primary-Only warning, which has no message body. Expected effect: the dispatch succeeds normally.

15. `15_family_etws_with_message_body`  
SentinelCBC sends an ETWS warning that includes a message body. Expected effect: the dispatch succeeds normally.

16. `16_family_eu_alert`  
SentinelCBC sends an EU-Alert warning through the simulator path. Expected effect: the dispatch succeeds normally.

17. `17_family_operator_defined`  
SentinelCBC sends an operator-defined warning through the simulator path. Expected effect: the dispatch succeeds normally.

18. `18_delivery_area_tai_list_multiple`  
SentinelCBC sends a specific-area warning with three TAC entries in the TAI list. Expected effect: the simulator decodes a tracking-area-list-for-warning with three items and the dispatch succeeds.

19. `19_delivery_area_cell_list_single`  
SentinelCBC sends a specific-area warning with a single cell in the CELL_ID_LIST delivery area. Expected effect: the simulator decodes a cell-ID-list with one item and the dispatch succeeds.

20. `20_delivery_area_cell_list_multiple`  
SentinelCBC sends a specific-area warning with three cells in the CELL_ID_LIST delivery area. Expected effect: the simulator decodes a cell-ID-list with three items and the dispatch succeeds.

21. `21_multiple_warnings_sequential_same_peer`  
SentinelCBC sends two warnings in sequence to the same peer. Expected effect: the simulator sees two separate WRR request/response exchanges with distinct message-identifier and serial-number pairs, and both dispatches succeed.
