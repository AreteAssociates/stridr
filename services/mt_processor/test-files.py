#!/usr/bin/env python3

from STRIDR.services.mt_processor.create_msg import format_msg, comms_set_rate_command
from STRIDR.services.mt_processor.commands import process_queue, validate
from glob import glob
import sys

flist = glob('sbd_files_testing/*.sbd')
args = sys.argv

# you can just put the file names you want to run on the command line
if len(args)>1:
    flist = args[1:]

for fname in flist:
    print('\n\n-----------------------------------------------------')
    print(fname)
    print('-----------------------------------------------------')
    with open(fname, 'rb') as fin:
        data = fin.read()
        command_list = validate(data)
        process_queue(command_list)
