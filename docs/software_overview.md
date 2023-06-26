STRIDR System Software Overview
===============================
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
      - Stops OOT_geofence_check.timer
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
- Starts OOT_geofence_check.timer
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
    - Flashing red (50% duty cycle, no blue) = setup + data acquisition took less than 180 seconds, so probably something broke.
    
