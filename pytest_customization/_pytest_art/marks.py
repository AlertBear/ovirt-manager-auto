"""
This module contains markers which are widely used in our tests, and include
them to xunit-results which is important for us, since polarion exporter read
polarion ids from this file.

And also implements -A which behaves same as nosetest does. So we don't need
to refactor our tests and keep @attr() decorator.

See https://pytest.org/latest/mark.html
"""
import ast
import pytest
from pkg_resources import parse_version

__all__ = [
    "attr",
    "bz",
    "jira",
    "polarion",
    "pytest_addoption",
    "pytest_configure",
]


# Polarion decorator
polarion = pytest.mark.polarion
polarion.name = 'polarion-id'

# Bugzilla decorator
# https://github.com/rhevm-qe-automation/pytest_marker_bugzilla
bz = pytest.mark.bugzilla

# Jira decorator
# https://github.com/vkondula/pytest_jira/
jira = pytest.mark.jira

# Attrib decorator, same as nose has
attr = pytest.mark.attr


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
            if kwargs.get('tier', tier) > tier:
                tier = kwargs['tier']
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

    def pytest_collection_modifyitems(self, session, config, items):
        for item in items[:]:
            if not self._matches(item):
                items.remove(item)


class JunitExtension(object):
    """
    Add custom properties into junit report.
    """

    markers = (
        'bugzilla',
        'jira',
        'polarion-id',
    )

    attributes = (
        'api',
        'storage',
    )

    global_properties = {
        'Planned In': None,
        'Automated': 'True',
        'ARCH': None
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
            for k, v in self.global_properties.iteritems():
                self.junit.add_global_property(k, v)

    def pytest_runtest_setup(self, item):
        self._add_marks(item)
        self._add_attributes(item)

    def pytest_artconf_ready(self, config):
        self.global_properties['Planned In'] = (
            config.ART_CONFIG['DEFAULT']['PRODUCT'] +
            config.ART_CONFIG['DEFAULT']['VERSION']
        )
        self.global_properties['ARCH'] = (
            config.ART_CONFIG['PARAMETERS']['arch']
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
