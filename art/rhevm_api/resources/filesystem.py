from art.rhevm_api.resources.service import Service


class FileSystem(Service):
    """
    class for working with filesystem
    """
    def _exec_file_test(self, op, path):
        return self.host.executor().run_cmd(
            ['[', '-%s' % op, path, ']'])[0] == 0

    def exists(self, path):
        return self._exec_file_test('e', path)

    def isfile(self, path):
        return self._exec_file_test('f', path)

    def isdir(self, path):
        return self._exec_file_test('d', path)
