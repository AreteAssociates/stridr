#!/usr/bin/env python3
from STRIDR.services.pymsp430 import pymsp430
import os
import sys
import subprocess

FILE_DEBUG_STAY_AWAKE = '/tmp/debug_stay_awake' # lives in /tmp, does not survive reboot
FILE_LATCH_SET        = '/var/latch_set'
MODE_FILE             = '/tmp/extend_timer_mode'
MSP_PORT              = '/dev/ttyS4'

msp430 = pymsp430.msp430(MSP_PORT)

if os.path.exists(FILE_DEBUG_STAY_AWAKE):
    # debug file exists
    # keep staying awake forever
    msp430.send_BB_EXTEND()
    print('extend: watchdog +4m, debug.')
    sys.exit(0)

if ( (not os.path.exists(FILE_LATCH_SET)) or (not os.path.exists(MODE_FILE)) ):
    # have not yet run extend BB once
    # we've been up for 4 minutes
    # extend one time
    msp430.send_BB_EXTEND()
    # set environment variable
    with open(MODE_FILE, 'w') as fout:
        fout.write('')
    print('extend: watchdog +4m.')
    sys.exit(0)

if os.path.exists(MODE_FILE):
    # have run extend BB once already
    # we've been up for 8 minutes
    # Remove mode file
    os.remove(MODE_FILE)
    # shutdown gracefully
    print('extend: Preparing to shut down.')
    msp430.send_BB_SHUTDOWN()
    subprocess.call('sudo shutdown now', shell=True)

