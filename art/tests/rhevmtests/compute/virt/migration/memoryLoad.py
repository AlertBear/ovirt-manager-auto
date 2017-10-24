#!/usr/bin/env python
#
# License: MIT (http://opensource.org/licenses/MIT)
# Copyright (C) 2015 Red Hat, Inc.
# Authors:
# Uri Lublin <uril@redhat.com>
# Israel Pinto <ipinto@redhat.com>

"""
This program occupies a give size of memory and keeps touching it.
Set target_mem_size in KB (same as rusage's ru_maxrss).
Program does not rest and use 100% of cpu.
Press CTRL-C to exit.
"""
import sys
import resource
import logging
import getopt


def parse_parameters(argv, size):
    """
    parse script parameters and return target size

    :param argv: command line args
    :type: args: list
    :param size: target size (user input)
    :type size: str
    :return: target size, reuse
    :rtype: (str,bool)
    """
    reuse = False
    to_kilobytes = 1000 * 1000
    help_output = "usage: test.py --size <size in GB> --reuse <True/False>"
    try:
        opts, args = getopt.getopt(argv, 's:r:h', ['size=', 'reuse=', 'help'])
    except getopt.GetoptError:
        print (help_output)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print (help_output)
        elif opt in ('-s', '--size'):
            size = arg
        elif opt in ('-r', '--reuse'):
            reuse = arg
        else:
            print (help_output)
    print ("size: %s , reuse: %s" % (size, reuse))
    target_mem_size = to_kilobytes * float(size)
    return target_mem_size, reuse


def main(argv):
    loop_size = 1000
    logging.basicConfig(
        filename="memoryLoad.log",
        filemode='w',
        level=logging.DEBUG
    )
    logger = logging.getLogger("memoryLoad")
    size = ""
    target_mem_size, reuse = parse_parameters(argv, size)
    logger.info(
        'Allocating memory -- target memory size is %dKB'
        % target_mem_size
    )
    current_mem_size = 0
    list_values = []
    try:
        while current_mem_size < target_mem_size:
            lnew = [i + j for i in range(loop_size) for j in range(loop_size)]
            list_values.extend(lnew)
            r = resource.getrusage(resource.RUSAGE_SELF)
            current_mem_size = r.ru_maxrss

        logger.info('... allocated %dKB' % current_mem_size)
        logger.info('Touching memory -- infinite loop -- press CTRL-C to exit')
        try:
            if reuse:
                logging.info("reuse %s", "on" if reuse else "off")
            n = len(list_values)
            while True:
                i = 0
                while i < n:
                    j = n - 1 - i
                    list_values[i] += 1
                    list_values[j] -= 1
                    i += 400
                    if not reuse:
                        break
        except KeyboardInterrupt, e:
            logger.info('got keyboard interrupt -- exiting')

        logger.info('memoryLoad: Done')
    except Exception, e:
        logger.error('Failed to run ...')
        logger.error(e.message)
    sys.exit(2)


if __name__ == '__main__':
    main(sys.argv[1:])
