#!/bin/bash

OPERATOR_USER=op
OPERATOR_PASS=oceanofthings

SYSTEM_DIR=/etc/systemd/system
RESOURCES_DIR=/home/oot/STRIDR/scripts/resources
OOT_FILES_DIR=$RESOURCES_DIR/systemd_services
DEPLOY_DIR=$RESOURCES_DIR/deploy

# Check whether run as root
if [[ $(id -u) -ne 0 ]]
then
  echo "Must be run as root. Quitting..."
  exit 1
fi

# Remount / as rw
echo "[-] Remounting / as read-write for modifications..."
mount -o remount,rw /

# Update device tree file
echo "[-] Updating device tree file with current unit"
mkdir -p $DEPLOY_DIR/boot/dtbs/4.19.31-bone30/
dtc -W no-unit_address_vs_reg -I dts -O dtb -o $DEPLOY_DIR/boot/dtbs/4.19.31-bone30/am335x-STRIDR-uboot-univ.dtb $RESOURCES_DIR/am335x-STRIDR-uboot-univ.dts
cp -u $DEPLOY_DIR/boot/dtbs/4.19.31-bone30/am335x-STRIDR-uboot-univ.dtb /boot/dtbs/4.19.31-bone30/am335x-boneblack-uboot-univ.dtb
rm $DEPLOY_DIR/boot/dtbs/4.19.31-bone30/am335x-STRIDR-uboot-univ.dtb

# Update wifi config files
echo "[-] Updating wifi config files for connman"
cp -u $DEPLOY_DIR/var/lib/connman/* /var/lib/connman

# Update boot script
echo "[-] Updating boot script"
cp -u $DEPLOY_DIR/opt/scripts/boot/* /opt/scripts/boot
cp -u $DEPLOY_DIR/etc/default/bb-boot /etc/default/bb-boot

# Pushing latest comms processing params
echo "[-] Pushing params.pkl to overwrite in system_messages"
cp -u $DEPLOY_DIR/var/system_messages/params.pkl /var/system_messages

# Remove existing service files
echo "[-] Removing service files from systemd/system"
rm $SYSTEM_DIR/OOT_acquire_data.service
rm $SYSTEM_DIR/OOT_acquire_data.timer
rm $SYSTEM_DIR/OOT_check_mode.service
rm $SYSTEM_DIR/OOT_check_mode.timer
rm $SYSTEM_DIR/OOT_extend_BB.service
rm $SYSTEM_DIR/OOT_extend_BB.timer
rm $SYSTEM_DIR/OOT_startup.service
rm $SYSTEM_DIR/OOT_geofence_check.service
rm $SYSTEM_DIR/OOT_geofence_check.timer
rm $SYSTEM_DIR/gps.service
rm $SYSTEM_DIR/OOT_MSP.service
rm $SYSTEM_DIR/OOT_flask.service

# Link service files to repo
echo "[-] Linking systemd service/timer files to STRIDR"
#ln -s $OOT_FILES_DIR/OOT_acquire_data.service $SYSTEM_DIR/OOT_acquire_data.service
#ln -s $OOT_FILES_DIR/OOT_acquire_data.timer  $SYSTEM_DIR/OOT_acquire_data.timer
ln -s $OOT_FILES_DIR/OOT_check_mode.service  $SYSTEM_DIR/OOT_check_mode.service
ln -s $OOT_FILES_DIR/OOT_check_mode.timer    $SYSTEM_DIR/OOT_check_mode.timer
ln -s $OOT_FILES_DIR/OOT_extend_BB.service  $SYSTEM_DIR/OOT_extend_BB.service
ln -s $OOT_FILES_DIR/OOT_startup.service $SYSTEM_DIR/OOT_startup.service
ln -s $OOT_FILES_DIR/OOT_extend_BB.timer  $SYSTEM_DIR/OOT_extend_BB.timer
ln -s $OOT_FILES_DIR/gps.service $SYSTEM_DIR/gps.service
ln -s $OOT_FILES_DIR/OOT_flask.service $SYSTEM_DIR/OOT_flask.service

# Reloading systemd
echo "[-] Reloading systemd"
systemctl daemon-reload

# Update database
echo "[-] Updating database from dump"
rm /var/config.db
cat $RESOURCES_DIR/config.dump | /usr/bin/sqlite3 /var/config.db

# Update IMU calibrations
cp -f resources/imu_cal/* /var/lib/robotcontrol/

# Create op user if not exist
echo "[-] Adding operator user ($OPERATOR_USER) if it does not already exist... errors may appear."
echo -e "$OPERATOR_PASS\n$OPERATOR_PASS\n\n\n\n\n\n" | sudo adduser $OPERATOR_USER
if [[ $? -eq 0 ]] 
  then
  echo "[-] Created user $OPERATOR_USER."
fi
echo "Updating files to $OPERATOR_USER home directory."
cp -r $RESOURCES_DIR/op/* /home/$OPERATOR_USER
echo "[-] Setting permissions"
chown $OPERATOR_USER:$OPERATOR_USER /home/$OPERATOR_USER -R

# Make sure op can modify device_type
echo "[-] Setting /var/device_type to ownership $OPERATOR_USER:$OPERATOR_USER"
chown $OPERATOR_USER:$OPERATOR_USER /var/device_type

# Remount / as ro
echo "[-] Remounting / as read-only to prevent further modifications..."
mount -o remount,ro /

echo "[+] Deploy script completed."

