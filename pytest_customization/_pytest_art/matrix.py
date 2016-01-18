"""
This module implements our matrix multiplication.

TEST x ENGINE x STORAGE
"""
import logging
import inspect
from _pytest.python import PyCollector as Collector
from unittest import TestCase
from art.test_handler import settings


__all__ = [
    "pytest_artconf_ready",
]


logger = logging.getLogger("pytest.art.matrix")


class MatrixCollector(Collector):
    def __init__(self, name, parent, apis, storages):
        super(MatrixCollector, self).__init__(name, parent)
        self._apis = apis
        self._storages = storages

    def collect(self):
        obj = self.parent.module.__dict__[self.name]
        objs = self._generate_api_and_storage_matrix(obj)
        for new_obj in objs:
            yield self.makeitem(new_obj.__name__, new_obj)

    def makeitem(self, name, obj):
        return self.ihook.pytest_pycollect_makeitem(
            collector=self.parent, name=name, obj=obj,
        )

    def _create_test_class_obj(self, obj, new_name, api, storage=None):
        '''
        Description: this function multiplies test classes
        :param obj: The class to be multiplied
        :type obj: object
        :param new_name: name to give for the new class
        :type new_name: str
        :param api: api to run with
        :type api: str
        :param storage: storage to use
        :type storage: str
        :return: test class
        :rtype object
        '''
        new_dict = dict(obj.__dict__)
        new_dict.update({'api': api, 'storage': storage, '__gen': True})
        bases = [obj] + list(obj.__bases__)

        new_obj = type(new_name, tuple(bases), new_dict)

        self.parent.module.__dict__[new_name] = new_obj

        return new_obj

    def _generate_api_and_storage_matrix(self, obj):
        objs = []

        if not self._storages:
            matrix = [{"api": x} for x in self._apis]
        else:
            matrix = [
                {"api": x, "storage": y}
                for x in self._apis for y in self._storages
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
            objs.append(new_obj)

        return objs

    def _generate_test_class_name(self, name):
        return '_'.join(name)


class ARTMatrix(object):
    """
    Implements test generator for ART library based on STORAGE x API
    """
    def __init__(self):
        super(ARTMatrix, self).__init__()
        self._storages_defined_in_conf = None
        self._apis_defined_in_conf = None
        self.not_applicable = 'N/A'
        self._actual_api = None
        self._system_api = None

    @property
    def storages_defined_in_conf(self):
        if self._storages_defined_in_conf is None:
            try:
                self._storages_defined_in_conf = set(settings.opts['storages'])
            except KeyError:
                pass
        return self._storages_defined_in_conf

    @property
    def apis_defined_in_conf(self):
        if self._apis_defined_in_conf is None:
            try:
                self._apis_defined_in_conf = set(settings.opts['engines'])
            except KeyError:
                pass
        return self._apis_defined_in_conf

    def pytest_pycollect_makeitem(self, collector, name, obj):
        if not inspect.isclass(obj):
            return
        if not issubclass(obj, TestCase):
            return
        if isinstance(collector, MatrixCollector):
            return
        if getattr(obj, '__gen', False):
            return

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

        # Return new collector
        return MatrixCollector(name, collector, apis_to_use, storages_to_use)

    def pytest_runtest_setup(self, item):
        api = getattr(item.parent.obj, 'api', None)
        if not isinstance(api, basestring):
            return
        if self._system_api is None:
            self._system_api = settings.opts['engine']
        if settings.opts['engine'] != api:
            settings.opts['engine'] = api
            logger.info("The API backend switched to %s", api)

        storage = getattr(item.parent.obj, 'storage', None)
        if not isinstance(storage, basestring):
            return
        if settings.opts['storage_type'] != storage:
            settings.opts['storage_type'] = storage
            logger.info("The storage type switched to %s", storage)

    def pytest_runtest_teardown(self, item, nextitem):
        if self._system_api is None:
            self._system_api = settings.opts['engine']
        elif settings.opts['engine'] != self._system_api:
            settings.opts['engine'] = self._system_api
            logger.info(
                "The API backend switched to %s", self._system_api,
            )

        if settings.opts['storage_type']:
            settings.opts['storage_type'] = None
            logger.info("The storage type reset to None")


def pytest_artconf_ready(config):
    """
    Register ARTMatrix plugin in case multiplier is enabled.
    """
    enabled = settings.ART_CONFIG.get(
        'UNITTEST'
    ).as_bool('nose_test_multiplier_enabled')
    if enabled:
        config.pluginmanager.register(ARTMatrix())
