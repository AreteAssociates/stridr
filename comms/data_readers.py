# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 15:49:47 2019

@author: kroman
"""
import numpy as np
import datetime
import re
import json
import traceback
from imageio import imread
import pandas as pd
import os
import pickle
from STRIDR.comms.parameters import TIME_PATTERN
try:
    import pynmea2
    parse_FLAG = True
except ImportError: 
    parse_FLAG = False
    
datetime_pattern = TIME_PATTERN; #"%Y-%m-%dT%H%M%S" #Expect this convention in all filenames
# Also, expect all filenames to fit '*_' + datetime_pattern + .ext
strip_datetime = lambda f: datetime.datetime.strptime(os.path.splitext(f)[0].split('_')[-1],
                                                      datetime_pattern).timestamp()

def read_data(file, source, pointer=True):
    # pointer: whether to just return pointer to location rather than loading into memory
    # Returns: All subfunctions return dictionary containing, among others, 'time' key in unix
    source = source.lower()
    try: 
        if 'gps' in source:
            return _read_gps(file, mode='parse')
        elif 'imu' in source:
            return _read_imu(file, pointer=pointer)
        elif 'waves' in source:
            return _read_imu(file, pointer=pointer)
        elif source == 'audio':
            return _read_audio(file, pointer=pointer)
        elif source == 'audio_fft':
            return _read_audio_fft(file,pointer=pointer)
        elif source == 'temperature':
            return _read_temperature(file)
        elif source == 'camera' or source == 'camera_ae' or source == 'camera_hdr':
            return _read_camera(file, pointer=pointer)
        elif source == 'conductivity':
            return _read_conductivity(file)
        elif source[0:4] == "fft_":
            return _read_ffts(file)
        elif source == 'sst':
            return _read_sst(file)
        elif source == 'charger':
            return _read_charger(file)
        elif pointer == False:
            return _read_pointer(file)
        else:
            raise NotImplementedError('No reader for sensor: {}'.format(source))
    except Exception as e:
        print(file + ' does not want to play nice')
        print( repr( e ) )
        return None
        
def _read_ffts(file):
  data_dict = {};
  data_dict['time'] = 0;
  data_dict['fft'] = np.load(file)
  return data_dict

def _read_imu(file, pointer=True):
    if 'wave_spectrum' in os.path.basename(file):
        time = strip_datetime(file)
        if pointer:
            with open( file, 'r' ) as wave_fid:
                line = wave_fid.readline()
                sig_wave_height = float( line.split( ':' )[ -1 ].replace( ',', '' ) )
                line = wave_fid.readline()
                peak_period = float( line.split( ':' )[ -1 ] )
            return { 'time': [ time, ],
                     'spc': [ file, ],
                     'sig_wave_height' : [ sig_wave_height, ],
                     'peak_period' : [ peak_period, ] }

        else:
            with open( file, 'r' ) as wave_fid:
                line = wave_fid.readline()
                sig_wave_height = float( line.split( ':' )[ -1 ].replace( ',', '' ) )
                line = wave_fid.readline()
                peak_period = float( line.split( ':' )[ -1 ] )
            df = pd.read_csv(file, index_col=False, skiprows = 2, sep=',' )
            df.columns = [col.strip().replace(" ", "_").replace('(', '').replace(')','').lower() if 'time' not in col else 'time'for col in df.columns]
            return_dict = df.to_dict( orient = 'list' )
            return_dict[ 'time' ] = time
            return_dict[ 'sig_wave_height' ] = [ sig_wave_height, ]
            return_dict[ 'peak_period' ] = [ peak_period, ]
            return return_dict, return_dict[ 'time' ]
    elif 'imu_summary' in os.path.basename(file):
        # adding mean and var values to the database seems problematic as of Oct. 31, 2019, so for now the read code is here, but imu_summary
        # will return None so this data stream is never seen by comms
        time = strip_datetime(file)
        with open( file, 'r' ) as json_fid:
            imu_summary = json.load( json_fid )
        imu_summary[ 'time' ] = [ time, ]
        return None
    elif 'wave_height' in os.path.basename(file):
        # wave height handled with sensor_timeseries so timestamping is only done once
        return None
    elif 'sensor_timeseries' in os.path.basename( file ):
        df = pd.read_csv( file, 
                        delimiter = ',', 
                        converters = { 0 : lambda x: datetime.datetime.strptime( x, '%Y-%m-%dT%H%M%S.%f' ).timestamp(),
                                        10 : lambda x: np.degrees( float( x ) ),
                                        11 : lambda x: np.degrees( float( x ) ) } )
        df.columns = [col.strip().replace(" ", "_").replace('(', '').replace(')','').lower() if 'time' not in col else 'time'for col in df.columns]
        wave_height = np.genfromtxt( file.replace( 'sensor_timeseries', 'wave_height' ),
                                     delimiter = ',',
                                     skip_header = 1 )
        df = df.assign( altitude = wave_height[ :, 0 ] )
        return df.to_dict( orient = 'list' )

def _read_sst(file):
    df = pd.read_csv(file, sep=',', header=None, index_col=None)
    df.columns = ['time', 'sst']
    df['time'] = df['time'].apply(lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H%M%S").timestamp())
    return df.to_dict(orient='list')

def _read_charger(file):
    df = pd.read_csv(file, sep=',', header=None, index_col=None)
    df.columns = ['time', 'Vin', 'Iin', 'Vout', 'Iout']
    df['time'] = df['time'].apply(lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H%M%S").timestamp())
    return df.to_dict(orient='list')
  
def _read_temperature(file):
    df = pd.read_csv(file, sep=',', index_col=None)
    df.columns = ['time', 'temperature']
    df['time'] = df['time'].apply(lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H%M%S.%f").timestamp())
    #df['temperature'] = df['temperature'].apply(lambda x: x/1000.)
    return df.to_dict(orient='list')

def _read_conductivity(file):
    df = pd.read_csv(file, sep=',', index_col=None)
    df.columns = ['time', 'conductivity']
    df['time'] = df['time'].apply(lambda x: datetime.datetime.strptime(x, "%Y%m%d_%H%M%S").timestamp())
    return df.to_dict(orient='list')

def _read_audio(file, pointer=True):
    data = np.fromfile(file,dtype=np.dtype('<H'),count=-1)
    time = strip_datetime(file)
    #time = re.findall('([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]+.[0-9]+)',file)
    if pointer:
        return {'audio':[file,], 'time':[time,]}
    else:
        return data,time
    
def _read_audio_fft(file, pointer=True):
    data = np.load(file)
    time = strip_datetime(file)
    if pointer:
        return {'audio_fft':[file,], 'time':[time,]}
    else:
        return data, time
    
def _read_camera( file, pointer = True ):
    # pointer: whether to just return pointer to location rather than loading into memory
    image_type = 'ae' if 'CAMERA_AE' in file else 'hdr'
    time = strip_datetime( file )
    return { image_type: [file,], 'time': [time,]} if pointer else (imread(file), time)

def _read_pointer(file):
    colname = '_'.join(file.split('_')[:-1])
    time = strip_datetime(file)
    with open(file, 'rb') as fin:
        data = pickle.load(fin)
    return data, time
    
def _read_gps( gps_data_file, mode='parse', returnHeader=False):
    """
    mode - 'parse' or 'str'
        'parse' will use pynmea2 to parse gps strings
        'str' will just separate strings, and read lat/lon/alt from gga
    keys
    ----
    'zda' - The parsed ZDA strings (timestamps)
    'gga' - The parsed GGA strings (lat-lon fixes)
    'gbs' - The parsed GBS strings
    [...]
    'latitude' - decimal latitude list
    'longitude' - decimal longitude list
    'altitude' - antenna altitude in [m]
    'time' - datetime time, the *GPS* timestamp in the GGA strings
    """
    if (mode == 'parse') & (not parse_FLAG):
        print("'parse' mode not supported. Reading as strings.")
        mode = 'str'
    with open( gps_data_file, 'r' ) as gps_fid:
        gps_data = { 'latitude' : [],
                     'longitude' : [],
                     'altitude' : [],
                     'time' : [],
                     'number_of_satellites' : [],
                     'pdop' : [],
                     'hdop' : [],
                     'vdop' : [] }
        header = ''
        most_recent_data = {}
        filedatetime = datetime.datetime.fromtimestamp(strip_datetime(gps_data_file))
        most_recent_date = datetime.date(filedatetime.year,filedatetime.month,filedatetime.day) # so can compare with other sensors
        for n, line in enumerate(gps_fid):
            if mode == 'parse': 
                try:
                    parsed_line = pynmea2.parse( line )
                    #gps_data[ parsed_line.sentence_type.lower() ].append( parsed_line )
                    if parsed_line.sentence_type.lower() in [ 'zda', ]:
                        most_recent_date = datetime.date(parsed_line.year, parsed_line.month, parsed_line.day)
                    if parsed_line.sentence_type.lower() == 'gga':
                        if (parsed_line.is_valid and ( parsed_line.gps_qual >= 1 ) ):
                            gps_data[ 'time' ].append( datetime.datetime(most_recent_date.year, 
                                                                         most_recent_date.month, 
                                                                         most_recent_date.day,
                                                                         parsed_line.timestamp.hour, 
                                                                         parsed_line.timestamp.minute, 
                                                                         parsed_line.timestamp.second).timestamp())
                            gps_data[ 'latitude' ].append( parsed_line.latitude )
                            gps_data[ 'longitude' ].append( parsed_line.longitude )
                            gps_data[ 'number_of_satellites' ].append( int( parsed_line.num_sats ) )
                            gps_data[ 'altitude' ].append( parsed_line.altitude )
                    elif parsed_line.sentence_type.lower() == 'gsa':
                        if parsed_line.is_valid:
                            gps_data[ 'pdop' ].append( float( parsed_line.pdop ) )
                            gps_data[ 'hdop' ].append( float( parsed_line.hdop ) )
                            gps_data[ 'vdop' ].append( float( parsed_line.vdop ) )
                except:
                    header += line
            # should not be using this at all from image release H on
            elif mode == 'str':
                print('*** using str parser for NMEA data; planning to delete this... ***')
                if line[0] == '$':
                    if not line[3:6].lower() in gps_data.keys():
                      gps_data[line[3:6].lower()] = [];
                      most_recent_data[line[3:6].lower()] = line[7:-1]
                    most_recent_data[line[3:6].lower()] = line[7:-1]
                    #gps_data[ line[3:6].lower() ].append( line[7:-1])
                    if line[3:6].lower() == 'zda':
                        fields = line.split(',')
                        most_recent_date = datetime.date(int(fields[4]), int(fields[3]),int(fields[2]))
                    if line[3:6].lower() == 'rmc':
                        fields = line.split(',')
                        most_recent_date = datetime.date(int('20'+fields[9][-2:]),int(fields[9][2:4]),int(fields[9][:2]))
                    if line[3:6].lower() == 'gga':
                        fields = line.split(',')
                        gps_data['time'].append(datetime.datetime(most_recent_date.year, most_recent_date.month, most_recent_date.day,
                                int(fields[1][:2]),int(fields[1][2:4]),int(fields[1][4:6])).timestamp())
                        gps_data['latitude'].append(dm_to_sd(fields[2]) if fields[3] == 'N' else -dm_to_sd(fields[2]))
                        gps_data['longitude'].append(dm_to_sd(fields[4]) if fields[5] == 'E' else -dm_to_sd(fields[4]))
                        gps_data['altitude'].append(float(fields[9]))
                        for mostrecentk, mostrecentv in most_recent_data.items():
                            gps_data[mostrecentk].append(mostrecentv)
                else:
                    header += line
            else:
                raise ValueError('Unkown mode : {}'.format(mode))
    if returnHeader:
      return gps_data, header
    return gps_data

def dm_to_sd(dm):   
    # convert lon/lat from deg minutes to signed decimal
    if not dm or dm == '0':
        return 0.
    d, m = re.match(r'^(\d+)(\d\d\.\d+)$', dm).groups()
    return float(d) + float(m) / 60

def write_data(source, data):
    # Returns filepath
    source = source.lower()
    raise NotImplementedError('need to put in filename conventions.')
    if source == 'gps':
        return _write_gps_data(file)
    elif source == 'imu':
        return _write_imu(file)
    elif source == 'camera':
        return _write_camera(file)
    else:
        raise NotImplementedError('No writer for sensor: {}'.format(source))
