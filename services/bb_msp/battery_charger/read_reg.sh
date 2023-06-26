#!/bin/sh

echo "Register Status"
i2cdump -r 0x00-0x20 -y 1 0x24

