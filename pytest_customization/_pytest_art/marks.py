"""
This module contains markers which are widely used in our tests, and include
them to xunit-results which is important for us, since polarion exporter read
polarion ids from this file.

And also implements -A which behaves same as nosetest does.

Now changed to pytest custom marks. Each class or test case should be decorated
with proper tier marker (tier1, tier2, tier3 and so on)

See https://pytest.org/latest/mark.html
"""
import ast
import re

from pkg_resources import parse_version

import pytest

__all__ = [
    "bz",
    "jira",
    "polarion",
    "pytest_addoption",
    "pytest_configure",
    "timeout",
    "storages",
]

MIN = 60
UNDEFINED_TEAM = "UNDEFINED-TEAM"

# upgrade order
BEFORE_UPGRADE = 1
UPGRADE = 2
BEFORE_UPGRADE_HOSTS = 3
UPGRADE_HOSTS = 4
AFTER_UPGRADE_HOSTS = 5
UPGRADE_CL = 6
AFTER_UPGRADE_CL = 7
UPGRADE_DC = 8
AFTER_UPGRADE = 9

# Polarion decorator
polarion = pytest.mark.polarion

# Bugzilla decorator
# https://github.com/rhevm-qe-automation/pytest_marker_bugzilla
bz = pytest.mark.bugzilla

# Jira decorator
# https://github.com/vkondula/pytest_jira/
jira = pytest.mark.jira

network = pytest.mark.network
sla = pytest.mark.sla
storage = pytest.mark.storage
coresystem = pytest.mark.coresystem
virt = pytest.mark.virt
integration = pytest.mark.integration

# used for tests that are not adjusted to GE or tests that we don't want to run
do_not_run = pytest.mark.do_not_run(value=17)
upgrade = pytest.mark.upgrade(value='upgrade')
tier1 = pytest.mark.tier1(value=1)
tier2 = pytest.mark.tier2(value=2)
tier3 = pytest.mark.tier3(value=3)
tier4 = pytest.mark.tier4(value=4)
timeout = pytest.mark.timeout
storages = pytest.mark.storages

tier_markers = [tier1, tier2, tier3, tier4, upgrade, do_not_run]
team_markers = [network, sla, storage, coresystem, virt, upgrade]

# order markers for ordering tests
order_before_upgrade = pytest.mark.run(order=BEFORE_UPGRADE)
order_upgrade = pytest.mark.run(order=UPGRADE)
order_before_upgrade_hosts = pytest.mark.run(order=BEFORE_UPGRADE_HOSTS)
order_upgrade_hosts = pytest.mark.run(order=UPGRADE_HOSTS)
order_after_upgrade_hosts = pytest.mark.run(order=AFTER_UPGRADE_HOSTS)
order_upgrade_cluster = pytest.mark.run(order=UPGRADE_CL)
order_after_upgrade_cluster = pytest.mark.run(order=AFTER_UPGRADE_CL)
order_upgrade_dc = pytest.mark.run(order=UPGRADE_DC)
order_after_upgrade = pytest.mark.run(order=AFTER_UPGRADE)


def get_item_tier(item):
    """
    Returns tier of item

    Args:
        item (_pytest.python.Function): pytest item

    Returns:
        int: Tier number if specified 0 otherwise
    """

    item_markers = getattr(item.function, 'pytestmark', [])
    tier_marker_names = [mark.name for mark in tier_markers]
    for item_mark in item_markers:
        if item_mark.name in tier_marker_names:
            return item_mark.kwargs['value']
    if item.cls:
        cls_markers = getattr(item.cls, 'pytestmark', [])
        for cls_mark in cls_markers[::-1]:
            if cls_mark.name in tier_marker_names:
                return cls_mark.kwargs['value']
    return 0


def get_item_team(item):
    """
    Returns team of item

    Args:
        item (_pytest.python.Function): Pytest item

    Returns:
        str: Team name if specified, otherwise UNDEFINED_TEAM
    """
    item_markers = getattr(item.function, 'pytestmark', [])
    for item_mark in item_markers:
        if item_mark.name in [mark.name for mark in team_markers]:
            return item_mark.name
    for team_marker in team_markers:
        item_mark_info = item.get_marker(team_marker.name)
        if item_mark_info:
            return item_mark_info.name
    return UNDEFINED_TEAM


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
        self.version = None
        self.upgrade_version = None
        self.expr = expression
        self._names = set()
        for node in ast.walk(ast.parse(expression)):
            if isinstance(node, ast.Name):
                self._names.add(node.id)

    def _matches(self, item, tier, team):
        if not tier or team == UNDEFINED_TEAM:
            return False

        values = dict(tier=tier, team=team)

        # Add all missing names as arg=None
        values.update(
            dict((a, None) for a in self._names - set(values.keys()))
        )

        # Evaluate expression
        try:
            return bool(eval(self.expr, values))
        except Exception:
            return False

    def _match_upgrade_non_relevant_test(self, item, tier):
        after_upgrade = self.version == self.upgrade_version
        run_mark = item.get_marker('run')
        if tier == upgrade.kwargs['value'] and run_mark:
            upgrade_order = run_mark.kwargs.get('order')
            if upgrade_order is not None:
                if after_upgrade:
                    if upgrade_order < BEFORE_UPGRADE_HOSTS:
                        return True
                else:
                    if upgrade_order > UPGRADE:
                        return True
        return False

    def set_tier_timeout(self, item, tier):
        """
        Set timeout to item for specified tier

        Args:
            item (_pytest.python.Function): Pytest item
            tier (int): Tier number
        """
        if not tier or item.get_marker('timeout'):
            return
        _timeout = MIN*60
        if isinstance(tier, int):
            _timeout *= tier
        item_timeout = timeout(_timeout)
        item.add_marker(item_timeout)

    def pytest_collection_modifyitems(self, session, config, items):
        art_config = config.ART_CONFIG
        self.version = art_config['DEFAULT'].get('VERSION')
        self.upgrade_version = art_config['PARAMETERS'].get(
            'upgrade_version', self.version
        )
        for item in items[:]:

            item_tier = get_item_tier(item)
            item_team = get_item_team(item)

            if not self._matches(item, item_tier, item_team):
                items.remove(item)
                continue
            if self._match_upgrade_non_relevant_test(item, item_tier):
                items.remove(item)
                continue

            self.set_tier_timeout(item, item_tier)


class JunitExtension(object):
    """
    Add custom properties into junit report.
    """

    markers = (
        'bugzilla',
        'jira',
        'polarion',
    )

    polarion_attributes = (
        'storage',
    )

    attributes_name_prefix = 'polarion-parameter-'

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
                    if mark_name == 'polarion':
                        self._add_property(item, 'polarion-testcase-id', value)
                    else:
                        self._add_property(item, mark_info.name, value)

    def _add_polarion_attributes(self, item):
        for attr_name in self.polarion_attributes:
            attr_value = getattr(item.parent.obj, attr_name, None)
            if attr_value:
                self._add_property(
                    item, self.attributes_name_prefix + attr_name, attr_value
                )

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
        # TODO remove comment once relevant tests will have storage param
        # in polarion (pending on Gil)
        # self._add_polarion_attributes(item)

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
            pattern = re.compile("tier==\S*")
            tag_exp = "_".join(
                re.findall(pattern, tag_exp)
            ).replace("=", "").replace("'", "")
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
