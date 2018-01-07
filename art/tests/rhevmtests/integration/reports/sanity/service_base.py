import art.unittest_lib as u_lib

from reports.reports_base import ReportsTest


class ServiceTest(ReportsTest):
    """ Base class for tests services """
    @classmethod
    def assert_service_running_logs_exist(cls, machine, service, logs):
        """
        Check if service is running and all logs exist

        Args:
          machine (Host): host where service should run
          service (str): service that should run
          files (list[str]): list containing paths to logs
        """
        cls.assert_service_is_running(machine, service)
        cls.assert_files_exist(machine, logs)

    @staticmethod
    def assert_files_exist(machine, files):
        """
        Check if files in list exists

        Args:
          machine (Host): host where files should be located
          files (list[str]): list containing paths to files
        """
        filesystem = machine.fs
        for filename in files:
            u_lib.testflow.step("Checking %s log file", filename)
            assert filesystem.isfile(filename)

    @staticmethod
    def assert_service_is_enabled(machine, service):
        """
        Check if service is enabled on the machine

        Args:
            machine (Host): host where service should run
            service (str): service that should run
        """
        u_lib.testflow.step("Checking %s service is enabled", service)
        assert machine.service(service).is_enabled()
