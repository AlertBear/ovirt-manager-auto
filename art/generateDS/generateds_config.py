# In some cases the element and attribute names in an XML document
# will conflict with Python keywords.
#
# There are two solutions to fixing and avoiding name conflicts:
# 1. to change the dictionary named NameTable in generateDS.py
# 2. to make this file which extend the dictionary named NameTable
#
# we choose the second option to be able to upgrade the generateDS.py easily
# you can see more details:
#   http://www.davekuhlman.org/generateDS.html
#
# author = 'khakimi'

NameTable = {
    'import': 'import___',
    'from': 'from___',
    }
