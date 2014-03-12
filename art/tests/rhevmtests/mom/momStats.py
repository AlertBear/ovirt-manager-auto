import sys
from xmlrpclib import ServerProxy
mom = ServerProxy("http://localhost:"+sys.argv[1])
print(mom.getStatistics())
