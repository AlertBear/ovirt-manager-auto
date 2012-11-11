
--------------------------
Cpu Name Resolution Plugin
--------------------------

This plugin adjusts config section for cpu_name attribute.
It finds the maximum compatible cpu_name to use for the vds configured and
puts it into PARAMETERS.cpu_name value.

CLI Options:
------------
    --with-cpu-name-resolution enable plugin

Configuration File Options:
----------------------
    [CPU_NAME_RESOLUTION]
    enabled   to enable the plugin (true/false)
