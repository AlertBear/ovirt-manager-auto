
--------------------
Mac Converter Plugin
--------------------

Plugin captures DHCP leases on VDS hosts, which means you are able to get
IP address of VM according to MAC address.
ART provides function convertMacToIp which maps MAC to IP according to
RHEVM QA lab definitions.
Plugin rebinds this function to converter, so you don't need to use
two different functions and don't need to change your tests.

CLI Options:
------------
    --with-mac-ip-conv enable plugin

Configuration Options:
---------------------
    [MAC_TO_IP_CONV]
    enabled - to enable plugin (true/false)
    timeout - timeout in seconds for reading DHCP leases, default: 10
    attempts - number of attempts for retry, default: 60
    wait_interval - seconds to sleep between attempts, default: 1
