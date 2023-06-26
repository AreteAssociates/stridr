#!/usr/bin/env python3

import sys
import os
import time
import subprocess
from STRIDR.services.pymsp430 import pymsp430
import systemd_control

retries = 3
DEBUG = True

GPIO_BASE               = r'/sys/class/gpio/gpio'
BB_GPIO_ENABLE          = 46
BB_GPIO_HOLD_5V         = 114
BB_GPIO_RST             = 116
BB_GPIO_TEST            = 45
BB_MSP_UART             = 4
MSP_PORT                = r'/dev/ttyS4'

FILE_FWVER              = r'/var/fw_version'
FW_UPDATE_PATH          = r'/home/oot/STRIDR/scripts/resources/firmware'
IMAGE_FLASHER_PATH      = r'/home/oot/STRIDR/scripts/resources/bootloader/'
IMAGE_FLASHER_BINARY    = IMAGE_FLASHER_PATH + 'command_line_bsl'

BB_PORT_ENABLE          = GPIO_BASE+str(BB_GPIO_ENABLE)
BB_PORT_HOLD_5V         = GPIO_BASE+str(BB_GPIO_HOLD_5V)
IMAGE_FLASHER_COMMAND   = '{} {} {} {}'.format(IMAGE_FLASHER_BINARY, BB_GPIO_RST, BB_GPIO_TEST, BB_MSP_UART)

def get_running_version():
    try:
        msp430 = pymsp430.msp430(MSP_PORT)
        running_version_string = msp430.get_version()
        return running_version_string.decode().split(' ')[1][:-1]
        # result is in form '0.001x'
    except:
        # either very old or nothing burned
        return ''

def get_latest_fw_version():
    flist = os.listdir(FW_UPDATE_PATH)
    newest_fw_file = max(flist)
    newest_ver_string = os.path.splitext(newest_fw_file)[0]
    newest_ver_string = newest_ver_string[newest_ver_string.find('main')+5:]
    newest_ver_string = newest_ver_string.replace('_', '.')

    print('Newest FW version in {} is {}.'.format(FW_UPDATE_PATH, newest_ver_string))
    return newest_ver_string, newest_fw_file

def do_flash(fw_fpath):
    if DEBUG: print('do_flash', fw_fpath)

    subprocess.call("echo x > /dev/ttyS4", shell=True)
    subprocess.call("echo X > /dev/ttyS4", shell=True)
    subprocess.call("echo out > {}/direction".format(BB_PORT_HOLD_5V), shell=True)
    subprocess.call("echo 1 > {}/value".format(BB_PORT_HOLD_5V), shell=True)
    subprocess.call("echo out > {}/direction".format(BB_PORT_ENABLE), shell=True)
    subprocess.call("echo 1 > {}/value".format(BB_PORT_ENABLE), shell=True)
    subprocess.call("echo Z > /dev/ttyS4", shell=True)
    try:
        subprocess.call("cat /dev/ttyS4", shell=True, timeout=1)
    except subprocess.TimeoutExpired:
        # there was nothing there to flush out, fine.
        pass

    print('MSP versions are different. Need update.')
    p = subprocess.Popen([IMAGE_FLASHER_BINARY, 
                          str(BB_GPIO_RST),
                          str(BB_GPIO_TEST),
                          str(BB_MSP_UART),
                          fw_fpath], shell=False).wait()
    while type(p) is not int: p.poll()
    returncode = p
    print ('Flasher returned {}'.format(returncode))
    if returncode == 0:
        return True
    return False

def cleanup_from_flash_attempt():
    subprocess.call("echo 0 > {}/value".format(BB_PORT_HOLD_5V), shell=True)
    subprocess.call("echo 0 > {}/value".format(BB_PORT_ENABLE), shell=True)
    subprocess.call("echo 0 > {}/value".format(BB_PORT_HOLD_5V), shell=True)
    return

def is_flash_up_to_date(fw_fpath):
    if DEBUG: print('is_flash_up_to_date', fw_fpath)
    # Tell new image that we're up and running
    msp430 = pymsp430.msp430(MSP_PORT)
    print('BB_RUNNING:', msp430.send_BB_RUNNING())
    print('BB_EXTEND:', msp430.send_BB_EXTEND())

    # Get version of newly-flashed MSP
    try:
        running_version = get_running_version()
        if DEBUG: print('Running version:', running_version)
        if DEBUG: print('Expected version:', os.path.basename(fw_fpath))
        with open(FILE_FWVER, 'w') as fout:
            fout.write(running_version)
        if os.path.basename(fw_fpath) != running_version:
            print('Update failed!')
            return False
    except Exception as e:
        print('MSP not responding. Not sure what is going on.')
        print(e)
        return False
    return True

def try_flash_msp():
    # get version burned into micro
    running_version = get_running_version()
    print('Running version on MSP430 is: {}'.format(running_version))
    fw_latest_file_version, fw_fpath = get_latest_fw_version()
    if running_version != fw_latest_file_version:
        # different. need to burn new
        retries = 3
        while retries > 0:
            if do_flash(os.path.join(FW_UPDATE_PATH, fw_fpath)):
                print('Successfully burned flash.')
                break
            print('Flash burn failed. Waiting a little while to retry...')
            cleanup_from_flash_attempt()
            time.sleep(1)
            retries -= 1

        # flash attempts complete. see if it worked
        if is_flash_up_to_date(fw_latest_file_version):
            running_version = get_running_version()
            with open(FILE_FWVER, 'w') as fout:
                fout.write(running_version)
            return True
        else:
            # FAIL
            print('Tried and tried and tried and failed to update MSP flash.')
            return False
    else:
        print('No update needed.')
        return True


if __name__ == '__main__':
    try_flash_msp()
