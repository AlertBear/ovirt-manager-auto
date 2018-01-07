import re
import logging
from datetime import datetime, timedelta

from art.unittest_lib import testflow, CoreSystemTest as TestCase

import config

logger = logging.getLogger(__name__)


class ServicesTest(TestCase):
    """ Base class for tests services """

    @staticmethod
    def assert_service_is_running(machine, service):
        """
        Check if service is running on the machine

        Args:
            machine (Host): host where service should run
            service (str): service that should run
        """
        testflow.step(
            "Checking %s service is running on host %s", service, machine.fqdn
        )
        assert machine.service(service).status()

    @staticmethod
    def assert_service_is_enabled(machine, service, positive=True):
        """
        Check if service is enabled on the machine

        Args:
            machine (Host): host where service should run
            service (str): service that should run
            positive (bool): if service should be enabled
        """
        testflow.step(
            "Checking %s service is %s on host %s",
            service,
            "enabled" if positive else "disabled",
            machine.fqdn
        )
        assert machine.service(service).is_enabled() is positive

    @staticmethod
    def assert_service_is_faultless(machine, service):
        """
        Check if services unit file contains any errors or warnings.
        Fails when it finds a traceback,
        otherwise only logger warning is reported.

        Args:
            machine (Host): host where service should run
            service (str): service that should run
        """
        date_since = (
            datetime.now() - timedelta(days=config.DAYS_TO_CHECK_LOGS)
        ).strftime("%F")
        cmd = ['journalctl', '--unit', service, '-p', '0..4', '-S', date_since]
        testflow.step(
            "Running command %s on machine %s", " ".join(cmd), machine.fqdn
        )
        rc, out, err = machine.executor().run_cmd(cmd)
        assert not int(rc), (
            "journalctl cmd on machine %s failed with error %s" % (
                machine.fqdn, err
            )
        )
        out = out.split('\n', 1)[1]
        if out:
            testflow.step(
                "Check if unit file of %s service on host %s "
                "contains any errors or warnings",
                service,
                machine.fqdn
            )
            logger.warning(
                "On machine %s there were these errors/warnings: %s",
                machine.fqdn, out
            )
            tracebacks = []
            for match in re.finditer(
                "((.*\n)^.*?traceback.*?$(.*\n)*?)[a-z]{3} [0-9]{1,2}",
                out, re.MULTILINE | re.IGNORECASE
            ):
                tracebacks.append(match.group(1))
            testflow.step(
                "Check if there are any tracebacks on machine %s",
                machine.fqdn
            )
            assert not tracebacks, (
                "On machine %s these tracebacks were found: %s" % (
                    machine.fqdn, '\n'.join(tracebacks)
                )
            )
        else:
            logger.info(
                "journalctl output was empty, "
                "no errors nor warnings were found"
            )
