import pytest

from art.unittest_lib import testflow, attr


@pytest.mark.coresystem
@attr(team="coresystem")
class ServicesTest(object):
    """ Base class for tests services """

    apis = set(["rest", "java", "sdk"])

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
