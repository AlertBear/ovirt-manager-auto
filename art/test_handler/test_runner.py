#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from configobj import ConfigObj
from datetime import datetime
from dateutil.tz import tzutc
import threading
import copy
from art.test_handler.settings import opts, initPlmanager
from art.test_handler.exceptions import VitalTestFailed, SkipTest
from utilities.jobs import JobsSet, Job # TODO: consider to use http://docs.python.org/dev/library/concurrent.futures.html instead

# TODO: Consider trigger_action
# TODO: Consider async. actions
# TODO: need to adjust plugins to parallel


logger = logging.getLogger('test_runner')


def serial_generator(start=0, end=None, step=1):
    lock = threading.Lock()
    number = start
    while True:
        with lock:
            if end is not None and number > end:
                raise StopIteration()
            curr = number
            number += step
        yield curr

SERIAL = serial_generator()


class _DictLikeObject(dict):

    def __getattribute__(self, key):
        try:
            return super(_DictLikeObject, self).__getattribute__(key)
        except AttributeError as ex:
            try:
                return self[key]
            except KeyError:
                raise ex

    def __setattr__(self, key, val):
        if key.startswith('_'):
            super(_DictLikeObject, self).__setattr__(key, val)
        else:
            self[key] = val
#class _DictLikeObject(object):
#    pass


class TestResult(_DictLikeObject):
    # result.attr_name: (test_elm.name, 'nice_name', 'default_value')
    ATTRIBUTES = {
            'id': ('id', 'Test ID', 'NaN'),
            'test_name': ('test_name', 'Test Name', 'Unknown name'),
            'test_description': ('test_description', 'Description', ''),
            'start_time': ('start_time', 'Start Time', None),
            'end_time': ('end_time', 'End Time', None),
            'status': ('status', 'Status', None),
            }

    def __init__(self):
        super(TestResult, self).__init__()
        self._report = True

    @classmethod
    def result_from_test_case(cls, test_case):
        res = TestResult()
        for r_name, attrs in cls.ATTRIBUTES.items():
            setattr(res, r_name, getattr(test_case, attrs[0], attrs[2]))
        # TODO: more informations
        return res

    @classmethod
    def add_result_attribute(cls, attr_name, te_name, nice_name=None, default=None):
        cls.ATTRIBUTES[attr_name] = (te_name, nice_name, default)

    def formated_attribute(self, attr_name):
        val = getattr(self, attr_name, None)
        return self.format_attrib(attr_name, val)

    @classmethod
    def format_attrib(cls, attr_name, val):
        attr = cls.ATTRIBUTES[attr_name]
        res = attr[1] if attr[1] is not None else attr_name
        if val is None:
            val = attr[2]
        return "%s: %s" % (res, val)


class _TestElm(_DictLikeObject):
    TEST_STATUS_PASSED = 'Pass'
    TEST_STATUS_FAILED = 'Fail'
    TEST_STATUS_SKIPPED = 'Skipped'
    TEST_STATUS_ERROR = 'Error'
    TEST_STATUS_UNDEFINED = 'Undefined'

    def __init__(self):
        super(_TestElm, self).__init__()
        self.serial = SERIAL.next()
        self.name = None
        self.description = None
        self.status = self.TEST_STATUS_UNDEFINED
        self.vital = False
        self.start_time = None
        self.end_time = None

    def format_attr(self, name):
        try:
            form = [x for x, y in TestResult.ATTRIBUTES.items() if y[0] == name][0]
        except IndexError:
            raise KeyError(name)
        return TestResult.format_attrib(form, self.get(name, None))

    def __copy__(self):
        cp = copy.copy(super(_TestElm, self))
        cp.serial = SERIAL.next()
        return cp


class TestGroup(_TestElm):
    '''
    Defines test group properties and methods
    '''

    def __init__(self):
        super(TestGroup, self).__init__()
        self.workers = 1
        self.failed = 0
        self.passed = 0
        self.skipped = 0
        self.unhandled = 0

    def __iter__(self):
        raise NotImplementedError()


class TestCase(_TestElm):
    '''
    Defines test case properties and methods
    '''

    def __init__(self):
        super(TestCase, self).__init__()
        self.exc = None

    def __call__(self):
        raise NotImplementedError()


class TestSuite(TestGroup):
    pass


class TestRunner(object):
    '''
    Implements general methods for test runs
    '''
    def __init__(self, parser):
        self.parser = parser
        self.plmanager = initPlmanager()

    def run(self):
        in_parallel = False
        if not in_parallel:
            while True:
                test_elm = self.parser.next_test_object()
                if test_elm is None:
                    break
                self._run_test_suite(test_elm)
        else:
            jobs = []
            while True:
                test_elm = self.parser.next_test_object()
                if test_elm is None:
                    break
                jobs += Job(target=self._run_test_suite, args=(test_elm,))
            if not jobs:
                return
            job_set = JobsSet(test_elm.workers)
            job_set.addJobs(jobs)
            job_set.start()
            job_set.join()
            for job in jobs:
                if isinstance(job.exception, VitalTestFailed):
                    raise job.exception

    def _run_test_suite(self, test_suite):
        assert isinstance(test_suite, TestSuite), \
                "test_elm must be TestSuite, not %s" % type(test_suite)
        try:
            self.plmanager.test_suites.pre_test_suite(test_suite)
            self._run_test_elm(test_suite)
        finally:
            self.plmanager.test_suites.post_test_suite(test_suite)

    def _run_test_elm(self, test_elm):
        if isinstance(test_elm, TestGroup):
            self._run_test_group(test_elm)
        elif isinstance(test_elm, TestCase):
            self._run_test_case(test_elm)
        else:
            assert False, "Test Element must be TestCase or "\
                    "TestGroup not %s" % type(test_elm)

    def _run_test_case(self, test_case):
        assert isinstance(test_case, TestCase), \
                "test_elm must be TestCase, not %s" % type(test_case)
        test_case.start_time = datetime.now(tzutc())
        try:
            self.plmanager.test_cases.pre_test_case(test_case)
            self.plmanager.test_skippers.should_be_test_case_skipped(test_case)
            test_case()
        except SkipTest as s:
            test_case.status = test_case.TEST_STATUS_SKIPPED
            test_case.exc = s
        except Exception as ex:
            test_case.status = test_case.TEST_STATUS_ERROR
            test_case.exc = ex
            raise
        finally:
            test_case.end_time = datetime.now(tzutc())
            self.plmanager.test_cases.post_test_case(test_case)
        result = TestResult.result_from_test_case(test_case)
        result.status = test_case.status
        self.plmanager.results_collector.pre_test_result_reported(result, test_case)
        self.plmanager.results_collector.add_test_result(result, test_case)
        if test_case.vital and test_case.status != test_case.TEST_STATUS_PASSED:
            raise VitalTestFailed(test_case.test_name)

    def _run_test_group(self, test_group):
        assert isinstance(test_group, TestGroup), \
                "test_elm must be TestGroup, not %s" % type(test_group)
        test_group.start_time = datetime.now(tzutc())
        try:
            # TODO: consider to have Result for group
            self.plmanager.test_groups.pre_test_group(test_group)
            self.plmanager.test_skippers.should_be_test_group_skipped(test_group)
            if test_group.workers == 1:
                for test_elm in test_group:
                    self._run_test_elm(test_elm)
            elif test_group.workers > 1:
                self.__run_test_group_in_parallel(test_group)
            else:
                assert False, 'number of workers must be positive not %s' % test_group.workers
        except SkipTest as s:
            pass
            # TODO: what will we do here?, maybe we should go over whole
            # content and mark everythig as Skipped.
        finally:
            test_group.end_time = datetime.now(tzutc())
            self.plmanager.test_groups.post_test_group(test_group)
        # TODO: need to think out how to report group_result
        if test_group.vital:
            if test_group.failed != 0 or \
                    test_group.skipped != 0 or \
                    test_group.unhandled != 0:
                raise VitalTestFailed(test_group.test_name)

    def __run_test_group_in_parallel(self, test_group):
        jobs = [Job(target=self._run_test_elm, args=(x,))
                for x in test_group]
        if not jobs:
            return
        job_set = JobsSet(test_group.workers)
        job_set.addJobs(jobs)
        job_set.start()
        job_set.join()
        for job in jobs:
            if isinstance(job.exception, VitalTestFailed):
                raise job.exception
        # TODO: check whether something finished with exception

