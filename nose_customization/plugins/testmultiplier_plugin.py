"""
This plugin when enbaled multiplies class according two parameters:
    1. apis: rest, sdk, java, cli
    2. storages: iscsi, nfs

    apis = opts['engines'] = sdk,rest,cli,java by default
    storages = opts['storages'] = list() by default

    storages is emtpy list because it is not necessary to run tests
    on different storage types.
    Storage tests should however to run in all types, therefore storages
    attribute is set to set([iscsi, nfs etc]) in the StorageTestBase Class in
    unittest_lib/commonn.py

    Examples:
    =======
    (1) Matrix will be: (sdk, nfs), (java, nfs), (cli, nfs)
    ./art/run.py -conf <path/to/conf/file> --log <path/to/log/file>
    -DPARAMETERS.vds=<hostname>
    -DRUN.tests_file=unittest://tests:rhevmtests.system.test_example_1.test_1772
    -DRUN.storages=nfs -DRUN.engines=sdk,java,cli
    --with-multiplier

    Note that we do intersetction with whatever in apis attribute in the
    TeamBaseClass, for example CLI is not supported for network so it won't
    be part of the matrix.

    (2) Matrix will be: engines x storages
    ./art/run.py -conf <path/to/conf/file> --log <path/to/log/file>
    -DPARAMETERS.vds=<hostname>
    -DRUN.tests_file=unittest://tests:rhevmtests.system.test_example_1.test_1772
    --with-multiplier

    Note that it will multiplies whatever in opts['engines'] and whatever in
    storages attribute in TeamBaseClass
"""
import logging
from nose.util import transplant_class
from nose.plugins import Plugin as NosePlugin
from art.test_handler.settings import opts
from art.test_handler.plmanagement import get_logger

log = logging.getLogger('nose.plugins.testmultiplier')
art_log = get_logger("testmultiplier")


class TestMultiplierPlugin(NosePlugin):
    '''
    http://nose.readthedocs.org/en/latest/plugins/interface.html
    '''
    name = 'testmultiplier'

    def configure(self, options, conf):
        '''
        Initial plugin settings
        '''
        super(TestMultiplierPlugin, self).configure(options, conf)
        log.info('Configuring test multiplier')

        self.enabled = True if options.enable_plugin_testmultiplier else False

        self.storages_defined_in_conf = set(opts['storages'])
        self.apis_defined_in_conf = set(opts['engines'])
        self.not_applicable = 'N/A'

    def prepareTestLoader(self, loader):
        '''
          we need to use configured loader in order to have plugins working
        '''
        self.loader = loader

    def makeTest(self, obj, parent):
        '''
        Description: modify and multiply class to be run.
        Here we tweaj each instant of class with correct API and storage
        depending on the storages*apis
        '''
        if parent and obj.__module__ != parent.__name__:
            obj = transplant_class(obj, parent.__name__)

        # apis defined in TestClass
        apis = getattr(obj, 'apis', set([]))
        # storages defined in TestClass
        storages = getattr(obj, 'storages', set([]))

        if self.not_applicable in storages:
            # in case TestCase doesn't care about storage type
            storages_to_use = None
        elif not storages:
            # in case storages is None (means: TestCase can run on any storage)
            storages_to_use = self.storages_defined_in_conf
        elif self.storages_defined_in_conf:
            # TestCase can run on some storage types
            storages_to_use = storages & self.storages_defined_in_conf
        else:
            # No storages provided via conf so use whatever set in TestCase
            storages_to_use = storages

        # intersection with apis in test class and opts['engines']
        apis_to_use = set(apis) & self.apis_defined_in_conf

        objs = self._generate_api_and_storage_matrix(
            obj, apis_to_use, storages_to_use
        )

        return self.loader.suiteClass(objs)

    def _create_test_class_obj(self, obj, new_name, api, storage=None):
        '''
        Description: this function multiplies test classes
        :param obj: The class to be multiplied
        :type obj: object
        :param new_name: name to give for the new class
        :type new_name: str
        :param api: spi to run with
        :type api: str
        :param storage: storage to use
        :type storage: str
        :return: test class
        :rtype object
        '''

        new_dict = dict(obj.__dict__)
        new_dict.update({'api': api, 'storage': storage})
        bases = [obj] + list(obj.__bases__)

        new_obj = type(new_name, tuple(bases), new_dict)

        return new_obj

    def _generate_api_and_storage_matrix(self, obj, apis, storages=None):
        objs = []

        if not storages:
            matrix = [{"api": x} for x in apis]
        else:
            matrix = [
                {"api": x, "storage": y} for x in apis for y in storages
            ]

        for option in matrix:
            class_name_to_generate = [obj.__name__]
            api = option["api"]
            class_name_to_generate.append(api.upper())
            storage = option["storage"] if "storage" in option else None
            if storage:
                class_name_to_generate.append(storage.upper())

            new_name = self._generate_test_class_name(class_name_to_generate)

            new_obj = self._create_test_class_obj(obj, new_name, api, storage)
            objs.append(self.loader.loadTestsFromTestCase(new_obj))

        return objs

    def _generate_test_class_name(self, name):
        log.info('creating  %s', '_'.join(name))

        return '_'.join(name)
