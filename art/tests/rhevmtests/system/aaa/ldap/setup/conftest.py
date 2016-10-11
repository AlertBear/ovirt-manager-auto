import os
import logging
import pytest

from rhevmtests.system.aaa.ldap import config, common

from art.unittest_lib import testflow


logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def setup_session(request):
    def finalize():
        testflow.teardown("Tearing down module %s", __name__)

        testflow.teardown("Disabling AAA debug logs")
        common.enable_aaa_debug_logs(config.ENGINE_HOST, disable=True)

        testflow.teardown(
            "Cleaning %s directory", config.ENGINE_EXTENSIONS_DIR
        )
        common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)

        testflow.teardown("Cleaning %s directory", config.AAA_DIR)
        common.cleanExtDirectory(config.AAA_DIR)

        testflow.teardown("Restarting engine")
        common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)
    dir_name = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../answerfiles',
    )
    ad_profile = 'ad-w2k12r2'
    executor = config.ENGINE_HOST.executor()
    ext_ad_file = '/etc/ovirt-engine/aaa/%s.properties' % ad_profile
    properties = {
        'pool.default.serverset.srvrecord.domain-conversion.'
        'type': 'regex',
        'pool.default.serverset.srvrecord.domain-conversion.'
        'regex.pattern': '^(?<domain>.*)$',
        'pool.default.serverset.srvrecord.domain-conversion.'
        'regex.replacement': 'BRQ._sites.${domain}',
    }

    testflow.setup("Enabling AAA debug logs")
    common.enable_aaa_debug_logs(config.ENGINE_HOST)

    testflow.setup("Setting up LDAPs")
    for answerfile in os.listdir(dir_name):
        assert common.setup_ldap(
            host=config.ENGINE_HOST,
            conf_file=os.path.join(dir_name, answerfile),
        )
        if 'w2k12r2' in answerfile:
            common.append_to_file(executor, ext_ad_file, properties, mode='a')
    testflow.setup("Restarting engine")
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
    testflow.setup("Logging as admin")
    common.loginAsAdmin()
