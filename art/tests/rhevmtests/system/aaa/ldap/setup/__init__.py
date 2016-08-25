import os
import logging

from rhevmtests.system.aaa.ldap import config, common


logger = logging.getLogger(__name__)


def setup_package():
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

    for answerfile in os.listdir(dir_name):
        assert common.setup_ldap(
            host=config.ENGINE_HOST,
            conf_file=os.path.join(dir_name, answerfile),
        )
        if 'w2k12r2' in answerfile:
            common.append_to_file(executor, ext_ad_file, properties, mode='a')
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
    common.loginAsAdmin()


def teardown_package():
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)
    common.cleanExtDirectory(config.AAA_DIR)
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
