#!/bin/sh
DEVICE=/dev/mmcblk0
PARTITION=p1
SECTOR_SIZE=$(fdisk -l "$DEVICE" | grep "Sector size" | awk '{print $7}')
NUM_PARTITIONS=$(fdisk -l "$DEVICE" | grep 0p | wc -l)
END_SECTOR=$(fdisk -l "$DEVICE" | tail -n1 | awk '{print $4}')

if [ $# -lt 1 ]
then
	echo "Usage: ./read_image.sh IMAGEFILEPATH"
	echo "where IMAGEFILEPATH is a path to the output image file to be recorded"
	exit 255
fi

IMAGEFILEPATH="$1"

if [ $NUM_PARTITIONS -ne 1 ]
then
	echo "Wrong number of partitions on disk. Should be just 1 for a proper image."
	exit 1
fi

dd if="$DEVICE$PARTITION" of="$IMAGEFILEPATH" bs=$SECTOR_SIZE count=$END_SECTOR status=progress
