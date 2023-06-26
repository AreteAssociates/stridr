#!/usr/bin/env python3

import os
import dbus
import subprocess
import time
import STRIDR.scripts.stridr_hw as stridr_hw
from STRIDR.services.pymsp430 import pymsp430
from STRIDR.sensors.charger import act2861
from STRIDR.scripts.systemd_control import systemd_control
import flash_msp 

def first_boot():
    print('OOT_start.py: Mode: First Boot!')
    # program msp
    retries = 3
    flash_success = False
    while retries > 0:
        if flash_msp.try_flash_msp():
            print('try_flash_msp successful.')
            flash_success = True
            break
        retries -= 1
        time.sleep(1)
    if flash_success == False:
        print('MSP programming final failure. Do not continue.')
        stridr_hw.test_fail()

    # create partition/mounts
    subprocess.Popen('/home/oot/STRIDR/scripts/create_mount_partition.sh', shell=True).wait()

    # See if /data is mounted
    if not os.path.ismount('/data'):
        print('Failed to mount /data. Do not continue.')
        stridr_hw.test_fail()

    # See if new partition is writeable
    try:
        # see if /data exists and is writable
        with open('/data/new_partition_is_writable', 'w') as fout:
            fout.write('w1')
        with open('/data/new_partition_is_writable', 'r') as fin:
            result = fin.read()
            if result != 'w1':
                print('Failure to write/read file data partition. Do not continue.')
                stridr_hw.test_fail()
    except:
        # couldn't write to partition. Something is broken.
        print('Failure related to creating file data partition. Do not continue.')
        stridr_hw.test_fail()

    # So far so good.
    # write FILE_FIRST_BOOT so we never come back here again
    with open(stridr_hw.FILE_FIRST_BOOT, 'w') as fout:
        fout.write('')

    # Turn off green LED. Too annoying
    stridr_hw.set_led(stridr_hw.GREEN_LED, 0)

    # INSERT CODE TO RUN ONCE AT SYSTEM SETUP HERE
    # 
    #

    # At completion of first_boot, sound buzzer and blue LED in repeatable way 
    # Lock up here and be annoying enough to cause the user to flip the switch
    # We will never return to this code
    msp430 = pymsp430.msp430(MSP_PORT)
    for i in range(3):
        msp430.enable_buzzer()
        stridr_hw.set_led(stridr_hw.BLUE_LED, 1)
        time.sleep(0.5)
        msp430.disable_buzzer()
        stridr_hw.set_led(stridr_hw.BLUE_LED, 0)
        time.sleep(0.5)

    stridr_hw.set_led(stridr_hw.BLUE_LED, 1)    # keep blue LED on after completion
    stridr_hw.shutdown_in_secs(0)

def startup_mode():
    print('OOT_start.py: Mode: Startup.')
    import sys
    import gpsd
    # wifi on by default
    # we do not shut down automatically
    # make sure OOT_acquire_data is off - don't want crap data with bad time/position
    s = systemd_control()
    s.stop('OOT_acquire_data.timer')
    # make sure OOT_check_mode is off - can't go operational without GPS/time fixes
    s.stop('OOT_check_mode.timer')
    # start flask server
    print('OOT_start:startup_mode: starting flask server')
    s.start('OOT_flask.service')
    # check GPS and set buzzer and hold here until it works
    print('OOT_start:startup_mode: checking GPS, time setting.')
    gpsd.connect()
    start = stridr_hw.get_uptime() # seconds since start
    while True:
        time.sleep(1)
        fix = gpsd.get_current()
        print('got gpsd fix: {}'.format(fix))
        if fix.mode <= 3: # waiting for a 3d fix
            if time.gmtime().tm_year < 2019: # and for the year to be now or later
                if stridr_hw.get_uptime() - start > 180: # and we've been up for a long time
                    print('Testing GPS failed (mode {}<3), time not set ({}<2019), it\'s been > 180 seconds.'.format(fix.mode, time.gmtime().tm_year))
                    stridr_hw.test_fail()
        # on the other hand (better way to do this requires bourbon)
        if fix.mode == 3:
            # check and probably set time
            stridr_hw.check_time_set_time()
            if time.gmtime().tm_year >= 2019:
                print('GPS test passed, time is set.')
                # Things are good
                break

    # If we get here:
    # GPS fix is good - 3D
    # System time is good

    # Well, we've passed our startup tests. GPS works, time works. Let's be green.
    stridr_hw.set_led(stridr_hw.GREEN_LED, 1)
    print('OOT_start.py:startup_mode(): Unit initial boot testing completed. GPS position data: {}'.format(fix))

    # We can proceed to acquire data and go operational when latch sets
    print('OOT_start.py:startup_mode(): GPS 3D fix and time is valid')
    # enable OOT_acquire_data
    # s.start('OOT_acquire_data.timer')
    # enable OOT_check_mode
    s.start('OOT_check_mode.timer')

    # INSERT CODE HERE TO RUN THE FIRST TIME THE SYSTEM RUNS AFTER DEPLOYMENT
    #
    #

    # since we no longer need to use the timer to run acquire data, run it one time.
    # import it late, here, because it's really slow to load
    from STRIDR.services.daq_manager import acquire_data
    acquire_data.acquire_data()

    # systemd timer checks latch every 5 minutes, if set, run change_to_operational_mode()
    # At the end of this, if things are good, blue and green LEDs are on. We'll shut them off
    # when the latch is set and we switch to operational mode.
    sys.exit()

def change_to_operational_mode():
    # TODO: kill wifi
    # Turn off the LEDs
    stridr_hw.set_led(stridr_hw.GREEN_LED, 0)
    stridr_hw.set_led(stridr_hw.BLUE_LED, 0)

    # write FILE_LATCH_ENABLED
    with open(stridr_hw.FILE_LATCH_SET, 'w') as fout:
        fout.write('latch_enabled')
 
    # kill flask server 
    s = systemd_control()
    s.stop('OOT_flask.service')
    # disable OOT_acquire_data
    s.stop('OOT_acquire_data.timer')
    # disable OOT_check_mode
    s.stop('OOT_check_mode.timer')

    print('OOT_start.py: Change to operational mode. Completed.')
    print('OOT_start.py: Shutting down; to await MSP reboot.')
    # Now shut down
    stridr_hw.shutdown_in_secs(0)

def check_latch_change_mode():
    # intended to be run by systemd every few minutes
    print('OOT_start.py: checking latch status.')
    if stridr_hw.latch_disabled == True:
        # never latch
        stridr_hw.latch_disable()
        print('OOT_start.py: latch disabled by device_type.')
        return True
    if stridr_hw.get_latch_status():
        print('OOT_start.py: latch is set, changing to operational mode.')
        change_to_operational_mode()
    return True

def change_to_startup_mode():
    # Turn off latch and remove FILE_LATCH_SET
    stridr_hw.latch_disable()
    print('OOT_start.py: Change to startup mode. Completed.')
    return

if __name__ == '__main__':
    try:
        # get start time to make sure we run for at least 60 seconds for debug
        start = stridr_hw.get_uptime()
        # Confirm power is on to MSP so it doesn't kill us
        print('OOT_start.py: Start configuring peripherals.')
        stridr_hw.configure_all_peripherals()
        stridr_hw.send_BB_RUNNING()

        # Check mode 0: virgin board
        if not os.path.exists(stridr_hw.FILE_FIRST_BOOT): 
            # which also mounts the /data partition
            first_boot()
        else:
            # Can't work with charger until MSP is programmed, which happens in first_boot
            if stridr_hw.charger_enabled: stridr_hw.configure_charger(stridr_hw.BATTERY_VOLTAGE) # will raise error if i2c fails
            else: stridr_hw.disable_battery_charger()

            # mount partition 
            subprocess.Popen('mount /dev/mmcblk0p3 /data', shell=True).wait()
            print('Mounted partition.')

        # continue boot
        if not os.path.exists(stridr_hw.FILE_LATCH_SET): startup_mode()

        # No special mode, so we should be RUNNING
        print('OOT_start.py: Mode: Operational')

        # By this point, we either have GPS (from startup_mode) or we've previously collected a data point
        # check_time_set_time will use GPS/NTP or the latest GPS filename to set or guess the correct time
        print('OOT_start.py: Checking time is set by GPS.')
        stridr_hw.check_time_set_time()

        # INSERT CODE HERE TO RUN EVERY TIME THE SYSTEM BOOTS AFTER DEPLOYMENT
        #
        #

        # putting this here because it is really slow to load
        from STRIDR.services.daq_manager import acquire_data
        acquire_data.acquire_data()
        print('OOT_start.py: Acquisition complete, clearing failure counter, return to OOT_start.py')
    except Exception as e:
        print('Error during boot: OOT_start.py failed')
        print(e)
        # This is a bad state and LEDs will indicate that
        # If the IMU is ever set to run for less than 180 seconds, we might see this happen anyway
        stridr_hw.set_led(stridr_hw.RED_LED, 1, trigger='timer', delay_on=200, delay_off=50)
        stridr_hw.set_led(stridr_hw.GREEN_LED, 1, trigger='timer', delay_on=200, delay_off=100)
        stridr_hw.set_led(stridr_hw.BLUE_LED, 0)

    # Make sure we have run for at least 180 seconds; everything takes longer than that
    # Give someone debugging a half a freaking chance to stop the madness
    while stridr_hw.get_uptime() - start < 180:
        stridr_hw.set_led(stridr_hw.RED_LED, 1, trigger='timer', delay_on=200, delay_off=200)
        stridr_hw.set_led(stridr_hw.BLUE_LED, 0)
        print('delaying shutdown; run time way too short.')
        time.sleep(1)

    # Finally shut down
    # Set charger voltage back to more reasonable level
    if stridr_hw.charger_enabled: stridr_hw.configure_charger(stridr_hw.BATTERY_VOLTAGE) # will raise error if i2c fails
    print('OOT_start.py: Start completed, shutdown NOW!!!')
    stridr_hw.shutdown_in_secs(0)
