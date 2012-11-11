Reports
=======
Test reports are  located by default in results/results.xml. You can also specify  a customized location  using the --resultXmlFile/--res parameter during a  test run. The test report header has the following attributes:

* logfile - path to a test log file
* testFile - input test file name

All tests results  appear as sub nodes of the related group or just 'test'  node in case of independent tests. Names of test statistics nodes depend on parameters set in the REPORT section of your settings.conf file,  .The following default nodes are always added:

* start_time - time stamp when test started 
* end_time - time stamp when test finished 
* status - test status (Pass/Fail) 
* iter_num - test iteration number
* all test cases attributes you used in your input file (test_name, parameters, positive, etc.)