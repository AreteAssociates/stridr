#!/bin/sh

# make the buzzer output low
if [ -e /sys/class/gpio/gpio64 ]
then
  # shut up damn buzzer
  echo "not making directory"
  echo out > `readlink -f /sys/class/gpio/gpio64/direction`
  echo 0 > `readlink -f /sys/class/gpio/gpio64/value`
else
  echo "making directory"
  echo 64 > /sys/class/gpio/export
  echo out > `readlink -f /sys/class/gpio/gpio64/direction`
  echo 0 > `readlink -f /sys/class/gpio/gpio64/value`
fi

# enable satcom
echo "enabling satcom"
echo out > /sys/class/gpio/gpio47/direction
echo 0 > /sys/class/gpio/gpio47/value

# set bus enable BB_PORT_ENABLE (active low)
echo "out" > /sys/class/gpio/gpio46/direction
echo 0 > /sys/class/gpio/gpio46/value

# pins for UART4 & GPIO - BSL
config-pin P9.11 uart
config-pin P9.13 uart

# gpio44 is the problematic pin- that causes a crash when turned to gpio
# seemingly this can be avoided by setting the direction as out, below
# then - try to set as gpio after - config-pin lines were initially before
# where echo out > ... is now
echo out > /sys/class/gpio/gpio44/direction
echo out > /sys/class/gpio/gpio45/direction

config-pin P8.11 gpio
config-pin P8.12 gpio


# pins for UART1 - GPS
config-pin P9.24 uart
config-pin P9.26 uart

# pins for UART2 - modem
config-pin P9.21 uart
config-pin P9.22 uart

# i2c1
config-pin P9.17 i2c
config-pin P9.18 i2c

# power up 1w bus
echo out > /sys/class/gpio/gpio49/direction
echo 1 > /sys/class/gpio/gpio49/value
