#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

from lxml.etree import Element, ElementTree, parse, _Comment, XMLParser
import argparse
from sys import argv
import uuid


def load(testFile):
    '''
    Loads xml file
    Parameters:
    * testFile - file to load
    '''
    
    parser = XMLParser(remove_blank_text=True)
    return parse(testFile, parser)
    

def generateId():
    '''
    Generates UUID from a host ID, sequence number, and the current time
    '''

    return str(uuid.uuid1())


def writeXml(root, path):
    '''
    Write xml file from provided root element
    Parameters:
    * root - root element
    * path - output file path
    '''

    file = open(path, 'w')
    ElementTree(root).write(file, encoding="utf-8",
            pretty_print=True, xml_declaration=True)
    file.close()


def buildXml(inputFilePath, outputFilePath):
    '''
    Builds new xml. If test case has no <id> node - add it
    Parameters:
    * inputFilePath - path of input xml file
    * outputFilePath - path of output xml file
    '''
    

    testCasesTree = load(inputFilePath)
    rootElement = testCasesTree.getroot()
    for elm in list(rootElement):
        if not isinstance(elm, _Comment):
            if not elm.findall('id'):
                idElm = Element('id')
                idElm.text = generateId()
                elm.insert(0, idElm)
        rootElement.append(elm)

    writeXml(rootElement, outputFilePath)

    print 'The new file is created at %s' % outputFilePath


parser = argparse.ArgumentParser(
                    prog=argv[0],
                    description='Execute the test specified by config file.')

parser.add_argument("--input_file", "-in", dest="input",
                    help="input test file path", metavar="FILE")
parser.add_argument("--output_file", "-out", dest="output",
                    help="input test file path", metavar="FILE")

args = parser.parse_args(argv[1:])
buildXml(args.input, args.output)



