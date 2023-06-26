#!/usr/bin/env python3

import serial
import struct
import atexit
import time

class msp430(object):
    
    s = None
    port = None
    speed = None
    condo_enabled = False
    rf_enabled = False
    rf_running = False
    
    def __init__(self, port='/dev/ttyS4', speed=115200):
        self.port = port
        self.speed = speed
        self.s = serial.Serial(self.port, self.speed)
        if self.s is not None:
            self.s.timeout = 1
            atexit.register(self.close)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()
           
    def __del__(self):
        self.close()

    def close(self):
        self.s.close()
 
    def get_version(self):
        cmd = b'/'
        return self._send_cmd_get_reply(cmd)

    def unlock_firmware_flash(self):
        cmd = b'Z'
        response = self._send_cmd_get_reply(cmd)
        if response == b'RST enabled': # unit is programmed
            return True
        if response == b'':            # unit is not programmed
            return True
        return False
        
    def lock_firmware_flash(self):
        cmd = b'z'
        response = self._send_cmd_get_reply(cmd)
        if response == b'RST disabled': # unit is programmed
            return True
        return False

    def send_BB_RUNNING(self):
        cmd = b'X'
        response = self._send_cmd_get_reply(cmd)
        if response[:-1] == b'BB_RUNNING ack': return True
        return False

    def send_BB_EXTEND(self):
        cmd = b'x'
        response = self._send_cmd_get_reply(cmd)
        if response[:-1] == b'5 minute extension': return True
        return False

    def send_BB_SHUTDOWN(self):
        cmd = b'.'
        return self._send_cmd_get_reply(cmd)

    def send_BB_WAKE_ME(self, wake_time=1800):
        return self._set_argument(b'W', wake_time)
        
    def enable_modem(self):
        cmd = b'S'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Modem On': return True
        return False

    def disable_modem(self):
        cmd = b's'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Modem Off': return True
        return False
        
    def enable_latch(self):
        cmd = b'L'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Latch on': return True
        return False
        
    def disable_latch(self):
        cmd = b'l'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Latch off': return True
        return False

    def get_latch_status(self):
        cmd = b'?L'
        response = self._send_cmd_get_reply(cmd)
        try:
            val = int(response.decode().split(':')[1].strip()) # return int
            if val == 0: return False
            if val == 1: return True
        except: # if there are any problems decoding the response
             pass
        return 0 # anything wrong, return 0

    def enable_condo(self):
        cmd = b'C'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Condo on':
            self.condo_enabled = True
            return True
        return False

    def read_condo(self):  # turns on condo 
        if not self.condo_enabled:
            self.enable_condo()
        cmd = b'O'
        response = self._send_cmd_get_reply(cmd)
        try:
            return int(response.decode().split(':')[1].strip()) # return int
        except: # if there are any problems decoding the response
            pass
        return 0 # anything wrong, return 0

    def disable_condo(self):
        cmd = b'c'
        response = self._send_cmd_get_reply(cmd)
        if response == b'Condo off': 
            self.condo_enabled = False
            return True
        return False

    def get_condo_status(self):
        return self.condo_enabled

    def enable_buzzer(self):
        cmd = b'B'
        response = self._send_cmd_get_reply(cmd)
        return True

    def disable_buzzer(self):
        cmd = b'b'
        response = self._send_cmd_get_reply(cmd)
        return True

    def enable_blue_led(self):
        cmd = b'U'
        response = self._send_cmd_get_reply(cmd)
        return True

    def disable_blue_led(self):
        cmd = b'u'
        response = self._send_cmd_get_reply(cmd)
        return True
    
    def enable_P5V0_SW(self):
        cmd = b'F'
        response = self._send_cmd_get_reply(cmd)
        if response == b'EN_P5V0_SW on': return True
        return False
    
    def disable_P5V0_SW(self):
        cmd = b'f'
        response = self._send_cmd_get_reply(cmd)
        if response == b'EN_P5V0_SW off': return True
        return False
    
    def enable_P3V3_SW(self):
        cmd = b'T'
        response = self._send_cmd_get_reply(cmd)
        if response == b'EN_P3V3_SW on': return True
        return False
    
    def disable_P3V3_SW(self):
        cmd = b't'
        response = self._send_cmd_get_reply(cmd)
        if response == b'EN_P3V3_SW off': return True
        return False
    


        

    def _set_argument(self, cmd, argument):
        cmd += struct.pack('<H', argument)
        response = self._send_cmd_get_reply(cmd)
        print(response)
        success = ( int(response.split()[-1]) == argument )
        return success

    def _send_cmd_get_reply(self, cmd):
        if not self.s.is_open:
            self.__init__()
        self.s.write(cmd)
        return self.s.readline()        
            
    def _retry_cmd(self, cmd, expect, retries=3):
        while retries >= 0:
            reply = self._send_cmd_get_reply(cmd) # always times out because no \r
            if type(expect) is not list:
                expect = [expect]
            for e in expect:
                if reply == e:
                    return True
            retries -= 1
        return False # never got what we expected

