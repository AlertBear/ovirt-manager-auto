"""
This module contains markers which are widely used in our tests.

See https://pytest.org/latest/mark.html
"""
import ast
import pytest


__all__ = [
    "attr",
    "bz",
    "jira",
    "polarion",
    "pytest_addoption",
    "pytest_configure",
]


# Polarion decorator
polarion = pytest.mark.polarion('polarion-id')

# Bugzilla decorator
# Consider using 3rd part, I don't think it will suite us ...
# https://github.com/davehunt/pytest-bugzilla/blob/master/pytest_bugzilla.py
bz = pytest.mark.bugzilla('bz-id')

# Jira decorator
# Consider using 3rd part, it could suite us ...
# missing components support, we could send patch.
jira = pytest.mark.jira('jira-id')

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
        'polarion',
    )

    attributes = (
        'api',
        'storage',
    )

    def __init__(self, config):
        super(JunitExtension, self).__init__()
        self._conf = config

    @property
    def junit(self):
        return getattr(self._conf, '_xml', None)

    def _add_marks(self, item):

        for mark_name in self.markers:
            mark_info = item.get_marker(mark_name)
            if mark_info:
                self.junit.add_custom_property(mark_info.name, *mark_info.args)

    def _add_attributes(self, item):
        for attr_name in self.attributes:
            attr_value = getattr(item.parent.obj, attr_name, None)
            if attr_value:
                self.junit.add_custom_property(attr_name, attr_value)

    def pytest_runtest_setup(self, item):
        self._add_marks(item)
        self._add_attributes(item)


def pytest_configure(config):
    if config.getoption('-A'):
        config.pluginmanager.register(
            AttribDecorator(config.getoption('-A'))
        )
    if tuple(pytest.__version__.split('.')) < ('2', '8', '3'):
        # NOTE(lbednar): this feature was released in 2.8.3
        return

    if config.pluginmanager.hasplugin('junitxml'):
        config.pluginmanager.register(JunitExtension(config))
