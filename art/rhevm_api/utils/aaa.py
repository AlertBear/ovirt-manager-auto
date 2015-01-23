"""
This file provides utilities to manage ADs using AAA.
(Authentication, Authorization and Accounting)

You can find description of feature here:
http://www.ovirt.org/Features/AAA#Mapping
"""

import logging


LOGGER = logging.getLogger(__name__)


def copy_extension_file(host, ext_file, target_file, chown):
    """
    :param host: host where copy file to
    :type host: instance of resources.Host
    :param ext_file: file to copy
    :type ext_file: str
    :param target_file: file to create
    :type target_file: str
    :param chown: permission to set
    :type chown: str / int
    """
    with host.executor().session() as ss:
        with open(ext_file) as fhs:
            with ss.open_file(target_file, 'w') as fhd:
                fhd.write(fhs.read())
        if chown:
            chown_cmd = [
                'chown', '%s:%s' % (chown, chown), target_file,
            ]
            res = ss.run_cmd(chown_cmd)
            assert not res[0], res[1]
    LOGGER.info('Configuration "%s" has been copied.', ext_file)
