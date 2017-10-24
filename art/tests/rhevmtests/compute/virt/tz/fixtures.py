import pytest

import config
import rhevmtests.compute.virt.helper as virt_helper
from art.unittest_lib import testflow


@pytest.fixture()
def change_default_tz(request):
    """
    Changes default tz with teardown. Requires tz and tz_val to be set
    via test arguments. Like def test_cli_change_tz(self, tz, tz_val):
    """
    tz = request.getfixturevalue("tz")
    tz_val = request.getfixturevalue('tz_val')
    testflow.step('Get default timezone values')
    default_tz_val = virt_helper.get_default_tz_from_db(config.ENGINE)[tz]
    cmd_tmpl = '{tz}={tz_val}'

    def fin():
        testflow.step('Restore {tz} to {val}'.format(
            tz=tz,
            val=default_tz_val)
        )
        assert config.ENGINE.engine_config(
                action='set',
                param=cmd_tmpl.format(tz=tz, tz_val=default_tz_val)
            ).get('results'), 'Failed to return default value'

    request.addfinalizer(fin)
    testflow.step('Change {tz} value to: {val}'.format(tz=tz, val=tz_val))
    config.ENGINE.engine_config(
        action='set',
        param=cmd_tmpl.format(tz=tz, tz_val=tz_val)
    )
