
from rhevm_utils import RHEVMUtilities, RHEVMUtilsError

def main():
    # just check functionality (testing purposes)
    import logging
    from argparse import ArgumentParser

    logging.basicConfig(level=logging.DEBUG)
    elms = {'setup': [{'help': None}, {'gen-answer-file': '/tmp/aswers'}, \
                {'answer-file': 'host:/root/answer'}],\
            'config': [{'help': None}, {'all': None}, \
                        {'get': 'UserDefinedVMProperties', 'cver': '2.2'},\
                        {'get': 'AdminPassword'},\
                        {'set': 'UserDefinedVMProperties=20', 'cver': '2.2'}],\
            'iso_uploader': [{'help': None}, \
                {'__args': ['list'], 'u': 'admin@internal', 'passwd': '123456'}],\
            'log_collector': [{'help': None}, \
                {'__args': ['list'], 'passwd': '123456'}, \
                {'__args': ['collect']}],\
            'manage_domains': [{'help': None}],\
            'cleanup': [{'help': None}, \
                {'dont_drop_db': None, 'dont_remove_ca': None}],\
            'upgrade' : [{'help': None}]
            }
    tests = elms.keys()

    par = ArgumentParser()
    par.add_argument('-s', '--setup', action='store', dest='host', \
            default='10.34.60.130', help='address of setup (%(default)s)')
    par.add_argument('-u', '--user', action='store', dest='user', \
            default='root', help="username (%(default)s)")
    par.add_argument('-p', '--pass', action='store', dest='passwd', \
            default='123456', help='password (%(default)s)')
    #par.add_argument('-t', '--product', action='store', dest='product', \
    #        default='rhevm', help='product name', choices=('rhevm', 'engine'))
    par.add_argument('-d', '--db-user', action='store', dest='dbuser', \
            default='postgres', help='DB username (%(default)s)')
    par.add_argument('tests', metavar="TEST_NAME", type=str , nargs="*", \
            help='name of utilities: %(choices)s', choices=tests)# default=tests)

    opts = par.parse_args()

    opts.tests = set(opts.tests)

    a = RHEVMUtilities(host=opts.host, user=opts.user, passwd=opts.passwd,\
            #product=opts.product, dbuser=opts.dbuser)
            dbuser=opts.dbuser)

    for test in opts.tests:
        for kwargs in elms.get(test, tuple()):
            args = kwargs.pop('__args', [])
            util  = getattr(a, test)
            try:
                util(*args, **kwargs)
                util.autoTest()
            except RHEVMUtilsError as ex:
                logging.exception(ex)

if __name__ == '__main__':
    main()

