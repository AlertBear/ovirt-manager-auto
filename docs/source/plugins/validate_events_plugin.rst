
------------------------
Events Validation Plugin
------------------------

Plugin provides validation of events by correlation id.
Correlation Id can be added in RHEVM to each REST request in order
to be able to track actions with this id later in logs and events pages.
The plugin will be triggered for test cases with existed Correlation-Id in
headers of 'conf' attribute, for an example:
    <conf>headers={'Correlation-Id': 101}</conf>

CLI Options:
------------
    --validate-events enable plugin

Configuration Options:
----------------------
    [VALIDATE_EVENTS]
    enabled   to enable the plugin (true/false)
