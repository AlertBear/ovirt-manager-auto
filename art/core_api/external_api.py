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

import os
import logging
from time import strftime
from art.core_api.apis_exceptions import APICommandError
from art.test_handler.logger_utils import initialize_logger

opts = {}


class TestRunnerWrapper():
    """
    Runs APIs functions not from run.py and without settings.conf.
    Required settings options are defined in constructor.

    Usage Example:
        from art.core_api.external_api import TestRunnerWrapper
        from art.core_api.apis_exceptions import APICommandError
        wrapper = TestRunnerWrapper("10.10.10.10")
        try:
            status = wrapper.runCommand(\
                "art.rhevm_api.tests_lib.low_level.datacenters.addDataCenter",
                "true",name="test",version="3.1")
        except APICommandError:
            pass #handle error
    """

    def __init__(self, ip, **kwargs):
        """
        Defines settings configuration required to run REST APIs functions

        :param ip: vdc IP
        :type ip: str
        :param kwargs: dictionary with settings configurations, keys names are
                       the same as in settings.conf, if omitted - defaults
                       are set
        :type kwargs: dict
        """
        opts["host"] = ip
        opts["scheme"] = kwargs.get("scheme", "https")
        opts["port"] = kwargs.get("port", "443")
        opts["entry_point"] = kwargs.get("entry_point", "api")
        opts["user"] = kwargs.get("user", "admin")
        opts["user_domain"] = kwargs.get("user_domain", "internal")
        opts["password"] = kwargs.get("password", "123456")
        opts["engine"] = kwargs.get("engine", "rest")
        opts["debug"] = kwargs.get("debug", True)
        opts["media_type"] = kwargs.get("media_type", "application/xml")
        opts["headers"] = kwargs.get("headers", {})
        opts["validate"] = kwargs.get("validate", True)
        opts["secure"] = kwargs.get("secure", False)
        opts["data_struct_mod"] = kwargs.get(
            "data_struct_mod", "art.rhevm_api.data_struct.data_structures"
        )
        opts["log"] = kwargs.get(
            "log", "/var/tmp/%s_tests%s.log" % (
                opts["engine"], strftime("%Y%m%d_%H%M%S"))
        )
        opts["log_conf"] = kwargs.get('log_conf')
        opts.setdefault('logdir', os.path.dirname(opts['log']))
        opts["urisuffix"] = ""
        opts["uri"] = (
            "%(scheme)s://%(host)s:%(port)s/%(entry_point)s%(""urisuffix)s/"
            % opts
        )
        opts["standalone"] = kwargs.get("standalone", False)

        logger_init = kwargs.pop("logger_init", True)

        for arg in kwargs:
            if arg not in opts:
                opts[arg] = kwargs[arg]

        if logger_init:
            initialize_logger(
                conf_file=opts['log_conf'],
                log_file=opts["log"]
            )
        self.logger = logging.getLogger(__name__)
        if opts["debug"]:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info("Log file is initialized at %s", opts["log"])

    @classmethod
    def runCommand(cls, action, *args, **kwargs):
        """
        Runs REST APIs functions

        :param action: full path of the action which should be run
        :type action: str
        :param args: list of function"s non-keyword arguments
        :ype args: list
        :param kwargs: dictionary with function"s keyword arguments
        :type kwargs: dict
        :raise: APICommandError in case of error
        """

        action_modules_names = action.split(".")
        func_package = ".".join(action_modules_names[:-1])
        func_name = action_modules_names[-1]

        exec("from %s import %s", func_package, func_name)

        params = ""
        for arg in args:
            params = "{0},{1!r}".format(params, arg)

        for paramName, paramVal in kwargs.items():
            params = "{0},{1}={2!r}".format(params, paramName, paramVal)
        cmd = "%s(%s)" % (func_name, params.strip(" ,"))

        try:
            return eval(cmd)
        except Exception as e:
            raise APICommandError(cmd, e)
