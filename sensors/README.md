# Sensor Data Acquisition Code Library

This is the home for code for acquiring data used for STRIDR sensors 
used in the Ocean of Things program.

The current hotel sensor list includes
--
- Air Temperature and Barometric Pressure, Freescale MPL115A2
- Sea Surface Temperature, Maxim DS18B20
- IMU, TDK Invensense 9250 (testing) and ICM-20948 (production)
- Microphone, CUI XXXXXX
- GPS, uBlox MAX-M8Q

The current mission sensor list includes
--
- Camera, ELP or TTL USB camera module with wide angle lens
- Conductivity, Hanna Instruments flow-through conductivity probe
- Hydrophone, OEM hydrophone
- SDR, OEM module for X-band and AIS detection

Each sensor has a directory for sampling code. As of 22-Jan-2019 each sensor should be writing data to a human readable csv file with timestamps. See [file formats](/file_formats_readme.md) for details on data formatting.  

Bench, laboratory, and marina testing data can be found in two places.  

- Maybe check [Sharepoint][] if it's really old data you're looking for.  
- But, Sharepoint is really slow, so you should use [Arete shared][arete-shared] instead.  



[Sharepoint]: <aretesp/projects/OoT/Shared Documents/Testing Data/benchdata>
"Sharepoint"
[arete-shared]: </arete/shared/arlington/Engineering/Projects/3_Data> "Arete shared"