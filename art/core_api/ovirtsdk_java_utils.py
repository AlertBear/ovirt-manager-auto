#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import time
import logging
import types
from functools import wraps
import threading
import thread
from decimal import Decimal

from art.core_api import validator, measure_time
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.data_struct.data_structures import GDSClassesMapping
from art.core_api.apis_exceptions import APIException, APILoginError
from art.core_api.apis_utils import APIUtil, NEGATIVE_CODES, api_error,\
    ApiOperation

import java_sdk
import java
import javax.xml.datatype

logger = logging.getLogger(__name__)
addlock = threading.Lock()

# starting Java VM
jvm = java_sdk.initVM(java_sdk.CLASSPATH)

import org.ovirt.engine.sdk

# default timeout
DEF_TIMEOUT = 900
# default sleep
DEF_SLEEP = 10
STYLE_EXCEPTIONS_JAVA_COLLECTIONS = {
    'vms': 'vMs',
    'vmpools': 'vmPools',
    'snapshots': 'VMSnapshots'
}
JAVA_IGNORE_LIST = ['getClass', 'getLinks']
PYTHON_IGNORE_LIST = ['get_link']
STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS = {
    'get_valueOf_': 'isValue',
    'get_power_management': 'getPowerManagers',
    'get_host_nic': 'getSlaves',
    'get_property': 'getProperties',
    'get_model': 'getWatchdogModels',
    'get_action': 'getWatchdogActions'
}
ACTION_EXCEPTIONS_PYTHON_JAVA_METHODS = {
    'VM': {'export': 'exportVm'},
    'Template': {'export': 'exportTemplate'},
    'StorageDomainVM': {'import': 'importVm'},
    'StorageDomainTemplate': {'import': 'importTemplate'},
    'StorageDomainImage': {'import': 'importImage'}
}


def jvm_thread_care(func):
    """
    Description: This closure will be used as decorator for critical section
    Author: imeerovi
    Parameters:
        *  func - function that runs critical section code
    Returns: returns apifunc wrapper for func
    """
    @wraps(func)
    def apifunc(*args, **kwargs):
        """
        Description: this code will run when func will be called
        Author: imeerovi
        Parameters:
            *  *args, **kwargs - parameters that should be passed to func
        Returns: result of func run
        """
        thread_id = 0
        with addlock:
            if not jvm.isCurrentThreadAttached():
                jvm.attachCurrentThread()
                thread_id = thread.get_ident()
        result = func(*args, **kwargs)
        if thread_id == thread.get_ident():
            jvm.detachCurrentThread()
        return result

    return apifunc


def underscore_to_camelcase(name):
    """
    Description: function that converts python coding style to java coding
                 style
    Author: imeerovi
    Parameters:
        *  name - under_score style name that should be converted
    Returns: returns camelCase name
    """
    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize
    c = camelcase()
    return "".join(c.next()(x) if x else '_' for x in name.split("_"))


def get_object_name(entity):
    """
    Description: function that gets object name from entity
    Author: imeerovi
    Parameters:
        *  entity - SDK or data_structures.py entity
    Returns: returns object name
    """
    if isinstance(entity, JavaTranslator):
        return entity.java_object.__class__.__name__
    return entity.__class__.__name__


def get_collection_name_from_entity(entity):
    """
    Description: function that gets collection name from entity
    Author: imeerovi
    Parameters:
        *  entity - SDK or data_structures.py entity
    Returns: returns collection name
    """
    entity_name = get_object_name(entity)
    collection_name = "".join([entity_name[0].lower(), entity_name[1:], 's'])
    return collection_name


def get_object_name_from_ds(object_name):
    """
    Description: function that gets relevant data_structures.py object name
    Author: imeerovi
    Parameters:
        *  object_name - rest name of object
    Returns: returns SDK name of object
    """
    ds_key = filter(lambda x: x.lower() == object_name.lower(),
                    GDSClassesMapping.keys())[0]
    return GDSClassesMapping[ds_key].__name__


def get_getters_and_setters(python_object=None, java_object=None):
    """
    Description: function that gets getters and setters from python
                 or/and java objects
    Author: imeerovi
    Parameters:
        * python_object - generate_ds.py object
        * java_object - java SDK object
    Returns: returns tuple with getters and setters
    """
    python_getters = None
    python_setters = None
    java_getters = None
    java_setters = None
    if python_object:
        # getting python methods
        python_methods = filter(lambda method: not method.startswith('__')
                                and not method.endswith('_')
                                and not method in PYTHON_IGNORE_LIST,
                                dir(python_object))
        python_getters = filter(lambda method: 'get' in method
                                and method.find('get') == 0, python_methods)
        python_setters = filter(lambda method: 'set' in method
                                and method.find('set') == 0, python_methods)
    if java_object:
        # getting java methods
        java_methods = filter(lambda method: not method.startswith('__')
                              and not method.endswith('_')
                              and not method in JAVA_IGNORE_LIST,
                              dir(java_object))
        java_setters = filter(lambda method: 'set' in method
                              and method.find('set') == 0, java_methods)
        java_getters = filter(lambda method: ('get' in method
                              and method.find('get') == 0) or
                              ('is' in method and method.find('is') == 0),
                              java_methods)

    return (python_getters, python_setters, java_getters, java_setters)


def python_primitives_converter(java_datatype, data):
    """
    Description: function that converts python primitives to java ones
    Author: imeerovi
    Parameters:
        * java_datatype - java primitive datatype
        * data - python primitive
    Returns: returns java primitive
    """
    if java_datatype in 'java.lang.String':
        if not isinstance(data, str):
            logger.warning("%s should be str but it is %s",
                           data, type(data))
            data = str(data)

    elif java_datatype in 'java.lang.Boolean':
        if not isinstance(data, bool):
            logger.warning("%s should be boolean but it is %s",
                           data, type(data))
            data = True if data == 'true' else False

    elif java_datatype in 'java.lang.Integer':
        if not isinstance(data, int):
            logger.warning("%s should be int but it is %s",
                           data, type(data))
            data = int(data, 10)

    elif java_datatype in 'java.lang.long':
        if not isinstance(data, long):
            logger.warning("%s should be long but it is %s",
                           data, type(data))
            data = long(data)

    return data


def get_java_setters_datatypes(java_object):
    """
    Description: function that creates setter: expected datatype dictionary
                 for java object. we need it in order to know what to pass to
                 setter
    Author: imeerovi
    Parameters:
        * java_object - java SDK object
    Returns:  setter: expected datatype dictionary
    """
    # getting java methods signatures
    java_setters_signatures = \
        filter(lambda x: 'set' in x,
               [str(m) for m in java_object.getClass().getMethods()])

    # creating dictionary of setter:type, like 'setAction': 'java.lang.Boolean'
    java_setters_datatypes_dict = \
        dict([(k.split('.')[-1], v.strip(')'))
              for k, v in map(lambda x: x.split('('),
                              java_setters_signatures)])
    return java_setters_datatypes_dict


def get_java_object_name_by_getter_name(python_getter):
    """
    Description: function that gets java object name from python getter name
    Author: imeerovi
    Parameters:
        * python_getter - python getter
    Returns: java entity name
    """
    # we need to add relevant object first so we find its name
    suggested_name = ''.join(python_getter.split('get_')[1:])
    # looking for it
    try:
        ds_name = get_object_name_from_ds(suggested_name)
        # The XJC compiler used to generate Java code eliminates underscores
        # from class names, so we need to eliminate them here as well
        return ds_name.replace('_', '')
    except Exception:
        err_msg = "Entity '%s' is missing in \
org.ovirt.engine.sdk.entities %s" % (suggested_name,
                                     dir(org.ovirt.engine.sdk.entities))
        logger.error(err_msg)
        raise APIException(err_msg)


def translator_to_java(python_object, java_object):
    """
    Description: translator to java from python
    Author: imeerovi
    Parameters:
        * python_object - generate_ds.py object to translate
        * java_object - java SDK object that will be filled up with
          data from python object
    """
    # getting getters and setters
    python_getters, _, java_getters, java_setters = get_getters_and_setters(
        python_object, java_object
    )

    # creating lowercase to java methods mapping of java_setters
    java_setters = dict([(setter.lower(), setter) for setter in java_setters])

    # creating lowercase to java methods mapping of java_getters
    java_getters = dict([(getter.lower(), getter) for getter in java_getters])

    # creating dictionary of setter:type, like 'setAction': 'java.lang.Boolean'
    java_setters_datatypes_dict = get_java_setters_datatypes(java_object)

    # translate
    for getter in python_getters:

        # getting data
        data = getattr(python_object, getter)()

        # omitting empty data
        if data is None or (isinstance(data, list) and not len(data)):
            continue

        # finding needed java getter and setter
        # sometimes there are mismatches and typos in api.xsd so in one place
        # name is correct and it is not correct in another
        if getter in STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS and hasattr(
            java_object, STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS[getter]
        ):
            java_getter = STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS[getter]
        else:
            lower_case_getter = getter.lower().replace('_', '')
            potential_lower_case_getter_names = [
                lower_case_getter,
                "%ss" % lower_case_getter,
                lower_case_getter.replace('get', 'is', 1)
            ]

            for getter_name in potential_lower_case_getter_names:
                if getter_name in java_getters:
                    java_getter = java_getters[getter_name]
                    break
                else:
                    logger.debug(
                        "translator to java from python: %s:'%s' of '%s'"
                        " doesn't exists in: %s trying another getter",
                        java_object, getter_name, get_object_name(java_object),
                        java_getters
                    )
            else:
                logger.debug(
                    "translator to java from python: %s: "
                    "No java getter found for '%s' of '%s'",
                    java_object, getter, python_object
                )
                continue
        for prefix in ('is', 'get'):
            if java_getter.lower().startswith(prefix):
                setter_name = java_getter.lower().replace(prefix, 'set', 1)
                java_setter = java_setters.get(setter_name, None)
                if java_setter:
                    break
                logger.debug(
                    "translator to java from python: %s: '%s' of"
                    " '%s' doesn't exists in:\n%s",
                    java_object, setter_name,
                    get_object_name(java_object), java_setters
                )

        if java_setter is None:
            continue

        logger.debug(
            "translator to java from python: %s: "
            "Found Java getter %s that matches Python getter %s",
            java_object, java_getter, getter
        )
        logger.debug(
            "translator to java from python: %s:Found expected Java setter %s",
            java_object, java_setter
        )

        # checking data
        # this way i'm finding relevant objects also when
        # list of objects is passed
        if 'brokers' in str(data):
            logger.warning(
                "broker case - shouldn't get there,"
                "if we are here it means python SDK is used in parallel"
            )
        elif 'object' in str(data):
            # in this case no recursion needed, just pass internal
            # java_object to Java SDK object
            if 'JavaTranslator' in str(data):
                if isinstance(data, JavaTranslator):
                    getattr(java_object, java_setter)(data.java_object)
                # list case
                elif isinstance(data, list):
                    java_list_already_set = False
                    # cleaning existing data in java object if exists
                    if getattr(java_object, java_getter)():
                        getattr(java_object, java_getter)().clear()
                        java_list_already_set = True
                    container = []
                    # taking care of mixed list (python,
                    # javatranslator objects)
                    # TODO: redesign all this stuff
                    for entity in data:
                        if isinstance(entity, JavaTranslator):
                            container.append(entity.java_object)
                        else:
                            # we need to add relevant object first
                            real_object_name = \
                                get_java_object_name_by_getter_name(getter)
                            # creating empty object
                            java_entity = getattr(
                                org.ovirt.engine.sdk.entities, real_object_name
                            )()
                            # filling it with data from python
                            translator_to_java(entity, java_entity)
                            # adding it to container
                            container.append(java_entity)
                    # adding to existing empty java container
                    if java_list_already_set:
                        for obj in container:
                            getattr(java_object, java_getter)().add(obj)
                    else:
                        getattr(java_object, java_setter)(container)
                continue

            # we need to add relevant object first so we find its name
            real_object_name = get_java_object_name_by_getter_name(getter)

            # ready to dig one layer in
            if isinstance(data, list):
                java_list_already_set = False
                # cleaning existing data in java object if exists
                if getattr(java_object, java_getter)():
                    getattr(java_object, java_getter)().clear()
                    java_list_already_set = True
                container = []
                for python_entity in data:
                    # creating empty object
                    java_entity = getattr(
                        org.ovirt.engine.sdk.entities, real_object_name
                    )()
                    # filling it with data from python
                    translator_to_java(python_entity, java_entity)
                    # adding it to container
                    container.append(java_entity)
                # setting it
                # adding to existing empty java container
                if java_list_already_set:
                    for obj in container:
                        getattr(java_object, java_getter)().add(obj)
                else:
                    getattr(java_object, java_setter)(container)
            else:
                # creating empty object
                java_entity = getattr(
                    org.ovirt.engine.sdk.entities, real_object_name
                )()
                # adding it
                getattr(java_object, java_setter)(java_entity)

                # getting back for casting check
                java_object_to_fill = getattr(java_object, java_getter)()

                # checking if casting OK (Permits issue)
                if 'Object' in str(type(java_object_to_fill)):
                    java_object_to_fill = getattr(
                        org.ovirt.engine.sdk.entities, real_object_name
                    ).cast_(java_object_to_fill)

                translator_to_java(
                    getattr(python_object, getter)(), java_object_to_fill
                )
        # primitives and lists of primitives cases
        else:
            if isinstance(data, list):
                # will work ok with string, bool, int
                # TODO: to add long and more complex datatypes support if
                # needed
                for item in data:
                    logger.debug(
                        'translator to java from python: %s: list case,'
                        ' Setting %s().add(%s)',
                        java_object, getattr(java_object, java_getter), item
                    )
                    getattr(java_object, java_getter)().add(item)
            else:
                java_datatype = java_setters_datatypes_dict[java_setter]
                java_data = python_primitives_converter(java_datatype, data)
                logger.debug(
                    'translator to java from python: %s: Setting %s with %s',
                    java_object, getattr(java_object, java_setter), java_data
                )
                getattr(java_object, java_setter)(java_data)


class JavaTranslator(object):
    """
    Description: Python interface of Java SDK object
    Author: imeerovi
    Parameters:
        * java_object - java SDK object
    """
    _special_methods = ['list', 'add']

    def __init__(self, java_object):
        self._refs_dict = {}
        self.java_object = java_object

        _, _, getters, setters = \
            get_getters_and_setters(java_object=self.java_object)
        java_object_methods = getters + setters
        # setting references to java_object methods
        [self.referense_maker(method) for method in java_object_methods]
        # for rare case when test will do set on java object instead of
        # creating new object and than do update (translator_to_java path)
        self._java_setters_datatypes_dict = \
            get_java_setters_datatypes(java_object)

    @jvm_thread_care
    def __getattr__(self, name):
        """
        Description: method that gets relevant java SDK method by python method
                     name For now it takes care of getters only
        Author: imeerovi
        Parameters:
        * name - python method name
        Returns: relevant java SDK method or data in case of trying of direct
                 data access
        """
        run_func_call = False
        # check if it is special method like list()
        if name in self._special_methods:
            return getattr(self.java_object, name)

        if not name.startswith('set'):
            if not name.startswith('get'):
                # if we didn't got getter so lets prepare it and
                # get what user expects
                lower_case_name = name.lower()
                lower_case_getter_name = "get%s" % lower_case_name
                lower_case_getter_name = \
                    lower_case_getter_name.replace('_', '')
                run_func_call = True
            else:
                # sometimes there are mismatches and typos in api.xsd so in one
                # place name is correct and it is not correct in another
                if name in STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS and \
                    hasattr(self.java_object,
                            STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS[name]):
                    return self.python_decorator(
                        getattr(self.java_object,
                                STYLE_EXCEPTIONS_PYTHON_JAVA_METHODS[name]))

                lower_case_getter_name = name.replace('_', '').lower()

            # potential getters
            potential_getter_names = \
                [lower_case_getter_name, "%ss" % lower_case_getter_name,
                 lower_case_getter_name.replace('get', 'is', 1),
                 'get%s%s' % (get_object_name(self.java_object).lower(), name)]
            for getter_name in potential_getter_names:
                try:
                    getter = \
                        self.python_decorator(self._refs_dict[getter_name])
                    logger.debug("JavaTranslator: %s: getter %s found for %s",
                                 self.java_object, getter, name)
                    break
                except KeyError:
                    logger.debug("JavaTranslator: %s is not method of %s, "
                                 "trying another getter", getter_name,
                                 self.java_object)
            # ok, we passed over all options and didn't find needed getter
            else:
                # in case of direct access try by user lets try to do it
                if run_func_call:
                    logger.debug("JavaTranslator: %s: "
                                 "No getter for %s, trying access it directly",
                                 self.java_object, name)
                    getter = \
                        self.python_decorator(getattr(self.java_object, name))
                else:
                    raise AttributeError("JavaTranslator: %s: "
                                         "No suitable getter for %s in %s" %
                                         (self.java_object, name,
                                          str(potential_getter_names)))

            # in this case I need to call getter
            if run_func_call:
                return getter()

            return getter

        else:
            try:
                setter_name = self._refs_dict[name.replace('_', '').lower()]
                logger.debug("JavaTranslator: Setter %s is a method of %s",
                             setter_name, self.java_object)
            except KeyError:
                    logger.debug("JavaTranslator: %s is not method of %s",
                                 setter_name, self.java_object)
                    return object.__getattribute__(self, name)

            setter = self.python_decorator(setter_name)
            return setter

    def referense_maker(self, method):
        """
        Description: method that prepares reference for java SDK member class
                     getter or setter. This way SDK can access needed
                     methods of java SDK member via JavaTranslator object.
                     It is important since SDK shouldn't be aware of
                     JavaTranslator. For now it takes care of getters only
        Author: imeerovi
        Parameters:
        * method - java SDK method name
        """
        ref = getattr(self.java_object, method)
        # creating references for java_object methods
        setattr(self, method, ref)
        # creating lowercase dict of references for java_object methods
        self._refs_dict[method.lower()] = ref

    def python_decorator(self, java_func):
        """
        Description: This decorator will be used in order to wrap java getter
                     (and setter in future)
        Author: imeerovi
        Parameters:
        * java_func - java SDK method
        Return: returns wrapper
        """

        @wraps(java_func)
        def wrapper(*args, **kwargs):
            """
            Description: wrapper of java getter it convert its results to
                         python or return JavaTranslator object/list if getter
                         returns entity/collection
            Author: imeerovi
            Parameters:
            * *args, **kwargs - java getter parameters
            Return: returns wrapper results in python way or returns
                    JavaTranslator object/list if getter returns
                    entity/collection
            """
#java_func.__class__
#<type 'builtin_function_or_method'>
            # getter path
            if not java_func.__name__.lower().startswith('set'):
                data = None
                # getting data
                if isinstance(java_func, types.BuiltinMethodType):
                    data = java_func(*args, **kwargs)
                else:
                    data = java_func

                logger.debug("JavaTranslator: %s returns %s (before"
                             " converting to python datatype)", java_func,
                             data)

                # taking care about SDK objects
                try:
                    if 'decorators' in str(data) or 'entities' in str(data) \
                            or 'JavaTranslator' in str(data):
                        # list case (collection)
                        if isinstance(data, java.util.List) or \
                                isinstance(data, list):
                            return [JavaTranslator(entity)
                                    if not isinstance(entity, JavaTranslator)
                                    else entity.java_object for entity in data]
                        # single object
                        if isinstance(data, JavaTranslator):
                            return JavaTranslator(data.java_object)
                        return JavaTranslator(data)
                except UnicodeEncodeError:
                    pass

                # primitives and lists of primitives
                #list
                if isinstance(data, java.util.List):
                    # consider data conversion inside list
                    return [self.java_datatypes_converter(d) for d in data]
                return self.java_datatypes_converter(data)
            # setter path
            else:
                param_to_set = args[0]
                # taking care about data_structures.py or JavaTranslator
                # objects
                if 'object' in str(param_to_set) or \
                        'JavaTranslator' in str(param_to_set):
                    # single object
                    if not isinstance(param_to_set, list):
                        if isinstance(param_to_set, JavaTranslator):
                            java_func(param_to_set.java_object)
                        else:
                            # getting entity name
                            entity_name = get_object_name(param_to_set)
                            # translating to java
                            java_entity = \
                                getattr(org.ovirt.engine.sdk.entities,
                                        entity_name)()
                            translator_to_java(param_to_set, java_entity)
                            # setting
                            java_func(java_entity)
                    # TODO: to take care on collection case
                    else:
                        logger.error("JavaTranslator: Collection setting is"
                                     " not supported yet")
                # primitive case
                else:
                    logger.debug("Setting with setter: %s, data: %s",
                                 java_func, args)
                    java_datatype = \
                        self._java_setters_datatypes_dict[java_func.__name__]
                    java_primitive = \
                        python_primitives_converter(java_datatype,
                                                    param_to_set)
                    java_func(java_primitive)

        return jvm_thread_care(wrapper)

    def java_datatypes_converter(self, data):
        """
        Description: method that converts java datatypes to python ones
        Author: imeerovi
        Parameters:
        * data - java getter results
        Return: python primitive/object
        """
        python_data = None
        # integer
        if isinstance(data, java.lang.Integer):
            python_data = int(data.intValue())
        # long
        elif isinstance(data, java.lang.Long):
            python_data = int(data.longValue())
        # javax.xml.datatype instance
        elif isinstance(data, javax.xml.datatype.XMLGregorianCalendar):
            python_data = data.toString()
        # boolean
        elif isinstance(data, java.lang.Boolean):
            python_data = True if data.toString() == 'true' else False
        # jboolean case:
        elif isinstance(data, bool):
            python_data = data
        # BigDecimal case
        elif isinstance(data, java.math.BigDecimal):
            python_data = Decimal(data.toString())
        # enum case
        elif isinstance(data, java.lang.Enum):
            python_data = data.toString()
        # assuming that this is string
        elif data is not None:
            python_data = data.encode('utf8')
        # maybe it is None
        return python_data


class JavaSdkUtil(APIUtil):
    """
    Description: Implements Java SDK APIs methods
    Author: imeerovi
    Parameters:
        * element - data_structures.py style element
        * collection - data_structures.py style collection
    """
    _sdk_init = None

    @jvm_thread_care
    def __init__(self, element, collection):
        super(JavaSdkUtil, self).__init__(element, collection)

        # for cases when collection name is plural of element name
        # also: data_center, datacenters in python are
        # dataCenter, dataCenters in java
        if element.replace('_', '') in collection:
            self.java_sdk_collection_name = \
                "%ss" % underscore_to_camelcase(element)
        else:
            self.java_sdk_collection_name = \
                underscore_to_camelcase(self.collection_name)
        self.login()

    def login(self):
        """
        Description: login to java sdk.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if not self._sdk_init:
            session_id = \
                self.opts['session_id'] if 'session_id' in self.opts else None
            request_timeout = self.opts['request_timeout'] if \
                'request_timeout' in self.opts else None
            user_with_domain = \
                '{0}@{1}'.format(self.opts['user'], self.opts['user_domain'])
            try:
                if not self.opts['secure']:
                    # Api(java.lang.String url, java.lang.String username,
                    # java.lang.String password, java.lang.String sessionid,
                    # java.lang.Integer port, java.lang.Integer requestTimeout,
                    # java.lang.Integer sessionTimeout,
                    # java.lang.Boolean persistentAuth,
                    # java.lang.Boolean noHostVerification,
                    # java.lang.Boolean filter,
                    # java.lang.Boolean debug)
                    self.api = org.ovirt.engine.sdk.Api(
                        self.opts['uri'].rstrip('/'),
                        user_with_domain, self.opts['password'], session_id,
                        self.opts['port'], request_timeout,
                        self.opts['session_timeout'],
                        self.opts['persistent_auth'],
                        True, self.opts['filter'], self.opts['debug'])
                else:
                    # Api(java.lang.String url, java.lang.String username,
                    # java.lang.String password, java.lang.String sessionid,
                    # java.lang.Integer port, java.lang.Integer requestTimeout,
                    # java.lang.Integer sessionTimeout,
                    # java.lang.Boolean persistentAuth,
                    # java.lang.String keyStorePath,
                    # java.lang.String keyStorePassword,
                    # java.lang.Boolean filter,
                    # java.lang.Boolean debug)
                    self.api = org.ovirt.engine.sdk.Api(
                        self.opts['uri'].rstrip('/'),
                        user_with_domain, self.opts['password'], session_id,
                        self.opts['port'], request_timeout,
                        self.opts['session_timeout'],
                        self.opts['persistent_auth'],
                        self.opts['ssl_key_store_file'],
                        self.opts['password'], self.opts['filter'],
                        self.opts['debug'])
            except java_sdk.JavaError as e:
                raise APILoginError(e)

            self.__class__._sdk_init = self.api
        else:
            self.api = self._sdk_init

    @classmethod
    def logout(cls):
        """
        Description: logout from java sdk.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if cls._sdk_init:
            try:
                cls._sdk_init.shutdown()
            except Exception as e:
                raise APIException(e, 'logout from java sdk failed')
            cls._sdk_init = None

    def __java_method_selector(self, collection, opcode):
        '''
        Description: returns java method with maximum parameters
        Author: imeerovi
        Parameters:
           * collection - JavaTranslator/java SDK collection object
           * opcode - opcode like add, list
        Return: number of parameters to pass
        '''
        # FIXME: currently we are choosing method by looking for longest
        # signature. This assumption is working
        # meanwhile but it is wrong.
        # This function should also receive list of
        # parameter types and return matched overload signature

        # get needed signature
        collection_methods = \
            filter(lambda x: opcode in x, [str(m) for m in
                   collection.getClass().getMethods()])
        # getting methods declarations
        methods_args_list = \
            map(lambda x: x[(x.find('(') + 1):x.find(')')].split(','),
                collection_methods)
        # filtering empty declarations
        methods_args_list = filter(lambda x: len(x[0]) > 0, methods_args_list)

        # take method with maximum parameters and go with it
        sorted_method_args_list = sorted(methods_args_list,
                                         key=lambda item: len(item))[-1]

        return len(sorted_method_args_list), sorted_method_args_list

    @jvm_thread_care
    def get(self, collection=None, **kwargs):
        '''
        Description: get collection by its name
        Author: imeerovi
        Parameters:
           * collection - collection name to get
        Return: parsed GET response
        '''
        python_results = []

        href = kwargs.pop('href', None)
        if href is not None:
            if href == '':
                python_object = JavaTranslator(self.api)
                return python_object
            else:
                # TODO - remove this work-around when solving problem of
                # same returned objects in all engines
                return href

        if not collection:
            collection = self.java_sdk_collection_name

        self.logger.debug("GET request content is --  collection:%(col)s "
                          % {'col': collection})

        results = None
        try:
            results = self.__getCollection(collection).list()
            for entity in results:
                python_results.append(JavaTranslator(entity))
        except AttributeError as exc:
            raise EntityNotFound("Can't get collection '{0}': {1}".
                                 format(collection, exc))

        return python_results

    @jvm_thread_care
    def create(self, entity, positive, expectedEntity=None, incrementBy=1,
               async=False, collection=None, current=None, compare=True,
               **kwargs):
        '''
        Description: creates a new element
        Author: imeerovi
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expectedEntity - if there are some expected entity different from
                              sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        python_response = None
        is_java_translator = False

        if isinstance(entity, JavaTranslator):
            is_java_translator = True

        if not collection:
            # in this case we need to provide correct name for collection,
            # collection itself and entity
            collection_name = get_collection_name_from_entity(entity)
            collection = self.__getCollection(collection_name)
            entity_name = get_object_name(entity)
        else:
            # if we got collection from user it should be JavaTranslator
            collection_name = get_object_name(collection)
            entity_name = get_object_name(entity)

        try:
            self.logger.debug("CREATE api content is --  collection:%(col)s\
element:%(elm)s " % {'col': self.collection_name,
                     'elm': validator.dump_entity(entity, self.element_name)})
        except Exception:
            pass

        try:
            if isinstance(collection, JavaTranslator):
                collection = collection.java_object
            if is_java_translator:
                java_entity = entity.java_object
            else:
                # translating to java
                java_entity = getattr(org.ovirt.engine.sdk.entities,
                                      entity_name)()
                translator_to_java(entity, java_entity)
            # getting correlation id and running
            correlation_id = self.getCorrelationId(ApiOperation.create)

            # setting expect status
            expect = "201-created"

            if correlation_id:
                correlation_id = str(correlation_id)
                add_method_args_length, sorted_add_method_args_list = \
                    self.__java_method_selector(collection, 'add')
                self.logger.debug("Using %s.add(%s)",
                                  get_collection_name_from_entity(entity),
                                  ', '.join(sorted_add_method_args_list))
                if add_method_args_length == 2:
                    with measure_time('POST'):
                        response = collection.add(java_entity, correlation_id)
                elif add_method_args_length == 3:
                    if 'vms' == collection_name.lower():
                        with measure_time('POST'):
                            response = collection.add(java_entity,
                                                      correlation_id, expect)
                    else:
                        with measure_time('POST'):
                            response = collection.add(java_entity, expect,
                                                      correlation_id)
                elif add_method_args_length == 4:
                    with measure_time('POST'):
                        response = collection.add(java_entity, async, expect,
                                                  correlation_id)
                else:
                    msg = "We shouldn't get here, unknown add "\
                        "signature: add(%s)" % sorted_add_method_args_list
                    self.logger.error(msg)
                    raise Exception(msg)
            else:
                with measure_time('POST'):
                    response = collection.add(java_entity)

            # translating of result to python
            python_response = JavaTranslator(response)

            if not async:
                self.find(response.id, 'id', collection=collection.list(),
                          pythonic=False)

            self.logger.info("New entity was added successfully")
            exp_entity = entity if not expectedEntity else expectedEntity
            if compare and not validator.compareElements(
                    exp_entity, python_response, self.logger,
                    self.element_name, java_sdk_mode=True):
                return python_response, False

        except java_sdk.JavaError as e:
            self.parse_java_error(e, ApiOperation.create, positive)
            if positive:
                return None, False

        return python_response, True

    @jvm_thread_care
    def __set_property(self, entity, property_name, property_value,
                       pythonic=False):
        '''
        Set property for sdk object
        pythonic flag sets working mode - False: working with java sdk
                                          True: working with python sdk
        '''
        if not pythonic:
            # java sdk
            setter = 'set%s' % underscore_to_camelcase(property_name)
        else:
            # python sdk
            setter = 'set_%s' % property_name
        getattr(entity, setter)(property_value)

    @jvm_thread_care
    def update(self, origEntity, newEntity, positive,
               expected_neg_status=NEGATIVE_CODES, current=None, async=False,
               compare=True):
        '''
        Description: update an element
        Author: imeerovi
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_neg_status - list of expected statuses for negative
                                    request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: PUT response, True if PUT test succeeded, False otherwise
        '''
        python_response = None

        if isinstance(newEntity, JavaTranslator):
            java_entity = newEntity.java_object
        else:
            java_entity = origEntity.java_object
            translator_to_java(newEntity, origEntity.java_object)

        dumpedEntity = None
        try:
            dumpedEntity = validator.dump_entity(newEntity, self.element_name)
        except Exception:
            pass

        self.logger.debug("UPDATE api content is --  collection :%(col)s \
element:%(elm)s " % {'col': self.collection_name, 'elm': dumpedEntity})

        # getting correlation id and running
        correlation_id = self.getCorrelationId(ApiOperation.update)

        try:
            if correlation_id is not None or current is not None or async:
                correlation_id = str(correlation_id)
                upd_method_args_length, sorted_upd_method_args_list = \
                    self.__java_method_selector(java_entity,
                                                ApiOperation.update)
                if upd_method_args_length == 1:
                    with measure_time('PUT'):
                        response = java_entity.update(correlation_id)
                elif upd_method_args_length == 2:
                    with measure_time('PUT'):
                        response = java_entity.update(correlation_id, async)

                elif upd_method_args_length == 3:
                    with measure_time('PUT'):
                        if (
                            'hosts' == self.collection_name.lower() or
                            'storagedomains' == self.collection_name.lower()
                        ):
                            response = java_entity.update(
                                async, correlation_id, current
                            )
                        else:
                            response = java_entity.update(
                                correlation_id, async, current
                            )
                else:
                    msg = "We shouldn't get here, unknown update signature"\
                        "e: update(%s)" % sorted_upd_method_args_list
                    self.logger.error(msg)
                    raise Exception(msg)
            else:
                with measure_time('PUT'):
                    response = java_entity.update()

            # translating of result to python
            python_response = JavaTranslator(response)
            self.logger.info("%s was updated", self.element_name)
            compare_elements = True if not compare else (
                validator.compareElements(newEntity, python_response,
                                          self.logger, self.element_name,
                                          java_sdk_mode=True))
            if not compare_elements:
                return None, False

        except java_sdk.JavaError as e:
            e = self.parse_java_error(e, ApiOperation.update, positive)
            if positive or not validator.compareResponseCode(
                    e.status, expected_neg_status, self.logger):
                return None, False
            return None, True

        if ((positive and compare_elements) or
                (not positive and expected_neg_status not in NEGATIVE_CODES)):
            return python_response, True

        return None, False

    @jvm_thread_care
    def delete(self, entity, positive, body=None, async=False, **kwargs):
        '''
        Description: delete an element
        Author: imeerovi
        Parameters:
           * entity - entity to delete
           * positive - if positive or negative verification should be done
        Return: status (True if DELETE test succeeded, False otherwise)
        '''

        correlation_id = str(self.getCorrelationId(ApiOperation.delete)
                             or "666")

        try:
            self.logger.debug("DELETE entity: {0}".format(entity.get_id()))
            java_entity = entity.java_object
            if body:
                java_body = getattr(org.ovirt.engine.sdk.entities,
                                    get_object_name(body))()
                translator_to_java(body, java_body)
                # public Response delete(entity, Boolean async,
                #                        String correlationId)
                with measure_time('DELETE'):
                    java_entity.delete(java_body, async, correlation_id)
            # if async is False and no correlation id defined - we got default
            # behavior (last case)
            elif async or self.getCorrelationId(ApiOperation.delete):
                # public Response delete(Boolean async, String correlationId)
                with measure_time('DELETE'):
                    java_entity.delete(async, correlation_id)
            else:
                # public Response delete()
                with measure_time('DELETE'):
                    java_entity.delete()

        except java_sdk.JavaError as e:
            self.parse_java_error(e, ApiOperation.delete, positive)
            if positive:
                return False
            return True

        return True

    @jvm_thread_care
    def query(self, constraint, exp_status=None, href=None, event_id=None,
              all_content=None, **params):
        '''
        Description: run search query
        Author: imeerovi
        Parameters:
           * constraint - query for search
        Return: query results
        '''
        collection = href
        if not href:
            collection = self.java_sdk_collection_name

        search = None
        collection = self.__getCollection(collection)

        params['from_event_id'] = event_id

        MSG = "SEARCH content is -- collection:%(col)s query:%(q)s params \
:%(params)s"
        self.logger.debug(MSG % {'col': self.collection_name,
                                 'q': constraint, 'params': params})

        if constraint is None:
            with measure_time('GET'):
                search = collection.list()
        else:
            # get needed signature
            list_method_args_length, sorted_list_method_args_list = \
                self.__java_method_selector(collection, 'list')

            case_sensitive = params.get('case_sensitive', 'false') == 'true'
            max_ = params.get('max', -1)
            all_content = str(all_content).lower() if all_content else None
            self.logger.debug("Using %s.list(%s)", get_object_name(collection),
                              ', '.join(sorted_list_method_args_list))
            if list_method_args_length == 3:
                with measure_time('GET'):
                    search = collection.list(constraint, case_sensitive, max_)
            elif list_method_args_length == 4:
                if 'events' == get_object_name(collection).lower():
                    with measure_time('GET'):
                        search = collection.list(constraint, case_sensitive,
                                                 event_id, max_)
                else:
                    with measure_time('GET'):
                        search = collection.list(constraint, case_sensitive,
                                                 max_, all_content)
            else:
                msg = "We shouldn't get here, unknown list "\
                    "signature: list(%s)" % sorted_list_method_args_list
                self.logger.error(msg)
                raise Exception(msg)

        self.logger.debug("Response for QUERY request is: %s " % search)
        python_result = [JavaTranslator(entity) for entity in search]
        return python_result

    @jvm_thread_care
    def find(self, val, attribute='name', absLink=True, collection=None,
             pythonic=True, **kwargs):
        '''
        Find entity by name or id
        Author: imeerovi
        :param val: name or id to look for
        :type val: str
        :param attribute: name or id, the key to look for
        :type attribute: str
        :param absLink: True: absolute link, suffix otherwise
        :type absLink: bool
        :param collection: list of entities, where to find your val
        :type collection: object
        :param pythonic: True if we are python context, java otherwise
        :type pythonic: bool
        :param all_content: parameter to get more info about entities
        :type all_content: bool
        :param max: max number of entities to list
        :type max: int
        :return: entity found or None if not found
        '''
        if not collection:
            collection = self.__getCollection(
                self.java_sdk_collection_name
            )
            list_method_args_length, sorted_list_method_args_list = (
                self.__java_method_selector(collection, 'list')
            )
            self.logger.debug(
                "Using %s.list(%s)", get_object_name(collection),
                ', '.join(sorted_list_method_args_list)
            )
            all_content = kwargs.pop('all_content', False)
            max = kwargs.pop('max', -1)

            if all_content:
                collection = collection.list(
                    val, False, max, str(all_content).lower()
                )
            else:
                collection = collection.list()
        else:
            if not isinstance(collection, java.util.List) and \
                    not isinstance(collection, list):
                collection = collection.list()

        results = None
        try:
            if attribute == 'name':
                results = filter(lambda r: r.getName() == val, collection)[0]
            if attribute == 'id':
                results = filter(lambda r: r.getId() == val, collection)[0]
        except Exception:
            raise EntityNotFound("Entity %s not found for collection '%s'."
                                 % (val, collection))

        if pythonic:
            return results if isinstance(results, JavaTranslator) else \
                JavaTranslator(results)
        else:
            # java sdk style
            return results

    def __getCollection(self, collection_name):
        '''
        Returns sdk collection object
        '''
        # checking if this exeception from rules
        collection_name = \
            STYLE_EXCEPTIONS_JAVA_COLLECTIONS.get(collection_name,
                                                  collection_name)
        res = getattr(self.api, collection_name)
        return res

    def _get_results_by_best_list_function(self, entities, all_content, max_):
        '''
        Java classes may have more than one method called list(). In java it
        is called function overloading.
        This function tries to use the one depending on number of params.
        Currently getElemFromLink calls this function and this will run list()
        or list(Integer max) or list(Integer max, String all_content)
        :param entities: Name of element (vms, snapshots...)
        :type entities str
        :param all_content: True to get more data from object false otherwise
        :type all_content: bool
        :param max_: max number of objects to list
        :type max_: int
        :return: list of object
        '''
        # TODO: Try to handle 3 & 4 parameters as well, and use it for find
        #       query and getElmfromLink
        # This function is selecting by assumption that all list with 1 params
        # will invoke list(integer max)
        # all list with 2 params will invoke list(max, all_content)
        # otherwise will invoke list()
        list_method_args_length, sorted_list_method_args_list = (
            self.__java_method_selector(
                entities.java_object, 'list'
            )
        )
        self.logger.info(
            "Using %s.list(%s)", get_object_name(
                entities.java_object
            ), ', '.join(sorted_list_method_args_list)
        )
        if list_method_args_length == 1:
            elements = entities.list(max_)
        elif list_method_args_length == 2:
            elements = entities.list(
                max_, str(all_content).lower()
            )
        else:
            elements = entities.list()

        return elements

    @jvm_thread_care
    def getElemFromLink(self, elm, link_name=None, attr=None, get_href=False,
                        pythonic=True, **kwargs):
        '''
        get collection of elements from specified link for example:
        vms/snapshots
        :param elm: object like vms, disks..
        :type elm: object
        :param link_name: another object to get like vms/snapshots
        :type link_name: str
        :param attr: used in restapi only
        :type attr: str
        :param get_href: True if it is a link False otherwise
        :type get_href: bool
        :param pythonic: True if python, False if java
        :type pythonic: bool
        :param all_content: True get more info about object, False otherwise
        :type all_content: bool
        :param max: maximum number of elements to list
        :type max: int
        :return: list of objects
        '''
        if not link_name:
            link_name = self.java_sdk_collection_name
        # TODO: to check if translation of link name
        # to java sdk convention is needed

        all_content = kwargs.pop('all_content', False)
        max = kwargs.pop('max', -1)

        if not pythonic:
            if get_href:
                return getattr(elm, link_name)
            else:
                entities = getattr(elm, link_name)
                return self._get_results_by_best_list_function(
                    entities, all_content, max
                )
        else:
            if get_href:
                data = getattr(elm, link_name)
                # checking if we already have translator wrapper
                if isinstance(data, JavaTranslator):
                    return data
                return JavaTranslator(getattr(elm, link_name))
            else:
                entities = getattr(elm, link_name)

                if all_content:
                    entities = self._get_results_by_best_list_function(
                        entities, all_content, max
                    )
                else:
                    entities = getattr(elm, link_name).list()

                return [JavaTranslator(entity)
                        if not isinstance(entity, JavaTranslator)
                        else entity
                        for entity in entities]

    @jvm_thread_care
    def syncAction(self, entity, action, positive, async=False, **params):
        '''
        Description: run synchronic action
        Author: imeerovi
        Parameters:
           * entity - target entity
           * action - desired action
           * positive - if positive or negative verification should be done
           * asynch - synch or asynch action
        Return: status (True if Action test succeeded, False otherwise)
        '''
        act = self.makeAction(async, 10, **params)

        try:
            self.logger.info("Running action {0} on {1}".
                             format(validator.dump_entity(action, 'action'),
                                    entity))
        except Exception:
            pass

        # taking care on language specific differences in action name:
        obj_name = get_object_name(entity)
        if get_object_name(entity) in ACTION_EXCEPTIONS_PYTHON_JAVA_METHODS:
            action = \
                ACTION_EXCEPTIONS_PYTHON_JAVA_METHODS[obj_name].get(action,
                                                                    action)

        if isinstance(entity, JavaTranslator):
            java_entity = entity.java_object
        else:
            # TODO: here we have potential bug since we can search
            # in wrong collection. for example search for StorageDomain
            # and not for DataCenterStorageDomain
            java_entity = self.find(entity.name, pythonic=False)

        try:
            java_action_entity_name = get_object_name(act)
            java_action_entity = getattr(org.ovirt.engine.sdk.entities,
                                         java_action_entity_name)()
            translator_to_java(act, java_action_entity)
            with measure_time('POST'):
                act = getattr(java_entity, action)(
                    java_action_entity,
                    str(self.getCorrelationId(ApiOperation.syncAction)))
        except java_sdk.JavaError as e:
            self.parse_java_error(e, ApiOperation.syncAction, positive)
            if positive:
                return False
            return True
        else:
            if not positive:
                errorMsg = "Succeeded to run an action '{0}' for negative test"
                self.logger.error(errorMsg.format(action))
                return False

        return validator.compareAsyncActionStatus(
            async, act.status.state, self.logger)

    @jvm_thread_care
    def waitForElemStatus(self, elm, status, timeout=DEF_TIMEOUT,
                          ignoreFinalStates=False, collection=None):
        '''
        Description: Wait till the sdk element (the Host, VM) gets the desired
        status or till timeout.

        Author: imeerovi
        Parameters:
            * elm - sdk element to probe for a status
            * status - a string represents status to wait for. it could be
                       multiple statuses as a string with space delimiter
                       Example: "active maintenance inactive"
            * timeout - maximum time to continue status probing
        Return: status (True if element get the desired status,
                        False otherwise)
        '''
        handleTimeout = 0
        while handleTimeout <= timeout:
            java_element = self.find(elm.name, collection=collection)

            element_status = None
            if hasattr(java_element, 'snapshotStatus'):
                element_status = java_element.snapshotStatus.lower()
            elif hasattr(java_element, 'status'):
                element_status = java_element.status.state.lower()
            else:
                self.logger.error("Element %s doesn't have attribute status",
                                  self.element_name)
                return False

            try:
                python_element = JavaTranslator(java_element)
                # reporting
                self.logger.info("Element {0} Waiting for the status {1}".
                                 format(validator.
                                        dump_entity(python_element,
                                                    self.element_name),
                                        status))
            except Exception as ex:
                self.logger.debug(ex)

            # TODO: why do we need it here???
            if not hasattr(java_element, 'status'):
                self.logger.error("Element %s doesn't have attribute status",
                                  self.element_name)
                return False

            if element_status in status.lower().split():
                self.logger.info("%s status is '%s'", self.element_name,
                                 element_status)
                return True
            elif element_status.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  element_status)
                return False
            elif element_status == 'up' and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  element_status)
                return False
            else:
                self.logger.debug("Waiting for status '%s', \
currently status is '%s' ", status, element_status)
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'.",
                          self.element_name, element_status)
        return False

    def parse_java_error(self, java_error, op_code, positive=True):
        """
        Description: function that converts java error to object that has
                     code, reason, detail, java_traceback fields
        Author: imeerovi
        Parameters:
            * java_error - java_sdk.JavaError object
            * op_code - operation name (like create, delete, update ..)
        """
        detail = ''
        try:
            extra_details = False
            # extracting message
            for line in filter(lambda x: len(x) > 0,
                               java_error.args[0].toString().splitlines()):
                if extra_details is False:
                    name, value = line.split(':', 1)
                else:
                    detail = '\n\t\t'.join([detail, line])
                if 'code' in name:
                    status = int(value.strip())
                elif 'reason' in name:
                    reason = value.strip()
                elif extra_details is False:
                    detail = value.strip()
                    extra_details = True

            # getting traceback
            java_traceback = '\n\t'.join([trace.toString() for trace
                                          in java_error.args[0].stackTrace])
            super(JavaSdkUtil, self).print_error_msg(op_code, status, reason,
                                                     detail, java_traceback,
                                                     positive=positive)
        except Exception as e:
            self.logger.error('Caught Exception %s', e)
            self.logger.error('Possible internal error: %s', str(java_error))

        return api_error(reason=reason, status=status, detail=detail)

# APIUtil.register(JavaSdkUtil)
