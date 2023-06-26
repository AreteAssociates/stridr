#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/oot')

from STRIDR.services.satcom import satcom
from STRIDR.sensors.charger import act2861
from STRIDR.sensors.imu import mpu9250
from STRIDR.services.pymsp430 import pymsp430
import gpsd
import time
import math

# set up all our little goodies
gpsd.connect()
#iridium = satcom.iridiumModem('/dev/ttyS2') # do this after unit is powered up
charger = act2861.act2861(1)
try:
    imu = mpu9250.MPU9250() # bus is hardwired into it
    imu_ok = True
except:
    print('FAIL: imu not on bus')
    imu_ok = False

gps_retries = 30
iridium_retries = 10
interval = 1 #seconds

#############################################
# wait for gps
while gps_retries >= 0:
    g_current = gpsd.get_current()
    if g_current.mode < 3:
        print('Waiting on GPS: current mode {}.'.format(g_current.mode))
        interval = 1 #seconds
        time.sleep(interval - time.monotonic() % 1)
        gps_retries -= 1
    else:
        print(gps_retries, g_current)
        print('PASS: GPS 3D lock and position obtained.')
        break
else:
    print('FAIL: No gps!')

#############################################
# check imu
if imu_ok:
    print('Checking IMU')
    print(imu.readAccel())
    accels = imu.readAccel()
    x = accels['x']
    y = accels['y']
    z = accels['z']
    a = math.sqrt(x**2 + y**2 + z**2)
    print('Acceleration vector magnitude: {:0.3f}'.format(a))
    if ( (a > 0.95) and (a < 1.05) ):
        print('PASS: Accelerometer within 5%.')
    else:
        print('FAIL: Accelerometer outside 5%.')
else:
    print('FAIL: IMU not on bus!')

#############################################
# look at i2c bus - charger
vout = 0
vout = float(charger.get_adc_vout())
print('Charger battery voltage: {:0.3f}'.format(vout))
if ( (vout < 16) and (vout > 10) ):
    print('PASS. Charger battery voltage {:0.3f} within limits (10-16V)'.format(vout))
vout = float(charger.get_adc_vout())
vin = float(charger.get_adc_vin())
iout = float(charger.get_adc_iout())
iin = float(charger.get_adc_iin())
print('Battery charger status: Vin: {}V, Iin: {}'.format(vin, iin))
print('Battery charger status: Vout: {}V, Iout: {}'.format(vout, iout))

#############################################
# power up modem
msp430 = pymsp430.msp430('/dev/ttyS4')
msp430.enable_modem()
iridium = satcom.iridiumModem('/dev/ttyS2')
imei = iridium.get_imei()
print('Iridium modem detected: imei: {}'.format(imei))
if iridium.is_gateway_commercial(): print('*****FAIL*****! WRONG MODEM INSTALLED, NON-DOD GATEWAY!')
print('Trying {} times to get iridium modem network time.'.format(iridium_retries))
while iridium_retries >= 0:
    signal_strength = iridium.get_signal_strength()
    if signal_strength > 0:
        print('Signal strength: {}, attempt: {}'.format(signal_strength, iridium_retries))
        for i in range(10):
            iridium_time = iridium.get_time()
            print('Iridium network time: {}'.format(iridium_time))
            time.sleep(interval - time.monotonic() % 1)
        break
    else:
        print('Signal strength: {}, attempt: {}'.format(signal_strength, iridium_retries))
        iridium_retries -= 1
else:
    print('FAIL: No Iridium signal!')

msp430.disable_modem()


