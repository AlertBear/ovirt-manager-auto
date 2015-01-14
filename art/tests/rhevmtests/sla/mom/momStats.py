import sys
from xmlrpclib import ServerProxy

if __name__ == "__main__":
    mom = ServerProxy("http://localhost:%s" % sys.argv[1])
    print(mom.getStatistics())
