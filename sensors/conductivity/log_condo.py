#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from STRIDR.services.pymsp430 import pymsp430
import time

DEBUG = False

outlier_limit = 4000    # counts, need to establish a real measurement-based limit

def log_sensor_data(num_seconds, opath, rate, DEBUG=True):
    # creating place to store data and a filename to store it in
    if DEBUG: print('Checking output path ({}).'.format(opath))
    if not os.path.exists(opath): os.makedirs(opath)
    timestamp = datetime.now().strftime('CONDO_%Y%m%dT%H%M%S.%f')[:-3] #only want milliseconds, lose the microseconds
    ofpath = os.path.join(opath, timestamp+'.log')

    msp430 = pymsp430.msp430('/dev/ttyS4')
    msp430.enable_condo()

    delay_time = 10
    if DEBUG: print('Waiting {} seconds for sensor to warm up.'.format(delay_time))
    time.sleep(delay_time)

    if DEBUG: print('Starting data log to file: {}'.format(ofpath))
    num_samples = int(num_seconds/rate)
    while num_samples > 0:
        with open(ofpath, 'a') as fout:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            val = msp430.read_condo()
            if ( (val > 0) and (val < outlier_limit) ):
                line = '{}, {:0d}'.format(timestamp, val)
                fout.write(line + '\n')
                if DEBUG: print(line)
            else: 
                if DEBUG: print('Skipped bad value: {}'.format(val))

        # finished read sensors; sleep interval time
        num_samples -= 1
        interval = 1/rate
        time.sleep(interval - time.monotonic() % 1)
    msp430.disable_condo()

if __name__ == '__main__':
    '''
    log_condo.py
    Logs data from the onboard conductivity sensor

    Usage:
    log_condo.py num_seconds opath rate

    where:
        num_seconds = number of seconds to collect data for
        opath = the path to write output files to
        rate = rate of sample collection at

    example:
    log_condo.py 15 /data/conductivity 1


    '''

    opath = '/data/conductivity/'
    opath='.'
    num_seconds = 15 #number of seconds to run
    rate = 1 #data rate in Hz

    if len(sys.argv) > 1:
        num_seconds = int(sys.argv[1])
        if len(sys.argv) > 2:
            opath = sys.argv[2]
            if len(sys.argv) > 3:
                rate = int(sys.argv[3])
    print(len(sys.argv))
    log_sensor_data(num_seconds, opath, rate)


