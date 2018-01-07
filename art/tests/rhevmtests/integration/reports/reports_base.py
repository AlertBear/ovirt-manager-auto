from time import sleep

import art.unittest_lib as u_lib

from art.unittest_lib import CoreSystemTest as TestCase


class ReportsTest(TestCase):
    """ Base class for reports tests """
    @staticmethod
    def assert_service_is_running(machine, service):
        """
        Check if service is running on the machine

        Args:
            machine (Host): host where service should run
            service (str): service that should run
        """
        u_lib.testflow.step("Checking %s service is running", service)
        assert machine.service(service).status()

    @classmethod
    def assert_service_restart(cls, machine, service, sleep_time=0):
        """
        Check if service is running after restart

        Args:
            machine (Host): host where service should be restarted
            service (str): service to restart
            sleep_time (int): wait for number of seconds after restart
        """
        u_lib.testflow.step("Restarting %s service", service)
        assert machine.service(service).restart()
        cls.assert_service_is_running(machine, service)
        sleep(sleep_time)
