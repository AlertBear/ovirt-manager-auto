Run The Test
============

Compile ods/xml file for local run
-----------------------------------
To check there  are no errors in your ods or xml files, run a compilation beforehand. It will  validate your input file but  not run the tests:
    ``python run.py  --compile``
In case there are errors in your ods/xml file you will see them in your console. Fix them as required.  

Run test
--------
When your configuration is ready run the test from your working folder. The test requires several parameters:
* configFile (conf) - Mandatory path to the settings.conf file .
* resultsXmlFile (res) - Optional path to the results.xml file, the default is results/results.xml. 
* log - Optional path to the log file, default is /var/log/restTest<timestamp>.log
      .. seealso::
        Run ``python run.py --help`` for other possible options.
If you want to run the test with default parameters  run the main script as: 
``python run.py -conf=<config_path>``

Run only specific lines or test groups from input file
------------------------------------------------------
You can run only specific lines from your .ods file or specific test cases from xml file. In this case all other lines or test cases will be skipped.

Lines numbers should be greater than 1 as the first line in .ods file is actually a header.

``python run.py --lines=50-60,70,80-90,100``

You can run only specific test groups and skip all other groups:

``python run.py --groups=Test1,Test3,Test5``

The test will  run and report all its actions to your console. Test results will be reported to results/results.xml and junit_results.xml files .

The log file can be found at /var/tmp/restTest_<timestamp>.log or at the location specified at -log cli option.

Run externally (without settings, ods and run.py)
-------------------------------------------------
If you want to use REST APIs functions in your own code independent of the whole framework you can do it with the RestTestRunnerWrapper instance. For example::

    from utils.restutils import RestTestRunnerWrapper
    restWrapper = RestTestRunnerWrapper('10.35.113.80') # provide ip of your rest client server
    try:
        status = restWrapper.runCommand('rest.datacenters.addDataCenter', 'true', name='test',storage_type='NFS', version='2.2') # run the function via wrapper, first parameter is a function path, then a list of function's parameters
    except RestApiCommandError:
        pass #handle error