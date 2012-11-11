
-----------
TCMS Plugin
-----------

Plugin allows registering automatic test runs in TCMS site.

CLI Options
------------
    --with-tcms enable the plugin
    --tcms-user username for TCMS site
    --tcms-gen-links generate links to tmcs_test_cases

Configuration Options:
----------------------
    [TCMS]
    enabled - to enable the plugin (true/false)
    user - username for TCMS site
    site - url addres to TCMS site,
           default: https://tcms.engineering.redhat.com/xmlrpc/
    realm - KRB realm, default: @REDHAT.COM
    keytab_files_location - path to directory where KRB keytabs are located
    send_result_email - if to send the results by email (true/false)
    test_run_name_template - test run template name, for an example:
            "Auto Run for {0} TestPlan"
    category - test category name (should be compatible with TCMS category)

Usage
-----
For XML tests sheet
+++++++++++++++++++
There are 2 tags dedicated for this plugin:
    * <tcms_test_plan> - TCMS test plan ID. You can use this tag for each
    test_suite,  test_group or test_case.
    It is inherited into nested elements (grouped test cases for an example),
    so you don't need to repeate it there.
    * <tcms_test_case> - TCMS test case ID. You can use this tag for either
    test_group or test_case.

From unittets suite
+++++++++++++++++++
In art.test_handler.tools module there is defined tcms(plan_id, case_id)
decorator. You can use it to decorate your functions.
