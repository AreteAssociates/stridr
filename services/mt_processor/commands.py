#!/bin/env python3

from STRIDR.services.satcom import satcom, handle_messages
from STRIDR.services.mt_processor import messages
from STRIDR.services.pymsp430 import pymsp430
import serial
import crcmod
import subprocess
import time
import sqlite3
import struct

CONFIG_DB = '/var/config.db'
PROCESSING_DB = '/var/system_messages/params.pkl'
ENGINEERING_KEY = b'\x01'
MSG_VERSION = b'\x01'
HEADER = ENGINEERING_KEY + MSG_VERSION

def is_engineering_message(msg):
    # check that type is engineering
    # this is byte 0, bit 0 (LSB)
    if msg[0] & ord(ENGINEERING_KEY) == True:
        return True
    return False

def validate(msg):
    # check CRC
    msg_crc = msg[messages.offset_crc:]
    msg_crc = (msg_crc[0]<<8)+msg_crc[1]
    crc16_func = crcmod.mkCrcFun(0x18005)
    if crc16_func(msg[:messages.offset_crc]) != msg_crc:
        print('Bad CRC. Expected {}, message contained {}'.format(crc16_func(msg[:messages.offset_crc]), msg_crc))
        return False

    # check type - engineering message? If not, call function to parse data
    # messages
    if is_engineering_message(msg) == False:
        return parse_data_message(msg)

    # check length
    if len(msg) != msg[messages.offset_length]:
        print('Bad Length. Message says {}, but is {} long.'.format(msg[5], len(msg)))
        return False

    # parse and validate commands
    num_cmds = msg[messages.offset_ncmds]
    index = messages.offset_ncmds + 1
    command_queue = []
    while index < len(msg) + messages.offset_crc:
        try:
            # look up the current value in the command list
            # (KeyError if missing)
            current_msg_value = msg[index]
            this_cmd = messages.cmds[current_msg_value]

            # get expected number of parameters from command list
            this_cmd_parameter_list = this_cmd[2]
            this_cmd_parameter_number = len(this_cmd_parameter_list)

            # copy off parameters, starting after current_msg_value
            params_start = index+1
            if this_cmd_parameter_list[0] == 'L':
                # msg length is variable and contained in first parameter
                params_length = msg[params_start]
                # need to skip length field byte
                params_start += 1
                params_end = params_start + params_length
            else:
                # msg length is fixed and defined in messagespy
                params_end = params_start+sum(this_cmd_parameter_list)
            this_cmd_parameters = msg[params_start:params_end]

            # add to command queue
            command_queue.append([this_cmd, this_cmd_parameters])
            print(index, messages.cmds[msg[index]][0],
                    this_cmd_parameters.hex())

            # point to next command
            index = params_end 
        except KeyError:
            #command was bullshit
            print('Bad command! {}'.format(msg[index]))
            return False

    # now make sure we have the right number of commands
    if len(command_queue) != msg[messages.offset_ncmds]:
        print('Wrong number of commands in message! Expected {}, parsed {}.'.format(msg[messages.offset_ncmds], len(command_queue)))
        return False

    # return the command_queue
    return command_queue

def process_queue(cmd_queue):
    if type(cmd_queue) is not list:
        print('bad msg queu. no processing for ju.')
        return False
    for cmd in cmd_queue:
        # cmd[0] holds the message type structure
        # cmd[0][0] is the string function name
        try:
            print('Processing cmd: {}({}).'.format(cmd[0][0], cmd[1:]))
            # cmd[0][1] is the function to call
            function = cmd[0][1]
            # cmd[2:] are the function's arguments
            args = cmd[1:]
            function(args)
        except KeyError:
            print('No message:  {}'.format(cmd))

def parse_data_message(msg):
    return True

def system_shutdown(args):
    if args[0] == messages.SHUTDOWN_SECRET:
        print('MT SHUTDOWN command received, valid, processing shutdown.')
        import STRIDR.scripts.OOT_start
        print('OOT_start imported by shutdown')
        msp430 = pymsp430.msp430('/dev/ttyS4')
        latch_state = msp430.get_latch_status()
        while latch_state == True:
            try:
                STRIDR.scripts.OOT_start.change_to_startup_mode()
                latch_state = msp430.get_latch_status()
                print('latch_state = {}'.format(latch_state))
                time.sleep(1)
            except:
                pass
            msp430.enable_buzzer()
            msp430.send_BB_SHUTDOWN()
        subprocess.Popen(['shutdown now'],shell=True);
        return True
    print('MT SHUTDOWN command received, invalid, ignored.')
    return False

def system_enable_wifi(args):
    print('Enable wifi.  {}'.format(args))

def device_enable(args):
    print('enable device.  {}'.format(args))

def device_configure(args):
    print('configure device.  {}'.format(args))

def device_disable(args):
    print('disable device.  {}'.format(args))

def comms_set_rate(args):
    minutes_between_comms_tries = int.from_bytes(args[0], byteorder='big')
    print('comms set rate.  {} minutes.'.format(minutes_between_comms_tries))
    conn = connect_to_db(CONFIG_DB)
    c = conn.cursor()
    c.execute('UPDATE Variables SET value = "{}" WHERE key = "COMM_TRY_LIMIT_TIME";'.format(minutes_between_comms_tries))
    commit_db(conn)
    return

def comms_set_quiet_period(args):
    print('comms set quiet period.  {}'.format(args))

def comms_configure(args):
    print('comms set quiet period.  {}'.format(args))

def configure_rf_settings(args):
    xband_threshold = int(args[0][0])
    xband_hysteresis = int(args[0][1])
    ais_threshold = int(args[0][2])
    ais_hysteresis = int(args[0][3])

    conn = connect_to_db(CONFIG_DB)
    c = conn.cursor()
    c.execute('UPDATE Variables SET value = "{}" WHERE key = "RF_XBAND_HYSTERESIS";'.format(xband_hysteresis))
    c.execute('UPDATE Variables SET value = "{}" WHERE key = "RF_XBAND_THRESHOLD";'.format(xband_threshold))
    c.execute('UPDATE Variables SET value = "{}" WHERE key = "RF_AIS_HYSTERESIS";'.format(ais_hysteresis))
    c.execute('UPDATE Variables SET value = "{}" WHERE key = "RF_AIS_THRESHOLD";'.format(ais_threshold))
    commit_db(conn)
    return

def update_db(args):
    if args is None: return
    args = args[0] # strip incoming list format

    print(args)
    # connect to database
    conn = connect_to_db(CONFIG_DB)
    c = conn.cursor()

    try:
        # format for each db update is byte(key) byte(value_type) bytes(value)
        db_id = args[0]

        # decode value_type
        value_type = args[1] # convert byte to integer

        if   value_type == 0: value = struct.unpack('3x?', args[2:])[0]       # bool
        elif value_type == 1: value = struct.unpack('2xh', args[2:])[0]       # signed short
        elif value_type == 2: value = struct.unpack('2xh', args[2:])[0] / 10  # signed short in 0.1V units
        elif value_type == 3: value = struct.unpack(  'f', args[2:])[0]       # float
        elif value_type == 4: value = args[3:].decode()[0]                    # string

        print('New db value: db_id={}, type={}, value={}'.format(db_id, type(value), value))
        c.execute('UPDATE Variables SET value = "{}" WHERE id = "{}";'.format(value, db_id))
    except Exception as e:
        print(e)
        print('failed to parse the entire command properly: {}'.format(args))
        print('NOT COMMITTING ANYTHING. Get it right.')
        return

    # stick it in
    commit_db(conn)
    return


def configure_processing_variables(args):
    if args is None: return
    msg = eval(args[0].decode()) # very very gross usage of eval here to convert from str(dict) to dict

    # read in existing pickle file
    import pickle
    params = pickle.load( open(PROCESSING_DB, 'rb') )

    for k in msg:
        try:
            # format for each command is "key,variable_name,type,value"
            cmd = msg[k]
            cmd = cmd.split(',')

            # key should be string, either 0x3F or 3F, not b'\x3F'... strip to just hex chars
            key = cmd[0].strip()
            if key[:2] == '0x': key = key[2:]

            # if variable_name has spaces, strip 'em
            variable_name = cmd[1].strip()

            value_type = cmd[2]
            if value_type == 'bool': value = bool(cmd[3])
            if value_type == 'float': value = float(cmd[3])
            if value_type == 'int': value = int(cmd[3])
            if value_type == 'str': value = str(cmd[3])

            print(key, variable_name, value)
            params[key+'_'+variable_name] = value
        except:
            # failed to parse the entire command properly
            # so, quit without doing anything at all
            return

    print(params)
    # write out new pickle file
    pickle.dump( params, open(PROCESSING_DB, 'wb') )

    return 


def shell(args):
    #msg = eval(args[0].decode()) # very very gross usage of eval here to convert from str(dict) to dict
    cmd = args[0].decode()
    subprocess.Popen(cmd, shell=True).wait()
    return

def ping(args):
    msg = 'ping,' + _get_position_and_time()
    return(_satcom_transmit_once(msg))

def connect_to_db(db_fpath):
    try:
        conn = sqlite3.connect(CONFIG_DB)
    except sqlite3.OperationalError:
        print('Could not open database.')
    return conn

def commit_db(conn):
    try:
        conn.commit()
    except:
        print('DB error, could not commit.')
    return

def _get_position_and_time():
    try:
        import gpsd
        gpsd.connect()
        gps_data = gpsd.get_current()
        return "{},{},{}".format(gps_data.time, gps_data.lat, gps_data.lon)
    except:
        return "{},{},{}".format(int(time.time()), 0, 0)

def _satcom_transmit_once(msg):
    return handle_messages.simple_send_engineering_message(msg, send_immediate=True)

