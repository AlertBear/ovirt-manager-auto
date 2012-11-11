
---------------------
Errors Fetcher Plugin
---------------------
Plugin collects error messages from VDC machine for test_cases which fail.

CLI Options:
------------
    --fetch-errors enable plugin
    --fe-vdc-pass password for root account on VDC machine
    --fe-path-to-log path to log on VDC machine

Configuration Options:
----------------------
    [ERROR_FETCHER]
    enabled - to enable the plugin (true/false)
    path_to_log - path to log on VDC machine

    [PARAMETERS]
    vdc_root_password - password for root account on VDC machine
