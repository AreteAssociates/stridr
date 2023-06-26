#!/bin/sh

DEVICE=/dev/mmcblk0
DATA_PARTITION=p3
MOUNT_POINT=/data
FS_TYPE=ext4
PASSWORD="$1"

create_partition() {
    start_sector=$(fdisk -l $DEVICE | tail -n1 | awk '{print $3 + 1}')
    echo $start_sector
    echo -e "\nn\np\n3\n$start_sector\n\np\nw\n" | fdisk $DEVICE
    new_partition_name=$(fdisk -l /dev/mmcblk0 | tail -n1 | awk '{print $1}')
}


mount $DEVICE$DATA_PARTITION $MOUNT_POINT
if test $? -ne 0; then
    # mount /data failed
    # so it's not there (we hope, I guess!)
    echo "$MOUNT_POINT partition not mounted!"

    mount -t $FS_TYPE $DEVICE$DATA_PARTITION $MOUNT_POINT
    if test $? -eq 32; then
        # no /data is mounted or can be mounted
        # either there is no partition to mount, or the partition is not formatted
        # check whether partition exists
        partition2=$(fdisk -l $DEVICE | tail -n1 | awk '{print $1}')
        if test "$partition2" != $DEVICE$DATA_PARTITION; then
            # partition does NOT exist
            # let's try and create one using this crazy scripted procedure!
            create_partition
            if test "$new_partition_name" = "$DEVICE$DATA_PARTITION"; then
                echo "Created new partition $new_partition_name."
                sleep 1
                partprobe $DEVICE

                # now the partition should exist and there should be a /dev/$DEVICE$DATA_PARTITION
                # time for trust (better to verify but I want to go home)

		# then make file system and mountpoint
                mkfs.$FS_TYPE $DEVICE$DATA_PARTITION
                mount -o remount,rw /
                rm -rf $MOUNT_POINT
                mkdir $MOUNT_POINT
		mount $DEVICE$DATA_PARTITION $MOUNT_POINT

                if test $? -eq "0"; then
                    # Partition is mounted, so add to fstab
                    echo "$DEVICE$DATA_PARTITION $MOUNT_POINT $FS_TYPE defaults 1 2" >> /etc/fstab
           	    echo "Worked; added to fstab."
                else 
                    echo "Failed to create/mount new $MOUNT_POINT partition."
                fi

                mount -o remount,ro /

                mkdir $MOUNT_POINT/audio
                mkdir $MOUNT_POINT/camera
                mkdir $MOUNT_POINT/charger
                mkdir $MOUNT_POINT/conductivity
                mkdir $MOUNT_POINT/gps
                mkdir $MOUNT_POINT/imu
                mkdir $MOUNT_POINT/rf
                mkdir $MOUNT_POINT/satcom
                mkdir $MOUNT_POINT/satcom/mo
                mkdir $MOUNT_POINT/satcom/mt
                mkdir $MOUNT_POINT/sst
                
                chown oot:users $MOUNT_POINT -R
                chmod 775 $MOUNT_POINT -R
                
            else
                echo "FAILED TO CREATE PARTITION!!!"
                exit -1
            fi
        fi
    fi
fi
