#!/usr/bin/env python3

import os
import dbus
import subprocess
import time
from STRIDR.services.pymsp430 import pymsp430
from STRIDR.sensors.charger import act2861
from STRIDR.scripts.systemd_control import systemd_control

charger_enabled = True
latch_disabled = False
boot_failure = False

FILE_FIRST_BOOT         = r'/var/first_boot'
FILE_LATCH_SET          = r'/var/latch_set'
FILE_DEBUG_STAY_AWAKE   = r'/tmp/debug_stay_awake' # note lives in /tmp, does not survive reboot
MSP_PORT                = r'/dev/ttyS4'

BB_PORT_ENABLE          = r'/sys/class/gpio/gpio46'
LEDS                    = r'/sys/class/leds/'
RED_LED                 = r'stridr:red:usr0/'
GREEN_LED               = r'stridr:green:usr1/'
BLUE_LED                = r'msp'

BATTERY_VOLTAGE         = 14.1

DEVICE_TYPE_FILE = '/var/device_type'

try:
    with open(DEVICE_TYPE_FILE, 'r') as fin:
        DEVICE_TYPE_FLAG=fin.read()[0]
except:
    DEVICE_TYPE_FLAG = 'E' # code responds to 'A', 'B', 'C', 'D', 'E'
# B: battery charger disabled
if (DEVICE_TYPE_FLAG == 'B'):
    charger_enabled = False

# For in house testing.
if (DEVICE_TYPE_FLAG == '_'):
    latch_disabled = True


def config_pin(pinlist, mode):
    # mode = e.g. 'uart', 'i2c', 'gpio'
    port_config_path = r'/sys/devices/platform/ocp/'
    for pin in pinlist:
        with open(port_config_path + 'ocp:' + pin + '_pinmux/state', 'w') as fout:
            fout.write(mode)
    return

def configure_all_peripherals():
    # Configure UART4
    uart4 = ['P9_11', 'P9_13']
    config_pin(uart4, 'uart')

    # Configure UART1 (GPS)
    uart1 = ['P9_24', 'P9_26']
    config_pin(uart1, 'uart')

    # Configure UART2 (MODEM)
    uart2 = ['P9_21', 'P9_22']
    config_pin(uart2, 'uart')

    # Configure i2c1
    i2c1 = ['P9_17', 'P9_18']
    config_pin(i2c1, 'i2c')
    
    # Enable BB_PORT_ENABLE
    subprocess.call("echo out > {}/direction".format(BB_PORT_ENABLE), shell=True)
    subprocess.call("echo 1 > {}/value".format(BB_PORT_ENABLE), shell=True)

    print('Configured UART1, UART2, UART4, I2C1')
    return

def configure_charger(batt_set_voltage):
    a = act2861.act2861(1)
    # read any faults, which should clear them
    print('Configuring charger; start by reading status bytes and faults.')
    print(a.get_faults())
    print(a.get_charger_status())
    print(a.get_general_status())

    a.set_register(a.reg_CHG_CONTROL1, 0xd8) #batt short thold=10v
    a.set_register(a.reg_CHG_CONTROL2, 0x52)
    a.set_register(a.reg_CHG_CONTROL3, 0x4e) 
    a.set_batt_recharge_voltage(400) # repeats part of CONTROL3 setting
    a.set_register(a.reg_OTG_MODE1, 0x00)
    a.set_register(a.reg_BATT_LOW_V, 0x46)# set batt_low_voltage (0x1a)
    a.set_register(a.reg_JEITA, 0x32) # set jeita (0x1c)

    # disable TH and JEITA
    a.disable_th()
    # set vbatt
    a.set_batt_set_voltage(batt_set_voltage)

    # as good a place as any to test the i2c bus
    if a.get_batt_set_voltage() != batt_set_voltage:
        raise Exception('Failed to configure battery charger; possible i2c error.')

    # set vin_lim
    a.set_input_voltage_limit(5.9)
    # disable safety timer in case of very long day
    a.disable_safety_timer()
    return

def disable_battery_charger():
    a = act2861.act2861(1)
    a.set_register_bit(a.reg_MAIN_CONTROL1, 7) # Hi-Z Mode
    return

def send_BB_RUNNING():
    # Send BB_RUNNING to MSP
    msp430 = pymsp430.msp430(MSP_PORT)
    msp430.send_BB_RUNNING()
    print('Sent BB_RUNNING command to MSP.')
    return

def latch_enable():
    # create status_file
    with open(FILE_LATCH_SET, 'w') as fout:
        fout.write('latch_enabled')
    # done
    msp430 = pymsp430.msp430(MSP_PORT)
    msp430.enable_latch()
    print('Latch set for first time.')
    return

def latch_disable():
    msp430 = pymsp430.msp430(MSP_PORT)
    msp430.disable_latch()
    # remove status_file
    try:
        print('OOT_start.py: latch_disable:: Removing latch set file: {}'.format(FILE_LATCH_SET))
        os.remove(FILE_LATCH_SET)
    except:
        pass
    print('OOT_start.py: latch disabled.')
    return

def get_latch_status():
    # is there a /home/oot/.latch_enabled ?
    if os.path.isfile(FILE_LATCH_SET):
        return True # latch is already set
    # if not, check latch status
    msp430 = pymsp430.msp430(MSP_PORT)
    latch_status = msp430.get_latch_status()
    if latch_status:
        latch_enable()
        print('OOT_start.py: latch status = enabled')
        return True # latch is set
    print('OOT_start.py: latch status = disabled')
    return False # latch is not set

def get_uptime():
    with open('/proc/uptime') as fin:
        uptime = fin.read()
    return float(uptime.split()[0])

def set_led(led, brightness, trigger=None, delay_on=None, delay_off=None):
    if led == BLUE_LED:
        msp430 = pymsp430.msp430(MSP_PORT)
        if brightness == 0: msp430.disable_blue_led()
        else: msp430.enable_blue_led()
        return
    if trigger is None: trigger = 'none'
    subprocess.Popen('echo {} > {}{}trigger'.format(trigger, LEDS, led), shell=True)
    subprocess.Popen('echo {} > {}{}brightness'.format(brightness, LEDS, led), shell=True)
    if delay_on is not None:
        subprocess.Popen('echo {} > {}{}delay_on'.format(delay_on, LEDS, led), shell=True)
    if delay_off is not None:
        subprocess.Popen('echo {} > {}{}delay_off'.format(delay_off, LEDS, led), shell=True)
    return

def test_fail():
    # Never exit this state
    print('Test failed. Enabling red LED, disabling blue, disabling latch, enabling buzzer.')
    set_led(RED_LED, 1)
    set_led(BLUE_LED, 0)
    msp430 = pymsp430.msp430(MSP_PORT)
    msp430.enable_buzzer() # time to be a dickhead
    msp430.disable_latch() # let the switch work
    print('test_fail: waiting forever...')
    while True:
        time.sleep(10)

def check_time_set_time():
    while True:
        if time.gmtime().tm_year >= 2019: # wait for the year to be now or later
            print('Time was already set by NTP/GPSD to: {}'.format( time.ctime() ) )
            break # we're good, keep going, get data
        else:
            import gpsd
            try:
                gpsd.connect()
                gps_now = gpsd.get_current().time
                if gps_now != '':
                    print('platform.py: directly setting time from gps to {}.'.format(gps_now))
                    subprocess.call('date -s {}'.format(gps_now), shell=True)
                else:
                    print('platform.py: Error setting time. No valid GPS source. Setting based on ded reckoning from last GPS file write time.')
                    gps_dir = '/data/gps'
                    gps_fpaths_list = [os.path.join(gps_dir, f) for f in os.listdir(gps_dir)]
                    newest_fpath = max(gps_fpaths_list, key=os.path.getctime)
                    newest_file = os.path.basename(newest_fpath)
                    latest_time = time.strptime(newest_file, 'GPS_%Y%m%dT%H%M%S.%f.log')
                    boot_time_seconds = 60
                    time_offset = 15*60 - boot_time_seconds # ideally get this number (15) from database someday
                    set_time_value = time.gmtime(time.mktime(latest_time) + time_offset)
                    set_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', set_time_value)
                    subprocess.call('date -s {}'.format(set_time), shell=True)
                return
            except:
                continue

    # We have tried to ensure time is set. Is it?
    if time.gmtime().tm_year < 2019:
        # do something about the fact that time is bad
        # not sure what that should be
        # just keep swimming
        pass
    return

def shutdown_in_secs(secs):
    if os.path.exists(FILE_DEBUG_STAY_AWAKE):
        print('platform.py: debug mode configured by {} file, not shutting down.'.format(FILE_DEBUG_STAY_AWAKE))
        return False
    msp430 = pymsp430.msp430(MSP_PORT)
    msp430.send_BB_SHUTDOWN()
    subprocess.Popen(['sleep '+str(int(secs))+'; sudo shutdown now'],shell=True);
    return


