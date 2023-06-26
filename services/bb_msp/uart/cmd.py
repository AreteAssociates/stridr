#!/usr/bin/python

# BeagleBone to MSP430 UART serial interface for OoT
# Author - cgrebe 
# Initial version 4/26/19
# Uses the BB's UART4 - set to 115.2 kbps
# takes command line arguments of 1 byte, e.g. 1, 2, 3, p, t, etc.
# send those to the MSP, which understands the meaning of the command.
# MSP takes the desired action (through turning on/off corresponding GPIO pins)
# and sends a confirmation message back to the BB.


import sys, serial, time

if __name__ == '__main__':
#    ser = serial.Serial( port = '/dev/ttyS4', 
    ser = serial.Serial( port = '/dev/ttyO4', 
#                     baudrate = 9600,
                     baudrate = 115200,
                     parity = serial.PARITY_NONE,
                     stopbits = serial.STOPBITS_ONE,
                     bytesize = serial.EIGHTBITS,
                     timeout = 0)

    ser.close()
    ser.open()
#    if ser.isOpen():
#        print("Serial is open")
#    ser.write("1")

#    serialcmd = input("serial command: ")
    serialcmd = sys.argv[1]
    ser.write(serialcmd.encode())
#    time.sleep(0.01)
    time.sleep(0.05)    # 50 ms delay to allow MSP to respond
    #outbin = ser.read()
    #out = outbin.decode("utf-8")
    out = ''
    outbin = b'1'
    while (outbin != b''):
        outbin = ser.read()
        out = out + outbin.decode("utf-8")
    print(out)

#    for i in range(4):
#        print(ser.read())
    ser.close()


