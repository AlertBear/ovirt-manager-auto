
--------------------
Log Capturing Plugin
--------------------

This plugin collects log messages when executing  test cases.
When a test case is finished, this plugin groups and sends logs
to the related test case. Log bunches are available in results file
under <captured_log> tag.

CLI Options:
------------
    --log-capture enable plugin

Configuration Options:
----------------------
    [LOG_CAPTURE]
    enabled - to enable the plugin (true/false)
    level - logging level, default: debug
    record_name - xml node name in results file, default: captured_log
    fmt - a string which describes the log  message format, for an example:
        '#(asctime)s - #(threadName)s - #(name)s - #(levelname)s - #(message)s')
