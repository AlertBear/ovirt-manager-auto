from art.rhevm_api.resources.service import Service


class Database(Service):

    def __init__(self, host, name, user):
        """
        :param host: Remote resouce to DB machine
        :type host: instance of Host
        :param name: database name
        :type name: str
        :param user: user/role
        :type user: instance of User
        """
        super(Database, self).__init__(host)
        self.name = name
        self.user = user

    def psql(self, sql):
        raise NotImplementedError()

    def restart(self):
        self.host.service('postgresql').restart()
