
from utilities.errors import GeneralException



class RHEVMUtilsError(GeneralException):
    message = "failed to run rhevm utility"

class ProductIsNotInstaled(RHEVMUtilsError):
    message = "there is no product"

class ExecuteDBQueryError(RHEVMUtilsError):
    message = "failed to exec sql query"
    def __init__(self, host, sql, rc, out, err):
        self.kwargs = {'msg': self.message, 'sql': sql, 'rc': rc, 'out': out, \
                'err': err, 'host': host}
    def __str__(self):
        return "{msg} host({host}): {sql}; RC: {rc}; out: {out}; err: {err}".format(**self.kwargs)

class CheckFileError(RHEVMUtilsError):
    pass

class FileTransferError(RHEVMUtilsError):
    pass

class ReturnCodeError(RHEVMUtilsError):
    def __init__(self, exprc, rc, out, err):
        self.args = [exprc, rc, out, err]
    def __str__(self):
        return "Unexpected RC code, expected: {0}, got: RC: {1}, out: {2}; "\
                "err: {3}".format(*self.args)

class UnrecognizedError(RHEVMUtilsError):
    message = "failed to recognize error message in"

class OutputVerificationError(RHEVMUtilsError):
    message = "failed to find expected string"

class InvalidParameter(RHEVMUtilsError):
    message = "failed to parse arguments"

class InvalidAction(InvalidParameter):
    message = "invalid action"

class MissingParameter(InvalidParameter):
    message = "parameter is required"

class InconsistentDataInDB(RHEVMUtilsError):
    message = "there are some wrong data in DB"

class AddSnapshotFailure(RHEVMUtilsError):
    message = "failed to add snapshot"

class RestoreSnapshotFailure(RHEVMUtilsError):
    message = "failed to restore snapshot"

# SETUP

class SetupUtilityError(RHEVMUtilsError):
    pass

class MissingAnswerFile(SetupUtilityError):
    message = "failed to find generated answer file"

class RHEVMIsNotInstalledProperly(SetupUtilityError):
    message = "installation is not complete"

class MissingDatabase(RHEVMIsNotInstalledProperly):
    message = "there is no DB after instalation"

class JbossIsNotRunning(RHEVMIsNotInstalledProperly):
    message = "jboss is not running"

class WrongOptionsInAnswerFile(SetupUtilityError):
    message = "wrong otion in answer file"

class MissingPTRRecord(WrongOptionsInAnswerFile):
    message = "missing PTR for host"

class MountPointIsNotValidPath(WrongOptionsInAnswerFile):
    message = "mount point is not valid path"

class EmptyParamInAnswerFile(WrongOptionsInAnswerFile):
    message = "param can't be empty"

class HTTPConnectionError(SetupUtilityError):
    message = "cannot connect to http server"

# CONFIG

class ConfigUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-config"

class MissingPropertyFile(ConfigUtilityError):
    message = "property file doesn't exist"

class FetchOptionError(ConfigUtilityError):
    message = "there is no such option"

class OptionIsNotAllowed(FetchOptionError):
    message = "option is not allowed"

class FailedToSetValue(ConfigUtilityError):
    message = "Variable was not set properly"


# ISO_UPLOADER

class ISOUploadUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-iso-upload"

class AuthorizationError(ISOUploadUtilityError):
    message = "failed to authorizate"

# MANAGE_DOMAINS

class ManageDomainsUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-manage-domains"

class DomainAlreadyExists(ManageDomainsUtilityError):
    message = "Domain already exists in DB"

class DomainDoesNotExists(ManageDomainsUtilityError):
    message = "Domain doens't exists"

class MissingDmainError(ManageDomainsUtilityError):
    message = "can't find added domain"

class RedundantDmainError(ManageDomainsUtilityError):
    message = "there is still removed domain"

class UnexpectedUserError(ManageDomainsUtilityError):
    message = "there is unexpected user"

# UPGRADE

class UpgradeUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-upgrade"

# CLEAN

class CleanUpUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-cleanup"

class DBExistsError(CleanUpUtilityError):
    message = "database still exists, but it shouldn't"

class DBDoesntExistError(CleanUpUtilityError):
    message = "database doesn't exist, but it should"

class CAExistsError(CleanUpUtilityError):
    message = "rhevm CA still exists, but it shouldn't"

class CADoesntExistError(CleanUpUtilityError):
    message = "rhevm CA doesn't exist, but it should"

class ProfileExistsError(CleanUpUtilityError):
    message = "jboss profile still exists, but it shouldn't"

class ProfileDoesntExistError(CleanUpUtilityError):
    message = "jboss profile doesn't exist, but it should"

class JbossIsStillRunning(CleanUpUtilityError):
    message = "jboss service is running"


# LOG_COLLECTOR

class LogCollectorUtilityError(RHEVMUtilsError):
    message = "error occured during rhevm-log-collector"

class ReportsExtractionError(LogCollectorUtilityError):
    message = "failed to extract reports"

class ReportsVerificationError(LogCollectorUtilityError):
    message = "reports verification failed"

class RHEVMReportsVerificationError(ReportsExtractionError):
    message = "rhevm reports verification failed"

class DBReportsVerificationError(ReportsExtractionError):
    message = "database reports verification failed"

class HostReportsVerificationError(ReportsExtractionError):
    message = "host reports verification failed"

class ListActionVerification(LogCollectorUtilityError):
    message = "list verification failed"

# ==================

class SetupsManagerError(RHEVMUtilsError):
    pass

class WaitForStatusTimeout(SetupsManagerError):
    message = "waiting timeout for status expired"

class NoIpFoundError(SetupsManagerError):
    message = "failed to retrieve ip"
