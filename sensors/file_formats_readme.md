Some notes on OoT File Formats
------------------------------
Author: P.J. Rusello, prusello@arete.com  

### Each sensor stores data in a human readable file format with header information in a separate readme file.  

1. On the BeagleBone each sensor gets a folder on the SD card at `/data/[sensor_name]`  

    If your sensor produces a lot of data or multiple files for each sample, e.g. the IMU, go ahead and make sub-directories for each type if that makes sense. Put a readme in each sub-directory instead of at the top level describing the files in the sub-directory only.  

2. Make new datafiles each hour.  

    Filenames should have the the [sensor_name] and UTC date and time in ISO format, reporting time to the minute: `sea_surface_temperature_2019-01-22T1500.csv`

    Note no colons between hours and minutes.  
    We can explore short names for sensors in the future (e.g. sst for sea surface temperature).

3. Report data to a reasonable accuracy and use at least `", "` (note the whitespace after the comma) as a separator. This will help if someone is debugging and scanning visually for odd values.  

    If you want to be even nerdier, make it comma separated and fixed width fields so everything is column aligned.  


4. The first field on each row of data should be the ISO timestamp in UTC reported to fractional seconds (hundredths of a second should be sufficient for most sensors). Timestamp format is `2019-01-22T150530.00`

    If a sample represents an average over time, the timestamp should reflect the middle of the sampling interval (e.g. a 30 second average starting at 170500 would get a timestamp of 170515.00)  


    All other fields are at the discretion of the sensor lead, but should be documented in the readme file.  

    Here's a sample data row for air temperature and barometer:

        `2019-11-15T134501.00,     35.7500,    102.0827`
    
### We can and probably will modify these standards once things are running, if you identify something that doesn't work or needs clarification, mention it to P.J. and Jim and we'll update this document.  


# Sensor readme 

At `/data/[sensor_name]/` make a file called `[sensor_name]_readme.txt`. Make sure the directory and readme use the same `[sensor_name]`.  

- Line 1 should be field_names, comma separated with at least `", "`
- Line 2 should be SI units, comma separated with at least `", "`

Combination units should be separated by `_` and have powers listed as a carat `^` and an integer after the unit if needed. E.g. `m/s` would be `m_s^-1`.  

The remainder of the readme should be human readable descriptions with at least the following information: 

- Last update (make it ISO format, just to be consistent) and by whom.
- Manufacturer and model number of the sensor (go ahead and download datasheets and put them in the OoT repo if you haven't)
- Sampling strategy, e.g. warmup for 5 seconds, measure for 20 seconds, average the 20 second measurement and report it as a sample, do this every 15 minutes
- Expected uncertainty - put "unknown" if we don't know anything
- Derived data products - e.g. pressure trend, wave height

For derived data products, feel free to elaborate in the readme on calculation detials or refer to the code (which should be self-documenting, no?) for calculation details. Make references as explicit as possible, e.g. filename and line number.