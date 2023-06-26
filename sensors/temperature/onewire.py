#!/usr/bin/env python3

import os
import sys
from datetime import datetime
import time 
import subprocess

onewire_dir = '/sys/bus/w1/devices'
outlier_limit = 55 # maximum value expected, in degrees C

DEBUG = False
ONEWIRE_DEV_TEMP = '28'
ONEWIRE_PWR_PORT = '/sys/class/gpio/gpio49'


def enable_1w_power():
    subprocess.call("echo out > {}/direction".format(ONEWIRE_PWR_PORT), shell=True)
    subprocess.call("echo 1 > {}/value".format(ONEWIRE_PWR_PORT), shell=True)
    return

def disable_1w_power():
    subprocess.call("echo 0 > {}/value".format(ONEWIRE_PWR_PORT), shell=True)
    return

def get_1w_device_list(sensor_type):
    onewire_devIDs = []
    d = os.listdir(onewire_dir)
    for item in d:
        if item.split('-')[0] == sensor_type:
            onewire_devIDs.append(item)
    return onewire_devIDs

def log_1w_sensor_data(num_seconds, opath, rate, sensor_type, DEBUG=True):
    # creating place to store data and a filename to store it in
    if DEBUG: print('Enabling 1wire power port, then waiting 10 seconds.')
    enable_1w_power()
    time.sleep(10)
    if DEBUG: print('Checking output path ({}).'.format(opath))
    if not os.path.exists(opath): os.makedirs(opath)
    timestamp = datetime.now().strftime('SST_%Y%m%dT%H%M%S.%f')[:-3] #only want milliseconds, lose the microseconds
    ofpath = os.path.join(opath, timestamp+'.log')

    # get list of device IDs to log
    onewire_devIDs = get_1w_device_list(sensor_type)
    if DEBUG: print('Device list: {}'.format(onewire_devIDs))

    if DEBUG: print('Starting data log to file: {}'.format(ofpath))
    num_samples = int(num_seconds/rate)
    while num_samples > 0:
        for device in onewire_devIDs:
            with open(os.path.join(onewire_dir,device,'w1_slave'), 'r') as fin:
                with open(ofpath, 'a') as fout:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    value = fin.read().strip()
                    result = int(value.split('=')[-1])
                    result /= 1000 # convert from kiloCelsius to Celsius
                    if result < outlier_limit:
                        fout.write('{}, {:0.3f}\n'.format(timestamp, result))
                    else:
                        print('Value exceeded outlier limit: {} > {}'.format(result, outlier_limit))
                    if DEBUG: print(timestamp, device,result)

        # finished read sensors; sleep interval time
        num_samples -= 1
        interval = 1/rate
        time.sleep(interval - time.monotonic() % 1)

    # Turn power off, now that we're done
    disable_1w_power()

if __name__ == '__main__':
    '''
    1w.py
    Logs data from a 1-wire sensor using the Linux driver

    Usage:
    1w.py num_seconds opath rate

    where:
        num_seconds = number of seconds to collect data for
        opath = the path to write output files to
        rate = rate of sample collection at

    example:
    1w.py 15 /data/temperature 1

    
    '''

    opath = '/data/temperature/'
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
    log_1w_sensor_data(num_seconds, opath, rate, sensor_type=ONEWIRE_DEV_TEMP)
