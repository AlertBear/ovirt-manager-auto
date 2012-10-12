#!/usr/bin/python

import sys
import os
import argparse
import art.test_handler.plmanagement as core
from art.test_handler.plmanagement import logger
from art.test_handler.plmanagement import implements
from interfaces import application, report_formatter, \
        tests_listener, time_measurement, config_validator

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), 'plugins')


# Note that application is Component as well as it's own ComponentManager.
class PluginManager(core.ComponentManager, core.Component):
    test_parsers = core.ExtensionPoint(application.ITestParser)
    application_liteners = core.ExtensionPoint(application.IApplicationListener)
    configurables = core.ExtensionPoint(application.IConfigurable)
    results_collector = core.ExtensionPoint(report_formatter.IResultsCollector)
    test_cases = core.ExtensionPoint(tests_listener.ITestCaseHandler)
    test_groups = core.ExtensionPoint(tests_listener.ITestGroupHandler)
    test_suites = core.ExtensionPoint(tests_listener.ITestSuiteHandler)
    test_skippers = core.ExtensionPoint(tests_listener.ITestSkipper)
    time_measurement = core.ExtensionPoint(time_measurement.ITimeMeasurement)
    conf_validators = core.ExtensionPoint(config_validator.IConfigValidation)

    def __init__(self):
        core.ComponentManager.__init__(self)
        core.Component.__init__(self)
        self.configured = False
        self.load_plugins()
        self.args = None
        self.config = None

    def load_plugins(self, path=DEFAULT_PATH):
        mod = os.path.basename(os.path.abspath(path))
        sys.path.insert(0, path)
        try:
            for root, dirs, files in os.walk(path, followlinks=True):
                for f in (f for f in files if f.endswith('plugin.py')):
                    logger.info("Loading %(f)s.", locals())
                    __import__(f.rstrip('.py'))
                    logger.info("Loading %(f)s DONE.", locals())
        finally:
            sys.path = sys.path[1:]
        self.application_liteners.on_plugins_loaded()

    def is_enabled(self, cls):
        return self.is_component_enabled(cls)

    def is_component_enabled(self, cls):
        if self.configured and hasattr(cls, 'is_enabled'):
            # after configuration each of them can say if is ready to work
            return super(PluginManager, self).is_component_enabled(cls) and \
                            cls.is_enabled(self.args, self.config)
        return super(PluginManager, self).is_component_enabled(cls)

    def configure(self, args=None, config=None):
        self.args = args
        self.config = config
        self.configurables.configure(args, config)
        self.configured = True


