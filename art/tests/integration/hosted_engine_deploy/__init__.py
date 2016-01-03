"""
Init file for HE Deploy test
"""
import logging
import config as conf

logger = logging.getLogger(__name__)


def setup_package():
    """
    Download appliance ova file on first host
    """
    if conf.APPLIANCE_OVA_URL:
        dir_to_download = (
            conf.RHEVH_RHEVM_APPLIANCE_DIR if conf.RHEVH_FLAG
            else conf.RHEL_RHEVM_APPLIANCE_DIR
        )
        logger.info(
            "Download rhevm-appliance ova from url %s to host %s",
            conf.APPLIANCE_OVA_URL, conf.VDS_HOSTS[0].fqdn
        )
        conf.APPLIANCE_PATH = conf.VDS_HOSTS[0].download_file(
            url=conf.APPLIANCE_OVA_URL, f_dir=dir_to_download
        )


def teardown_package():
    """
    Remove appliance ova file from host
    """
    if conf.APPLIANCE_PATH:
        if not conf.VDS_HOSTS[0].fs.remove(conf.APPLIANCE_PATH):
            logger.error(
                "Failed to remove appliance ova file from host %s",
                conf.VDS_HOSTS[0].fqdn
            )
