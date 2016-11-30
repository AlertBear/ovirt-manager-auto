#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Search for missing tags in TesCases
"""

import os
import re
import argparse
import inspect
import logging
from types import FunctionType
from art_wrapper import art, FakeDict
import rhevmtests  # noqa

EXCLUDE_TESTS = ["regression_infra", "builder", "cleaner"]


class IsTagsMissing(object):
    """
    Search for missing tags in TestCase
    """
    def __init__(self, start_dir, tags=None):
        """
        Search for missing tags in TestCase
        :param start_dir: Start directory to search for TestCases
        :type start_dir: str
        :param tags: Tags to search in TestCases
        :type tags: list
        """
        self.start_dir = start_dir
        self.tags = tags
        self.notok = {}
        self.f = None
        self.cls_obj = None
        self.summary = None
        self.bad_idx = 0
        self.good_idx = 0
        self.import_name = None
        self.cls_tags = []
        self.import_fail = []
        self.base_point = None

    def run(self):
        """
        Search for missing tags in TestCase
        :return: TestCases without tags, summary and imports that fail
        :rtype: tuple
        """
        for root, dirs, files in os.walk(self.start_dir):
            for self.f in files:
                if root.rsplit("/", 1)[-1] in EXCLUDE_TESTS:
                    continue

                if not self.f.endswith(".py"):
                    continue

                if self.f.startswith(
                    "__init__"
                ) or self.f.startswith(
                    "config"
                ) or 'test' not in self.f:
                    continue

                self.base_point = re.findall(r'rhevmtests.*', root)[0]
                m_ = re.findall(r'.*\.', self.f)[0].rstrip('.')
                self.import_name = "{0}.{1}".format(
                    self.base_point.replace("/", "."), m_
                )
                self.inspect_import()

        self.summary = "Missing: {0}\nOK: {1}\nTotal: {2}".format(
            self.bad_idx, self.good_idx, self.bad_idx + self.good_idx
        )
        return self.notok, self.summary, self.import_fail

    def inspect_import(self):
        """
        Import the relevant module and search for missing tags
        """
        test = None
        try:
            __import__(self.import_name)
        except Exception:
            self.import_fail.append(self.import_name)

        try:
            test = inspect.getmembers(eval(self.import_name), inspect.isclass)
        except AttributeError:
            pass

        if test:
            for name, obj in test:
                for cls_ in inspect.getmro(obj):
                    self.cls_obj = cls_
                    if self.is_class_test():
                        if self.is_tags_in_cls():
                            break
                        if self.is_tags_in_funcs():
                            break

    def is_class_test(self):
        """
        Check if class is TestCase
        :return: True/False
        :rtype: bool
        """
        try:
            return self.cls_obj.__test__
        except AttributeError:
            return False

    def is_tags_in_cls(self):
        """
        Search for tags in class
        :return: True/False
        :rtype: bool
        """
        self.cls_tags = []
        for t in self.tags:
            try:
                getattr(self.cls_obj, t)
                self.cls_tags.append(t)
            except AttributeError:
                pass
        if len(self.tags) == len(self.cls_tags):
            cls_funcs = self.get_funcs_from_class()
            self.good_idx += len(cls_funcs)
        return False

    def is_tags_in_funcs(self):
        """
        Search for tags in functions
        """
        cls_funcs = self.get_funcs_from_class()
        for func in cls_funcs:
            for tag in self.tags:
                if tag in self.cls_tags:
                    continue
                try:
                    getattr(func, tag)
                    self.good_idx += 1
                except AttributeError:
                    self.notok[func.func_name] = os.path.join(
                        self.base_point, self.f
                    )
                    self.bad_idx += 1
                    break

    def get_funcs_from_class(self):
        """
        Get all functions from class
        :return: all functions
        :rtype: list
        """
        is_func = [
            (i[1], isinstance(i[1], FunctionType)) for i in
            self.cls_obj.__dict__.iteritems()
        ]
        return [
            i[0] for i in filter(lambda x: x[1] is True, is_func)
        ]


def main():
    """
    Find missing tags in TestCases
    """
    sh = logging.StreamHandler()
    logging.getLogger().addHandler(sh)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Find missing tags in TestCases"
    )
    parser.add_argument(
        "-c", "--config_file", action="store", help="Config file",
        required=True
    )
    parser.add_argument(
        "-t", "--tags", action="store", help="Tags to search", required=True
    )
    parser.add_argument(
        "-d", "--tests_dir", action="store", help="TestCases directory",
        required=True
    )
    options = parser.parse_args()
    art_config = options.config_file
    art(art_config)
    import rhevmtests.config as rc
    new_params = FakeDict(lambda: "fake_value")
    new_params.update(rc.PARAMETERS)
    rc.PARAMETERS = new_params
    tags_list = options.tags.split(",")
    mt = IsTagsMissing(start_dir=options.tests_dir, tags=tags_list)
    notok, summary, import_fail = mt.run()
    for x, y in notok.iteritems():
        logger.error("Test: %s (File: %s)", x, y)
    logger.error("\n%s\nFailed imports: %s", summary, import_fail)
    if notok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
