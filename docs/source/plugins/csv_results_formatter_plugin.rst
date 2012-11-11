
----------------------------
CSV Results Formatter Plugin
----------------------------

This plugin generates CSV report for test results

CLI Options:
-----------
    --rf-csv enable plugin and set path to output file,
             default is results/results.csv

Configuration File Options:
---------------------------
    [CSV_FORMATER]
    enabled   to enable the plugin (true/false)
    precision - number of digits after decimal point, default: 5
    order - fields order in csv file, default: 'id, module_name, start_time,
    req_elapsed_time, test_status, captured_log'
