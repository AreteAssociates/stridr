#!/bin/sh
DEVICE=/dev/mmcblk0
DATA_PARTITION_ID=3
DATA_PARTITION=p$DATA_PARTITION_ID
DATA_MOUNT=/data
ENCRYPTED_MOUNT=/dev/mapper/c1
STRIDR_ROOT=/home/oot/STRIDR
MSP_PORT=/dev/ttyS4

RESOURCES_DIR=/home/oot/STRIDR/scripts/resources
DEPLOY_DIR=$RESOURCES_DIR/deploy

delete_if_exists() {
	if [ -e $1 ]
	then
		rm "$1" -rf
	fi
}

# Check whether run as root
if [ `id -u` -ne 0 ]
then
  echo "Must be run as root. Quitting..."
  exit 1
fi

# unset latch
echo l > $MSP_PORT

# mount drive rw
echo "Remounting drive as read-write to allow modifications..."
mount -o remount,rw /

# turn off most services, disable acquire and geofence. Make sure extend is enabled.
systemctl stop OOT_acquire_data.timer
systemctl disable OOT_acquire_data.timer
systemctl stop OOT_acquire_data
systemctl stop OOT_check_mode.timer
systemctl stop OOT_startup
systemctl stop OOT_geofence_check.timer
systemctl disable OOT_geofence_check.timer
systemctl start OOT_extend_BB.timer
systemctl enable OOT_extend_BB.timer

# find out how many partitions there are
MAX_PART_ID=$(fdisk -l /dev/mmcblk0 | tail -n1 | awk '{print $1}' | grep -o .$)

# kill partition 3 if it exists
if [ $MAX_PART_ID -eq $DATA_PARTITION_ID ]
then
	echo "Remove partition $DATA_PARTITION"
	umount $DATA_MOUNT
	cryptsetup luksClose $ENCRYPTED_MOUNT
	wipefs --force --all $DEVICE$DATA_PARTITION
	echo -e "\rp\nd\n$DATA_PARTITION_ID\np\nw\n" | fdisk $DEVICE
	partprobe $DEVICE
	echo "Reprobed devices."
	ls $DEVICE*
else
	echo "Already removed $DATA_PARTITION"
fi

# remove data mountpoint
echo "Removing data partition mountpoint"
delete_if_exists $DATA_MOUNT

# remove partition from fstab
#echo "Removing data partition from fstab"
#sed -i".bak" '/$DEVICE$DATA_PARTITION/d' /etc/fstab
#rm /etc/fstab.bak

# kill geofence data files
echo "Removing geofence status/log files"
delete_if_exists $STRIDR_ROOT/services/geofence/bash/*.txt
delete_if_exists $STRIDR_ROOT/services/geofence/bash/scuttle-command-log.txt
delete_if_exists $STRIDR_ROOT/services/geofence/bash/scuttle-system-status.bin
delete_if_exists $STRIDR_ROOT/services/geofence/scuttle-system-status.bin
delete_if_exists $STRIDR_ROOT/services/geofence/scuttle_result.txt
delete_if_exists $STRIDR_ROOT/services/geofence/check-geofence-log.txt
delete_if_exists $STRIDR_ROOT/services/geofence/gps-log.txt
delete_if_exists /var/scuttle-system-status.bin
delete_if_exists /var/gps-log.txt
delete_if_exists /var/check-geofence-log.txt


# kill STRIDR boot status files
echo "Removing STRIDR status files in /var"
delete_if_exists /var/latch_set
delete_if_exists /var/first_boot
delete_if_exists /var/last_comms_time
delete_if_exists /var/scuttle_enabled # not used yet

# remove comms database file
echo "Removing comms database and any signals and lat long files"
delete_if_exists /var/system_messages/example.db
rm -f /var/system_messages/signal_queue/*

# reset hostname
echo "Resetting hostname to: stridr-not_booted"
hostnamectl set-hostname stridr-not_booted

# deploy default hosts file
echo "Resetting /etc/hosts to default"
cp $DEPLOY_DIR/etc/hosts /etc/hosts

# unset latch just in case it latched while we worked
echo "Unsetting latch"
echo l > $MSP_PORT

# mount ro again
echo "Remounting drive read-only to prevent modifications..."
mount -o remount,ro /

# now ready for shut down and imaging
echo "Latch unset. Ready to shutdown now."
