
-----------
Trac Plugin
-----------

This plugin provides access to the Trac site.
This plugin is triggered by 'trac' attribute of test_case.
It skips test_case when provided trac_ticket_id isn't closed.

Test Case Configuration
-----------------------

<trac>ticket_id, ...</trac>

CLI Options
-----------
    --with-trac Enables plugin

Configuration File Options
--------------------------
    [TRAC]
    enabled - True/False, enables plugin
    url - trac site URL, 'http(s)://[user[:pass]@]host[:port]/path/to/rpc/entry'
            default: https://engineering.redhat.com/trac/automation/rpc

