#!/usr/bin/python

import serial
from datetime import datetime
import signal
import os
import sys

odir = '/data/gps'


def terminate(sig, frame):
        print('Logging terminated.')
        exit(0)

def _linux_set_time(time_tuple):
    # https://stackoverflow.com/questions/12081310/python-module-to-change-system-date-and-time
    import ctypes
    import ctypes.util
    import time

    # /usr/include/linux/time.h:
    #
    # define CLOCK_REALTIME                     0
    CLOCK_REALTIME = 0

    # /usr/include/time.h
    #
    # struct timespec
    #  {
    #    __time_t tv_sec;            /* Seconds.  */
    #    long int tv_nsec;           /* Nanoseconds.  */
    #  };
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long),
                    ("tv_nsec", ctypes.c_long)]

    librt = ctypes.CDLL(ctypes.util.find_library("rt"))

    ts = timespec()
    ts.tv_sec = int( time.mktime( datetime.datetime( *time_tuple[:6]).timetuple() ) )
    ts.tv_nsec = time_tuple[6] * 1000000 # Millisecond to nanosecond

    # http://linux.die.net/man/3/clock_settime
    librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))



if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)

    s = serial.Serial( port = '/dev/ttyS1',
                       baudrate = 9600,
                       parity = serial.PARITY_NONE,
                       stopbits = serial.STOPBITS_ONE,
                       bytesize = serial.EIGHTBITS,
                       timeout = 0)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ofpath = os.path.join(odir, timestamp+'.log')
    print('Starting data log to file: {}'.format(ofpath))

    line = []
    while True:
        with open(ofpath, 'a') as fout:
            for ch in s.read():
                line.append(ch)

                if ch == '\n':
                    line = ''.join(str(v) for v in line)
                    if line.split(',')[0] == '$GNGGA':
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        print(line)
                        fout.write('{} - {}'.format(timestamp, line))
                    line = []
                    break

    s.close()
