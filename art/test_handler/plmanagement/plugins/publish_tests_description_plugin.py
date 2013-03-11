"""
-------------------------
Publish tests description
-------------------------

This plugin publishes tests description.


Configuration File Options
--------------------------
    | **[PUBLISH_TEST_DESC]**
    | **url**  url to publisher
    | **enabled**  enable plugin
    | **[[ATTRIBUTES]]**  in this section define attributes of test element
         which should be included in report.
         format is 'test_elm[,test_elm]:name:target_type' where the test_elm
         is one from (*, case, group, suite), the name is name of variable
         of related element, and target_type is one of (origin, str, set, list)
    | **[[CONFIG_VARS]]**  in this section define all config values which
         should be included in report.

"""

import os
import urllib2
import json
from contextlib import closing
from lxml import etree
from art.test_handler.plmanagement import Component, implements, get_logger,\
     PluginError
from art.test_handler.plmanagement.interfaces.application import\
     IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
              IConfigValidation
from art.test_handler.plmanagement.interfaces.tests_listener import\
     ITestSuiteHandler, ITestGroupHandler, ITestCaseHandler
from art.test_handler import find_test_file


logger = get_logger('publish_test_desc')

CONF_SECTION = "PUBLISH_TEST_DESC"
URL = 'url'
DEFAULT_URL = "http://jenkins.qa.lab.tlv.redhat.com/cgi-bin/test_info.put"
CONFIG_VARS_SEC = 'CONFIG_VARS'
ATTRIBUTES_SECTION = 'ATTRIBUTES'
ENABLED = 'enabled'

TEST_NAME = "test_name"
TEST_DESC = "test_desc"
CONFIG_VARS = "config_vars"
TEST_ELM_VARS = "test_elm_vars"
CONFIG_NAME = "config_name"

CASE_NAME = 'case'
GROUP_NAME = 'group'
SUITE_NAME = 'suite'
ALL_NAME = '*'


class Type(object):
    """
    Class encapsulates target type, which will be published
    """
    def __init__(self):
        super(Type, self).__init__()
        self.val = None

    def __str__(self):
        return str(self.val)

    def new_value(self, val):
        raise NotImplementedError()

    def final_value(self):
        return self.val


class OriginType(Type):
    """
    Just copy value
    """

    def new_value(self, val):
        self.val = val
        return self.val


class SetType(Type):
    """
    Collects values, and reports only one occurance per each value
    """
    def __init__(self):
        super(SetType, self).__init__()
        self.val = set()

    def new_value(self, val):
        self.val.add(val)
        return self.val

    def final_value(self):
        return list(self.val) # set is not serializable

class ListType(Type):
    """
    Collects and reports everything what was got from test_elemet
    """
    def __init__(self):
        super(ListType, self).__init__()
        self.val = list()

    def new_value(self, val):
        self.val.append(val)
        return self.val


class StringType(Type):
    """
    Same as origin, but this can be helpfull when the variable implements
    __str__ method and we want get this value.
    """
    def __init__(self):
        super(StringType, self).__init__()
        self.val = str()

    def new_value(self, val):
        self.val = str(val)
        return self.val


class AttributeDispatcher(object):
    """
    Responsible for getting value from test element.
    """
    types = {
            'set': SetType,
            'list': ListType,
            'str': StringType,
            'origin': OriginType
            # we can add 'count', 'hostogram' or whatever else
            }

    def __init__(self, type_, var_name, target_type):
        super(AttributeDispatcher, self).__init__()
        self.type_ = set(type_)
        self.name = var_name
        self.target_type = target_type
        self.tt = self.types[target_type]()

    @property
    def value(self):
        return self.tt.final_value()

    def __get_var(self, obj):
        var = getattr(obj, self.name, None)
        if var is None:
            return var
        logger.debug("Got variable from tes_element %s: %s=%s",
                                            obj, self.name, var)
        return self.tt.new_value(var)

    def test_elm_var(self, obj, type_):
        if not self.type_ & set((ALL_NAME, type_)):
            return None
        return self.__get_var(obj)

    def __str__(self):
        return "%s:%s:%s" % (','.join(self.type_), self.name, self.target_type)

    @classmethod
    def from_string(cls, value):
        values = value.split(":")
        if len(values) != 3:
            raise ValueError("expected 'elm_type:var_name' got: %s" % value)
        type_, var_name, ttype = set(values[0].split(',')), values[1], values[2]
        accepted_options = set((CASE_NAME, GROUP_NAME, SUITE_NAME))
        if len(type_ | accepted_options) > len(accepted_options):
            ValueError("expected %s, got %s" % (accepted_options, type_))
        return AttributeDispatcher(type_, var_name, ttype)


class PulishTestDesc(Component):
    """
    This plugin publishes tests description.
    """
    implements(IConfigurable, IPackaging, IConfigValidation,
            ITestSuiteHandler, ITestGroupHandler, ITestCaseHandler)

    name = "Test description publisher"

    def __init__(self, *args, **kwargs):
        super(PulishTestDesc, self).__init__(*args, **kwargs)
        self.test_elm_attrs = {}
        self.data = {}
        self.resources = {}
        self.dispatchers = {}

    @classmethod
    def add_options(cls, parser):
        pass # no cli options

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        config = conf.get(CONF_SECTION)
        self.data[CONFIG_NAME] = os.path.basename(getattr(conf, 'filename', "unknown"))
        self.data[TEST_NAME] = self.test_name
        self.url = config[URL]
        resources = config.get(CONFIG_VARS_SEC, {})

        for key, path in resources.items():
            val = self.__get_var(conf, path)
            if val is None:
                continue
            logger.debug("Got value from config file: %s=%s", key, val)
            self.resources[key] = val

        dispatchers = config.get(ATTRIBUTES_SECTION, {})
        for key in dispatchers:
            self.dispatchers[key] = dispatchers[key]

    def __get_var(self, conf, path):
        path = path.split('.')
        data = conf
        for sec in path[:-1]:
            data = data.get(sec, {})
        return data.get(path[-1], None)

    def __call_dipatchers(self, obj, type_):
        for dis in self.dispatchers.values():
            dis.test_elm_var(obj, type_)

    @property
    def test_name(self):
        return os.environ.get('JOB_NAME', "unknown")

    def pre_test_suite(self, suite):
        self.data[TEST_DESC] = suite.description # problem in multiple suites
        self.__call_dipatchers(suite, 'suite')

    def post_test_suite(self, suite):
        self.data[CONFIG_VARS] = self.resources
        self.data[TEST_ELM_VARS] = dict((x, y.value)
                for x,y in self.dispatchers.items() if y.value is not None)
        self.publish_data(self.data)

    def pre_test_case(self, test_case):
        self.__call_dipatchers(test_case, 'case')

    def post_test_case(self, test_case):
        pass

    def test_case_skipped(self, test_case):
        pass

    def pre_test_group(self, test_group):
        self.__call_dipatchers(test_group, 'group')

    def post_test_group(self, test_group):
        pass

    def test_group_skipped(self, test_group):
        pass

    def publish_data(self, data):
        logger.debug("publishing collected data: %s", data)
        opener = urllib2.build_opener(urllib2.HTTPHandler)

        request = urllib2.Request(self.url, data=json.dumps(data))

        request.add_header('Content-Type', 'application/json')
        request.get_method = lambda: 'PUT'

        try:
            with closing(opener.open(request)):
                pass # don't care about answer
        except Exception as ex:
            logger.error("Publishing description failed: %s", ex)

    @classmethod
    def is_enabled(cls, params, conf):
        return conf[CONF_SECTION].as_bool(ENABLED)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(" ", '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Plugin for ART which publish test description'
        params['long_description'] = cls.__doc__
        params['requires'] = ['python-lxml']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'\
                'publish_tests_description_plugin']

    def config_spec(self, spec, val_funcs):
        val_funcs['test_attribute'] = AttributeDispatcher.from_string
        section_spec = spec.setdefault(CONF_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=False)'
        section_spec[URL] = 'string(default="%s")' % DEFAULT_URL
        resources = section_spec.setdefault(CONFIG_VARS_SEC, {})
        resources['__many__'] = "string()"
        attributes = section_spec.setdefault(ATTRIBUTES_SECTION, {})
        attributes['__many__'] = "test_attribute()"
