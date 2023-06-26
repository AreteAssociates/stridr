#!/bin/sh

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
