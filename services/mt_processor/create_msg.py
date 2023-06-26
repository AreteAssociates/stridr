#!/usr/bin/env python3

import crcmod

def format_msg(command_list):
    # creates validly populated messages given a command/payload list
    # feed me a list where each list item is a command and payload
    if type(command_list) is not list: command_list = [command_list]
    msg_hdr = b'\xff'*5  # python is so weird
    num_commands = len(command_list).to_bytes(1, 'big')
    msg_body = b''
    for cmd in command_list:
        msg_body += cmd
    msg_bytes = len(msg_hdr + b'1' + num_commands + msg_body + b'02').to_bytes(1, 'big')
    msg = msg_hdr + msg_bytes + num_commands + msg_body

    crc_16_func = crcmod.mkCrcFun(0x18005)
    msg_crc = crc_16_func(msg).to_bytes(2, 'big')

    return msg + msg_crc

def write_commands_to_msg_file(command_list, fpath):
    with open(fpath, 'wb') as fout:
        msg = format_msg(command_list)
        fout.write(msg)
    return msg

comms_set_rate_command = [b'\xe1\x0e']
