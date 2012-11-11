
----------------------------
Disabling Vital Tests Plugin
----------------------------

ART allows you to set any test case as vital. It means if it fails
no further test will be run. To map test case as vital in xml file
the following attribute should be added:
<vital>yes</vital>
Sometimes for debugging purposes you want to disable vital tests but
don't want to change your xml file.
This is exactly what this plugin provides for you.

CLI Options:
    --vital-disable enable plugin

Configuration Options:
    [VITAL_DISABLE]
    enabled   to enable the plugin (true/false)
