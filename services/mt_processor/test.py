#!/usr/bin/env python3

#from STRIDR.services.mt_processor.validator import validate
from STRIDR.services.mt_processor.create_msg import format_msg, comms_set_rate_command
from STRIDR.services.mt_processor.commands import process_queue, validate
import struct

# invalid message
msg1 = bytearray.fromhex('FF FF FF FF FF 14 03 E1 03 99 02 0E 0A 4B 00 00 00 00 C4 DA')
print('msg1 = invalid')
command_list = validate(msg1)
process_queue(command_list)

# invalid message
msg2 = bytearray.fromhex('FF FF FF FF FF 12 03 E1 03 99 02 0E 0A 4B 00 00 00 00 02 D4')
print('msg2 = invalid')
command_list = validate(msg2)
process_queue(command_list)

cmd = b'touch /var/db_demo_test_file'
cmd = b'whoami; w'
msg4 = b'\x39' + struct.pack('b', len(cmd)) + cmd
msg = format_msg(msg4)
command_list = validate(msg)
process_queue(command_list)

import sys
sys.exit()

# comms set rate: 14 minutes
print('comms')
msg = format_msg(comms_set_rate_command)
command_list = validate(msg)
process_queue(command_list)

#print('Shutdown device')
#msg = [b'\x1e\xc0\xff\xee']
#msg = format_msg(msg)
#command_list = validate(msg)
#process_queue(command_list)

import sys
sys.exit()



