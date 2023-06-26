#!/usr/bin/env python3

import os
import sys
from datetime import datetime
import time
import act2861

DEBUG = False

def log_sensor_data(num_seconds, opath, rate, DEBUG=True):
    # creating place to store data and a filename to store it in
    if DEBUG: print('Checking output path ({}).'.format(opath))
    if not os.path.exists(opath): os.makedirs(opath)
    timestamp = datetime.now().strftime('CHARGER_%Y%m%dT%H%M%S.%f')[:-3] #only want milliseconds, lose the microseconds
    ofpath = os.path.join(opath, timestamp+'.log')

    charger = act2861.act2861()

    if DEBUG: print('Starting data log to file: {}'.format(ofpath))
    num_samples = int(num_seconds/rate)
    while num_samples > 0:
        with open(ofpath, 'a') as fout:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            vin = charger.get_adc_vin()
            vout = charger.get_adc_vout()
            iin = charger.get_adc_iin()
            iout = charger.get_adc_iout()
            line = '{}, {:0.2f}, {:0.2f}, {:0.2f}, {:0.2f}'.format(timestamp, vin, iin, vout, iout)
            fout.write(line + '\n')
            if DEBUG: print(line)

        # finished read sensors; sleep interval time
        num_samples -= 1
        interval = 1/rate
        time.sleep(interval - time.monotonic() % 1)

if __name__ == '__main__':
    '''
    log_charger.py
    Logs data from an ACT2861 charger

    Usage:
    log_charger.py num_seconds opath rate

    where:
        num_seconds = number of seconds to collect data for
        opath = the path to write output files to
        rate = rate of sample collection at

    example:
    log_charger.py 15 /data/temperature 1


    '''

    opath = '/data/charger/'
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


