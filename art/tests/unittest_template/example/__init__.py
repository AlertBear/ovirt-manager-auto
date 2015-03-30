"""
Please be aware all your tests must be able to loaded by nose.loader.TestLoader
automatically. If you need something what is not visible for TestLoader first
of all ask yourself 'Why?'. Only in case you are convienced there is reason
to do that, just let me know (lbednar@redhat.com), I have workaround.

NOTE: test identifier for this example is
 tests_file = unittest://tests/unittest_template:example

Purpose of this doc string is also description of test suite.
"""

# Import module from rhevm_api
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters


def setup_package():
    # import MUST be in the function, cannot be on module level. That's
    # because of __init__.py is loaded first and then ART_CONFIG is set.
    import config
    # Here put your set-up action for whole bunch of tests
    datacenters.build_setup(config.PARAMETERS, config.STORAGE_CONF,
                            config.STORAGE_TYPE, config.TESTNAME)


def teardown_package():
    import config
    # Here put your tear-down action for whole bunch of tests
    datacenters.clean_datacenter(True, config.DATA_CENTER_NAME)
