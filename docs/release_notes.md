Release Notes, STRIDR Release J
===============================
- Removed numerous unnecessary features, including
    - battery_scuttle
    - general_fail functionality
    - geofence and related functionality, as well as nearly everything scuttle-related

Release Notes, STRIDR Release I
===============================

System Behavior
---------------

- Geofence scuttle behavior
    - Stale GPS scuttle now properly triggers scuttle directly; if GPS points are stale long enough, the system will scuttle when the position uncertainty (calculated using the programmed maximum drift speed) intersects with a geofence boundary.
    - Revised associated shell scripts to improve clarity and make sure we really do scuttle in the cases we want to scuttle.
    - Adds hooks for test mode.
    - On MT scuttle command, buzzer is enabled prior to scuttling.
- Engineering messages
    - Revised engineering message transmission concept to transmit such messages (scuttle, mostly) at the tail end of a normal MO comms message, and block until they do. A send_immediate mode is retained to allow specific messages to transmit on their own, since these are outside of the normal comms process (first_boot, battery_scuttle and general_fail_scuttle reports). This was necessary because there is no mechanism for sharing the SATCOM interface.
    - Field for battery voltage is now calculated the same way as for comms/data messages.
    - Adds software version to engineering messages, using subcomponent field to match comms/data messages.
- MT commands
    - Unmangles PING functionality; should work, now.
- Bootstrap (OOT_startup/OOT_start.py)
    - Fixes general_fail behavior to increment and test counter, ultimately resulting in scuttle on limit.
- Services
    - Eliminated OOT_acquire_data service and timer. Timer is no longer run during no-latch period, because the no-latch period has been reduced from 3 hours to 15 minutes. This corresponded with the latch time and associated events, which was confusing and strange, and so the system was recognizing the latch to be set and was starting to shut down, just at the same time as the timer was going off and starting a new DAQ round.

Algorithms and Comms Services
-----------------------------
- Reverted algorithm byteIDs to match the ICD
- Fixed comms.data_readers._read_gps() to only use ZDA messages for most_recent_date setting
- Fixed algorithms with import errors
- Verified algorithm Components match their Signal, updated Components to match Signal if they did not match
- Updated Mode_Zero.Mean_Var to return None if all means are zero (i.e. there is no data). Fixes issue where a Mode_Zero signal would be sent with all zeros
- Updated Mode_Zero.Co_Var to handle the case of more than three co-variances
- Updated Image_Clouds to fail gracefully and return a None Signal when it’s dark out
- Updated comms.data_readers._read_imu() to return the correct number of arguments when reading a wave spectrum
- Fixed ReadSpectrum.Read_Spectrum bin averaging, define its components the same as other array like Signals
- Fixed M~ to return the correct number of arguments from runSpectralFeatureExtractor()
- Changed the data message header to include GPS health information (dilution of precision and number of satellites)
- Updated Running_Light_Detector to return the number of detections (max 4) along with heading and color for each
- Updated the decoder to handle the new data message header format, prettify the output, and handle redefined components from Running_Light_Detector

Release Notes, STRIDR Release H
===============================

H1
--
- New GOM geofence
- Phase 1a, 1b geofences
- detect I2C failure
- hostname correctly set
- completely replaced MT SATCOM handler
- adds db update MT command
- TODO: make sure geofence isn't fucked up using /var/geofence_resources
- update battery_scuttle threshold to 12.8V based on new data and testing
- fixes param handling for analysis scripts
- adds shell MT command
- moves charger configuration after first_boot to make sure MSP is programmed first
- adds index to example.db for faster timestamp query
- BB battery scuttle voltage fixed to 12.8V


H0
--
- filesystem changes: ro /, rw /var
- add new general fail counter leading to scuttle (default 10 fails)
- minimum 180 seconds uptime
- fix flask server so it runs
- revise engineering message function to add a standard format for time/position
- simplify engineering message function to eliminate dependency on DB and add current position/battery
- make extend_BB back to a watchdog timer; runs 1x at 4 minutes, then only a second time after 8 minutes, after which system should shut down gracefully. If extend_BB never runs, the MSP will still cut off power at 5 minutes.
- add priority control for DAQ processes allowing different nice value for each sensor acquisition process
- add MT commands for
    - geofence get/set
    - ping
    - configure processing variables
- add new SATCOM message indicating successful boot
- new geofence handler
- add new op user
- only look at data > 10 minutes old
- IMU wavelog becomes separate file
- camera uses hdr, processes 3 files, disable heartbeat during camera acq
- audio processing
    - new processing
    - fixed reader
- re-enable M~ code
- update M~ code version
- lower battery voltage setpoint when BB turns off
