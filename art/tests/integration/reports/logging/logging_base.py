from art.unittest_lib import testflow

from reports.reports_base import ReportsTest
import config


class LoggingTest(ReportsTest):
    """Base class for logging test"""
    @staticmethod
    def assert_grep_diff_logs(
            search,
            log_file=config.DWH_LOG,
            backup_log_file=config.DWH_LOG_BACKUP,
            lines=0
    ):
        """
        Grep diff of two log files

        Args:
            search (str): grepped string
            log_file (str): log file
            backup_log_file (str): backup of the same log file from past
            lines (int): append number of lines to grep
        Returns
            str: return grepped string from diff of two files
        """
        testflow.step("Grepping dwh log")
        cmd = [
            'diff', '-e', backup_log_file, log_file, '|',
            'grep', '-F', search, '-A' + str(lines), '|',
            'grep', '-Fv', 'tWarn'
        ]
        result = config.ENGINE_HOST.run_command(command=cmd)
        assert not result[0]

        return result[1]

    @staticmethod
    def assert_backup_file(file_name, backup_file):
        """
        Create a backup for file

        Args:
            file (str): file to be backed up
            backup_file (str): service that should run
        """
        testflow.step("Backing up %s log to %s", file_name, backup_file)
        cmd = ['cp', file_name, backup_file]
        assert config.ENGINE_HOST.run_command(command=cmd), (
            "Error: Unable to backup {0}".format(file_name)
        )

    @staticmethod
    def assert_remove_backup(file_name):
        """
        Remove backup file

        Args:
            file (str): backed up file to be removed
        """
        testflow.step("Removing backup {0}".format(file_name))
        assert config.ENGINE_HOST.run_command(['rm', file_name])

    @staticmethod
    def assert_setting_variable(settings, var, val):
        """
        Check value of application server variable

        Args:
            settings (dict): dictionary with settings 'key':value
            var (str): variable to find
            val (str): value to check
        """
        assert var in settings.keys(), "Variable {0} not found.".format(var)
        assert val in settings[var], (
            "Option {0} with value {1} not in: {2}".format(var, val, settings)
        )
