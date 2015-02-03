from art.test_handler.settings import initPlmanager


class FakeIssue(object):

    class Fields(object):
        pass

    class Version(object):
        def __init__(self, name):
            self.name = name

    class Component(object):
        def __init__(self, name):
            self.name = name

    def __init__(self, id_, summary='Summary', resolution=None, affects=None,
                 fixed_in=None, components=None):
        self.fields = FakeIssue.Fields()
        self._add_field('summary', summary)
        self._add_field('resolution', resolution)
        if affects is None:
            self._add_field('versions', list())
        else:
            self._add_field(
                'versions',
                [FakeIssue.Version(v) for v in affects],
            )
        if fixed_in is None:
            self._add_field('fixed_in', list())
        else:
            self._add_field(
                'fixVersions',
                [FakeIssue.Version(v) for v in fixed_in],
            )
        if components is None:
            self._add_field('components', list())
        else:
            self._add_field(
                'components',
                [FakeIssue.Component(c) for c in components],
            )

    def _add_field(self, name, value):
        setattr(self.fields, name, value)


FAKE_ISSUES = {
    'ISSUE-1': FakeIssue(
        'ISSUE-1',
        summary="Easy skip, opened issue",
    ),
    'ISSUE-2': FakeIssue(
        'ISSUE-2',
        summary="Easy run, closed issue",
        resolution="Closed",
        fixed_in=["ovirt-3.4"],
    ),
    'ISSUE-3': FakeIssue(
        'ISSUE-3',
        summary="Run only when version >= 3.5",
        resolution="Closed",
        fixed_in=['ovirt-3.5'],
    ),
    'ISSUE-4': FakeIssue(
        'ISSUE-4',
        summary="Skip when version is 3.4",
        affects=['ovirt-3.4'],
    ),
    'ISSUE-5': FakeIssue(
        'ISSUE-5',
        summary="Skip when engine is SDK",
        components=['oVirt-API-PythonSDK'],
    ),
    'ISSUE-6': FakeIssue(
        'ISSUE-6',
        summary="Skip for version 3.4 & SDK, but run for 3.5.",
        resolution="Closed",
        affects=['ovirt-3.4', 'ovirt-3.5'],
        fixed_in=['ovirt-3.5'],
        components=['oVirt-API-PythonSDK'],
    ),
    'ISSUE-7': FakeIssue(
        'ISSUE-7',
        summary="Skip for CLI",
        components=['oVirt-API-CLI'],
    ),
}


def get_plugin(name):
    plmanager = initPlmanager()
    return [pl for pl in plmanager.configurables if pl.name == name][0]


def setup_package():
    plugin = get_plugin("Jira")
    plugin._cache = FAKE_ISSUES
