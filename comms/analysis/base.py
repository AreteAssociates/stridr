# Analysis base classes for the STRIDR buoy
# Arete Associates
# jhp

import os
import numpy as np
import pickle
from collections import namedtuple
from scipy.optimize import curve_fit
from math import radians

import scipy.signal

from STRIDR.comms.parameters import *

SYS_EXCEPT_BIT = int(0b10000000)
COMMS_EXCEPT_BIT = int(0b01000000)
LATCH_SET_BIT = int(0b00100000)

Signal = namedtuple('Signal', 'priority time algID components')


def lat_lon_to_xy(latlon1, latlon2):
    dx = 111111*(latlon1[0]-latlon2[0])
    dy = 111111*(latlon1[1]-latlon2[1]) * np.cos(radians(latlon1[0]))
    return np.array([dx, dy])


def xy_to_lat_lon(dxy, latlon):
    dlat = (dxy[0])/111111
    dlon = (dxy[1])/(111111*np.cos(radians(latlon[0])))
    return np.array([dlat, dlon])


def encode_dist(xy):
    signs = np.sign(xy)
    xy = abs(xy)**HEADER_LL_FACT
    if any(xy > 128):
        return np.int8([255, 255]).tobytes()
    xy = np.int8(signs*xy)
    return xy.tobytes()


def decode_dist(xy):
    if all(xy == np.int8([255, 255])):
        print('Diff too big!')
        return xy
    signs = np.sign(xy)
    xy = abs(xy)**(1.0/HEADER_LL_FACT)
    return signs*xy


def get_Battery_Status(database):
    try:
        Vout, times = database.get_data('charger_Vout')
        Vout = np.mean(Vout)
        BATTHI = 15.0
        BATTLOW = 12.5
        Vout = 16*(Vout - BATTLOW)/(BATTHI-BATTLOW)
        Vout = np.clip(Vout, 0, 16)
    except:
        Vout = 0
    try:
        Iin, times = database.get_data('charger_Iin')
        Iin = np.mean(Iin)
        CHRGHI = .5
        Iin = 16*(Iin)/CHRGHI
        Iin = np.clip(Iin, 0, 16)
    except:
        Iin = 0
    return np.uint8( int(Vout) + ( int(Iin) << 4 ) )


def get_System_Status(database, coms_exception, sys_exception):
    System_Status = b'\x00'
    try:
        wakeup_ind = database.timespan()[0]
        System_Status = np.uint8( wakeup_ind % 16 ).tobytes()
    except:
        print('db exception in get system status!!!')
        sys_exception = True

    if coms_exception:
        System_Status = (
            np.uint8([System_Status[0] | COMMS_EXCEPT_BIT])).tobytes()
    if sys_exception:
        System_Status = (
            np.uint8([System_Status[0] | SYS_EXCEPT_BIT])).tobytes()
    return System_Status


def get_Subcomponent(database):
    try:
        subcomponent = np.uint8(0)
        with open('/var/device_type', 'r') as f:
            dev_type = f.read()
        code_version = np.int8(dev_type.encode()[0] % 16)
        subcomponent += code_version << 4
        subcomponent = np.int8(subcomponent).tobytes()
    except:
        subcomponent = b'\x00'
    return subcomponent


def make_header(database, coms_exception=False, sys_exception=False):
    # the header is 16 bytes for a data message
    # system status - 1 bytes
    # P|H|V DOP - 3 bytes
    # number of satellites - 1 byte
    # battery status - 1 byte
    # subcomponent - 1 byte
    # latitude/longitude - 8 bytes ( two float32s )
    # making components in order. First, the system status
    System_Status = get_System_Status(database, coms_exception, sys_exception)
    print("systemStatus", System_Status)
    # now, the dxdy position
    # ok, enough subfunctions, now actual function. First, gathering data.
    curlat, _ = database.get_data("gps_latitude", start_time=None)
    curlon, _ = database.get_data("gps_longitude", start_time=None)
    if curlat and curlon:
        curlat = np.median(curlat)
        curlon = np.median(curlon)
        ll = np.array([curlat, curlon], dtype = 'float32')
        ll_full = ll.tobytes()
        pdop, _ = database.get_data("gps_pdop", start_time=None)
        pdop = ( 10 * np.median( pdop ) ).astype( 'uint8' )
        hdop, _ = database.get_data("gps_hdop", start_time=None)
        hdop = ( 10 * np.median( hdop ) ).astype( 'uint8' )
        vdop, _ = database.get_data("gps_vdop", start_time=None)
        vdop = ( 10 * np.median( vdop ) ).astype( 'uint8' )
        dops = np.array( [ pdop, hdop, vdop ], dtype = 'uint8' ).tobytes()
        number_of_satellites, _ = database.get_data("gps_number_of_satellites", start_time=None)
        number_of_satellites = np.median( number_of_satellites ).astype( 'uint8' ).tobytes()
    else:
        # the database has no GPS data, that's bad
        # so we'll poll the GPS for it's current position and add a known offset to latitude
        # to indicate what's happening on the message received side
        import gpsd
        gpsd.connect()
        current_gps = gpsd.get_current()
        curlat = current_gps.lat
        curlon = current_gps.lon
        
        ll = np.array([curlat + 500, curlon], dtype = 'float32' )
        ll_full = ll.tobytes()
        dops = np.array( [ 0, 10 * current_gps.position_precision()[ 0 ], 10 * current_gps.position_precision()[ 1 ] ], dtype = 'uint8' ).tobytes()
        number_of_satellites = np.array( [ current_gps.sats, ], dtype = 'uint8' ).tobytes()
    np.save(HEADER_LL_LOC, ll)
    # finally, the battery
    BatStat = get_Battery_Status(database)
    subcomponent = get_Subcomponent(database)
    print( """System_Status : {} bytes
dops : {} bytes,
number_of_satellites : {} bytes,
BatStat : {} bytes,
subcomponent : {} bytes,
ll_full : {} bytes""".format( System_Status, dops, number_of_satellites, BatStat, subcomponent, ll_full )
    )
    return b'' + System_Status + dops + number_of_satellites + BatStat + subcomponent + b'\x00' + ll_full


class Environment(object):
        # initialize with database, all param pkl file (to get most up-to-date params), and unique id
    def __init__(self, database=None, paramf='', byteID=b'\x00'):
        self.database = database
        self.byteID = byteID
        if not hasattr(self, 'params'):
            self.params = {}
        self.param_file = paramf
        with open(self.param_file, 'rb') as f:
            params = pickle.load(f)
        loaded_params = {'_'.join(
            k.split('_')[1:]): v for k, v in params.items() if self.byteID.hex() in k}
        self.params = {**loaded_params, **self.params}

    def characterize(self, start_time=None, end_time=None):
        return None

    def model(self, signal):
        return None

    def remove(self, signal, start_time=None, end_time=None):
        return signal

    def components(self):
        return None

    def struct_components(self):
        return None

    def parameters(self):
        return self.parameters

    def update_parameters(self, new_params, permanent=False):
        self.params.update(new_params)
        for k in self.params.keys():
            exec('self.'+k+'=self.params[k];')
        if permanent:
            with open(self.param_file, 'rb') as f:
                params = pickle.load(f)
            for k, v in new_params.items():
                params[self.byteID.hex() + '_'+k] = v
            with open(self.param_file, 'wb') as f:
                pickle.dump(params, f)
        return None


class Detection(object):
    def __init__(self, database=None, paramf={}, byteID=b'\x80'):
        self.database = database
        self.byteID = byteID
        if not hasattr(self, 'params'):
            self.params = {}
        self.param_file = paramf
        with open(self.param_file, 'rb') as f:
            params = pickle.load(f)
        loaded_params = {'_'.join(
            k.split('_')[1:]): v for k, v in params.items() if self.byteID.hex() in k}
        self.params = {**loaded_params, **self.params}

    def detect(self, start_time=None, end_time=None):
        return None

    def model(self, signal):
        return None

    def redetect(self, signal):
        return None

    def components(self):
        return None

    def struct_components(self):
        return None

    def match(self, signal1, signal2):
        return None

    def parameters(self):
        return self.parameters

    def update_parameters(self, new_params, permanent=False):
        self.params.update(new_params)
        for k in self.params.keys():
            exec('self.'+k+'=self.params[k];')
        if permanent:
            with open(self.param_file, 'rb') as f:
                params = pickle.load(f)
            for k, v in new_params.items():
                params[self.byteID.hex() + '_'+k] = v
            with open(self.param_file, 'wb') as f:
                pickle.dump(params, f)
        return None


class Prediction(object):
    def __init__(self, data_length=0):
        pass


class Compression(object):
    # initialize with database, all param pkl file (to get most up-to-date params), and unique id
    def __init__(self, database=None, paramf='', byteID=b'\xF0'):
        self.database = database
        self.byteID = byteID
        self.param_file = paramf
        with open(self.param_file, 'rb') as f:
            params = pickle.load(f)
        self.params = {'_'.join(
            k.split('_')[1:]): v for k, v in params.items() if self.byteID.hex() in k}

    def compress(self, key, start_time=None, end_time=None):
        return None

    def uncompress(self, signal):
        return None

    def parameters(self):
        return self.parameters

    def update_parameters(self, new_params, permanent=False):
        self.params.update(new_params)
        for k in self.params.keys():
            exec('self.'+k+'=self.params[k];')
        if permanent:
            with open(self.param_file, 'rb') as f:
                params = pickle.load(f)
            for k, v in new_params.items():
                params[self.byteID.hex() + '_'+k] = v
            with open(self.param_file, 'wb') as f:
                pickle.dump(params, f)
        return None
