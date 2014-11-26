from art.unittest_lib import CoreSystemTest as TestCase
from rhevm_api.resources.filesystem import FileSystem
from reports.config import LOGGER


class ServiceTest(TestCase):
    """ Base class for tests services """
    __test__ = False

    def assert_service_running_logs_exist(self, machine, service, logs):
        """
        Check if service is running and all logs exist
        :param machine: (Host object) host where service should run
        :param service: (string) service that should run
        :param logs: (list of strings) list containing paths to logs
        :param logger: logger
        """
        self.assert_service_is_running(machine, service)
        self.assert_files_exist(machine, logs)

    def assert_service_is_running(self, machine, service):
        """
        Check if service is running on machine
        :param machine: (Host object) host where service should run
        :param service: (string) service that should run
        :param logger: logger
        """
        LOGGER.info("Test if %s service is running", service)
        self.assertTrue(
            machine.service(service).status(),
            "%s is not running" % service
        )

    def assert_files_exist(self, machine, files):
        """
        Check if all files in list exist
        :param machine: (Host object) host where service should run
        :param files: (list of strings) list containing paths to logs
        :param logger: logger
        """
        filesystem = FileSystem(machine)
        for filename in files:
            LOGGER.info("Test if %s exists", filename)
            self.assertTrue(
                filesystem.isfile(filename),
                'File %s does not exist' % filename
            )

    def assert_service_is_enabled(self, machine, service):
        """
        Check if service is enabled
        :param machine: (Host object) host where service should be enabled
        :param service: (string) service name
        :param logger: logger
        """
        LOGGER.info("Test if %s service is enabled", service)
        self.assertTrue(
            machine.service(service).is_enabled(),
            "%s is not enabled" % service
        )
