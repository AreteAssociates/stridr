Image Configuration Table
======================

| Image | dev_type | Image Name            | Git ver  | FW ver | oot pw         | keepin | keepout         | M~ | D~ | G~ | Part 1 | 2     | 3     | Image configs | service changes                                          | python installs           | NOTES                     |
|-------|----------|-----------------------|----------|--------|----------------|--------|-----------------|----|-----|-----|--------|-------|-------|---------------|----------------------------------------------------------|---------------------------|---------------------------|
| I     | I        | wifi update           | a03bdc8e | 2i     | Liberty1Witch  | 00012  | 16405           | v2 | v1 | v1 | / (ro) | /var  | /data |               |                                                          |                           |                           |

STRIDR Operation Concept
========================
(this is a work in progress)

Overall starting of functions is handled by systemd. The main processes so handled are:
OOT_startup
-----------
OOT_startup is run by systemd at boot. It contains three major states, and performs the following tasks.
   - Configures peripherals (UART, SPI, I2C)
   - Mode 0: first_boot (IF /var/first_boot does NOT exist)
      - Creates /data
      - Checks MSP version and updates if we have a newer file
      - Creates /var/fw_version
      - Creates /var/first_boot
      - Removes /var/last_comms_time
      - Shuts down BB
   - Configures battery charger, set voltage up, checks battery voltage (IF voltage < v_threshold, SCUTTLE)
   - Open partition
   - Mode 1: startup (IF /var/latch_set does NOT exist)
      - Starts OOT_check_latch_change_mode.timer, runs every 5 minutes
      - Starts OOT_acquire_data.timer, runs every 15 minutes
      - quits OOT_startup, lets timers run
   - Set time from GPS or by ded reckoning from previous data file names
   - Mode 2: operational mode (occurs IF /var/latch_set exists)
    - Runs acquire_data.py
    - Sets battery charge voltage back down
    - Shuts down

OOT_startup - check_latch_change_mode
-------------------------------------
check_latch_change_mode is a function which is triggered every 5 minutes by the systemd OOT_check_mode.timer. 
- Checks whether the MSP430 has set its latch (normally after 15 minutes of power on time)
- Stops OOT_check_latch_change_mode
- NOTE: For faster run, this function should be separated out into its own file.


LED Indications and Buzzer
==========================
LEDs are mostly driven by code in OOT_startup. There are several LED states. The red and green LEDs are driven by the BB processor, while the blue is driven by the MSP430, though the BB tells it to turn on or off.
- During first_boot (manufacturing test)
    - Yellow = occurs for around 1 second after turning on power
    - Green = received GPS position and time data correctly
    - Red heartbeat = BB is running
    - 3 beeps + very slowly blinking blue LED = successful first boot, unit passes. Blue light remains on after BB powers itself down
    - Solid red LED = boot test fails (many potential causes)

- During normal boot
    - Yellow = occurs for around 1 second after turning on power
    - Green = received GPS position and time data correctly
    - Red heartbeat = BB is running
    - Solid red LED = boot test fails (many potential causes)

- During operational mode
    - Blue, green LEDs disabled
    - Red heartbeat continues, except during camera data acquisition (see camera DAQ code)

- During other failures
    - Flashing red and flashing green, unsynchronized (no blue) = this probably shouldn't happen anymore, but it means OOT_start broke somewhere.
    - Flashing red (50% duty cycle, no blue) = setup + data acquisition took less than 180 seconds, so probably something broke.
    
Tools for Understanding STRIDR better
=====================================
Understanding STRIDR's current state is easier if you can use the following tools.

Basic Commands
--------------
```systemctl list-timers``` produces the timer list. The timers are turned on and off by the various modes of the system. 

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
```buzzkill``` will shut the damn buzzer off for a second, if it turns on anymore.

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
