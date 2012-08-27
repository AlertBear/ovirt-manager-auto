"""
Please be aware all your tests must be able to loaded by nose.loader.TestLoader
automatically. If you need something what is not visible for TestLoader first
of all ask yourself 'Why?'. Only in case you are convienced there is reason
to do that, just let me know (lbednar@redhat.com), I have workaround.

NOTE: test identifier for this example is
 tests_file = unittest://tests/unittest_template:example

"""


def setUpPackage():
    print "Here put your set-up action for whole bunch of tests"

def tearDownPackage():
    print "Here put your tear-down action for whole bunch of tests"

