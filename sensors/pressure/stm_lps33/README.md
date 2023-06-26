
Initial results of playing with the pressure sensor are positive.

$ i2cdetect -y -r 1
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- 5d -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --

Try sending the 'WHO_AM_I' command; expect 0xb1

$ i2cget -y 1 0x5d 0x0f b
0xb1

Reading pressure values, in order of highest to lowest byte:

$ i2cget -y 1 0x5d 0x2a b
0x2f
$ i2cget -y 1 0x5d 0x29 b
0x4e
$ i2cget -y 1 0x5d 0x28 b
0x48

Not sure if that's good or not. KDCA reports 1020.4mb or 30.14 inches as of 1 hour prior.
0x2f4e48 as a 24 bit value in 2's complement... is 3,100,232. Divided by 4096 LSB/hPa =
756 hPa. So... that's a little low, since 1 hPa = 1 mbar. The sensor does say calibration
needs to be done.

Temperature sensor doesn't look... good.

$ i2cget -y 1 0x5d 0x2c b
0x00
$ i2cget -y 1 0x5d 0x2b b
0x00

