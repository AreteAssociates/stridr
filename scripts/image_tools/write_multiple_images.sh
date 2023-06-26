#!/bin/sh
OUTPUT_ROOT=/dev/sd
OUTPUTS=[b-z]  # will output to $OUTPUT_ROOT$OUTPUTS i.e. /dev/sdb, /dev/sdc... /dev/sdz if they exist
DIRLIST=$(ls $OUTPUT_ROOT$OUTPUTS)

if [ $# -lt 1 ]
then
        echo "Usage: ./copy_images.sh IMAGEFILEPATH"
        echo "where IMAGEFILEPATH is a path to an image file to be written to every damn drive in the range $OUTPUT_ROOT$OUTPUTS"
        exit 255
fi
IMAGEFILE=$1
if [ -e "$IMAGEFILE" ]
then

        for f in $DIRLIST
        do
                if [ ! $progress_indicator ]
                then
                        dd if="$IMAGEFILE" of="$f" status=progress &
                        progress_indicator=1
                else
                        dd if="$IMAGEFILE" of="$f" &
                fi
        done
else
        echo "Image file: $IMAGEFILE not found."
        exit 1
fi

