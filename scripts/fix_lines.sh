#!/bin/sh

cd ~/STRIDR
find . -type f -name *.sh -exec sed -i -e 's/\r$//' "{}" \;
find . -type f -name *.py -exec sed -i -e 's/\r$//' "{}" \;
