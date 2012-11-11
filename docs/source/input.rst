Input Test Scenario File
========================
This file defines the test scenario. Each test case in this file should contain the following attributes (xml nodes for .xml file, column for .ods file, TestCase object attributes for .py file):

* test_name - *mandatory* Name of the test which will appear in reports 
* test_action - *mandatory* Action which will run to implement the test, each action is mapped to the function in conf/actions.conf file 
* parameters - *mandatory* Parameters received by the test. See `Parameters`_ section for more information.
* positive - mandatory TRUE if the test should succeed, FALSE otherwise. You can set NONE if your function should not use this parameter at all. 
* run - *mandatory* 'yes' if the test should be run, 'no' if you want to skip the test. Also, you can specify a Python condition here, see `Run Conditions`_ section. 
* report - *optional* (default is ‘yes’) 'yes' if the test results should be reported (in the results.xml file), 'no' if the test results should not be reported. If this column is omitted all tests are reported. 
* fetch_output - *optional* If your function returns some value that you want to use in further tests, specify it in this column. See `Fetch Output`_ section.
* vital - *optional* (default is ‘no’) 'yes' if the test is vital and further tests cannot  continue without its success, 'no' otherwise. If a vital test fails all further tests will not be run. 
* tmcs_test_case - *optional* The numeric identifier of the TCMS test case related to your REST-Framework test case. 
* test_description - *optional* Detailed description of your test. 
* conf - *optional* Option to change the global configuration settings for each  test case. For  example if you want to change user and http headers for one of the tests you can set the following:
    ``headers={'Filter': true}, user='new_user'``


Grouping tests in input file into test sets
-------------------------------------------
You can group your tests according to their functionality, flows, testing purpose, and so on. To define a custom group in input file,  add a new test case before the tests that should be grouped. Fill this test case as follows: 
    ``test_name=START_GROUP: <name_of_tests_group>``
All other fields except 'run'  are not applicable and can be set as 'n/a' or  skipped. 
The 'run' value should be set if you want to run the whole group of tests in a loop or by certain conditions. See 'run' possible values above. All test case ‘run’ possible values are applicable also in scope of tests groups. 
To mark where the test group is finished add a new test case after the last test of the group and fill it as follows: 
test_name=END_GROUP:<name_of_tests_group>. Name of the test group here  must be the same as the value specified in START_GROUP . 


Parameters
----------
Parameter names should correspond to the names of test function parameters. You can put parameters names from conf/settings.conf file here as place holders.

Just put parameter name in {} brackets and it will be replaced with the relevant value during the run time. If you want to get product constants from conf/elements.conf section call it  e{param_name}.

If you have a comma separated list in conf/settings.conf you can fetch its value in a way of array indexing - {name_of_param[param_index]}.

If you want to get these listed as a string you can call it as [name_of_param].

If you are using loop in 'run' column (see below) you can concatenate loop iteration index to any of your parameters.

Here are a few examples for values of parameters column:

Get parameter 'compatibility_version' from settings
        
    ``name='Test1',version='{compatibility_version}'``
Get parameter 'storage_type_nfs' from conf/elements.conf 
        
    ``name='Test1',storage_type='e{storage_type_nfs}'`` 
Get first parameter from list of 'vm_names' from settings 
        
    ``name='{vm_names[0]}'``
Get list of 'vm_names' names as a string from settings 
        
    ``name='[vm_names]'``
Add iteration index to name (relevant when running in loop) 
        
    ``name='testVM#loop_index'``

Run Conditions
--------------
Simple condition:
    ``if(<condition>)``

Action condition:
    ``ifaction(<action_name>,<action parameters>) # test will run if action returns True``

    ``not ifaction(<action_name>,<action parameters>) # test will run if action return False``

Loop and forkfor:
Loop can be used to make several same operations. While  loop does all iterations one after another , forkfor executes them simultaneously. Both can be used with groups so the contents of the group will get executed several times. 
    ``loop(<number_of_iterations>) loop(<iterations_range>) loop({<parameter_name_to_iterate_on>})``

    ``forkfor(<number_of_iterations>) forkfor(<iterations_range>)``

    ``forkfor({<parameter_name_to_iterate_on>})``
Note that Python might not be able to create more than  600 threads, therefore forkfor(700) may fail.  In addition, executing too many  requests can lead to load problems on remote side.

'if' and 'loop' together:

    ``if(<condition>);loop(<number_of_iterations>)``

Examples: 

Simple condition:
    ``if('{compatibility_version}'=='2.3')``
    
    ``if(len({hosts})>2) # will run if number of values in ‘hosts’ parameter in configuration file is greater than 2``

Action conditions: 
    ``ifaction(activateHost,'TRUE',name='{host}')``

    ``not ifaction(activateHost,'TRUE',name='{host}')``

Loop statements
    ``loop(5) loop(5-10) loop({os_name})``

'if' and 'loop' together: 
    ``if('{compatibility_version}'=='2.3');loop(5)``

You can iterate over several parameters at once. It can be useful for an example for host installation.  If you want to install several hosts which all have different passwords, define the following parameters in the settings.conf file::

    hosts = host1,host2,host3
    password = pass1,pass2,pass3

Then in your input file put the following in the 'parameters' field: 
    ``host={host},password={password}``
And in 'run' field: 
    ``loop({host},{password})``
Your test will run for 3 times and each time the required action will be run with the hostname and password relevant to the current iteration.

Fetch Output
------------
It assumed that the function will  return additional values (besides status) in dictionary format. Specify  the key name related to the desired output value and  the parameter name of where the key will be put. The format of this value should be the following: 
    ``<fetch_output_from_key_name>-><fetch_output_to_parameter_name>``
Examples: 
    ``osName->myOsName``
You can use parameters place holders in <fetch_output_to_parameter_name> (can be useful in parallel runs) 
    ``osName->osName{index}``
Then you can use this fetched value as parameter in your further tests: 
    ``vm='MyVm',os_name=%myOsName%``
or with parameters place holders: 
    ``vm='MyVm',os_name=%osName{index}%``
or to concatenate fetched output to another string: 
    ``vm='MyVm',os_name='test' + %osName{index}%``
You can fetch several output parameters in the same manner, just separate them with commas. For example: 
    ``osName->myOsName, osType->myOsType``
If the function returns a Python list type object, it's possible to reference the individual items like this later on: 
    ``name=%out%[1]``

Test Templates
---------------
 You can find samples of test scenarios files at tests/xml_templates/ folder.