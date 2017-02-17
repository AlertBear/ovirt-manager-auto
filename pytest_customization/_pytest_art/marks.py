"""
This module contains markers which are widely used in our tests, and include
them to xunit-results which is important for us, since polarion exporter read
polarion ids from this file.

And also implements -A which behaves same as nosetest does. So we don't need
to refactor our tests and keep @attr() decorator.

See https://pytest.org/latest/mark.html
"""
import ast
import re

from pkg_resources import parse_version

import pytest

__all__ = [
    "attr",
    "bz",
    "jira",
    "polarion",
    "pytest_addoption",
    "pytest_configure",
    "timeout",
]

MIN = 60

# Polarion decorator
polarion = pytest.mark.polarion
polarion.name = 'polarion-testcase-id'

# Bugzilla decorator
# https://github.com/rhevm-qe-automation/pytest_marker_bugzilla
bz = pytest.mark.bugzilla

# Jira decorator
# https://github.com/vkondula/pytest_jira/
jira = pytest.mark.jira

# Attrib decorator, same as nose has
attr = pytest.mark.attr

network = pytest.mark.network
sla = pytest.mark.sla
storage = pytest.mark.storage
coresystem = pytest.mark.coresystem
virt = pytest.mark.virt
do_not_run = pytest.mark.do_not_run
integration = pytest.mark.integration
tier1 = pytest.mark.tier1
tier2 = pytest.mark.tier2
tier3 = pytest.mark.tier3
tier4 = pytest.mark.tier4
timeout = pytest.mark.timeout


def pytest_addoption(parser):

    parser.addoption(
        '-A',
        dest='attr_expr',
        default=None,
        help="You can pass pythonic expression to match tests to run.",
    )


class AttribDecorator(object):
    """
    It adds option to filter tests according to pythonic expression.
    """

    def __init__(self, expression):
        super(AttribDecorator, self).__init__()
        self.expr = expression
        self._names = set()
        for node in ast.walk(ast.parse(expression)):
            if isinstance(node, ast.Name):
                self._names.add(node.id)

    def _get_keywords(self, mark):
        """
        FIXME: Following doc string describes problematic parts.

        Purpose of this function is fix order of MarkInfo.kwargs attribute.
        (I Sent patch to pytest repository, waiting for response.)

        Problematic case NO#1:

        @attr(tier=1)
        class A(TestCase):
            @attr(tier=2)
            def test_one():  # Here MarkInfo.kwargs == {'tier': 1}
                pass

        Problematic case NO#2:

        @attr(tier=1)
        class A(object):
            __test__ = False

        @attr(tier=2)
        class B(A):
            def test_one(self):  # Here is tier=1
                pass

        Unfortunately these two cases goes against to each other.
        I decided to pick up the highest tier number for tier,
        and reverse order applied keywords to add precedence to decorated
        methods before class inheritance.
        """
        keywords = {}
        tier = 0
        for _, kwargs in mark._arglist[::-1]:
            item_tier = kwargs.get('tier', tier)
            if isinstance(item_tier, str):
                tier = item_tier
                break
            if item_tier > tier:
                tier = item_tier
            keywords.update(kwargs)
        if tier:
            keywords['tier'] = tier
        return keywords

    def _matches(self, item):
        m = item.get_marker('attr')
        if not m:
            return False
        # Get regular keywords
        values = self._get_keywords(m)
        # Add agrs as arg=True keyword
        values.update(
            dict((a, True) for a in m.args if a != 'attr')
        )
        # Add all missing names as arg=None
        values.update(
            dict((a, None) for a in self._names - set(values.keys()))
        )

        # This is maybe redundant
        if not self._names.issubset(set(values.keys())):
            return False

        # Evaluate expression
        try:
            return bool(eval(self.expr, values))
        except Exception:
            return False

    def set_tiers_timeout(self, items):
        """
        Set timeout to all tiers
        """
        for index, item in enumerate(items[:]):
            item_attr = item.get_marker('attr')
            if not item_attr or item.get_marker('timeout'):
                continue
            item_tier = item_attr.kwargs.get("tier")
            if not item_tier:
                break
            _timeout = MIN*60
            if isinstance(item_tier, int):
                _timeout *= item_tier
            item_timeout = timeout(_timeout)
            items[index].add_marker(item_timeout)

    def pytest_collection_modifyitems(self, session, config, items):
        for item in items[:]:
            if not self._matches(item):
                items.remove(item)
        self.set_tiers_timeout(items)


class JunitExtension(object):
    """
    Add custom properties into junit report.
    """

    markers = (
        'bugzilla',
        'jira',
        'polarion-testcase-id',
    )

    attributes = (
        'api',
        'storage',
    )

    polarion_importer_properties = {
        'polarion-project-id': None,
        'polarion-user-id': None,
        'polarion-response-myproduct': None,
        'polarion-testrun-id': None,
    }

    global_properties = {
        'polarion-custom-plannedin': None,
        'polarion-custom-isautomated': 'True',
        'polarion-custom-arch': None,
    }

    def __init__(self, config):
        super(JunitExtension, self).__init__()
        self._conf = config

    @property
    def junit(self):
        return getattr(self._conf, '_xml', None)

    def _add_property(self, item, name, value):
        if parse_version(pytest.__version__) >= parse_version("2.8.3"):
            reporter = self.junit.node_reporter(item.nodeid)
            reporter.add_property(name, value)
        else:
            self.junit.add_custom_property(name, value)

    def _add_marks(self, item):
        for mark_name in self.markers:
            mark_info = item.get_marker(mark_name)
            if mark_info:
                for value in mark_info.args:
                    self._add_property(item, mark_info.name, value)

    def _add_attributes(self, item):
        for attr_name in self.attributes:
            attr_value = getattr(item.parent.obj, attr_name, None)
            if attr_value:
                self._add_property(item, attr_name, attr_value)

    def _add_global_properties(self):
        # junit.add_global_property(k, v) will be available in pytest 2.10.1
        # This will check if the junit have such method and if not we simply
        # won't add global properties node
        if getattr(self.junit, 'add_global_property', None):
            all_properties = dict(
                self.global_properties, **self.polarion_importer_properties
            )
            for k, v in all_properties.iteritems():
                self.junit.add_global_property(k, v)

    def pytest_runtest_setup(self, item):
        self._add_marks(item)
        self._add_attributes(item)

    def pytest_artconf_ready(self, config):
        self.global_properties['polarion-custom-plannedin'] = (
            'RHV_' +
            config.ART_CONFIG['DEFAULT']['VERSION'].replace(".", "_")
        )
        self.global_properties['polarion-custom-arch'] = (
            config.ART_CONFIG['PARAMETERS']['arch'].replace("_", "")
        )
        self.polarion_importer_properties['polarion-project-id'] = (
            config.ART_CONFIG['PARAMETERS']['polarion_project']
        )
        self.polarion_importer_properties['polarion-user-id'] = (
            config.ART_CONFIG['PARAMETERS']['polarion_user']
        )
        self.polarion_importer_properties['polarion-response-myproduct'] = (
            config.ART_CONFIG['PARAMETERS']['polarion_response_myproduct']
        )

        # manipulate the tag expression to get the tier value
        # it will get multiple values in case they exists,
        # but it is not expected in production jobs
        tag_exp = config.getoption('-A')
        if tag_exp:
            pattern = re.compile("tier==\S")
            tag_exp = "_".join(re.findall(pattern, tag_exp)).replace("=", "")
        else:
            tag_exp = ''

        self.polarion_importer_properties['polarion-testrun-id'] = (
            "RHV_{0}_{1}_{2}".format(
                config.ART_CONFIG['DEFAULT']['VERSION'],
                tag_exp,
                config.ART_CONFIG['PARAMETERS']['arch']
            ).replace(".", "_")
        )

    def pytest_sessionstart(self, session):
        self._add_global_properties()


def pytest_configure(config):
    if config.getoption('-A'):
        config.pluginmanager.register(
            AttribDecorator(config.getoption('-A'))
        )

    if parse_version(pytest.__version__) <= parse_version("2.8.3"):
        return

    if config.pluginmanager.hasplugin('junitxml'):
        config.pluginmanager.register(JunitExtension(config))


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" % previousfailed.name)
