#!/usr/bin/env python3
from STRIDR.services.pymsp430 import msp430

msp430 = pymsp430.msp430('/dev/ttyS4')
msp430.send_BB_EXTEND()
