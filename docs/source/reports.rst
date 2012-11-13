Reports
=======
Test reports are located by default in ``results/results.xml``. You can also specify  a customized location  using the *--res* parameter during a  test run. The test report header has the following attributes:

* logfile - path to a test log file
* testFile - input test file name

All tests results  appear as sub nodes of the related group or just 'test'  node in case of independent tests. Names of test statistics nodes depend on parameters set in the *REPORT* section of your *settings.conf* file.
The following default nodes are always added:

* start_time - time stamp when test started 
* end_time - time stamp when test finished 
* status - test status (Pass/Fail) 
* iter_num - test iteration number
* all test cases attributes you used in your input file (test_name, parameters, positive, etc.)

You can generate also report in xunit format by enabling *xunit_results_formater_plugin* ::

    python run.py -conf=<config_path> --rf-x-unit

By defauls xunit report will be stored at ``results/xunit_output.xml``.
You can change this default location by setting a new path::

    python run.py -conf=<config_path> --rf-x-unit=<xunit_results_path>