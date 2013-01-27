Quick Start
===========
If your application works via REST APIs with XML application content it's very easy to test
it with ART framework. See below the instructions for quick start of your testing.

Data Structures
---------------
In order to start working with ART you need to generate Python data structures from api.xsd file of your application.
There are 2 ways to do it.

*   First and the simpliest one is to get hard-coded version of api.xsd file and generate hard-coded version of data structures.
    It's not very generic since for any change of api.xsd you will have to regenerate the data structures again. However using
    this approach you can start testing almost immediately.

    * Create data structures module of your project under ART/art ::

        mkdir my_app/data_struct

    * Make it a Python module::

        touch my_app/__init__.py
        touch my_app/data_struct/__init__.py

    * Download api.xsd file from your application and put it at ``my_app/data_struct``

    * Run ``generateDS/generateDS.py`` to generate the data structures module::

        python generateDS.py -f  -o ../my_app/data_struct/data_structures.py --member-specs=dict ../my_app/data_struct/api.xsd

      or to redefine default namespace to empty (when working with OpenStack REST APIs for an example)::

        python generateDS.py -f  -o ../my_app/data_struct/data_structures.py --member-specs=dict -a '' ../my_app/data_struct/api.xsd

*   Second way is to implement Python functions which will download api.xsd file
    and run the above script to generate data strcutures automatically on each test run.
    This implemenation should be done in ``my_app/__init__.py``. You can find the example in ``rhevm_api/__init__.py``.

Develop the tests
-----------------

*   Create a new module which will contain the Python tests for your application::

        touch my_app/tests.py

*   Develop your testing function::

        from art.core_api.apis_utils import data_st
        from from art.rhevm_api.utils.test_utils import get_api

        ELEMENT = 'test_object'
        COLLECTION = 'tests_objects'
        util = get_api(ELEMENT, COLLECTION)

        @is_action()
        def addObject(positive, **kwargs):
        '''
        Creating some object
        '''

            majorV, minorV = kwargs.pop('version').split(".")
            objVersion = data_st.Version(major=majorV, minor=minorV)

            obj = data_st.TestObject(version=objVersion, **kwargs)

            obj, status = util.create(obj, positive)

            return status

*   Create xml interface for your test in ``/tmp/my_app_test.xml``::

        <input>
            <test_case>
                <test_name>Create Object Test</test_name>
                <test_action>addObject</test_action>
                <parameters>name='MyTestObj',version='{version}'</parameters>
                <positive>true</positive>
                <run>yes</run>
            </test_case>
        </input>


Basic Configuration
-------------------
Define your configuration file as following (set REST_CONNECTION section
according to your application definitions)::

    [RUN]
    tests_file = /tmp/my_app_test.xml
    data_struct_mod=my_app.data_struct.data_structures
    api_xsd = my_app/data_struct/api.xsd

    [REST_CONNECTION]
    scheme = <http|https>
    host = <app_server>
    port = <app_port>
    user = <app_user>
    password = <app_password>
    user_domain = <app_domain>

    [PARAMETERS]
    version = 3.0

Run
---
Run the test from ART/art with your configuration file::

    python run.py -conf=<path_to_your_conf> -log=/tmp/app_log.log


Analyse the results
-------------------
Check file ``art/results/results.xml`` for the test results or ``/tmp/app_log.log`` for more details.


