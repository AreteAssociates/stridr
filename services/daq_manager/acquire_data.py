#!/bin/env python3
import os
import sys
import traceback
import time
import sqlite3
import threading 
import psutil           # includes subprocess

from STRIDR.services.pymsp430 import pymsp430
from STRIDR.comms.comms_main import run_algorithms, make_packet, load_db

# defaults
CONFIG_DB = '/var/config.db'

global jobs_list, jobs_dict
jobs_list = list()
jobs_dict = dict()

def run_process(cmd, a):
    args = ""
    for arg in a:
        args += " "
        args += str(arg)
    print("exec " + cmd + args)
    p = psutil.Popen("exec "+cmd+args, stdout=psutil.subprocess.PIPE, shell=True)
    jobs_list.append(p)
    jobs_dict[p] = cmd
    return p

def on_complete(proc):
    print('DAQ process {} finished, exit code {}.'.format(jobs_dict[proc], proc.returncode))
    jobs_list.remove(proc)

def acquire_data():
    # connect to database and get list of sensors to run
    conn = sqlite3.connect(CONFIG_DB)
    c = conn.cursor()
    # also create a cursor that only returns a list for single result queries
    conn.row_factory = lambda cursor, row: row[0]
    single_c = conn.cursor()
    single_c.execute('SELECT id FROM HW_Config WHERE enabled=1')
    sensor_ids = single_c.fetchall()

    # get some variables from the database
    single_c.execute('SELECT value FROM Variables WHERE key="PATH_ROOT_SENSOR_ACQ"')
    PATH_ROOT_SENSOR_ACQ = single_c.fetchone()
    single_c.execute('SELECT value FROM Variables WHERE key="PATH_ROOT_SENSOR_DATA"')
    PATH_ROOT_SENSOR_DATA = single_c.fetchone()
    print( 'service.acquire_data: PATH_ROOT_SENSOR_DATA is {}'.format( PATH_ROOT_SENSOR_DATA ) )

    # Query for each ID and get the necessary config info
    for sensor_id in sensor_ids:
        c.execute('SELECT * FROM HW_Config WHERE id={}'.format(sensor_id))
        sensor_config_data = c.fetchall()

    #create the algorithm db
    algorithm_db = load_db();
    #Start algorithms on the last 15 minutes of data
    algorithm_thread = threading.Thread(target=run_algorithms, args=[algorithm_db,]);
    #setting this as a daemon means that it runs until the main thread exits. 
    algorithm_thread.daemon = True
    algorithm_thread.start();

    # Max run time for watchdog
    max_daq_process_run_seconds = 0
    time_sensors_start = time.time()
    # For each sensor, configure the scheduler to start the job
    for sensor_id in sensor_ids:
        print( 'services.acquire_data: Configuring sensor {}'.format( sensor_id ) )
        c.execute('SELECT Schedule, RunTime, AcquireProcess, Rate, DataPath, AcquirePriority FROM HW_Config WHERE id={}'.format(sensor_id))
        sensor_run_schedule_minutes, sensor_run_time_seconds, sensor_acq_process, sensor_rate, sensor_opath, sensor_acq_priority = c.fetchone()

        if not sensor_opath:
          continue
        # set watchdog to longest sensor run time
        if sensor_run_time_seconds > max_daq_process_run_seconds: max_daq_process_run_seconds = sensor_run_time_seconds

        if sensor_acq_process is not None:
            # set priority if it is configured
            sensor_nice_command = ''
            if type(sensor_acq_priority) is int:
                if ( (sensor_acq_priority < 20) and (sensor_acq_priority > -20) ):
                    sensor_nice_command = 'nice -n {} '.format(sensor_acq_priority)
            sensor_acq_process = sensor_nice_command + os.path.join(PATH_ROOT_SENSOR_ACQ, sensor_acq_process)
            sensor_opath = os.path.join(PATH_ROOT_SENSOR_DATA, sensor_opath)
            print( 'services.acquire_data: sensor_opath is {}'.format( sensor_opath ) )
            if not os.path.exists(sensor_opath):
                # then create it
                os.makedirs(sensor_opath)
            
            # and run the process immediately
            run_process(sensor_acq_process, [sensor_run_time_seconds, sensor_opath, sensor_rate])

    # Configure a watchdog to run in (90) seconds after expected end of daq processes
    watchdog_buffer = 90
    max_daq_run_time = time_sensors_start + max_daq_process_run_seconds + watchdog_buffer

    packet_made = False;
    try:
        # wait for daq processes until watchdog times out
        while time.time() < max_daq_run_time:
            if not algorithm_thread.isAlive():
                # Run next step in pipeline (packet generation)
                if not packet_made:
                    make_packet(algorithm_db,send=True);
                    packet_made = True;
            gone, alive = psutil.wait_procs(jobs_list, timeout=1, callback=on_complete)
            if len(alive) == 0: break

        # this is supposed to be plenty of time for the algorithms to finish running
        if not packet_made:
            make_packet(algorithm_db,send=True);

        # if there are any jobs left, kill them
        for p in jobs_list:
            p.kill()
    except Exception as e:
        traceback.print_exc()

    algorithm_db.source.close_db();

    return

if __name__=='__main__':
    acquire_data()
