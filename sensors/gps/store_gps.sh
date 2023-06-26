#!/bin/sh
#
# Runs gpspipe (from gpsd) to store gps raw NMEA strings
# Takes command line arguments
# Usage:
#   store_gps.sh run_seconds output_path
#
# Where:
#   run_seconds = number of seconds of data to run for
#   output_path = location to write output files to

NUM_SECONDS=$1
OPATH=$2

# create output filename in specified path
DATE=$(date +%Y%m%dT%H%M%S.%3N)     # add .%3N for .milliseconds
OFPATH=$2/GPS_$DATE.log

# make sure directory exists
mkdir -p $OPATH

/opt/gpsd/gpspipe -r -x $NUM_SECONDS -o $OFPATH
