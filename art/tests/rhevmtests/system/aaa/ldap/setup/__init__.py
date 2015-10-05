import os
import logging

from rhevmtests.system.aaa.ldap import config, common


logger = logging.getLogger(__name__)


def setup_module():
    dir_name = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'answerfiles',
    )
    for answerfile in os.listdir(dir_name):
        assert common.setup_ldap(
            host=config.ENGINE_HOST,
            conf_file=os.path.join(dir_name, answerfile),
        )
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
    common.loginAsAdmin()