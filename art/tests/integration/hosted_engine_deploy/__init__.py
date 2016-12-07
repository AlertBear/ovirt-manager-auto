"""
Init file for HE Deploy test
"""
import os
import logging
import config as conf

logger = logging.getLogger(__name__)


def setup_package():
    """
    Download appliance ova file on first host
    """
    conf.RHEVH_FLAG = conf.VDS_HOSTS[0].os.distribution.distname == conf.RHEVH
    if conf.APPLIANCE_OVA_URL:
        dir_to_download = (
            conf.RHEVH_RHEVM_APPLIANCE_DIR if conf.RHEVH_FLAG
            else conf.RHEL_RHEVM_APPLIANCE_DIR
        )
        logger.info(
            "Download rhevm-appliance ova from url %s to host %s",
            conf.APPLIANCE_OVA_URL, conf.VDS_HOSTS[0].fqdn
        )
        file_path = os.path.join(dir_to_download, "rhevm-appliance.ova")
        conf.APPLIANCE_PATH = conf.VDS_HOSTS[0].fs.wget(
            url=conf.APPLIANCE_OVA_URL,
            output_file=file_path,
            progress_handler=lambda msg: logger.info(msg=msg)
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
