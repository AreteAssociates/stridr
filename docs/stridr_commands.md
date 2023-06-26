STRIDR Commands
===============
Understanding STRIDR's current state is easier if you can use the following tools.

Basic Commands
--------------
```systemctl list-timers``` produces the timer list. The timers are turned on and off by the various modes of the system. Geofence, for example, is disabled until the latch is set 15 minutes after boot.

```systemctl status OOT_startup``` is most interesting during the modes first_boot and operational_mode.

```systemctl status OOT_acquire_data``` shows data acquisition during startup mode.

```systemctl status OOT_MSP``` shows the log of interactions between the MSP and client code. Returned data is base64 encoded.

```systemctl status OOT_check_mode``` shwos the log of the latch status monitor. It becomes interesting about 5 minutes after power up and until the latch is set.

Keeping Units Running
---------------------
When running the unit on the benchtop for a while, it can be handy to do the following things.

```touch /tmp/debug_stay_awake``` inhibits latch and shutdown so the unit stays awake indefinitely

```sudo systemctl start OOT_acquire_data.timer``` makes the DAQ process run every 15 minutes

System State Files in /var
--------------------------
There are a number of files in /var which help understand what's going on.
```/var/first_boot``` is created after first_boot is completed. STRIDR will not run first_boot if this file exists.

```/var/latch_set``` is created after the latch is set and the unit is in operational mode.

```/var/serial_number``` is the IMEI of the modem.

```/var/battery_voltage``` is the battery voltage (from the charger) at boot.

```/var/device_type``` contains a single letter indicating the unit image type. It isn't used for much anymore, unless it's 'B'.

```/var/fw_version``` contains the version of firmware currently programmed into the MSP430.

```/var/last_comms_time``` is stamped with the last successful Iridium comms time. Once this is (typically) 24 hours old, the unit will scuttle.

```/var/system_fail_count``` is the general_fail_counter. If this gets to 10, the unit will scuttle itself.

Starting Over or Creating an Image
----------------------------------
If you want to start from scratch on your unit, don't delete files or do anything by hand. You'll probably make a mistake which you'll regret, and subsequently won't be able to make anything work right. There is a tool which will repave the unit so that it is ready to run from scratch. This will allow you to create an image from this card, if desired, or just run the unit almost as though it has never run before.
```
/home/oot/STRIDR/scripts/deploy.sh
/home/oot/STRIDR/scripts/image_tools/prepare_for_image.sh
```
The first will delete /data, remove the device serial number, unset the latch, and a variety of other functions. The second pulls files from the local repository and deploys them around the filesystem as appropriate.

Read-Only Filesystem
--------------------
The root filesystem is mounted, by default, as a read-only filesystem. You can't even update STRIDR. There are tools in .bashrc if you log in as oot which will help you.

```rw``` will remount the filesystem read-write.

```ro``` will remount the filesystem read only.

Interacting with the Buzzer
---------------------------
```buzzkill``` will shut the damn buzzer off for a second. Some scuttle sources will turn it right back on. Best of luck.

```buzz``` will make your neighbors angry with you.

Talking to the MSP430
---------------------
The MSP430 interacts with the main processor using a serial interface. If you aren't careful collisions can occur.
```python
from STRIDR.services.pymsp430 import pymsp430
msp430 = pymsp430.msp430('/dev/ttyS4')
msp430.disable_latch()
```

When a component returns data (beyond a boolean status) it can be accessed using the ```.data``` attribute, ala ```msp430.get_password().data```. In most cases this is handled within pymsp430.

There are existing scripts in ```STRIDR/scripts/msp_tools```.

If you need to interact with the MSP directly, perhaps for a function which is not implemented in pymsp430, or for speed/convenience (i.e. via a console port), it is possible. It may mess up things that the RPC server is expecting (by eating received data) and cause other errors, so do it quick and close the port fast.
```shell
miniterm.py /dev/ttyS4 115200
b
^[
```
The previous commands would open the serial port, turn the buzzer off, and close the port. These commands are buried within the pymsp430 function. Useful commands include:
```b``` Turn off the buzzer.

```B``` Turn on the buzzer.

```l``` Turn off the latch.

```L``` Turn on the latch.

```?L``` Get the latch state.

Crashes During Boot?
--------------------
The system is designed such that if the MSP430 doesn't get appropriate acknowledgment within 60s it will attempt to reboot. The typical presentation of this failure mode looks something like the following, usually in the middle of a session on the command line:
```shell
[   57.370611] musb-hdrc m▒▒▒
```
This usually occurs after a failure during OOT_startup in which the very first few tasks don't run. Those first few tasks configure the pins connecting to the MSP430 as UARTs and send it a command to let it know that the processor successfully booted. The following commands will give you about 5 minutes of run time.
```shell
sudo -s
echo uart > /sys/devices/platform/ocp/ocp:P9_11_pinmux/state
echo uart > /sys/devices/platform/ocp/ocp:P9_13_pinmux/state
echo out > /sys/class/gpio/gpio46/direction
echo 1 > /sys/class/gpio/gpio46/value
echo X > /dev/ttyS4
echo x > /dev/ttyS4
touch /tmp/debug_stay_awake
date -s '2023-01-19 16:00:00'
exit
```
Once this has run there should be some breathing room. Check systemctl to make sure that OOT_extend_BB is running - both its timer and the task.
```shell
sudo systemctl list-timers
sudo systemctl OOT_extend_BB status
```
If they are not running, or if there is an error on either, you'll have to send the
```shell
sudo -s
echo x > /dev/ttyS4
exit
```
before five minutes elapse, every five minutes. You can either write a script to do this for you, or figure out how to fix this timer/task which do exactly this for you automatically. Then you need to debug whatever causes the crashes in the first place. It mostly has to do with something screwing up OOT_start, which can be a lot.

