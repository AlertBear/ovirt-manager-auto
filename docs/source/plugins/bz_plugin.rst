
---------------
Bugzilla Plugin
---------------

This plugin provides access to the Bugzilla site.
This plugin is triggered by 'bz' attribute of test case. If the provided
bug is opened the test will be marked as Skipped in case of its failure.

Test Case Configuration
-----------------------
<bz>bug_num</bz>

CLI Options
------------
    --with-bz  Enables  the Bugzilla plugin.
    --bz-user BZ_USER  User name for Bugzilla ,
        the default is 'bugzilla-qe-tlv@redhat.com'.
    --bz-pass BZ_PASS  Password for the Bugzilla ,
            the default is 'F3x5RiBnzn'.
    --bz-host BZ_HOST  URL  address for Bugzilla ,
            the default is https://bugzilla.redhat.com/xmlrpc.cgi

Configuration File Options
--------------------------
    [BUGZILLA]
    enabled  true/false; equivalent to with-bz CLI option
    user  equivalent to bz-user CLI option
    password  equivalent to bz-pass CLI option
    url  equivalent to bz-host CLI option
    constant_list  list of bug states which should be not skipped

Usage
-----

From XML test sheet
+++++++++++++++++++
You can add <bz> tag for each test_case or test_group with appropiate bugzilla
id. You can define more than one comma-separated ids.

From unittest suite
+++++++++++++++++++
In art.test_handler.tools module is defined bz(*bz_ids) decorator. You can
decorate your functions and pass as many ids as you need.
