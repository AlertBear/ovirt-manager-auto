# Copyright (C) 2011 Red Hat, Inc.
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

import inspect
import re
from collections import namedtuple
from distutils.version import StrictVersion
from functools import wraps

import art.test_handler.exceptions as exceptions
from art.core_api import validator
from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api
from art.unittest_lib import testflow

util = get_api('', '')
vmUtil = get_api('vm', 'vms')
hostUtil = get_api('host', 'hosts')
domUtil = get_api('domain', 'domains')
userUtil = get_api('user', 'users')
sdUtil = get_api('storage_domain', 'storagedomains')
dcUtil = get_api('data_center', 'datacenters')
permitUtil = get_api('cluster_level', 'clusterlevels')

VM = getDS('VM')

ProductVersion = namedtuple(
    'ProductVersion', ['major', 'minor', 'build', 'revision']
)


def check_system_version_tag(positive):
    '''
    Checks whether there are attributes named:
        revision build minor major
    in the api->product_version tag, whether it is unique and whether the
    subtags are unique and their values converts to integer numbers.

    Author: jhenner
    Parameters:
        None
    Return:
        bool
            * True iff error not detected
            * False if test is not positive, or if some violation from the
              above found.
    '''
    # Check whether positive is sane for this test case.
    assert positive

    try:
        version_caps = permitUtil.get(abs_link=False)
    except KeyError:
        util.logger.warn("Can't get list of permissions from capabilities")
        pass

    product_version = util.get(href='',
                               abs_link=False).get_product_info().get_version()
    system_version = StrictVersion(
        '.'.join(
            (
                str(product_version.get_major()),
                str(product_version.get_minor())
            )
        )
    )

    if not product_version:
        ERR = "The tag product_info->version is either not unique or is not"
        " present."
        util.logger.error(ERR)
        return False
    MSG = "The tag product_info->version is unique and present."
    util.logger.info(MSG)

    ERR1 = "Current version: '{0}' not found under clusterlevels node"

    version_caps_list = (
        version_caps
        if isinstance(version_caps, list)
        else [version_caps]
    )
    for version in version_caps_list:
        try:
            cluster_version = StrictVersion(
                version.get_id()
            )
        except ValueError as ex:
            util.logger.error("Bad version format: %s", ex)
            return False

        if system_version == cluster_version:
            return True

    util.logger.error(ERR1.format(system_version))
    return False


def convToInt(num, attr):
    try:
        int(num)
    except ValueError as e:
        util.logger.error(e)
        ERR = "Couldn't convert '{0}' to a int number."
        util.logger.error(ERR.format(attr))
        return False

    return True


def checkSummary(positive, domain):
    '''
    Description: validate system summary statistics values
    Author: edolinin
    Parameters:
      no
    Return: status (True if all statistics values are correct, False otherwise)
    '''

    get_all = util.get(href='', abs_link=False)
    status = True

    vms = vmUtil.get(abs_link=False)
    sum_vms_total = get_all.get_summary().get_vms().total
    util.logger.info('Comparing total vms number')
    if not validator.compareCollectionSize(vms, sum_vms_total, util.logger):
        status = False

    vms = vmUtil.get(abs_link=False)
    sum_vms_act = get_all.get_summary().get_vms().active
    vms = filter(lambda x: x.get_status() == 'up', vms)
    util.logger.info('Comparing active vms number')
    if not validator.compareCollectionSize(vms, sum_vms_act, util.logger):
        status = False

    hosts = hostUtil.get(abs_link=False)
    sum_hosts_total = get_all.get_summary().get_hosts().total
    util.logger.info('Comparing total hosts number')
    if not validator.compareCollectionSize(
        hosts, sum_hosts_total, util.logger
    ):
        status = False

    hosts = hostUtil.get(abs_link=False)
    sum_hosts_act = get_all.get_summary().get_hosts().active
    hosts = filter(lambda x: x.get_status() == 'up', hosts)
    util.logger.info('Comparing active hosts number')
    if not validator.compareCollectionSize(hosts, sum_hosts_act, util.logger):
        status = False

    users = userUtil.get(abs_link=False)
    sum_users_total = get_all.get_summary().get_users().total
    util.logger.info('Comparing total users number')
    if not len(users) <= sum_users_total:
        util.logger.error(
            "Collection size is wrong, "
            "actual should be smaller or equal to expected. "
            "expected is: %(exp)s, actual is: %(act)s",
            {'exp': sum_users_total, 'act': len(users)}
        )
        status = False
    else:
        util.logger.debug(
            "Collection size is correct: %(exp)s is bigger then %(act)s since "
            "the number of returned users is limited for performance reasons",
            {'exp': sum_users_total, 'act': len(users)}
        )

    util.logger.info('Comparing total storage number')
    sum_sd_total = get_all.get_summary().get_storage_domains().total
    storage_domains = sdUtil.get(abs_link=False)
    if not validator.compareCollectionSize(
            storage_domains, sum_sd_total, util.logger):
        status = False

    util.logger.info('Comparing active storages number')
    sum_s_d_active = get_all.get_summary().get_storage_domains().active
    sd_active = []
    dcs = dcUtil.get(abs_link=False)
    for dc in dcs:
        dc_storages = util.getElemFromLink(
            dc, link_name='storagedomains', attr='storage_domain',
            get_href=False)
        for dcSd in dc_storages:
            try:
                if dcSd.get_status() == 'active':
                    sd_active.append(dcSd)
            except AttributeError:
                pass

    if not validator.compareCollectionSize(
        sd_active, sum_s_d_active, util.logger
    ):
        status = False

    return status


def checkResponsesAreXsdValid():
    '''
    Checks for validations errors found out by restutils
    Author: jvorcak
    Return: True if all responses were valid against xsd schema
            False otherwise
    '''
    ret = True
    try:
        for error in util.xsd_schema_errors:
            href, ret, ex = error
            util.logger.error(
                "Response href: %s, status %d is not valid against xsd schema"
                % (href, ret['status']))
            util.logger.error("Response body: %s" % ret['body'])
            util.logger.error("Exception is: %s" % ex)
            ret = False
    except AttributeError:
        pass

    return ret


def getProductName():
    '''
    Get product name
    Author: atal
    Return True, dict(product name) is succeeded, Fals, dict('') otherwise
    '''
    try:
        product_name = util.get(
            href='', abs_link=False).get_product_info().get_name()
    except IndexError:
        return False, {'product_name': ''}
    return True, {'product_name': product_name}


def checkProductName(name):
    '''
    Checks whether the product's name is the same as name parameter.
    Author: gleibovi
    Return True if the name is the same as product_name, False if not or
    failed to get product name.
    '''
    status, ret = getProductName()
    if not status:
        return status
    product_name = ret['product_name']

    if product_name != name:
        util.logger.error(
            "Product name is wrong, expected: '%s', actual: '%s'"
            % (name, product_name))
        return False

    util.logger.info("Product name is correct: '%s'" % name)
    return True


def prepare_ds_object(object_name, **kwargs):
    """
    Create new data structure object

    :param object_name: name of instance to create
    :param kwargs: parameters of instance
    :return: data structure object or raise exceptions
    """
    ds_object = getDS(object_name)()
    for key, val in kwargs.iteritems():
        if hasattr(ds_object, key):
            setattr(ds_object, key, val)
        else:
            raise exceptions.RHEVMEntityException(
                "%s object has no attribute: %s" % (object_name, key)
            )
    return ds_object


def get_object_name_by_id(object_api, object_id):
    """
    Get object name by object object_id

    :param object_api: Object API (CLUSTER_API for example)
    :type object_api: class
    :param object_id: Object ID
    :type id: str
    :return: Object name
    :rtype: str
    """
    return object_api.find(object_id, "id").get_name()


def get_log_msg(
    log_action, obj_type="", obj_name="", positive=True, extra_txt="", **kwargs
):
    """
    Generate info and error logs for log_action on object.

    Args:
        log_action (str): The log_action to perform on the object
            (create, update, remove)
        obj_type (str): Object type
        obj_name (str): Object name
        positive (bool): Expected results
        extra_txt (str): Extra text to add to the log
        kwargs (dict): Parameters for the log_action if any

    Returns:
        tuple: Log info and log error text
    """
    kwargs = prepare_kwargs_for_log(**kwargs)
    kwargs_to_pop = []
    kwargs_to_log = {}
    log = [
        re.sub('[^0-9a-zA-Z|_]+', "", i) for i in log_action.lower().split()
    ]
    for k, v in kwargs.items():
        if k.lower() in log:
            if isinstance(v, bool):
                continue

            key = re.findall(r'\b%s\b' % k, log_action, re.IGNORECASE)[0]
            v = ", ".join(v) if isinstance(v, list) and all(
                [isinstance(i, str) for i in v]
            ) else v
            log_action = log_action.replace(
                key, "{key} {val}".format(key=key, val=v)
            )
            kwargs_to_pop.append(k)

    for k in kwargs_to_pop:
        kwargs.pop(k)

    for k, v in kwargs.items():
        if isinstance(v, list):
            kwargs_to_log[k] = [
                getattr(i, "name", getattr(i, "id", i)) for i in v
            ]
        else:
            kwargs_to_log[k] = getattr(
                v, "name", getattr(v, "id", getattr(v, "fqdn", v))
            )

    with_kwargs = "with %s" % kwargs_to_log if kwargs_to_log else ""
    state = "Succeeded to" if not positive else "Failed to"
    info_text = (
        "{log_action} {obj_type} {obj_name} {with_kwargs} {extra_txt}".format(
            log_action=log_action, obj_type=obj_type, obj_name=obj_name,
            with_kwargs=with_kwargs, extra_txt=extra_txt
        )
    ).strip()
    info_text = info_text.replace("  ", "")

    log_info_txt = (
        info_text if positive else "Negative: %s" % info_text.capitalize()
    )
    log_error_txt = "%s %s" % (state, info_text.lower())
    return log_info_txt, log_error_txt


def prepare_kwargs_for_log(**kwargs):
    """
    Prepare kwargs for get_log_msg()

    Args:
        kwargs (dict): kwargs to prepare

    Returns:
        dict: kwargs after prepare
    """
    new_kwargs = dict()
    for k, v in kwargs.iteritems():
        if v is None:
            continue
        new_kwargs[k] = v.name if hasattr(v, 'name') else v
    return new_kwargs


def generate_logs(info=True, error=True, step=False, warn=False):
    """
    Decorator to generate log info and log error for function.
    The log contain the first line from the function docstring and resolve
    names from function docstring by function args, any args that not
    resolved from the docstring will be printed after.
    If the function have positive arg the log will be based positive or
    negative based on that.
    In some cases only info or error log is needed, the decorator can be
    called with @generate_logs(error=False) to get only log INFO and vice versa

    For example:
        @generate_logs()
        def my_test(test, cases):
            '''
            Run test with cases
            '''
            return

        my_test(test='my-test-name', cases=['case01', 'case02']
        Will generate:
            INFO Run test my-test-name with cases case01, case02
            ERROR Failed to Run test my-test-name with cases case01, case02
            if step is True:
                Test Step   1: Run test my-test-name with cases case01, case02

    Args:
        info (bool): True to get INFO log
        error (bool): True to get ERROR log
        step (bool): True to get testflow.step if function called from test
        warn (bool): True to get WARN log

    Returns:
        any: The function return
    """
    def generate_logs_decorator(func):
        """
        The real decorator

        Args:
            func (Function): Function

        Returns:
            any: The function return
        """
        @wraps(func)
        def inner(*args, **kwargs):
            """
            The call for the function
            """
            kwargs_for_log = kwargs.copy()
            stack = inspect.stack()
            called_from, scope = get_called_from_test(stack=stack)
            func_doc = inspect.getdoc(func)
            func_argspec = inspect.getargspec(func)

            # Get function default args
            func_argspec_default = dict(
                zip(
                    func_argspec.args[
                        -len(func_argspec.defaults or list()):
                    ], func_argspec.defaults or list()
                )
            )

            # Get actual function args
            func_args = dict(zip(func_argspec.args, args))

            # Filter missing args from default if not sent by user
            missing_args = dict(
                (k, v) for k, v in func_argspec_default.iteritems() if
                k not in func_args.keys()
            )

            # Update func_args with missing args
            for k, v in missing_args.iteritems():
                if k not in func_args.keys():
                    func_args[k] = v

            # Update kwargs_for_log with all args
            for k, v in func_args.iteritems():
                if k not in kwargs_for_log.keys():
                    kwargs_for_log[k] = v

            log_action = func_doc.split("\n")[0]
            log_info, log_err = get_log_msg(
                log_action=log_action, **kwargs_for_log
            )
            if step and called_from:
                test_flow_call = getattr(testflow, called_from)
                scope_log = "[{scope}] ".format(scope=scope) if scope else ""
                test_flow_call(
                    "{scope_log}{log_info}".format(
                        scope_log=scope_log, log_info=log_info
                    )
                )

            if info:
                util.logger.info(log_info)

            res = func(*args, **kwargs)
            if not res:
                if warn:
                    util.logger.warn(log_err)
                elif error:
                    util.logger.error(log_err)
            return res
        return inner
    return generate_logs_decorator


def get_called_from_test(stack):
    """
    Check if function was called from test or from fixture

    Args:
        stack (list): stack (inspect.stack()) list

    Returns:
        tuple: From where the function called (step (test), setup or teardown)
            and if called from fixture the fixture scope as well
    """
    scope = ""
    call_args = [i[3] for i in stack]
    frames = [i[0] for i in stack]
    if "pytest_runtest_call" in call_args:
        return "step", scope

    if "pytest_fixture_setup" in call_args:
        for f in frames:
            fixture_def = f.f_locals.get("fixturedef", None)
            if fixture_def:
                scope = fixture_def.scope
        return "setup", scope

    if "pytest_runtest_teardown" in call_args:
        for f in frames:
            fixture_fin = f.f_locals.get("fin", None)
            if fixture_fin:
                scope = fixture_fin.im_self.scope
        return "teardown", scope

    return "", scope
